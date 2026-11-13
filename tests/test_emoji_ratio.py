import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import report
import stats
from telegram_loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_message(sender, text, when=datetime(2023, 1, 1, 12, 0)):
    """Build a minimal message dict (sender, text and date) for a test."""
    return {"sender": sender, "text": text, "date": when}


def make_day(day, count, with_emoji, sender="Alex"):
    """Build `count` messages on one day, the first `with_emoji` of them holding one emoji each."""
    messages = []
    start = datetime(day.year, day.month, day.day, 10, 0)
    for i in range(count):
        text = "ok 😄" if i < with_emoji else "ok"
        messages.append(make_message(sender, text, start + timedelta(minutes=i)))
    return messages


def days_of(items):
    """Return just the dates of a list of emoji_heavy_days items."""
    result = []
    for item in items:
        result.append(item["day"])
    return result


class EmojiRatioTest(unittest.TestCase):
    def test_counts_overall_and_per_person(self):
        """Emoji and messages are added up overall and per person, and every emoji counts, not just one per message."""
        messages = [
            make_message("Alex", "haha 😂😂"),
            make_message("Alex", "no emoji here"),
            make_message("Sam", "🥺"),
            make_message("Sam", "fine"),
            make_message("Sam", "ok"),
        ]
        result = stats.emoji_ratio(messages)
        self.assertEqual(result["overall"], {"emoji": 3, "messages": 5})
        self.assertEqual(result["per_person"]["Alex"], {"emoji": 2, "messages": 2})
        self.assertEqual(result["per_person"]["Sam"], {"emoji": 1, "messages": 3})

    def test_person_without_emoji_is_listed(self):
        """Someone who never types an emoji still shows up with 0."""
        result = stats.emoji_ratio([make_message("Alex", "😄"), make_message("Sam", "hi")])
        self.assertEqual(result["per_person"]["Sam"], {"emoji": 0, "messages": 1})

    def test_empty_chat(self):
        """A chat with no messages has zero totals and nobody in it."""
        result = stats.emoji_ratio([])
        self.assertEqual(result, {"overall": {"emoji": 0, "messages": 0}, "per_person": {}})


class EmojiDaysTest(unittest.TestCase):
    def test_minimum_is_fifty(self):
        """The minimum number of messages per day is a module-level constant of 50."""
        self.assertEqual(stats.MIN_MESSAGES_PER_DAY, 50)

    def test_small_days_are_ignored(self):
        """Days under the minimum can't be the heaviest when busier days exist."""
        messages = (
            make_day(date(2023, 1, 1), 2, 0)
            + make_day(date(2023, 1, 2), 50, 10)  # exactly the minimum, so it counts
            + make_day(date(2023, 1, 3), 2, 2)    # tiny and full of emoji: would be heaviest by accident
            + make_day(date(2023, 1, 4), 60, 3)
        )
        result = stats.emoji_heavy_days(messages)
        self.assertEqual(days_of(result), [date(2023, 1, 2), date(2023, 1, 4)])
        self.assertEqual(result[0], {"day": date(2023, 1, 2), "emoji": 10, "messages": 50})

    def test_falls_back_to_every_day(self):
        """If no day reaches the minimum, every day is used."""
        messages = make_day(date(2023, 1, 1), 4, 1) + make_day(date(2023, 1, 2), 3, 3) + make_day(date(2023, 1, 3), 5, 0)
        result = stats.emoji_heavy_days(messages)
        self.assertEqual(days_of(result), [date(2023, 1, 2), date(2023, 1, 1), date(2023, 1, 3)])

    def test_ties_keep_earlier_day(self):
        """Days with the same emoji per message are listed earliest first."""
        # Given newest first on purpose, to check the order comes from the dates and not the input.
        messages = (
            make_day(date(2023, 3, 1), 100, 20)
            + make_day(date(2023, 2, 1), 50, 10)
            + make_day(date(2023, 1, 1), 60, 12)
        )
        result = stats.emoji_heavy_days(messages)
        self.assertEqual(days_of(result), [date(2023, 1, 1), date(2023, 2, 1), date(2023, 3, 1)])

    def test_returns_at_most_how_many(self):
        """Only the top `how_many` days are returned."""
        messages = []
        for number in range(1, 6):
            messages += make_day(date(2023, 1, number), 50, number)
        result = stats.emoji_heavy_days(messages)
        self.assertEqual(days_of(result), [date(2023, 1, 5), date(2023, 1, 4), date(2023, 1, 3)])
        self.assertEqual(len(stats.emoji_heavy_days(messages, how_many=1)), 1)

    def test_groups_by_calendar_day(self):
        """Messages at different times on the same day are counted together."""
        messages = [
            make_message("Alex", "😄", datetime(2023, 1, 1, 0, 1)),
            make_message("Sam", "hi", datetime(2023, 1, 1, 23, 59)),
        ]
        result = stats.emoji_heavy_days(messages)
        self.assertEqual(result, [{"day": date(2023, 1, 1), "emoji": 1, "messages": 2}])

    def test_empty_chat(self):
        """A chat with no messages has no days to list."""
        self.assertEqual(stats.emoji_heavy_days([]), [])


