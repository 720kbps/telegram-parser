import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path

import main
from telegram_parser import html_report, report
from telegram_parser.chat_loader import find_export_in_folder, load_chat
from telegram_parser.whatsapp_loader import (attachment_kind, clean_sender, find_date_order, load_whatsapp,
                                             parse_date_time, read_body)

SAMPLES = Path(__file__).parent.parent / "samples"
IPHONE_SAMPLE = SAMPLES / "WhatsApp Chat - Sam.txt"
ANDROID_SAMPLE = SAMPLES / "WhatsApp Chat with Sam.txt"
TELEGRAM_SAMPLE = SAMPLES / "sample_chat.json"
# A words file that never exists, so tests don't depend on the user's own tracked_words.txt.
NO_WORDS_FILE = Path(__file__).parent / "no_such_tracked_words.txt"


def kinds_of(messages):
    """Return the kind of every message, in order."""
    kinds = []
    for msg in messages:
        kinds.append(msg["kind"])
    return kinds


class IphoneExportTest(unittest.TestCase):
    def setUp(self):
        """Load the fake iPhone export before each test."""
        self.chat = load_whatsapp(IPHONE_SAMPLE)
        self.messages = self.chat["messages"]

    def test_chat_details(self):
        """The chat is marked as WhatsApp, named after the file, and has no calls."""
        self.assertEqual(self.chat["source"], "whatsapp")
        self.assertEqual(self.chat["name"], "Sam")
        self.assertEqual(self.chat["calls"], [])

    def test_notices_and_calls_are_skipped(self):
        """The encryption notice and the missed call aren't counted as messages."""
        self.assertEqual(len(self.messages), 11)
        self.assertEqual(self.messages[0]["text"], "hey, is this the right chat?")

    def test_media_and_deleted_kinds(self):
        """Media placeholders and deleted messages get their own kinds."""
        self.assertEqual(kinds_of(self.messages), [
            "text", "text", "text", "text", "voice_message", "video_file", "sticker",
            "photo", "voice_message", "text", "deleted",
        ])

    def test_edited_marker(self):
        """The "<This message was edited>" marker is removed and the message is flagged as edited."""
        self.assertTrue(self.messages[0]["edited"])
        self.assertNotIn("edited", self.messages[0]["text"])
        self.assertFalse(self.messages[1]["edited"])

    def test_multi_line_message(self):
        """A line without a date belongs to the message before it."""
        self.assertEqual(self.messages[2]["text"], "check this out https://example.com\nit's a link")

    def test_dates_with_seconds(self):
        """iPhone exports have seconds in their timestamps."""
        self.assertEqual(self.messages[0]["date"], datetime(2023, 1, 5, 21, 14, 3))


class AndroidExportTest(unittest.TestCase):
    def setUp(self):
        """Load the fake Android export before each test."""
        self.messages = load_whatsapp(ANDROID_SAMPLE)["messages"]

    def test_month_first_dates_and_pm(self):
        """US-style month/day dates and PM times are read correctly, also with a narrow space before PM."""
        self.assertEqual(self.messages[0]["date"], datetime(2023, 1, 5, 21, 14))
        self.assertEqual(self.messages[1]["date"], datetime(2023, 1, 5, 21, 15))
        self.assertEqual(self.messages[-1]["date"], datetime(2023, 2, 14, 18, 33))

    def test_same_messages_as_iphone(self):
        """The Android export of the same chat gives the same senders and texts."""
        iphone = load_whatsapp(IPHONE_SAMPLE)["messages"]
        self.assertEqual(len(self.messages), len(iphone))
        for android_msg, iphone_msg in zip(self.messages, iphone):
            self.assertEqual(android_msg["sender"], iphone_msg["sender"])
            self.assertEqual(android_msg["text"], iphone_msg["text"])

    def test_media_kind_is_unknown(self):
        """Android's "<Media omitted>" doesn't say what kind of media it was."""
        self.assertEqual(self.messages[4]["kind"], "media")


class DateTimeTest(unittest.TestCase):
    def test_date_order(self):
        """The date order is found from any date that only works one way."""
        self.assertEqual(find_date_order(["01/02/2023", "25/02/2023"]), "dmy")
        self.assertEqual(find_date_order(["01/02/23", "2/25/23"]), "mdy")
        self.assertEqual(find_date_order(["2023-02-25"]), "ymd")
        self.assertEqual(find_date_order(["01/02/2023", "03/04/2023"]), "dmy")

    def test_twelve_hour_clock(self):
        """12 AM is midnight, 12 PM is noon, and "p.m." with dots works too."""
        self.assertEqual(parse_date_time("5/1/23", "12:05 AM", "dmy"), datetime(2023, 1, 5, 0, 5))
        self.assertEqual(parse_date_time("5/1/23", "12:05 PM", "dmy"), datetime(2023, 1, 5, 12, 5))
        self.assertEqual(parse_date_time("5/1/23", "9:05 p.m.", "dmy"), datetime(2023, 1, 5, 21, 5))

    def test_dotted_formats(self):
        """Dates and times written with dots, like "05.01.23, 22.15", are read too."""
        self.assertEqual(parse_date_time("05.01.23", "22.15", "dmy"), datetime(2023, 1, 5, 22, 15))


