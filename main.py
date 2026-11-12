import argparse
from pathlib import Path

import report
from telegram_loader import load_telegram

# Exports can contain private messages, so they go in a git-ignored folder by default.
EXPORT_FOLDER = Path(__file__).parent / "exports"


def ask_choice(prompt, choices):
    """Keep asking until the user types one of the allowed choices, then return it."""
    while True:
        answer = input(prompt).strip()
        if answer in choices:
            return answer
        print(f"Please type one of: {', '.join(choices)}")


def save_lines(lines, default_name):
    """Ask for a file name and write the lines to that file."""
    default_path = EXPORT_FOLDER / default_name
    answer = input(f"File name (Enter for {default_path}): ").strip()
    if answer:
        path = Path(answer).expanduser()
    else:
        path = default_path

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved to {path}")


def show_lines(lines, default_name):
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
        save_lines(lines, default_name)
    return choice != "3"


def run_menu(messages):
    """Show the main menu until the user chooses to exit."""
    while True:
        print()
        print(f"=== Telegram chat: {len(messages)} messages ===")
        print("1) Show all messages")
        print("2) Show statistics")
        print("3) Exit")
        choice = ask_choice("> ", ["1", "2", "3"])

        if choice == "1":
            keep_going = show_lines(report.message_lines(messages), "messages.txt")
        elif choice == "2":
            keep_going = show_lines(report.stats_lines(messages), "statistics.txt")
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
            messages = load_telegram(Path(export_path).expanduser())
        except (FileNotFoundError, ValueError) as error:
            # ValueError covers both broken JSON and a full-account export.
            print(f"Could not load the chat: {error}")
            return

        if not messages:
            print("No messages found in this export.")
            return
        run_menu(messages)
    except (KeyboardInterrupt, EOFError):
        print()
    print("Bye!")


if __name__ == "__main__":
    main()
