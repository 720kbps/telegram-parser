import unittest
from datetime import datetime
from pathlib import Path

import report
import stats
from telegram_loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_message(sender, date):
    """Build a message dict with only the fields the busiest-hour stats use."""
    return {"sender": sender, "date": datetime.fromisoformat(date)}


class BusiestHoursTest(unittest.TestCase):
    def test_counts_messages_by_hour(self):
        """Messages are counted under the hour they were sent in."""
        messages = [
            make_message("Alex", "2023-01-01T22:05:00"),
            make_message("Sam", "2023-01-02T22:59:59"),
            make_message("Alex", "2023-01-03T00:00:00"),
        ]
        counts = stats.busiest_hours(messages)
        self.assertEqual(counts[22], 2)
        self.assertEqual(counts[0], 1)
        self.assertEqual(counts[5], 0)

    def test_per_person_busiest_hour(self):
        """Each person gets their own busiest hour and its count."""
        messages = [
            make_message("Alex", "2023-01-01T09:00:00"),
            make_message("Alex", "2023-01-02T09:30:00"),
            make_message("Alex", "2023-01-02T23:30:00"),
            make_message("Sam", "2023-01-01T23:10:00"),
        ]
        result = stats.busiest_hour_per_person(messages)
        self.assertEqual(result, {"Alex": (9, 2), "Sam": (23, 1)})

    def test_per_person_tie_goes_to_earliest_hour(self):
        """When two hours are equally busy, the earlier one wins."""
        messages = [
            make_message("Alex", "2023-01-01T20:00:00"),
            make_message("Alex", "2023-01-01T07:00:00"),
        ]
        self.assertEqual(stats.busiest_hour_per_person(messages), {"Alex": (7, 1)})

    def test_sample_chat_hours(self):
        """The sample chat has 4 messages at 21:00, 3 at 09:00 and 3 at 18:00."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        counts = stats.busiest_hours(messages)
        self.assertEqual(counts[21], 4)
        self.assertEqual(counts[9], 3)
        self.assertEqual(counts[18], 3)
        self.assertEqual(sum(counts.values()), 10)


class BusiestHourLinesTest(unittest.TestCase):
    def setUp(self):
        """Build the report lines for the sample chat before each test."""
        self.lines = report.busiest_hour_lines(load_telegram(SAMPLE_PATH)["messages"])

    def test_heading_names_busiest_hour(self):
        """The first line names the busiest hour and its share of messages."""
        self.assertEqual(self.lines[0], "Busiest hour: 21:00–22:00 (40.0% of messages)")

    def test_histogram_has_24_rows(self):
        """The histogram shows every hour, including empty ones."""
        start = self.lines.index("Messages by hour:") + 1
        rows = self.lines[start:]
        self.assertEqual(len(rows), 24)
        self.assertTrue(rows[0].startswith("  00:00"))
        self.assertTrue(rows[23].startswith("  23:00"))

    def test_busiest_bar_is_full_width_and_empty_hours_have_no_bar(self):
        """The busiest hour gets the full bar and an hour with no messages gets none."""
        start = self.lines.index("Messages by hour:") + 1
        rows = self.lines[start:]
        self.assertEqual(rows[21].count("█"), report.HOUR_BAR_WIDTH)
        self.assertEqual(rows[3].count("█"), 0)
        self.assertTrue(rows[3].endswith(" 0"))

    def test_quiet_hour_still_gets_a_bar(self):
        """An hour with very few messages still shows at least one block."""
        messages = [make_message("Alex", "2023-01-01T01:00:00")]
        for minute in range(50):
            messages.append(make_message("Alex", f"2023-01-01T22:{minute:02d}:00"))
        rows = report.busiest_hour_lines(messages)[-24:]
        self.assertEqual(rows[1].count("█"), 1)

    def test_no_messages(self):
        """An empty chat doesn't crash."""
        self.assertEqual(report.busiest_hour_lines([]), ["Busiest hour: no messages"])


if __name__ == "__main__":
    unittest.main()
