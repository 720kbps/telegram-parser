import unittest

from telegram_parser.text_tools import normalize_text, split_words


class NormalizeTextTest(unittest.TestCase):
    def test_lowercases(self):
        """Text is lowercased."""
        self.assertEqual(normalize_text("Hello CAPY"), "hello capy")

    def test_romanian_diacritics(self):
        """Both forms of ș/ț and the other Romanian letters become plain letters."""
        self.assertEqual(normalize_text("și şi ȘI țară ţară ăâî"), "si si si tara tara aai")

    def test_other_alphabets_untouched(self):
        """Cyrillic letters like й and ё are only lowercased, not changed."""
        self.assertEqual(normalize_text("Йога Ёжик"), "йога ёжик")


class SplitWordsTest(unittest.TestCase):
    def test_punctuation_and_emoji_dropped(self):
        """Punctuation and emoji aren't part of words."""
        self.assertEqual(split_words("Haha, capy!! 😂 ok?"), ["haha", "capy", "ok"])

    def test_links_dropped(self):
        """Links are removed instead of being split into pieces."""
        self.assertEqual(split_words("look https://example.com/a?b=1 and www.test.ro now"), ["look", "and", "now"])

    def test_numbers_and_underscores(self):
        """Numbers count as words, and underscores split words."""
        self.assertEqual(split_words("ora 22 snake_case"), ["ora", "22", "snake", "case"])

    def test_diacritics_merge_words(self):
        """The same Romanian word typed with or without diacritics gives the same word."""
        self.assertEqual(split_words("Și si şi"), ["si", "si", "si"])

    def test_empty(self):
        """Empty text has no words."""
        self.assertEqual(split_words(""), [])


if __name__ == "__main__":
    unittest.main()
