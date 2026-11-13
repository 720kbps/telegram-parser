import unittest
from datetime import date, datetime
from pathlib import Path

import report
import stats
from telegram_loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"
DAY = date(2023, 3, 1)


def make_message(sender, text, kind="text", date="2023-03-01T10:00:00"):
    """Build a loader-style message dict for a test."""
    return {
        "platform": "telegram",
        "sender": sender,
        "date": datetime.fromisoformat(date),
        "text": text,
        "kind": kind,
        "duration": 0,
        "sticker_emoji": "",
    }


class DaySummaryTest(unittest.TestCase):
    def test_only_that_day_is_counted(self):
        """Messages from other days are left out of the summary."""
        messages = [
            make_message("Alex", "hello there"),
            make_message("Sam", "other day", date="2023-03-02T10:00:00"),
        ]
        summary = stats.day_summary(messages, DAY)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["per_person"], [("Alex", 1)])

    def test_peak_hour(self):
        """The hour with the most messages that day is the peak."""
        messages = [
            make_message("Alex", "a", date="2023-03-01T08:10:00"),
            make_message("Sam", "b", date="2023-03-01T22:05:00"),
            make_message("Alex", "c", date="2023-03-01T22:40:00"),
        ]
        self.assertEqual(stats.day_summary(messages, DAY)["peak_hour"], 22)

    def test_words_need_five_letters(self):
        """Only words of 5 or more letters count, with diacritics flattened."""
        messages = [
            make_message("Alex", "si ok the mâine mâine"),
            make_message("Sam", "maine pizza pizza ok ok ok"),
            make_message("Alex", "pizza seara"),
        ]
        words = stats.day_summary(messages, DAY)["words"]
        self.assertEqual(words, ["maine", "pizza", "seara"])

    def test_links_are_not_words(self):
        """Links don't turn into words like "https" or "example"."""
        messages = [make_message("Alex", "https://example.com/abcdef")]
        self.assertEqual(stats.day_summary(messages, DAY)["words"], [])

    def test_top_three_emoji(self):
        """Only the 3 most used emoji are kept, most used first."""
        messages = [
            make_message("Alex", "😂😂😂 ❤️❤️ 🔥🔥"),
            make_message("Sam", "😄 ❤"),
        ]
        self.assertEqual(stats.day_summary(messages, DAY)["emoji"], ["😂", "❤", "🔥"])

    def test_empty_day(self):
        """A day with no messages gives an empty summary."""
        summary = stats.day_summary([make_message("Alex", "hi")], date(2020, 1, 1))
        self.assertEqual(summary["total"], 0)
        self.assertIsNone(summary["peak_hour"])

    def test_messages_on_days(self):
        """Messages are grouped by the requested days, and other days are ignored."""
        messages = [
            make_message("Alex", "a"),
            make_message("Sam", "b", date="2023-03-02T10:00:00"),
            make_message("Sam", "c", date="2023-03-05T10:00:00"),
        ]
        grouped = stats.messages_on_days(messages, [DAY, date(2023, 3, 2)])
        self.assertEqual(len(grouped[DAY]), 1)
        self.assertEqual(grouped[date(2023, 3, 2)][0]["text"], "b")
        self.assertNotIn(date(2023, 3, 5), grouped)


class DayDescriptionTest(unittest.TestCase):
    def test_full_description(self):
        """Every part is shown, in order, on one line separated by " · "."""
        messages = [
            make_message("Sam", "salut, ce faci? 😄", date="2023-03-01T21:00:00"),
            make_message("Sam", "", kind="voice_message", date="2023-03-01T21:05:00"),
            make_message("Alex", "", kind="voice_message", date="2023-03-01T21:10:00"),
            make_message("Sam", "", kind="sticker", date="2023-03-01T09:00:00"),
        ]
        line = report.day_description(messages, DAY)
        expected = "Sam 75% · Alex 25% · peak 21:00 · 2 voice messages · 1 sticker · words: salut · emoji: 😄"
        self.assertEqual(line, expected)

    def test_empty_parts_are_left_out(self):
        """A day without media, long words or emoji only shows the shares and peak hour."""
        messages = [make_message("Alex", "ok"), make_message("Sam", "da")]
        self.assertEqual(report.day_description(messages, DAY), "Alex 50% · Sam 50% · peak 10:00")

    def test_singular_and_plural(self):
        """Media counts use the singular for 1 and the plural otherwise."""
        messages = [
            make_message("Alex", "", kind="photo"),
            make_message("Alex", "", kind="photo"),
            make_message("Alex", "", kind="video_message"),
            make_message("Alex", "", kind="animation"),
        ]
        line = report.day_description(messages, DAY)
        self.assertIn("2 photos", line)
        self.assertIn("1 round video", line)
        self.assertIn("1 GIF", line)
        self.assertNotIn("1 round videos", line)

    def test_files_are_not_listed(self):
        """Plain files aren't a notable media kind, so they don't appear."""
        line = report.day_description([make_message("Alex", "", kind="file")], DAY)
        self.assertEqual(line, "Alex 100% · peak 10:00")


class SampleChatTopDaysTest(unittest.TestCase):
    def test_sample_top_days_lines(self):
        """The sample chat's busiest days each get a description indented by 6 spaces."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        expected = [
            "Busiest days:",
            "  05 Jan 2023: 4 messages",
            "      Alex 50% · Sam 50% · peak 21:00 · words: right, check · emoji: 😂 😄",
            "  06 Jan 2023: 3 messages",
            "      Sam 67% · Alex 33% · peak 09:00 · 1 voice message · 1 round video · 1 sticker",
            "  14 Feb 2023: 3 messages",
            "      Sam 67% · Alex 33% · peak 18:00 · 1 voice message · 1 photo",
        ]
        self.assertEqual(report.top_days_lines(messages), expected)


if __name__ == "__main__":
    unittest.main()
