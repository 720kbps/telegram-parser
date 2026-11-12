import unittest
from datetime import datetime
from pathlib import Path

import report
from telegram_loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_message(sender, text, kind="text", date="2023-01-01T10:00:00"):
    """Build a loader-style message dict for a test."""
    return {
        "platform": "telegram",
        "sender": sender,
        "date": datetime.fromisoformat(date),
        "text": text,
        "kind": kind,
        "duration": 0,
    }


class MessageListTest(unittest.TestCase):
    def test_text_message_format(self):
        """A text message is shown as "Sender: text"."""
        line = report.format_message(make_message("Alex", "hello"))
        self.assertEqual(line, "Alex: hello")

    def test_media_without_text(self):
        """A media message with no caption shows only its kind."""
        line = report.format_message(make_message("Sam", "", kind="voice_message"))
        self.assertEqual(line, "Sam: [voice message]")

    def test_media_with_caption(self):
        """A photo with a caption shows the kind and the caption."""
        line = report.format_message(make_message("Alex", "look", kind="photo"))
        self.assertEqual(line, "Alex: [photo] look")

    def test_multiline_message_is_indented(self):
        """Extra lines of a multi-line message are indented under the sender."""
        line = report.format_message(make_message("Alex", "one\ntwo"))
        self.assertEqual(line, "Alex: one\n    two")

    def test_messages_are_sorted_by_date(self):
        """Messages come out oldest first even if the input is out of order."""
        messages = [
            make_message("Sam", "second", date="2023-01-02T10:00:00"),
            make_message("Alex", "first", date="2023-01-01T10:00:00"),
        ]
        self.assertEqual(report.message_lines(messages), ["Alex: first", "Sam: second"])

    def test_sample_chat_list(self):
        """The sample chat gives one line per message, starting with the first one."""
        lines = report.message_lines(load_telegram(SAMPLE_PATH))
        self.assertEqual(len(lines), 10)
        self.assertEqual(lines[0], "Alex: hey, is this the right chat?")


class StatsReportTest(unittest.TestCase):
    def test_report_has_every_section(self):
        """The statistics report includes each section heading."""
        text = "\n".join(report.stats_lines(load_telegram(SAMPLE_PATH)))
        for heading in ["First message:", "Total messages: 10", "Lost information", "Busiest days:", "Messages per month:"]:
            self.assertIn(heading, text)

    def test_format_duration(self):
        """Durations are shown in the largest sensible units."""
        self.assertEqual(report.format_duration(42), "42s")
        self.assertEqual(report.format_duration(75), "1m 15s")
        self.assertEqual(report.format_duration(3900), "1h 5m")


if __name__ == "__main__":
    unittest.main()
