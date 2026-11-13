import unittest
from datetime import datetime, timedelta

import report
import stats

START = datetime(2023, 1, 1, 10, 0)


def make_messages(rows):
    """Build messages from (sender, text) pairs, one minute apart, oldest first."""
    messages = []
    for number, (sender, text) in enumerate(rows):
        messages.append({"sender": sender, "date": START + timedelta(minutes=number), "text": text})
    return messages


class NormalizeMessageTest(unittest.TestCase):
    def test_case_and_diacritics(self):
        """Case and Romanian diacritics, in both ș/ț forms, are flattened."""
        self.assertEqual(stats.normalize_message("Noapte Bună"), "noapte buna")
        self.assertEqual(stats.normalize_message("ȘI ţie"), "si tie")
        self.assertEqual(stats.normalize_message("şi ție"), "si tie")

    def test_trailing_punctuation(self):
        """Punctuation at the end is dropped, punctuation inside is kept."""
        self.assertEqual(stats.normalize_message("Ok."), "ok")
        self.assertEqual(stats.normalize_message("OK!!!"), "ok")
        self.assertEqual(stats.normalize_message("ce faci?!…"), "ce faci")
        self.assertEqual(stats.normalize_message("ok !"), "ok")
        self.assertEqual(stats.normalize_message("a.b, c"), "a.b, c")

    def test_whitespace(self):
        """Spaces at both ends go away and inner runs of whitespace become one space."""
        self.assertEqual(stats.normalize_message("  good   night \n"), "good night")
        self.assertEqual(stats.normalize_message("good\n\nnight"), "good night")

    def test_emoji_kept(self):
        """An emoji on its own is a real message, not empty text."""
        self.assertEqual(stats.normalize_message("😂"), "😂")
        self.assertEqual(stats.normalize_message("Haha 😂!"), "haha 😂")

    def test_empty_and_punctuation_only(self):
        """Empty text, blank text and punctuation-only text all become empty."""
        self.assertEqual(stats.normalize_message(""), "")
        self.assertEqual(stats.normalize_message("   "), "")
        self.assertEqual(stats.normalize_message("?!..."), "")


class RepeatedMessagesTest(unittest.TestCase):
    def test_variants_counted_together(self):
        """Different spellings of the same message count as one, with counts per person."""
        messages = make_messages([
            ("Alex", "ok"), ("Sam", "Ok."), ("Alex", "OK!"), ("Sam", "  ok  "), ("Alex", "something else"),
        ])
        result = stats.repeated_messages(messages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["count"], 4)
        self.assertEqual(result[0]["per_person"], {"Alex": 2, "Sam": 2})

    def test_most_common_spelling_shown(self):
        """The entry shows the spelling that was used most often."""
        messages = make_messages([("Alex", "Ok."), ("Sam", "ok"), ("Alex", "ok"), ("Sam", "OK!")])
        self.assertEqual(stats.repeated_messages(messages)[0]["text"], "ok")

    def test_spelling_tie_keeps_first_seen(self):
        """When two spellings are used equally often, the one sent first is shown."""
        messages = make_messages([("Alex", "Noapte bună"), ("Sam", "noapte buna")])
        self.assertEqual(stats.repeated_messages(messages)[0]["text"], "Noapte bună")

    def test_empty_text_skipped(self):
        """Media without a caption, blank text and lone punctuation never count as repeats."""
        messages = make_messages([("Alex", ""), ("Sam", ""), ("Alex", "   "), ("Sam", "?"), ("Alex", "?")])
        self.assertEqual(stats.repeated_messages(messages), [])

    def test_single_messages_left_out(self):
        """Texts sent only once are not included."""
        messages = make_messages([("Alex", "😂"), ("Sam", "😂"), ("Alex", "only once")])
        result = stats.repeated_messages(messages)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "😂")

    def test_most_repeated_first_and_ties(self):
        """Higher counts come first, and on a tie the text first sent earliest wins."""
        messages = make_messages([
            ("Alex", "b"), ("Alex", "a"), ("Sam", "c"), ("Sam", "a"), ("Alex", "b"),
            ("Sam", "c"), ("Alex", "c"),
        ])
        result = stats.repeated_messages(messages)
        texts = []
        for entry in result:
            texts.append(entry["text"])
        self.assertEqual(texts, ["c", "b", "a"])

    def test_how_many(self):
        """Only the requested number of entries comes back."""
        rows = []
        for letter in "abcde":
            rows.append(("Alex", letter))
            rows.append(("Sam", letter))
        messages = make_messages(rows)
        self.assertEqual(len(stats.repeated_messages(messages)), 5)
        result = stats.repeated_messages(messages, how_many=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "a")
        self.assertEqual(result[1]["text"], "b")

    def test_no_messages(self):
        """An empty chat has no repeated messages."""
        self.assertEqual(stats.repeated_messages([]), [])


class RepeatedMessageLinesTest(unittest.TestCase):
    def test_lines(self):
        """Each entry shows its rank, text, total count and per-person counts, top sender first."""
        messages = make_messages([
            ("Sam", "ok"), ("Alex", "Ok."), ("Alex", "ok"), ("Alex", "haha 😂"), ("Sam", "Haha 😂!"),
        ])
        self.assertEqual(report.repeated_message_lines(messages), [
            "Most repeated messages:",
            "  1. \"ok\" × 3 (Alex 2, Sam 1)",
            "  2. \"haha 😂\" × 2 (Alex 1, Sam 1)",
        ])

    def test_long_and_multiline_text(self):
        """Long texts are cut to 40 characters ending in "…", and line breaks become spaces."""
        long_text = "this is a really long message that keeps going on and on"
        messages = make_messages([("Alex", long_text), ("Sam", long_text), ("Alex", "two\nlines"), ("Sam", "two\nlines")])
        lines = report.repeated_message_lines(messages)
        expected_text = long_text[:39] + "…"
        self.assertEqual(len(expected_text), 40)
        self.assertEqual(lines[1], f"  1. \"{expected_text}\" × 2 (Alex 1, Sam 1)")
        self.assertEqual(lines[2], "  2. \"two lines\" × 2 (Alex 1, Sam 1)")

    def test_exactly_40_characters_not_cut(self):
        """A text of exactly 40 characters is shown in full."""
        text = "x" * 40
        lines = report.repeated_message_lines(make_messages([("Alex", text), ("Sam", text)]))
        self.assertEqual(lines[1], f"  1. \"{text}\" × 2 (Alex 1, Sam 1)")

    def test_nothing_repeats(self):
        """When every text is different, the report says so."""
        messages = make_messages([("Alex", "hi"), ("Sam", "hello"), ("Alex", "")])
        self.assertEqual(report.repeated_message_lines(messages), [
            "Most repeated messages:",
            "  Nothing was sent more than once.",
        ])


if __name__ == "__main__":
    unittest.main()