class BodyAndNameTest(unittest.TestCase):
    def test_attachments_from_exports_with_media(self):
        """Attached file names tell the kind of media."""
        self.assertEqual(attachment_kind("<attached: 00000012-photo-2023-01-05-21-14-03.jpg>"), "photo")
        self.assertEqual(attachment_kind("ptt-20230105-wa0002.opus (file attached)"), "voice_message")
        self.assertEqual(attachment_kind("report.pdf (file attached)"), "file")
        self.assertEqual(attachment_kind("just text"), "")

    def test_sent_items_written_like_notices(self):
        """Video notes, view-once media, polls, locations and deleted messages count as messages; calls don't."""
        self.assertEqual(read_body("‎video note omitted")["kind"], "video_message")
        self.assertEqual(read_body("‎You received a view once message")["kind"], "media")
        self.assertEqual(read_body("‎POLL:\nPizza?\nOPTION: yes (2 votes)")["kind"], "poll")
        self.assertEqual(read_body("‎Location: https://maps.google.com/?q=1,2")["kind"], "location")
        self.assertEqual(read_body("‎This message was deleted by admin Alex.")["kind"], "deleted")
        self.assertIsNone(read_body("‎Video call. 38 min"))

    def test_typed_location_word_stays_text(self):
        """Text someone typed that starts with "Location:" is still a normal message."""
        self.assertEqual(read_body("Location: my place, 8pm")["kind"], "text")

    def test_typed_text_that_looks_like_a_notice(self):
        """A message someone typed stays a message, even if it reads like a call notice."""
        self.assertEqual(read_body("Missed voice call, sorry")["kind"], "text")
        self.assertIsNone(read_body("‎Missed voice call"))

    def test_sender_names(self):
        """Direction marks around phone numbers and the "~" before unsaved names are removed."""
        self.assertEqual(clean_sender("‪+40 712 345 678‬"), "+40 712 345 678")
        self.assertEqual(clean_sender("~ Alex"), "Alex")


class FilesTest(unittest.TestCase):
    def test_zip_export(self):
        """A .zip export is read from the _chat.txt inside and named after the zip."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "WhatsApp Chat - Sam.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("_chat.txt", IPHONE_SAMPLE.read_text(encoding="utf-8"))
                archive.writestr("00000012-PHOTO-2023-01-05.jpg", b"not really a photo")
            chat = load_whatsapp(path)
        self.assertEqual(chat["name"], "Sam")
        self.assertEqual(len(chat["messages"]), 11)

    def test_zip_without_chat(self):
        """A zip without a .txt file gives a clear error."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "photos.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("photo.jpg", b"x")
            with self.assertRaises(ValueError):
                load_whatsapp(path)

    def test_text_file_that_isnt_a_chat(self):
        """A .txt that isn't a WhatsApp export gives a clear error."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "notes.txt"
            path.write_text("shopping list\nmilk\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_whatsapp(path)

    def test_load_chat_picks_the_loader(self):
        """load_chat reads .json as Telegram and .txt as WhatsApp."""
        self.assertEqual(load_chat(TELEGRAM_SAMPLE)["source"], "telegram")
        self.assertEqual(load_chat(IPHONE_SAMPLE)["source"], "whatsapp")

    def test_export_found_in_dragged_folder(self):
        """Dragging an unzipped WhatsApp export folder finds the chat file inside."""
        with tempfile.TemporaryDirectory() as temp:
            iphone_folder = Path(temp) / "iphone"
            iphone_folder.mkdir()
            (iphone_folder / "_chat.txt").write_text("x", encoding="utf-8")
            android_folder = Path(temp) / "android"
            android_folder.mkdir()
            (android_folder / "WhatsApp Chat with Sam.txt").write_text("x", encoding="utf-8")
            empty_folder = Path(temp) / "empty"
            empty_folder.mkdir()

            self.assertEqual(find_export_in_folder(iphone_folder), iphone_folder / "_chat.txt")
            self.assertEqual(main.find_export_file(str(android_folder)), android_folder / "WhatsApp Chat with Sam.txt")
            self.assertIsNone(find_export_in_folder(empty_folder))


class WhatsappReportTest(unittest.TestCase):
    def test_sections_without_data_are_left_out(self):
        """The report skips quoted replies and calls, which WhatsApp exports don't have."""
        text = "\n".join(report.stats_lines(load_whatsapp(IPHONE_SAMPLE)))
        self.assertNotIn("Replies (quoting", text)
        self.assertNotIn("Calls:", text)
        self.assertIn("===== Media =====", text)
        self.assertIn("  Voice messages: 2", text)
        self.assertIn("Stickers: 1 sent\n  Sam: 1 sticker", text)
        self.assertIn("Double-texting", text)

    def test_android_media_is_counted_without_kinds(self):
        """Android media is counted as a whole, and no misleading sticker count is shown."""
        text = "\n".join(report.stats_lines(load_whatsapp(ANDROID_SAMPLE)))
        self.assertIn("  Media (photos, videos, voice notes, stickers…): 5", text)
        self.assertNotIn("Stickers:", text)

    def test_telegram_report_still_complete(self):
        """Telegram chats still get the replies and calls sections."""
        text = "\n".join(report.stats_lines(load_chat(TELEGRAM_SAMPLE)))
        self.assertIn("Replies (quoting a specific message):", text)
        self.assertIn("Calls: 2", text)
        self.assertIn("===== Media and calls =====", text)

    def test_wrapped_page(self):
        """The Wrapped page says WhatsApp and leaves out calls and quoted replies."""
        page = html_report.build_page(load_whatsapp(IPHONE_SAMPLE), NO_WORDS_FILE)
        self.assertIn("<title>Sam · WhatsApp wrapped</title>", page)
        self.assertIn("WhatsApp chat, wrapped", page)
        self.assertNotIn("<h3>Calls</h3>", page)
        self.assertIn("<h3>Edits</h3>", page)
        self.assertNotIn("quoted repl", page)
        self.assertIn("<h3>Voice and video notes</h3>", page)


if __name__ == "__main__":
    unittest.main()
