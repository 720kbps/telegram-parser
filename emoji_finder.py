# Finds emoji in text using only the standard library. It's kept simple on purpose: these ranges
# cover the emoji people actually type, and a symbol outside them (like ↔ or ☺) only counts when it's
# followed by the emoji presentation selector U+FE0F, which is how phones send those as emoji.
# A few plain text symbols inside the ranges (like ★ or ✓) are counted too; that's an accepted trade-off.
import re

EMOJI_RANGES = [
    (0x1F000, 0x1F0FF),  # mahjong tiles and playing cards
    (0x1F100, 0x1F2FF),  # enclosed letters and ideographs (🆗, 🈳) and regional indicators
    (0x1F300, 0x1F5FF),  # misc symbols and pictographs
    (0x1F600, 0x1F64F),  # emoticons
    (0x1F680, 0x1F6FF),  # transport and map
    (0x1F700, 0x1F7FF),  # geometric shapes like 🟢
    (0x1F900, 0x1F9FF),  # supplemental symbols and pictographs
    (0x1FA70, 0x1FAFF),  # newer symbols and pictographs (🩷, 🫠)
    (0x2600, 0x26FF),    # misc symbols (☀, ⚡, ⛔)
    (0x2700, 0x27BF),    # dingbats (✨, ❤, ✅)
]

# Any character that could start or be part of an emoji. Checking for these first (fast, done by the
# regex engine) lets find_emoji skip most messages without looking at them character by character.
POSSIBLE_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️⃣]")

VARIATION_SELECTOR = "️"
ZERO_WIDTH_JOINER = "‍"
KEYCAP = "⃣"


def is_emoji_base(char):
    """Return True if the character is an emoji on its own."""
    code = ord(char)
    for low, high in EMOJI_RANGES:
        if low <= code <= high:
            return True
    return False


def is_modifier(char):
    """Return True for characters that change the emoji before them: skin tones and flag tag letters."""
    code = ord(char)
    return 0x1F3FB <= code <= 0x1F3FF or 0xE0020 <= code <= 0xE007F


def is_regional_indicator(char):
    """Return True for the letter-like characters that make up country flags in pairs."""
    return char != "" and 0x1F1E6 <= ord(char) <= 0x1F1FF


def emoji_length(text, start):
    """Return how many characters the emoji starting at text[start] spans, or 0 if there's no emoji there."""
    char = text[start]
    next_char = text[start + 1:start + 2]

    # Keycaps like 1️⃣ are a digit or # or *, an optional selector, then the keycap mark.
    if char in "0123456789#*":
        if next_char == KEYCAP:
            return 2
        if next_char == VARIATION_SELECTOR and text[start + 2:start + 3] == KEYCAP:
            return 3
        return 0

    # A flag is two regional indicators, e.g. 🇷 + 🇴.
    if is_regional_indicator(char):
        if is_regional_indicator(next_char):
            return 2
        return 1

    if not is_emoji_base(char) and next_char != VARIATION_SELECTOR:
        return 0

    # Keep skin tones, selectors and zero-width-joined parts (👨‍👩‍👧) together as one emoji.
    end = start + 1
    while end < len(text):
        current = text[end]
        if current == VARIATION_SELECTOR or is_modifier(current):
            end += 1
        elif current == ZERO_WIDTH_JOINER and end + 1 < len(text) and is_emoji_base(text[end + 1]):
            end += 2
        else:
            break
    return end - start


# The report looks at the emoji of every message several times (counts, ratio, per day), and the
# character-by-character scan is the slow part, so each text's result is remembered after the first time.
FOUND_CACHE = {}


def find_emoji(text):
    """Return every emoji in the text in order, with the U+FE0F selector removed so "❤️" and "❤" match."""
    if not POSSIBLE_EMOJI.search(text):
        return []
    if text in FOUND_CACHE:
        # Return a copy so a caller changing the list can't change the remembered result.
        return list(FOUND_CACHE[text])

    found = []
    i = 0
    while i < len(text):
        length = emoji_length(text, i)
        if length == 0:
            i += 1
            continue
        found.append(text[i:i + length].replace(VARIATION_SELECTOR, ""))
        i += length
    FOUND_CACHE[text] = found
    return list(found)
