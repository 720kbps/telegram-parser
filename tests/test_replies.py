import unittest
from pathlib import Path

import report
import stats
from telegram_loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


def make_message(msg_id, sender, reply_to=None):
    """Build a message dict with only the fields the replies stat needs."""
    return {"id": msg_id, "sender": sender, "reply_to": reply_to}


class RepliesPerPersonTest(unittest.TestCase):
    def test_no_messages(self):
        """An empty chat gives an empty result."""
        self.assertEqual(stats.replies_per_person([]), {})

    def test_counts_replies_and_replied_to(self):
        """Replies count for the sender and replied_to counts for the quoted person."""
        messages = [
            make_message(1, "Alex"),
            make_message(2, "Sam", reply_to=1),
            make_message(3, "Sam", reply_to=1),
            make_message(4, "Alex"),
        ]
        result = stats.replies_per_person(messages)
        self.assertEqual(result["Alex"], {"replies": 0, "total": 2, "replied_to": 2})
        self.assertEqual(result["Sam"], {"replies": 2, "total": 2, "replied_to": 0})

    def test_reply_to_missing_message(self):
        """A reply to an id not in the export counts as a reply but gives nobody replied_to."""
        messages = [
            make_message(5, "Alex"),
            make_message(6, "Sam", reply_to=999),
        ]
        result = stats.replies_per_person(messages)
        self.assertEqual(result["Sam"], {"replies": 1, "total": 1, "replied_to": 0})
        self.assertEqual(result["Alex"], {"replies": 0, "total": 1, "replied_to": 0})

    def test_self_reply(self):
        """Replying to your own message counts as a reply but not as being replied to."""
        messages = [
            make_message(1, "Alex"),
            make_message(2, "Alex", reply_to=1),
        ]
        result = stats.replies_per_person(messages)
        self.assertEqual(result["Alex"], {"replies": 1, "total": 2, "replied_to": 0})

    def test_sample_chat(self):
        """In the sample chat each person replies once and is replied to once."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        result = stats.replies_per_person(messages)
        self.assertEqual(result["Alex"], {"replies": 1, "total": 4, "replied_to": 1})
        self.assertEqual(result["Sam"], {"replies": 1, "total": 6, "replied_to": 1})


class ReplyLinesTest(unittest.TestCase):
    def test_no_messages(self):
        """An empty chat says there is nothing to measure."""
        self.assertEqual(report.reply_lines([]), [
            "Replies (quoting a specific message):",
            "  No messages to measure.",
        ])

    def test_sorted_by_replies_with_grammar(self):
        """People are listed with the most replies first, using "time" and "times" correctly."""
        messages = [
            make_message(1, "Alex"),
            make_message(2, "Sam", reply_to=1),
            make_message(3, "Sam", reply_to=1),
            make_message(4, "Alex", reply_to=2),
        ]
        self.assertEqual(report.reply_lines(messages), [
            "Replies (quoting a specific message):",
            "  Sam: replied 2 times (100.0% of their messages), got replied to 1 time",
            "  Alex: replied 1 time (50.0% of their messages), got replied to 2 times",
        ])

    def test_sample_chat(self):
        """The sample chat report shows one reply each and one time replied to each."""
        messages = load_telegram(SAMPLE_PATH)["messages"]
        self.assertEqual(report.reply_lines(messages), [
            "Replies (quoting a specific message):",
            "  Alex: replied 1 time (25.0% of their messages), got replied to 1 time",
            "  Sam: replied 1 time (16.7% of their messages), got replied to 1 time",
        ])


if __name__ == "__main__":
    unittest.main()
