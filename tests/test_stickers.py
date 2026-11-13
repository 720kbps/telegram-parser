import unittest
from collections import Counter
from pathlib import Path

from telegram_parser import report
from telegram_parser import stats
from telegram_parser.loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def sticker(sender, emoji):
    """Build a minimal sticker message dict."""
    return {"sender": sender, "kind": "sticker", "sticker_emoji": emoji}


def text(sender):
    """Build a minimal text message dict, which should never count as a sticker."""
    return {"sender": sender, "kind": "text", "sticker_emoji": ""}


class StickerEmojiCountsTest(unittest.TestCase):
    def test_no_stickers(self):
        """A chat without stickers gives empty counters and zero totals."""
        result = stats.sticker_emoji_counts([text("Alex"), text("Sam")])
        self.assertEqual(result, {"overall": Counter(), "per_person": {}, "total": 0, "without_emoji": 0})

    def test_counts_overall_and_per_person(self):
        """Stickers are counted overall and per sender by their emoji."""
        messages = [sticker("Alex", "😂"), sticker("Sam", "😂"), sticker("Alex", "❤")]
        result = stats.sticker_emoji_counts(messages)
        self.assertEqual(result["overall"], Counter({"😂": 2, "❤": 1}))
        self.assertEqual(result["per_person"], {"Alex": Counter({"😂": 1, "❤": 1}), "Sam": Counter({"😂": 1})})
        self.assertEqual(result["total"], 3)

    def test_empty_emoji_goes_to_without_emoji(self):
        """Stickers with an empty emoji are counted in without_emoji, not in the counters."""
        messages = [sticker("Alex", ""), sticker("Alex", "👍"), sticker("Sam", "")]
        result = stats.sticker_emoji_counts(messages)
        self.assertEqual(result["overall"], Counter({"👍": 1}))
        self.assertEqual(result["per_person"], {"Alex": Counter({"👍": 1}), "Sam": Counter()})
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["without_emoji"], 2)

    def test_ignores_other_kinds(self):
        """Messages that are not stickers are ignored, even if they carry an emoji."""
        photo = {"sender": "Alex", "kind": "photo", "sticker_emoji": "😂"}
        result = stats.sticker_emoji_counts([photo, text("Sam"), sticker("Sam", "🥺")])
        self.assertEqual(result["overall"], Counter({"🥺": 1}))
        self.assertEqual(list(result["per_person"]), ["Sam"])
        self.assertEqual(result["total"], 1)

    def test_stickers_per_person_includes_empty_emoji(self):
        """stickers_per_person counts every sticker, including ones without an emoji."""
        messages = [sticker("Alex", ""), sticker("Alex", "😂"), text("Alex"), sticker("Sam", "")]
        self.assertEqual(stats.stickers_per_person(messages), Counter({"Alex": 2, "Sam": 1}))


class StickerLinesTest(unittest.TestCase):
    def test_no_stickers(self):
        """With no stickers the section is a single line."""
        self.assertEqual(report.sticker_lines([text("Alex")]), ["Stickers: 0 sent"])

    def test_full_report(self):
        """The report shows the top emoji, each person's favourite and the stickers without emoji."""
        messages = [
            sticker("Sam", "❤"),
            sticker("Alex", "😂"),
            sticker("Alex", "😂"),
            sticker("Alex", "❤"),
            sticker("Alex", ""),
            text("Sam"),
        ]
        self.assertEqual(report.sticker_lines(messages), [
            "Stickers: 5 sent",
            "  Top sticker emoji: ❤ 2, 😂 2",
            "  Alex: 4 stickers, favourite 😂 (2)",
            "  Sam: 1 sticker, favourite ❤ (1)",
            "  1 sticker has no emoji",
        ])

    def test_top_five_only(self):
        """Only the five most used emoji are listed overall."""
        messages = []
        for emoji, times in [("a", 6), ("b", 5), ("c", 4), ("d", 3), ("e", 2), ("f", 1)]:
            for _ in range(times):
                messages.append(sticker("Alex", emoji))
        lines = report.sticker_lines(messages)
        self.assertEqual(lines[1], "  Top sticker emoji: a 6, b 5, c 4, d 3, e 2")

    def test_favourite_tie_goes_to_first_used(self):
        """When two emoji are used equally often, the one used first is the favourite."""
        messages = [sticker("Alex", "🥺"), sticker("Alex", "😭"), sticker("Alex", "😭"), sticker("Alex", "🥺")]
        lines = report.sticker_lines(messages)
        self.assertEqual(lines[2], "  Alex: 4 stickers, favourite 🥺 (2)")

    def test_people_tie_sorted_by_name(self):
        """People with the same sticker count are listed by name."""
        messages = [sticker("Sam", "👍"), sticker("Alex", "👍")]
        lines = report.sticker_lines(messages)
        self.assertEqual(lines[2:], ["  Alex: 1 sticker, favourite 👍 (1)", "  Sam: 1 sticker, favourite 👍 (1)"])

    def test_only_empty_emoji(self):
        """If no sticker has an emoji, the top line is skipped and each person says so."""
        messages = [sticker("Alex", ""), sticker("Alex", "")]
        self.assertEqual(report.sticker_lines(messages), [
            "Stickers: 2 sent",
            "  Alex: 2 stickers, none with an emoji",
            "  2 stickers have no emoji",
        ])


class SampleChatStickerTest(unittest.TestCase):
    def test_sample_chat(self):
        """The sample chat has one sticker, sent by Sam with 😂."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        self.assertEqual(report.sticker_lines(messages), [
            "Stickers: 1 sent",
            "  Top sticker emoji: 😂 1",
            "  Sam: 1 sticker, favourite 😂 (1)",
        ])


if __name__ == "__main__":
    unittest.main()
