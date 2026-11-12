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
        self.messages = load_telegram(SAMPLE_PATH)

    def test_skips_service_messages(self):
        self.assertEqual(len(self.messages), 10)

    def test_joins_text_with_links(self):
        self.assertEqual(self.messages[2]["text"], "check this out https://example.com")

    def test_reads_old_export_without_text_entities(self):
        self.assertEqual(self.messages[-1]["text"], "nice")

    def test_text_as_mixed_list(self):
        msg = {"text": ["see ", {"type": "bold", "text": "this"}, "!"]}
        self.assertEqual(extract_text(msg), "see this!")

    def test_renamed_person_counts_once(self):
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
        self.messages = load_telegram(SAMPLE_PATH)

    def test_messages_per_person(self):
        counts = stats.messages_per_person(self.messages)
        self.assertEqual(counts["Alex"], 4)
        self.assertEqual(counts["Sam"], 6)

    def test_first_message(self):
        first = stats.first_message(self.messages)
        self.assertEqual(first["text"], "hey, is this the right chat?")

    def test_voice_and_video(self):
        totals = stats.voice_and_video(self.messages)
        self.assertEqual(totals["voice_message"], {"count": 2, "seconds": 60})
        self.assertEqual(totals["video_message"], {"count": 1, "seconds": 15})

    def test_top_days(self):
        days = stats.top_days(self.messages)
        self.assertEqual(days[0], (date(2023, 1, 5), 4))

    def test_messages_per_month(self):
        months = stats.messages_per_month(self.messages)
        self.assertEqual(months, [("2023-01", 7), ("2023-02", 3)])


if __name__ == "__main__":
    unittest.main()
