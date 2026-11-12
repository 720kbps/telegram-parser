import stats

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


def format_message(msg):
    """Format one message as "Sender: text", with a [kind] tag in front for media."""
    # Indent continuation lines so a multi-line message still reads as one entry.
    text = msg["text"].replace("\n", "\n    ")
    if msg["kind"] == "text":
        return f"{msg['sender']}: {text}"

    label = msg["kind"].replace("_", " ")
    if text:
        return f"{msg['sender']}: [{label}] {text}"
    return f"{msg['sender']}: [{label}]"


def message_lines(messages):
    """Return every message as one line, oldest first."""
    ordered = sorted(messages, key=lambda msg: msg["date"])
    lines = []
    for msg in ordered:
        lines.append(format_message(msg))
    return lines


def first_message_lines(messages):
    """Describe who sent the very first message, when, and what it was."""
    first = stats.first_message(messages)
    content = first["text"] or f"[{first['kind']}]"
    return [f"First message: {first['date']:%d %b %Y %H:%M}, {first['sender']}: {content}"]


def people_lines(messages):
    """Describe the total message count and each person's share of it."""
    total = len(messages)
    lines = [f"Total messages: {total}"]
    ranked = stats.messages_per_person(messages).most_common()
    for sender, count in ranked:
        percent = count / total * 100
        lines.append(f"  {sender}: {count} ({percent:.1f}%)")

    if len(ranked) == 2:
        top = ranked[0]
        other = ranked[1]
        difference = (top[1] - other[1]) / other[1] * 100
        lines.append(f"  {top[0]} sent {difference:.0f}% more messages than {other[0]}")
    return lines


def voice_and_video_lines(messages):
    """Describe how many voice and round video messages were sent and their total length."""
    lines = ["Lost information (not in the export as text):"]
    totals = stats.voice_and_video(messages)
    for kind, label in KIND_LABELS.items():
        count = totals[kind]["count"]
        duration = format_duration(totals[kind]["seconds"])
        lines.append(f"  {label}: {count} ({duration})")
    return lines


def top_days_lines(messages):
    """Describe the busiest days by number of messages."""
    lines = ["Busiest days:"]
    for day, count in stats.top_days(messages):
        lines.append(f"  {day:%d %b %Y}: {count} messages")
    return lines


def months_lines(messages):
    """Describe the number of messages sent in each month."""
    lines = ["Messages per month:"]
    for month, count in stats.messages_per_month(messages):
        lines.append(f"  {month}: {count}")
    return lines


def stats_lines(messages):
    """Return the full statistics report, with a blank line between sections."""
    sections = [first_message_lines, people_lines, voice_and_video_lines, top_days_lines, months_lines]
    lines = []
    for build_section in sections:
        if lines:
            lines.append("")
        lines.extend(build_section(messages))
    return lines
