import unittest
from pathlib import Path

from telegram_parser import report
from telegram_parser import stats
from telegram_parser.emoji_finder import find_emoji
from telegram_parser.loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_message(sender, text):
    """Build a minimal message dict (sender and text only) for a test."""
    return {"sender": sender, "text": text}


class FindEmojiTest(unittest.TestCase):
    def test_plain_text_has_none(self):
        """Ordinary text, digits and punctuation aren't emoji."""
        self.assertEqual(find_emoji("hello 123, how are you? #1"), [])

    def test_simple_emoji(self):
        """Each emoji is found once, in order."""
        self.assertEqual(find_emoji("haha 😂😂 ok 🥺"), ["😂", "😂", "🥺"])

    def test_selector_is_removed(self):
        """"❤️" (with U+FE0F) and "❤" count as the same emoji."""
        self.assertEqual(find_emoji("❤️ and ❤"), ["❤", "❤"])

    def test_symbol_only_counts_with_selector(self):
        """An arrow is plain text, but becomes an emoji when followed by U+FE0F."""
        self.assertEqual(find_emoji("a ↔ b"), [])
        self.assertEqual(find_emoji("a ↔️ b"), ["↔"])

    def test_skin_tone_stays_together(self):
        """A skin tone is part of the emoji before it, not a separate one."""
        self.assertEqual(find_emoji("👍🏽"), ["👍🏽"])

    def test_joined_emoji_stays_together(self):
        """Emoji joined with zero-width joiners, like a family, count as one."""
        family = "👨‍👩‍👧"
        self.assertEqual(find_emoji(f"my {family}!"), [family])

    def test_flag(self):
        """Two regional indicators make one flag."""
        self.assertEqual(find_emoji("🇷🇴 🇬🇧"), ["🇷🇴", "🇬🇧"])

    def test_keycap(self):
        """A digit with the keycap mark is an emoji, a plain digit isn't."""
        self.assertEqual(find_emoji("1️⃣ then 2"), ["1⃣"])

    def test_empty_text(self):
        """Empty text has no emoji."""
        self.assertEqual(find_emoji(""), [])


class EmojiCountsTest(unittest.TestCase):
    def test_counts_per_person(self):
        """Emoji are counted overall and per person, and messages with emoji are counted once each."""
        messages = [
            make_message("Alex", "lol 😂😂"),
            make_message("Alex", "no emoji here"),
            make_message("Sam", "❤️ 😂"),
            make_message("Sam", ""),
        ]
        counts = stats.emoji_counts(messages)
        self.assertEqual(counts["total"], 4)
        self.assertEqual(counts["overall"], {"😂": 3, "❤": 1})
        self.assertEqual(counts["per_person"]["Alex"], {"😂": 2})
        self.assertEqual(counts["messages_with_emoji"], {"Alex": 1, "Sam": 1})

    def test_person_without_emoji_is_listed(self):
        """Someone who never uses emoji still appears, with an empty counter."""
        counts = stats.emoji_counts([make_message("Alex", "hi")])
        self.assertEqual(counts["per_person"], {"Alex": {}})
        self.assertEqual(counts["total"], 0)

    def test_sample_chat(self):
        """The sample chat has 😄 from Sam and 😂😂 from Alex."""
        counts = stats.emoji_counts(load_telegram(SAMPLE_PATH)["messages"])
        self.assertEqual(counts["overall"], {"😂": 2, "😄": 1})


class EmojiLinesTest(unittest.TestCase):
    def test_sample_chat_lines(self):
        """The report shows the top emoji and each person's favourites, most emoji first."""
        lines = report.emoji_lines(load_telegram(SAMPLE_PATH)["messages"])
        self.assertEqual(lines, [
            "Emoji in messages: 3 used",
            "  Top emoji: 😂 2, 😄 1",
            "  Alex: 2 emoji, in 25.0% of their messages, favourites 😂 2",
            "  Sam: 1 emoji, in 16.7% of their messages, favourites 😄 1",
        ])

    def test_no_emoji(self):
        """A chat without emoji just says 0."""
        self.assertEqual(report.emoji_lines([make_message("Alex", "hi")]), ["Emoji in messages: 0 used"])

    def test_person_with_no_emoji(self):
        """A person who never used emoji gets a "no emoji" line."""
        messages = [make_message("Alex", "😂"), make_message("Sam", "hi")]
        self.assertIn("  Sam: no emoji", report.emoji_lines(messages))


if __name__ == "__main__":
    unittest.main()
