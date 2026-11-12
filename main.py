import argparse

import stats
from telegram_loader import load_telegram

KIND_LABELS = {
    "voice_message": "Voice messages",
    "video_message": "Round video messages",
}


def format_duration(total_seconds):
    """Turn a number of seconds into a short string like "1h 5m" or "42s"."""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def print_first_message(messages):
    """Print who sent the very first message, when, and what it was."""
    first = stats.first_message(messages)
    content = first["text"] or f"[{first['kind']}]"
    print(f"First message: {first['date']:%d %b %Y %H:%M}, {first['sender']}: {content}")


def print_people(messages):
    """Print the total message count and each person's share of it."""
    total = len(messages)
    print(f"Total messages: {total}")
    ranked = stats.messages_per_person(messages).most_common()
    for sender, count in ranked:
        percent = count / total * 100
        print(f"  {sender}: {count} ({percent:.1f}%)")

    if len(ranked) == 2:
        top = ranked[0]
        other = ranked[1]
        difference = (top[1] - other[1]) / other[1] * 100
        print(f"  {top[0]} sent {difference:.0f}% more messages than {other[0]}")


def print_voice_and_video(messages):
    """Print how many voice and round video messages were sent and their total length."""
    print("Lost information (not in the export as text):")
    totals = stats.voice_and_video(messages)
    for kind, label in KIND_LABELS.items():
        count = totals[kind]["count"]
        duration = format_duration(totals[kind]["seconds"])
        print(f"  {label}: {count} ({duration})")


def print_top_days(messages):
    """Print the busiest days by number of messages."""
    print("Busiest days:")
    for day, count in stats.top_days(messages):
        print(f"  {day:%d %b %Y}: {count} messages")


def print_months(messages):
    """Print the number of messages sent in each month."""
    print("Messages per month:")
    for month, count in stats.messages_per_month(messages):
        print(f"  {month}: {count}")


def main():
    """Read the export path from the command line and print the full report."""
    parser = argparse.ArgumentParser(description="Fun facts from a Telegram chat export.")
    parser.add_argument("export_path", help="path to the result.json from Telegram Desktop")
    args = parser.parse_args()

    messages = load_telegram(args.export_path)
    if not messages:
        print("No messages found in this export.")
        return

    sections = [print_first_message, print_people, print_voice_and_video, print_top_days, print_months]
    for print_section in sections:
        print_section(messages)
        print()


if __name__ == "__main__":
    main()
