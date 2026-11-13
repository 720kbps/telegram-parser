import unittest
from pathlib import Path

import report
import stats
from telegram_loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_messages(*pairs):
    """Build minimal message dicts (sender and edited only) from (sender, edited) pairs."""
    messages = []
    for sender, edited in pairs:
        messages.append({"sender": sender, "edited": edited})
    return messages


class EditedPerPersonTest(unittest.TestCase):
    def test_no_edits(self):
        """Everyone still shows up with zero edits when nothing was edited."""
        messages = make_messages(("Alex", False), ("Sam", False), ("Sam", False))
        result = stats.edited_per_person(messages)
        self.assertEqual(result, {
            "Alex": {"edited": 0, "total": 1},
            "Sam": {"edited": 0, "total": 2},
        })

    def test_every_message_edited(self):
        """A person who edited every message has edited equal to total."""
        messages = make_messages(("Alex", True), ("Alex", True), ("Sam", False))
        result = stats.edited_per_person(messages)
        self.assertEqual(result["Alex"], {"edited": 2, "total": 2})
        self.assertEqual(result["Sam"], {"edited": 0, "total": 1})

    def test_empty_chat(self):
        """An empty chat gives an empty result."""
        self.assertEqual(stats.edited_per_person([]), {})


class EditedLinesTest(unittest.TestCase):
    def test_no_edits(self):
        """A chat with no edits gets a single friendly line."""
        messages = make_messages(("Alex", False), ("Sam", False))
        self.assertEqual(report.edited_lines(messages), ["Edited messages: none"])

    def test_empty_chat(self):
        """An empty chat is treated like a chat with no edits."""
        self.assertEqual(report.edited_lines([]), ["Edited messages: none"])

    def test_every_message_edited_comes_first(self):
        """People are ordered by edit percentage, so 100% comes before a lower share."""
        messages = make_messages(("Sam", True), ("Sam", False), ("Alex", True))
        self.assertEqual(report.edited_lines(messages), [
            "Edited messages: 2 (66.7% of all messages)",
            "  Alex: 1 of 1 (100.0%)",
            "  Sam: 1 of 2 (50.0%)",
        ])

    def test_sample_chat(self):
        """The sample chat has one edit each from Alex and Sam."""
        chat = load_telegram(SAMPLE_PATH)
        self.assertEqual(report.edited_lines(chat["messages"]), [
            "Edited messages: 2 (20.0% of all messages)",
            "  Alex: 1 of 4 (25.0%)",
            "  Sam: 1 of 6 (16.7%)",
        ])


if __name__ == "__main__":
    unittest.main()
