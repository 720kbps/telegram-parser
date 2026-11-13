"""Text menu: load a Telegram chat export, then show the messages or the fun facts, or save them to reports/."""

import argparse
import webbrowser
from datetime import datetime
from pathlib import Path

from telegram_parser import html_report, report
from telegram_parser.loader import load_telegram

PROJECT_FOLDER = Path(__file__).parent
# Reports can contain private messages, so they always go in this git-ignored folder.
REPORTS_FOLDER = PROJECT_FOLDER / "reports"


def ask_choice(prompt, choices):
    """Keep asking until the user types one of the allowed choices, then return it."""
    while True:
        answer = input(prompt).strip()
        if answer in choices:
            return answer
        print(f"Please type one of: {', '.join(choices)}")


def default_file_name(kind, now=None, extension="txt"):
    """Return a name like "statistics_2026-11-13_22-15.txt" for the given kind of report."""
    if now is None:
        now = datetime.now()
    # The date and time keep later saves from overwriting earlier ones.
    return f"{kind}_{now.strftime('%Y-%m-%d_%H-%M')}.{extension}"


def clean_file_name(answer):
    """Return just the file-name part of what the user typed, with ".txt" added if it has no extension."""
    # Dropping any folders stops a typed path from writing outside the reports folder.
    name = Path(answer).name
    if name == "":
        return ""
    if Path(name).suffix == "":
        name = name + ".txt"
    return name


def free_path(folder, name):
    """Return a path in the folder for this name, adding _2, _3, ... if the file already exists."""
    path = folder / name
    stem = Path(name).stem
    suffix = Path(name).suffix
    number = 2
    while path.exists():
        path = folder / f"{stem}_{number}{suffix}"
        number += 1
    return path


def write_lines(path, lines):
    """Create the file's folder if needed and write the lines to the file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def shown_path(path):
    """Return the path relative to the project folder when possible, for printing."""
    try:
        return path.relative_to(PROJECT_FOLDER)
    except ValueError:
        return path


def save_lines(lines, kind, folder=REPORTS_FOLDER):
    """Ask for a file name, save the lines in the reports folder and return the saved path."""
    default_name = default_file_name(kind)
    answer = input(f"File name (Enter for {default_name}): ").strip()
    name = clean_file_name(answer)
    if name == "":
        name = default_name

    path = free_path(folder, name)
    write_lines(path, lines)
    print(f"Saved to {shown_path(path)}")
    return path


def save_wrapped_page(chat, folder=REPORTS_FOLDER):
    """Save the Wrapped HTML page in the reports folder, offer to open it, and return the saved path."""
    path = free_path(folder, default_file_name("wrapped", extension="html"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_report.build_page(chat), encoding="utf-8")
    print(f"Saved to {shown_path(path)}")

    answer = input("Open it in your browser? (y/n) ").strip().lower()
    if answer in ["y", "yes"]:
        # Opens the local file; nothing is uploaded.
        webbrowser.open(path.resolve().as_uri())
    return path


def show_lines(lines, kind):
    """Print the lines, then offer to export them; return False if the user wants to exit."""
    print()
    for line in lines:
        print(line)

    print()
    print("1) Export to a file")
    print("2) Back to the menu")
    print("3) Exit")
    choice = ask_choice("> ", ["1", "2", "3"])
    if choice == "1":
        save_lines(lines, kind)
    return choice != "3"


def run_menu(chat):
    """Show the main menu until the user chooses to exit."""
    messages = chat["messages"]
    while True:
        print()
        print(f"=== Telegram chat: {len(messages)} messages, {len(chat['calls'])} calls ===")
        print("1) Show all messages")
        print("2) Show statistics")
        print("3) Save the Wrapped page (HTML)")
        print("4) Exit")
        choice = ask_choice("> ", ["1", "2", "3", "4"])

        if choice == "1":
            keep_going = show_lines(report.message_lines(messages), "messages")
        elif choice == "2":
            keep_going = show_lines(report.stats_lines(chat), "statistics")
        elif choice == "3":
            save_wrapped_page(chat)
            keep_going = True
        else:
            keep_going = False

        if not keep_going:
            return


def main():
    """Load the chat export given on the command line (or ask for it) and start the menu."""
    parser = argparse.ArgumentParser(description="Fun facts from a Telegram chat export.")
    parser.add_argument("export_path", nargs="?", help="path to the JSON file from Telegram Desktop")
    args = parser.parse_args()

    try:
        export_path = args.export_path or input("Path to the Telegram chat export (.json): ").strip()
        try:
            chat = load_telegram(Path(export_path).expanduser())
        except (FileNotFoundError, ValueError) as error:
            # ValueError covers both broken JSON and a full-account export.
            print(f"Could not load the chat: {error}")
            return

        if not chat["messages"]:
            print("No messages found in this export.")
            return
        run_menu(chat)
    except (KeyboardInterrupt, EOFError):
        print()
    print("Bye!")


if __name__ == "__main__":
    main()
