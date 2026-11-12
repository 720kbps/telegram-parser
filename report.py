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


def starters_lines(messages):
    """Describe who starts conversations after a long silence."""
    gap_hours = int(stats.CONVERSATION_GAP.total_seconds() // 3600)
    starters = stats.conversation_starters(messages)
    total = sum(starters.values())
    lines = [f"Who starts conversations (first message after {gap_hours}+ hours of silence): {total} conversations"]
    # Go through everyone who sent messages, so someone who never starts still shows up with 0.
    rows = []
    for sender in stats.messages_per_person(messages):
        rows.append((starters[sender], sender))
    rows.sort(reverse=True)

    for count, sender in rows:
        percent = count / total * 100
        lines.append(f"  {sender}: {count} ({percent:.1f}%)")
    return lines


def reply_time_lines(messages):
    """Describe how fast each person usually replies to the other."""
    lines = ["Reply time:"]
    summary = stats.reply_times(messages)
    if not summary:
        lines.append("  Not enough back-and-forth to measure.")
        return lines

    for sender, times in summary.items():
        typical = format_duration(round(times["median"]))
        average = format_duration(round(times["average"]))
        replies = "reply" if times["count"] == 1 else "replies"
        lines.append(f"  {sender}: usually {typical}, on average {average} ({times['count']} {replies})")
    return lines


def calls_lines(calls):
    """Describe the calls: how many, how long, the longest one, and the ones nobody picked up."""
    summary = stats.call_summary(calls)
    lines = [f"Calls: {summary['total']}"]
    if summary["total"] == 0:
        return lines

    for caller, count in summary["started_by"].most_common():
        lines.append(f"  Started by {caller}: {count}")

    answered = summary["answered"]
    lines.append(f"  Answered: {answered}, total talk time {format_duration(summary['seconds'])}")
    if answered > 0:
        average = format_duration(round(summary["seconds"] / answered))
        longest = summary["longest"]
        lines.append(f"  Average call: {average}")
        lines.append(f"  Longest call: {format_duration(longest['duration'])} on {longest['date']:%d %b %Y}, started by {longest['caller']}")

    unanswered = summary["total"] - answered
    if unanswered > 0:
        reasons = []
        for reason, count in summary["unanswered_reasons"].most_common():
            reasons.append(f"{reason} {count}")
        lines.append(f"  Not answered: {unanswered} ({', '.join(reasons)})")
    return lines


def stats_lines(chat):
    """Return the full statistics report for a loaded chat, with a blank line between sections."""
    messages = chat["messages"]
    sections = [
        first_message_lines(messages),
        people_lines(messages),
        starters_lines(messages),
        reply_time_lines(messages),
        voice_and_video_lines(messages),
        calls_lines(chat["calls"]),
        top_days_lines(messages),
        months_lines(messages),
    ]
    lines = []
    for section in sections:
        if lines:
            lines.append("")
        lines.extend(section)
    return lines
