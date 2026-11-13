import re
import tempfile
import unittest
from pathlib import Path

from telegram_parser import html_report
from telegram_parser.loader import load_telegram

SAMPLE_PATH = Path(__file__).parent.parent / "samples" / "sample_chat.json"
# A words file that never exists, so tests don't depend on the user's own tracked_words.txt.
NO_WORDS_FILE = Path(__file__).parent / "no_such_tracked_words.txt"


def sample_page():
    """Build the page for the sample chat, without any tracked words."""
    return html_report.build_page(load_telegram(SAMPLE_PATH), NO_WORDS_FILE)


class PageTest(unittest.TestCase):
    def test_is_a_full_html_page(self):
        """The page is a complete HTML document titled after the chat."""
        page = sample_page()
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn("<title>Sam · Telegram wrapped</title>", page)
        self.assertTrue(page.rstrip().endswith("</html>"))

    def test_has_every_group_and_main_cards(self):
        """The sample chat fills every group and the main cards."""
        page = sample_page()
        groups = ["The basics", "Conversations", "Time", "Media and calls", "What you write", "Days and months"]
        for group in groups:
            self.assertIn(f'<h2 class="group">{group}</h2>', page)
        cards = ["Messages", "The very first message", "Who starts the conversation", "Reply time", "Busiest hour of the day",
                 "Longest streak", "Calls", "Stickers", "Emoji", "Busiest days", "Messages per month"]
        for title in cards:
            self.assertIn(f"<h3>{title}</h3>", page)

    def test_nothing_loads_from_the_internet(self):
        """The page has no scripts and no links to outside files, so opening it never sends data anywhere."""
        page = sample_page()
        self.assertNotIn("<script", page)
        self.assertIsNone(re.search(r'(src|href)\s*=\s*["\']?https?:', page))
        self.assertNotIn("@import", page)

    def test_text_and_names_are_escaped(self):
        """Message text and names show up as text, never as HTML."""
        chat = load_telegram(SAMPLE_PATH)
        chat["name"] = "<Sam & co>"
        chat["messages"][0]["text"] = "<script>alert(1)</script>"
        page = html_report.build_page(chat, NO_WORDS_FILE)
        self.assertNotIn("<script", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertIn("&lt;Sam &amp; co&gt;", page)

    def test_cards_without_data_are_left_out(self):
        """A chat with no calls has no calls card."""
        chat = load_telegram(SAMPLE_PATH)
        chat["calls"] = []
        page = html_report.build_page(chat, NO_WORDS_FILE)
        self.assertNotIn("<h3>Calls</h3>", page)

    def test_empty_chat(self):
        """A chat without messages still gives a valid page."""
        page = html_report.build_page({"name": "Empty", "messages": [], "calls": []}, NO_WORDS_FILE)
        self.assertIn("No messages in this chat", page)

    def test_tracked_words_card(self):
        """The tracked words card only appears when the words file has entries."""
        self.assertNotIn("<h3>Tracked words</h3>", sample_page())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "tracked_words.txt"
            path.write_text("haha\n", encoding="utf-8")
            page = html_report.build_page(load_telegram(SAMPLE_PATH), path)
        self.assertIn("<h3>Tracked words</h3>", page)


class BuildingBlocksTest(unittest.TestCase):
    def test_bar_chart_has_one_bar_per_value(self):
        """The chart draws a bar for every value and highlights the chosen one."""
        svg = html_report.bar_chart_svg([1, 5, 0, 3], ["a", "b", "c", "d"], ["a", "b", "c", "d"], highlight=1)
        self.assertEqual(svg.count("<rect"), 4)
        self.assertEqual(svg.count('class="bar top"'), 1)
        self.assertIn("<title>b: 5</title>", svg)

    def test_bar_chart_with_all_zeros(self):
        """A chart where every value is 0 doesn't divide by zero."""
        svg = html_report.bar_chart_svg([0, 0], ["a", "b"], ["a", "b"])
        self.assertEqual(svg.count("<rect"), 2)

    def test_people_colors_follow_message_counts(self):
        """The person with the most messages gets the first color."""
        colors = html_report.people_colors(load_telegram(SAMPLE_PATH)["messages"])
        self.assertEqual(colors["Sam"], "var(--person-1)")
        self.assertEqual(colors["Alex"], "var(--person-2)")

    def test_card_escapes_its_text(self):
        """Card titles and headline text are escaped."""
        html = html_report.card("<t>", "<big>", "<sub>")
        self.assertIn("&lt;t&gt;", html)
        self.assertIn("&lt;big&gt;", html)
        self.assertNotIn("<big>", html)


if __name__ == "__main__":
    unittest.main()
