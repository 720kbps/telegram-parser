import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import main

LINES = ["first line", "second line"]


class DefaultNameTest(unittest.TestCase):
    def test_name_has_kind_date_and_time(self):
        """The default name says what the report is and when it was made."""
        name = main.default_file_name("statistics", datetime(2026, 11, 13, 22, 15))
        self.assertEqual(name, "statistics_2026-11-13_22-15.txt")


class CleanNameTest(unittest.TestCase):
    def test_extension_added(self):
        """A typed name without an extension gets ".txt"."""
        self.assertEqual(main.clean_file_name("my_report"), "my_report.txt")

    def test_extension_kept(self):
        """A typed name that already has an extension is left alone."""
        self.assertEqual(main.clean_file_name("notes.md"), "notes.md")

    def test_path_reduced_to_name(self):
        """A typed path keeps only its file-name part."""
        self.assertEqual(main.clean_file_name("../../etc/secret.txt"), "secret.txt")


class FreePathTest(unittest.TestCase):
    def test_existing_names_get_numbers(self):
        """An existing name gets _2, and then _3 once _2 is taken too."""
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "report.txt").write_text("old", encoding="utf-8")
            second = main.free_path(folder, "report.txt")
            self.assertEqual(second, folder / "report_2.txt")

            second.write_text("old", encoding="utf-8")
            self.assertEqual(main.free_path(folder, "report.txt"), folder / "report_3.txt")


class SaveLinesTest(unittest.TestCase):
    def test_enter_uses_default_name(self):
        """Pressing Enter saves under the dated default name."""
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch("builtins.input", return_value=""), patch("builtins.print"):
                with patch("main.default_file_name", return_value="messages_2026-11-13_22-15.txt"):
                    path = main.save_lines(LINES, "messages", folder)
            self.assertEqual(path, folder / "messages_2026-11-13_22-15.txt")
            self.assertEqual(path.read_text(encoding="utf-8"), "first line\nsecond line\n")

    def test_typed_name_without_extension(self):
        """A typed name without an extension is saved with ".txt"."""
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch("builtins.input", return_value="chat"), patch("builtins.print"):
                path = main.save_lines(LINES, "messages", folder)
            self.assertEqual(path, folder / "chat.txt")
            self.assertTrue(path.exists())

    def test_typed_path_stays_in_folder(self):
        """A typed path is saved by its file name inside the given folder."""
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "reports"
            with patch("builtins.input", return_value="../outside/stats.txt"), patch("builtins.print"):
                path = main.save_lines(LINES, "statistics", folder)
            self.assertEqual(path, folder / "stats.txt")
            self.assertFalse((Path(temp) / "outside").exists())

    def test_existing_file_not_overwritten(self):
        """Saving the same name twice keeps the first file and adds _2."""
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch("builtins.input", return_value="same"), patch("builtins.print"):
                first = main.save_lines(["one"], "messages", folder)
                second = main.save_lines(["two"], "messages", folder)
            self.assertEqual(second, folder / "same_2.txt")
            self.assertEqual(first.read_text(encoding="utf-8"), "one\n")
            self.assertEqual(second.read_text(encoding="utf-8"), "two\n")

    def test_folder_created(self):
        """The reports folder is created when it doesn't exist yet."""
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "new" / "reports"
            with patch("builtins.input", return_value="x"), patch("builtins.print"):
                path = main.save_lines(LINES, "messages", folder)
            self.assertTrue(folder.is_dir())
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
