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


def conversation_starters(messages):
    """Count who sends the first message after a silence of CONVERSATION_GAP or more."""
    counts = Counter()
    previous = None
    for msg in messages:
        if previous is None or msg["date"] - previous["date"] >= CONVERSATION_GAP:
            counts[msg["sender"]] += 1
        previous = msg
    return counts


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
