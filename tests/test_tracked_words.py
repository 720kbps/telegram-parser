import os
import tempfile
import unittest
from collections import Counter
from datetime import date, datetime

from telegram_parser import report
from telegram_parser import stats


def make_message(sender, stamp, text):
    """Build a minimal message dict with a sender, an ISO date string and some text."""
    return {"sender": sender, "date": datetime.fromisoformat(stamp), "text": text, "kind": "text"}


def write_words_file(folder, content):
    """Write a temporary tracked words file inside folder and return its path."""
    path = os.path.join(folder, "words.txt")
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)
    return path


class ParseTrackedWordsTest(unittest.TestCase):
    def test_skips_comments_and_blank_lines(self):
        """Blank lines and lines starting with # are left out."""
        entries = stats.parse_tracked_words(["# my words", "", "   ", "hello", "  # indented comment"])
        self.assertEqual(entries, [{"label": "hello", "word": "hello", "prefix": False}])

    def test_star_makes_prefix(self):
        """A trailing * marks a prefix entry and is not part of the word."""
        entries = stats.parse_tracked_words(["capy*"])
        self.assertEqual(entries, [{"label": "capy*", "word": "capy", "prefix": True}])

    def test_normalizes_case_and_diacritics(self):
        """Entries are lowercased and Romanian diacritics are flattened, but the label keeps the original."""
        entries = stats.parse_tracked_words(["  Mulțumesc  ", "ŞTIU*"])
        self.assertEqual(entries[0], {"label": "Mulțumesc", "word": "multumesc", "prefix": False})
        self.assertEqual(entries[1], {"label": "ŞTIU*", "word": "stiu", "prefix": True})

    def test_lone_star_is_skipped(self):
        """A line that is only * is ignored instead of matching every word."""
        self.assertEqual(stats.parse_tracked_words(["*"]), [])

    def test_keeps_file_order(self):
        """Entries come back in the same order as the lines."""
        entries = stats.parse_tracked_words(["zebra", "apple", "mango*"])
        labels = []
        for entry in entries:
            labels.append(entry["label"])
        self.assertEqual(labels, ["zebra", "apple", "mango*"])


class TrackedWordCountsTest(unittest.TestCase):
    def setUp(self):
        """Build a small hand-made chat used by most tests."""
        self.messages = [
            make_message("Alex", "2023-01-05T10:00:00", "Look at this capy!"),
            make_message("Sam", "2023-01-06T11:00:00", "capybaras are great, CAPYBARA forever"),
            make_message("Alex", "2023-01-07T12:00:00", "capy capy capy"),
            make_message("Sam", "2023-01-08T13:00:00", "escapy is not a match, nor is cap"),
            make_message("Alex", "2023-01-09T14:00:00", ""),
        ]

    def counts_for(self, lines):
        """Parse lines into entries and count them in the hand-made chat."""
        return stats.tracked_word_counts(self.messages, stats.parse_tracked_words(lines))

    def test_whole_word_does_not_match_longer_words(self):
        """Without *, only the exact word counts, not capybara."""
        result = self.counts_for(["capy"])[0]
        self.assertEqual(result["total"], 4)

    def test_prefix_matches_longer_words(self):
        """With *, capy, capybara and capybaras all count, but not words that only contain capy."""
        result = self.counts_for(["capy*"])[0]
        self.assertEqual(result["total"], 6)

    def test_counts_every_occurrence(self):
        """A word repeated in one message counts once per use."""
        messages = [make_message("Alex", "2023-01-01T09:00:00", "capy capy")]
        result = stats.tracked_word_counts(messages, stats.parse_tracked_words(["capy"]))[0]
        self.assertEqual(result["total"], 2)

    def test_per_person_counts(self):
        """Each sender gets their own count."""
        result = self.counts_for(["capy*"])[0]
        self.assertEqual(result["per_person"], Counter({"Alex": 4, "Sam": 2}))

    def test_first_used_date(self):
        """The first used date is the day of the earliest matching message."""
        results = self.counts_for(["capybara", "capy*"])
        self.assertEqual(results[0]["first_used"], date(2023, 1, 6))
        self.assertEqual(results[1]["first_used"], date(2023, 1, 5))

    def test_unused_word(self):
        """A word nobody used has a total of 0, no per-person counts and no first used date."""
        result = self.counts_for(["hello"])[0]
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["per_person"], Counter())
        self.assertIsNone(result["first_used"])

    def test_diacritics_in_messages_match_plain_entry(self):
        """A plain entry matches words typed with diacritics in either ș form."""
        messages = [
            make_message("Alex", "2023-02-01T09:00:00", "știu"),
            make_message("Sam", "2023-02-01T09:05:00", "ştiu"),
            make_message("Sam", "2023-02-01T09:06:00", "stiu"),
        ]
        result = stats.tracked_word_counts(messages, stats.parse_tracked_words(["știu"]))[0]
        self.assertEqual(result["total"], 3)

    def test_word_can_match_several_entries(self):
        """One word counts towards every entry it matches."""
        results = self.counts_for(["capy", "capy*", "c*"])
        self.assertEqual(results[0]["total"], 4)
        self.assertEqual(results[1]["total"], 6)
        # "c*" also matches "cap" in the fourth message.
        self.assertEqual(results[2]["total"], 7)


class TrackedWordLinesTest(unittest.TestCase):
    def setUp(self):
        """Make a temporary folder for words files, so the real tracked_words.txt is never touched."""
        self.folder = tempfile.TemporaryDirectory()
        self.messages = [
            make_message("Alex", "2023-01-05T10:00:00", "capy capybara"),
            make_message("Sam", "2023-01-06T11:00:00", "Capy!"),
            make_message("Alex", "2023-01-07T12:00:00", "a capybara"),
        ]

    def tearDown(self):
        """Delete the temporary folder."""
        self.folder.cleanup()

    def test_report_lines_in_file_order(self):
        """Each entry gets a line with its total, per-person counts and first used date, in file order."""
        path = write_words_file(self.folder.name, "# tracked\ncapy*\n\nhello\n")
        lines = report.tracked_word_lines(self.messages, path)
        self.assertEqual(lines, [
            "Tracked words:",
            "  capy*: 4 (Alex 3, Sam 1), first used 05 Jan 2023",
            "  hello: 0",
        ])

    def test_missing_file(self):
        """A missing file loads as no entries and the report shows a setup hint."""
        path = os.path.join(self.folder.name, "does_not_exist.txt")
        self.assertEqual(report.load_tracked_words(path), [])
        lines = report.tracked_word_lines(self.messages, path)
        self.assertEqual(len(lines), 1)
        self.assertIn("none set up", lines[0])

    def test_empty_file(self):
        """A file with only comments and blank lines shows the setup hint too."""
        path = write_words_file(self.folder.name, "# nothing yet\n\n")
        lines = report.tracked_word_lines(self.messages, path)
        self.assertEqual(lines, ["Tracked words: none set up (copy tracked_words.example.txt to tracked_words.txt and add words)"])

    def test_default_path_is_in_project_root(self):
        """The default words file is tracked_words.txt in the project root, next to the example file."""
        project_root = report.Path(report.__file__).parent.parent
        self.assertEqual(report.TRACKED_WORDS_PATH, project_root / "tracked_words.txt")
        self.assertTrue((project_root / "tracked_words.example.txt").exists())


if __name__ == "__main__":
    unittest.main()
