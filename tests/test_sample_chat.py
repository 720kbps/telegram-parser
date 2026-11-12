import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import stats
from telegram_loader import extract_text, load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"


class LoaderTest(unittest.TestCase):
    def setUp(self):
        """Load the fake sample chat before each test."""
        self.messages = load_telegram(SAMPLE_PATH)

    def test_skips_service_messages(self):
        """Service entries like calls are not counted as messages."""
        self.assertEqual(len(self.messages), 10)

    def test_joins_text_with_links(self):
        """Text split into pieces around a link is joined back together."""
        self.assertEqual(self.messages[2]["text"], "check this out https://example.com")

    def test_reads_old_export_without_text_entities(self):
        """Old exports that only have a plain "text" field still work."""
        self.assertEqual(self.messages[-1]["text"], "nice")

    def test_text_as_mixed_list(self):
        """A text list mixing strings and formatted pieces is joined in order."""
        msg = {"text": ["see ", {"type": "bold", "text": "this"}, "!"]}
        self.assertEqual(extract_text(msg), "see this!")

    def test_renamed_person_counts_once(self):
        """Someone who changed their name counts as one person, under their newest name."""
        raw = [
            {"type": "message", "date": "2023-01-01T10:00:00", "from": "Old name", "from_id": "user1", "text": "a"},
            {"type": "message", "date": "2023-01-02T10:00:00", "from": "New name", "from_id": "user1", "text": "b"},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chat.json"
            path.write_text(json.dumps({"messages": raw}), encoding="utf-8")
            messages = load_telegram(path)

        senders = set()
        for msg in messages:
            senders.add(msg["sender"])
        self.assertEqual(senders, {"New name"})


class StatsTest(unittest.TestCase):
    def setUp(self):
        """Load the fake sample chat before each test."""
        self.messages = load_telegram(SAMPLE_PATH)

    def test_messages_per_person(self):
        """Each person's message count matches the sample."""
        counts = stats.messages_per_person(self.messages)
        self.assertEqual(counts["Alex"], 4)
        self.assertEqual(counts["Sam"], 6)

    def test_first_message(self):
        """The earliest message in the sample is found."""
        first = stats.first_message(self.messages)
        self.assertEqual(first["text"], "hey, is this the right chat?")

    def test_voice_and_video(self):
        """Voice and round video counts and durations add up correctly."""
        totals = stats.voice_and_video(self.messages)
        self.assertEqual(totals["voice_message"], {"count": 2, "seconds": 60})
        self.assertEqual(totals["video_message"], {"count": 1, "seconds": 15})

    def test_top_days(self):
        """The busiest day in the sample comes first."""
        days = stats.top_days(self.messages)
        self.assertEqual(days[0], (date(2023, 1, 5), 4))

    def test_messages_per_month(self):
        """Months are counted and listed in date order."""
        months = stats.messages_per_month(self.messages)
        self.assertEqual(months, [("2023-01", 7), ("2023-02", 3)])


if __name__ == "__main__":
    unittest.main()
