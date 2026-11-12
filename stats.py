from collections import Counter


def messages_per_person(messages):
    """Count how many messages each person sent."""
    counts = Counter()
    for msg in messages:
        counts[msg["sender"]] += 1
    return counts


def first_message(messages):
    """Return the earliest message in the chat."""
    first = messages[0]
    for msg in messages:
        if msg["date"] < first["date"]:
            first = msg
    return first


def voice_and_video(messages):
    """Count voice and round video messages and add up their length in seconds."""
    # The export has no transcripts for these, so this is the "lost information".
    totals = {
        "voice_message": {"count": 0, "seconds": 0},
        "video_message": {"count": 0, "seconds": 0},
    }
    for msg in messages:
        kind = msg["kind"]
        if kind in totals:
            totals[kind]["count"] += 1
            totals[kind]["seconds"] += msg["duration"]
    return totals


def top_days(messages, how_many=10):
    """Return the days with the most messages, busiest first."""
    counts = Counter()
    for msg in messages:
        counts[msg["date"].date()] += 1
    return counts.most_common(how_many)


def messages_per_month(messages):
    """Count messages per month, sorted from oldest to newest."""
    counts = Counter()
    for msg in messages:
        month = msg["date"].strftime("%Y-%m")
        counts[month] += 1
    return sorted(counts.items())
