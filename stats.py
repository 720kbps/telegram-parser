from collections import Counter


def messages_per_person(messages):
    counts = Counter()
    for msg in messages:
        counts[msg["sender"]] += 1
    return counts


def first_message(messages):
    first = messages[0]
    for msg in messages:
        if msg["date"] < first["date"]:
            first = msg
    return first


def voice_and_video(messages):
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
    counts = Counter()
    for msg in messages:
        counts[msg["date"].date()] += 1
    return counts.most_common(how_many)


def messages_per_month(messages):
    counts = Counter()
    for msg in messages:
        month = msg["date"].strftime("%Y-%m")
        counts[month] += 1
    return sorted(counts.items())
