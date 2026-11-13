import unittest
from datetime import datetime
from pathlib import Path

from telegram_parser import report
from telegram_parser import stats
from telegram_parser.loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_messages(*pairs):
    """Build minimal message dicts (sender and date only) from (sender, ISO date string) pairs."""
    messages = []
    for sender, stamp in pairs:
        messages.append({"sender": sender, "date": datetime.fromisoformat(stamp)})
    return messages


class DoubleTextsTest(unittest.TestCase):
    def test_empty_chat(self):
        """An empty chat has no senders to report."""
        self.assertEqual(stats.double_texts([]), {})

    def test_quick_follow_ups_are_not_double_texts(self):
        """Several messages in a row within the hour don't count."""
        messages = make_messages(
            ("Alex", "2023-03-01T10:00:00"),
            ("Alex", "2023-03-01T10:05:00"),
            ("Alex", "2023-03-01T10:59:00"),
        )
        result = stats.double_texts(messages)
        self.assertEqual(result["Alex"], {"count": 0, "longest_wait": 0, "longest_date": None})

    def test_exactly_one_hour_is_not_a_double_text(self):
        """The wait has to be longer than an hour, so exactly 1h doesn't count."""
        messages = make_messages(
            ("Alex", "2023-03-01T10:00:00"),
            ("Alex", "2023-03-01T11:00:00"),
        )
        self.assertEqual(stats.double_texts(messages)["Alex"]["count"], 0)

    def test_over_an_hour_is_a_double_text(self):
        """Texting again 1h 1m later without a reply counts once."""
        messages = make_messages(
            ("Alex", "2023-03-01T10:00:00"),
            ("Alex", "2023-03-01T11:01:00"),
        )
        result = stats.double_texts(messages)
        self.assertEqual(result["Alex"], {"count": 1, "longest_wait": 3660, "longest_date": datetime(2023, 3, 1, 11, 1)})

    def test_reply_in_between_cancels_it(self):
        """If the other person answered in between, the later message isn't a double text."""
        messages = make_messages(
            ("Alex", "2023-03-01T10:00:00"),
            ("Sam", "2023-03-01T10:30:00"),
            ("Alex", "2023-03-01T12:00:00"),
        )
        result = stats.double_texts(messages)
        self.assertEqual(result["Alex"]["count"], 0)
        self.assertEqual(result["Sam"]["count"], 0)

    def test_no_upper_limit(self):
        """Texting again the next day after being left on read still counts."""
        messages = make_messages(
            ("Alex", "2023-03-01T23:00:00"),
            ("Alex", "2023-03-03T09:00:00"),
        )
        result = stats.double_texts(messages)
        self.assertEqual(result["Alex"]["count"], 1)
        self.assertEqual(result["Alex"]["longest_wait"], 34 * 3600)

    def test_several_in_one_unanswered_stretch(self):
        """Each wait over an hour in the same unanswered stretch is its own double text."""
        messages = make_messages(
            ("Alex", "2023-03-01T10:00:00"),
            ("Alex", "2023-03-01T12:00:00"),
            ("Alex", "2023-03-01T12:10:00"),
            ("Alex", "2023-03-01T15:10:00"),
        )
        result = stats.double_texts(messages)
        self.assertEqual(result["Alex"]["count"], 2)
        self.assertEqual(result["Alex"]["longest_wait"], 3 * 3600)
        self.assertEqual(result["Alex"]["longest_date"], datetime(2023, 3, 1, 15, 10))

    def test_tie_keeps_earliest(self):
        """When two waits are equally long, the earlier one's date is kept."""
        messages = make_messages(
            ("Alex", "2023-03-01T10:00:00"),
            ("Alex", "2023-03-01T12:00:00"),
            ("Sam", "2023-03-01T12:01:00"),
            ("Alex", "2023-03-02T10:00:00"),
            ("Alex", "2023-03-02T12:00:00"),
        )
        result = stats.double_texts(messages)
        self.assertEqual(result["Alex"]["count"], 2)
        self.assertEqual(result["Alex"]["longest_date"], datetime(2023, 3, 1, 12, 0))

    def test_sample_chat(self):
        """In the sample chat only Alex double texts, the next morning after 11h 46m."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        result = stats.double_texts(messages)
        self.assertEqual(result["Alex"]["count"], 1)
        self.assertEqual(result["Alex"]["longest_wait"], 11 * 3600 + 46 * 60 + 9)
        self.assertEqual(result["Alex"]["longest_date"], datetime(2023, 1, 6, 9, 2, 11))
        self.assertEqual(result["Sam"]["count"], 0)


class DoubleTextLinesTest(unittest.TestCase):
    def test_sample_chat_lines(self):
        """The report section ranks Alex first and shows Sam with 0 times."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        self.assertEqual(report.double_text_lines(messages), [
            "Double-texting (texting again after more than 1h without a reply):",
            "  Alex: 1 time, longest wait 11h 46m before texting again (06 Jan 2023)",
            "  Sam: 0 times",
        ])

    def test_many_times_and_days(self):
        """Several double texts are written as "N times" and long waits use days."""
        messages = make_messages(
            ("Alex", "2023-03-01T10:00:00"),
            ("Alex", "2023-03-01T12:00:00"),
            ("Alex", "2023-03-04T14:00:00"),
        )
        lines = report.double_text_lines(messages)
        self.assertEqual(lines[1], "  Alex: 2 times, longest wait 3d 2h before texting again (04 Mar 2023)")

    def test_empty_chat_lines(self):
        """An empty chat says there is nothing to measure."""
        self.assertEqual(report.double_text_lines([])[1], "  No messages to measure.")


if __name__ == "__main__":
    unittest.main()
