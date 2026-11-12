import statistics
from collections import Counter
from datetime import timedelta

# A message after this much silence starts a new conversation instead of replying.
CONVERSATION_GAP = timedelta(hours=6)


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


def busiest_hours(messages):
    """Count messages by hour of the day (0-23)."""
    counts = Counter()
    for msg in messages:
        counts[msg["date"].hour] += 1
    return counts


def busiest_hour_per_person(messages):
    """Return each person's busiest hour as {sender: (hour, count)}."""
    hours_by_sender = {}
    for msg in messages:
        hours_by_sender.setdefault(msg["sender"], Counter())[msg["date"].hour] += 1

    result = {}
    for sender, counts in hours_by_sender.items():
        best_hour = None
        # Going through hours in order means a tie goes to the earliest hour.
        for hour in range(24):
            if best_hour is None or counts[hour] > counts[best_hour]:
                best_hour = hour
        result[sender] = (best_hour, counts[best_hour])
    return result


def conversation_starters(messages):
    """Count who sends the first message after a silence of CONVERSATION_GAP or more."""
    counts = Counter()
    previous = None
    for msg in messages:
        if previous is None or msg["date"] - previous["date"] >= CONVERSATION_GAP:
            counts[msg["sender"]] += 1
        previous = msg
    return counts


def talked_days(messages):
    """Return the distinct calendar days that have at least one message, oldest first."""
    days = set()
    for msg in messages:
        days.add(msg["date"].date())
    return sorted(days)


def longest_streak(messages):
    """Return the longest run of consecutive days with messages as {"days", "start", "end"}."""
    best = {"days": 0, "start": None, "end": None}
    run_start = None
    previous = None
    for day in talked_days(messages):
        if previous is None or day - previous != timedelta(days=1):
            run_start = day
        run_length = (day - run_start).days + 1
        # Only a strictly longer run replaces the best, so ties keep the earliest one.
        if run_length > best["days"]:
            best = {"days": run_length, "start": run_start, "end": day}
        previous = day
    return best


def days_talked(messages):
    """Return how many distinct days had messages and how many calendar days the chat spans."""
    days = talked_days(messages)
    if not days:
        return {"talked": 0, "total": 0}
    total = (days[-1] - days[0]).days + 1
    return {"talked": len(days), "total": total}


def reply_times(messages):
    """Return each person's median and average reply time in seconds, plus how many replies were measured."""
    # A reply is a message from a different person than the one before it. It's measured from the
    # other person's last message, and gaps of CONVERSATION_GAP or more count as new conversations.
    seconds_by_sender = {}
    previous = None
    for msg in messages:
        if previous is not None and msg["sender"] != previous["sender"]:
            gap = msg["date"] - previous["date"]
            if gap < CONVERSATION_GAP:
                seconds_by_sender.setdefault(msg["sender"], []).append(gap.total_seconds())
        previous = msg

    summary = {}
    for sender, seconds in seconds_by_sender.items():
        summary[sender] = {
            "count": len(seconds),
            "median": statistics.median(seconds),
            "average": statistics.mean(seconds),
        }
    return summary


def longest_silences(messages, how_many=3):
    """Return the longest gaps between two consecutive messages, longest first, with who broke each one."""
    gaps = []
    previous = None
    for msg in messages:
        if previous is not None:
            gap = msg["date"] - previous["date"]
            gaps.append({
                "seconds": gap.total_seconds(),
                "start": previous["date"],
                "end": msg["date"],
                "broken_by": msg["sender"],
            })
        previous = msg

    # Python's sort is stable, so equal gaps stay in the order they happened.
    gaps.sort(key=lambda gap: gap["seconds"], reverse=True)
    return gaps[:how_many]


def call_summary(calls):
    """Add up calls: how many, total talk time, the longest one, who called, and why unanswered ones ended."""
    summary = {
        "total": len(calls),
        "answered": 0,
        "seconds": 0,
        "longest": None,
        "started_by": Counter(),
        "unanswered_reasons": Counter(),
    }
    for call in calls:
        summary["started_by"][call["caller"]] += 1
        if call["duration"] > 0:
            summary["answered"] += 1
            summary["seconds"] += call["duration"]
            if summary["longest"] is None or call["duration"] > summary["longest"]["duration"]:
                summary["longest"] = call
        else:
            summary["unanswered_reasons"][call["outcome"]] += 1
    return summary
