"""Normalize text and split it into words, so the same word is counted the same way everywhere."""

import re

# Romanian is often typed without diacritics, and ș/ț exist in two Unicode forms (comma below and the
# older cedilla). Mapping them all to plain letters makes "și", "şi" and "si" count as the same word.
# Only these letters are mapped, so other alphabets (e.g. Cyrillic й or ё) are left untouched.
DIACRITICS = str.maketrans({
    "ă": "a",
    "â": "a",
    "î": "i",
    "ș": "s",
    "ş": "s",
    "ț": "t",
    "ţ": "t",
})

# Links would otherwise split into junk words like "https" and "com".
LINK_PATTERN = re.compile(r"https?://\S+|www\.\S+")

# Runs of letters or digits in any alphabet, without underscores.
WORD_PATTERN = re.compile(r"[^\W_]+")


def normalize_text(text):
    """Lowercase the text and replace Romanian diacritics with plain letters."""
    return text.lower().translate(DIACRITICS)


def split_words(text):
    """Return the normalized words in the text, leaving out links and punctuation."""
    without_links = LINK_PATTERN.sub(" ", normalize_text(text))
    return WORD_PATTERN.findall(without_links)