class QuietestDaysTest(unittest.TestCase):
    def test_fewest_messages_first(self):
        """The days with the fewest messages come first."""
        messages = make_day(date(2023, 1, 1), 5, 0) + make_day(date(2023, 1, 2), 1, 0) + make_day(date(2023, 1, 3), 3, 0)
        result = stats.quietest_days(messages)
        self.assertEqual(result, [(date(2023, 1, 2), 1), (date(2023, 1, 3), 3), (date(2023, 1, 1), 5)])

    def test_days_without_messages_are_skipped(self):
        """A day with no messages at all isn't listed, only days you talked."""
        messages = make_day(date(2023, 1, 1), 2, 0) + make_day(date(2023, 1, 10), 4, 0)
        self.assertEqual(stats.quietest_days(messages), [(date(2023, 1, 1), 2), (date(2023, 1, 10), 4)])

    def test_ties_keep_earlier_day(self):
        """Days with the same number of messages are listed earliest first."""
        messages = make_day(date(2023, 3, 1), 2, 0) + make_day(date(2023, 1, 1), 2, 0)
        self.assertEqual(stats.quietest_days(messages), [(date(2023, 1, 1), 2), (date(2023, 3, 1), 2)])

    def test_how_many(self):
        """Only the quietest `how_many` days are returned."""
        messages = []
        for number in range(1, 9):
            messages += make_day(date(2023, 1, number), number, 0)
        self.assertEqual(len(stats.quietest_days(messages)), 5)
        self.assertEqual(stats.quietest_days(messages, how_many=1), [(date(2023, 1, 1), 1)])

    def test_sample_chat_lines(self):
        """The sample chat's quietest days are its two 3-message days, then the 4-message one."""
        lines = report.quietest_days_lines(load_telegram(SAMPLE_PATH)["messages"])
        self.assertEqual(lines, [
            "Quietest days (fewest messages, not counting days with none):",
            "  06 Jan 2023: 3 messages",
            "  14 Feb 2023: 3 messages",
            "  05 Jan 2023: 4 messages",
        ])

    def test_one_message_and_empty_chat(self):
        """A single message is written as "1 message", and an empty chat says there's nothing to measure."""
        lines = report.quietest_days_lines(make_day(date(2023, 1, 1), 1, 0))
        self.assertEqual(lines[1], "  01 Jan 2023: 1 message")
        self.assertEqual(report.quietest_days_lines([])[1], "  No messages to measure.")


class EmojiRatioLinesTest(unittest.TestCase):
    def test_people_ordered_by_ratio(self):
        """People are listed by emoji per 100 messages, highest first, even if they sent fewer messages."""
        messages = [make_message("Sam", "hi"), make_message("Sam", "😄"), make_message("Alex", "😄😄")]
        lines = report.emoji_ratio_lines(messages)
        self.assertEqual(lines[0], "Emoji per 100 messages: 100.0")
        self.assertEqual(lines[1:3], ["  Alex: 200.0", "  Sam: 50.0"])

    def test_busy_days_header_and_lines(self):
        """With busy days, the header mentions the minimum, and heavy days show emoji per message."""
        messages = make_day(date(2023, 1, 5), 200, 120) + make_day(date(2023, 2, 14), 300, 0)
        lines = report.emoji_ratio_lines(messages)
        self.assertIn("Most emoji-heavy days (days with 50+ messages):", lines)
        self.assertIn("  05 Jan 2023: 120 emoji in 200 messages (0.6 per message)", lines)
        self.assertNotIn("Driest", "\n".join(lines))

    def test_heavy_days_skip_days_without_emoji(self):
        """A day with no emoji isn't listed as emoji-heavy."""
        messages = make_day(date(2023, 1, 5), 50, 5) + make_day(date(2023, 1, 6), 50, 0)
        lines = report.emoji_ratio_lines(messages)
        heavy = lines[lines.index("Most emoji-heavy days (days with 50+ messages):") + 1:]
        self.assertEqual(heavy, ["  05 Jan 2023: 5 emoji in 50 messages (0.1 per message)"])

    def test_emoji_only_on_small_days(self):
        """If the only emoji are on days under the minimum, the heavy list says so."""
        messages = make_day(date(2023, 1, 5), 2, 2) + make_day(date(2023, 1, 6), 50, 0)
        lines = report.emoji_ratio_lines(messages)
        self.assertEqual(lines[-1], "  No day with enough messages had any emoji.")

    def test_no_emoji(self):
        """A chat without emoji shows 0.0 for everyone and skips the day lists."""
        lines = report.emoji_ratio_lines([make_message("Alex", "hi"), make_message("Sam", "hey")])
        self.assertEqual(lines, [
            "Emoji per 100 messages: 0.0",
            "  Alex: 0.0",
            "  Sam: 0.0",
            "  No emoji typed at all, so there are no emoji-heavy days.",
        ])

    def test_empty_chat(self):
        """A chat with no messages gets a single line instead of an error."""
        self.assertEqual(report.emoji_ratio_lines([]), ["Emoji per 100 messages: no messages"])

    def test_sample_chat(self):
        """The sample chat has 3 emoji in 10 messages and no day with 50 messages, so every day is used."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        self.assertEqual(report.emoji_ratio_lines(messages), [
            "Emoji per 100 messages: 30.0",
            "  Alex: 50.0",
            "  Sam: 16.7",
            "Most emoji-heavy days (all days, since none had 50+ messages):",
            "  05 Jan 2023: 3 emoji in 4 messages (0.8 per message)",
        ])


if __name__ == "__main__":
    unittest.main()
