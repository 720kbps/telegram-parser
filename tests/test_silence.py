import unittest
from datetime import datetime
from pathlib import Path

from telegram_parser import report
from telegram_parser import stats
from telegram_parser.loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_message(sender, date):
    """Build a message dict with only the fields the silence stat needs."""
    return {"sender": sender, "date": datetime.fromisoformat(date)}


class LongestSilencesTest(unittest.TestCase):
    def test_fewer_than_two_messages(self):
        """No messages or a single message gives no silences."""
        self.assertEqual(stats.longest_silences([]), [])
        self.assertEqual(stats.longest_silences([make_message("Alex", "2023-01-01T10:00:00")]), [])

    def test_longest_first_with_who_broke_it(self):
        """Gaps come back longest first, with start, end and the sender who broke the silence."""
        messages = [
            make_message("Alex", "2023-01-01T10:00:00"),
            make_message("Sam", "2023-01-01T10:05:00"),
            make_message("Sam", "2023-01-03T10:05:00"),
            make_message("Alex", "2023-01-03T11:05:00"),
        ]
        silences = stats.longest_silences(messages)
        self.assertEqual(len(silences), 3)
        self.assertEqual(silences[0]["seconds"], 2 * 86400)
        self.assertEqual(silences[0]["start"], datetime(2023, 1, 1, 10, 5))
        self.assertEqual(silences[0]["end"], datetime(2023, 1, 3, 10, 5))
        self.assertEqual(silences[0]["broken_by"], "Sam")
        self.assertEqual(silences[1]["seconds"], 3600)
        self.assertEqual(silences[1]["broken_by"], "Alex")
        self.assertEqual(silences[2]["seconds"], 300)

    def test_how_many_limits_the_result(self):
        """Only the requested number of gaps is returned."""
        messages = [
            make_message("Alex", "2023-01-01T10:00:00"),
            make_message("Sam", "2023-01-01T10:01:00"),
            make_message("Alex", "2023-01-01T10:03:00"),
            make_message("Sam", "2023-01-01T10:06:00"),
        ]
        silences = stats.longest_silences(messages, how_many=1)
        self.assertEqual(len(silences), 1)
        self.assertEqual(silences[0]["seconds"], 180)

    def test_sample_chat_longest_gap(self):
        """The sample chat's longest gap is the one Alex broke on Valentine's Day."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        longest = stats.longest_silences(messages)[0]
        self.assertEqual(longest["start"], datetime(2023, 1, 6, 9, 6))
        self.assertEqual(longest["end"], datetime(2023, 2, 14, 18, 30))
        self.assertEqual(longest["broken_by"], "Alex")


class SilenceReportTest(unittest.TestCase):
    def test_format_duration_days(self):
        """24 hours or more is shown as days and hours."""
        self.assertEqual(report.format_duration(86400), "1d 0h")
        self.assertEqual(report.format_duration(3 * 86400 + 4 * 3600 + 59 * 60), "3d 4h")
        self.assertEqual(report.format_duration(335 * 3600 + 8 * 60), "13d 23h")

    def test_format_duration_under_a_day_unchanged(self):
        """Durations under 24 hours keep the old format."""
        self.assertEqual(report.format_duration(42), "42s")
        self.assertEqual(report.format_duration(75), "1m 15s")
        self.assertEqual(report.format_duration(3900), "1h 5m")
        self.assertEqual(report.format_duration(86399), "23h 59m")

    def test_silence_lines(self):
        """Each silence is one numbered line with its length, dates and who broke it."""
        messages = [
            make_message("Alex", "2023-03-12T22:10:00"),
            make_message("Sam", "2023-03-16T02:15:00"),
        ]
        lines = report.silence_lines(messages)
        self.assertEqual(lines, [
            "Longest silences:",
            "  1. 3d 4h: 12 Mar 2023 22:10 → 16 Mar 2023 02:15, broken by Sam",
        ])

    def test_silence_lines_not_enough_messages(self):
        """With fewer than two messages the section says there is nothing to measure."""
        lines = report.silence_lines([make_message("Alex", "2023-03-12T22:10:00")])
        self.assertEqual(lines, ["Longest silences:", "  Not enough messages to measure."])


if __name__ == "__main__":
    unittest.main()
