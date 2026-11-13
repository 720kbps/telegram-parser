import unittest
from datetime import date, datetime
from pathlib import Path

import report
import stats
from telegram_loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_messages(*stamps):
    """Build minimal message dicts (sender and date only) from ISO date strings."""
    messages = []
    for stamp in stamps:
        messages.append({"sender": "Alex", "date": datetime.fromisoformat(stamp)})
    return messages


class LongestStreakTest(unittest.TestCase):
    def test_single_day(self):
        """A chat on one day has a one-day streak starting and ending that day."""
        messages = make_messages("2023-03-01T09:00:00", "2023-03-01T23:59:00")
        streak = stats.longest_streak(messages)
        self.assertEqual(streak, {"days": 1, "start": date(2023, 3, 1), "end": date(2023, 3, 1)})

    def test_gap_breaks_streak(self):
        """A day without messages ends a streak, and the longer run wins."""
        messages = make_messages(
            "2023-03-01T10:00:00",
            "2023-03-02T10:00:00",
            "2023-03-04T10:00:00",
            "2023-03-05T10:00:00",
            "2023-03-06T10:00:00",
        )
        streak = stats.longest_streak(messages)
        self.assertEqual(streak, {"days": 3, "start": date(2023, 3, 4), "end": date(2023, 3, 6)})

    def test_tie_keeps_earliest(self):
        """When two streaks are equally long, the earlier one is returned."""
        messages = make_messages(
            "2023-03-01T10:00:00",
            "2023-03-02T10:00:00",
            "2023-03-10T10:00:00",
            "2023-03-11T10:00:00",
        )
        streak = stats.longest_streak(messages)
        self.assertEqual(streak, {"days": 2, "start": date(2023, 3, 1), "end": date(2023, 3, 2)})

    def test_crosses_midnight_and_month(self):
        """Late-night and early-morning messages on neighbouring days across a month end form a streak."""
        messages = make_messages("2023-01-31T23:59:00", "2023-02-01T00:01:00")
        streak = stats.longest_streak(messages)
        self.assertEqual(streak["days"], 2)

    def test_empty_chat(self):
        """An empty chat has no streak."""
        self.assertEqual(stats.longest_streak([]), {"days": 0, "start": None, "end": None})


class DaysTalkedTest(unittest.TestCase):
    def test_counts_distinct_days_and_span(self):
        """Several messages on one day count once, and the span includes both ends."""
        messages = make_messages(
            "2023-03-01T10:00:00",
            "2023-03-01T11:00:00",
            "2023-03-05T10:00:00",
        )
        self.assertEqual(stats.days_talked(messages), {"talked": 2, "total": 5})

    def test_single_day(self):
        """A chat on one day talked on 1 of 1 days."""
        messages = make_messages("2023-03-01T10:00:00")
        self.assertEqual(stats.days_talked(messages), {"talked": 1, "total": 1})

    def test_empty_chat(self):
        """An empty chat talked on 0 of 0 days."""
        self.assertEqual(stats.days_talked([]), {"talked": 0, "total": 0})


class SampleChatStreakTest(unittest.TestCase):
    def setUp(self):
        """Load the fake sample chat before each test."""
        self.messages = load_telegram(SAMPLE_PATH)["messages"]

    def test_longest_streak(self):
        """The sample chat's longest streak is 05 Jan to 06 Jan 2023."""
        streak = stats.longest_streak(self.messages)
        self.assertEqual(streak, {"days": 2, "start": date(2023, 1, 5), "end": date(2023, 1, 6)})

    def test_days_talked(self):
        """The sample chat has messages on 3 of 41 days."""
        self.assertEqual(stats.days_talked(self.messages), {"talked": 3, "total": 41})

    def test_streak_lines(self):
        """The streak section reads as expected for the sample chat."""
        lines = report.streak_lines(self.messages)
        self.assertEqual(lines, [
            "Streaks:",
            "  Longest streak: 2 days in a row (05 Jan 2023 – 06 Jan 2023)",
            "  Talked on 3 of 41 days (7.3%)",
        ])


class StreakLinesTest(unittest.TestCase):
    def test_single_day_uses_singular(self):
        """A one-day streak says "1 day", not "1 days"."""
        lines = report.streak_lines(make_messages("2023-03-01T10:00:00"))
        self.assertEqual(lines[1], "  Longest streak: 1 day in a row (01 Mar 2023 – 01 Mar 2023)")
        self.assertEqual(lines[2], "  Talked on 1 of 1 days (100.0%)")

    def test_empty_chat(self):
        """An empty chat shows a note instead of dividing by zero."""
        self.assertEqual(report.streak_lines([]), ["Streaks:", "  No messages to measure."])


if __name__ == "__main__":
    unittest.main()
