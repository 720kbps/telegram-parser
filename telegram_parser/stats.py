"""One small function per fun fact. Each takes the loaded messages (or calls) and returns plain data."""

import statistics
from collections import Counter
from datetime import timedelta

from telegram_parser.emoji_finder import find_emoji
from telegram_parser.text_tools import normalize_text, split_words


# A message after this much silence starts a new conversation instead of replying.
CONVERSATION_GAP = timedelta(hours=6)

# Texting again after waiting longer than this, without getting a reply, counts as a double text.
DOUBLE_TEXT_GAP = timedelta(hours=1)

# A day needs at least this many messages to be one of the most emoji-heavy days,
# so a day with only a couple of messages can't win by accident.
MIN_MESSAGES_PER_DAY = 50

# Punctuation at the end of a message doesn't change what it says, so "ok", "Ok." and "OK!" match.
TRAILING_PUNCTUATION = ".,!?…"


# --------------------------------------------------------------------------------------------------
# The basics: who sent what
# --------------------------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------------------------
# Conversations: who starts, how fast and how people reply
# --------------------------------------------------------------------------------------------------


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


def replies_per_person(messages):
    """Count each person's replies, total messages, and how often others replied to them."""
    sender_by_id = {}
    result = {}
    for msg in messages:
        sender_by_id[msg["id"]] = msg["sender"]
        result.setdefault(msg["sender"], {"replies": 0, "total": 0, "replied_to": 0})

    for msg in messages:
        counts = result[msg["sender"]]
        counts["total"] += 1
        if msg["reply_to"] is None:
            continue
        counts["replies"] += 1
        # The quoted message may be missing from the export (deleted or older), so nobody gets credit.
        quoted_sender = sender_by_id.get(msg["reply_to"])
        if quoted_sender is not None and quoted_sender != msg["sender"]:
            result[quoted_sender]["replied_to"] += 1
    return result


def double_texts(messages):
    """Count each person's double texts: messages sent more than DOUBLE_TEXT_GAP after their own last one, with no reply between."""
    # Quick follow-ups within the hour are just someone typing in several messages, not a double text.
    # There's no upper limit: texting again the next morning after being left on read counts too.
    # "longest_wait" is in seconds, and "longest_date" is when they finally texted again.
    result = {}
    previous = None
    for msg in messages:
        totals = result.setdefault(msg["sender"], {"count": 0, "longest_wait": 0, "longest_date": None})
        if previous is not None and msg["sender"] == previous["sender"]:
            wait = (msg["date"] - previous["date"]).total_seconds()
            if wait > DOUBLE_TEXT_GAP.total_seconds():
                totals["count"] += 1
                # Only a strictly longer wait replaces the record, so ties keep the earliest one.
                if wait > totals["longest_wait"]:
                    totals["longest_wait"] = wait
                    totals["longest_date"] = msg["date"]
        previous = msg
    return result


def edited_per_person(messages):
    """Count each person's edited messages and their total messages, media included."""
    result = {}
    for msg in messages:
        sender = msg["sender"]
        if sender not in result:
            result[sender] = {"edited": 0, "total": 0}
        result[sender]["total"] += 1
        if msg["edited"]:
            result[sender]["edited"] += 1
    return result


# --------------------------------------------------------------------------------------------------
# Time: hours, streaks and silences
# --------------------------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------------------------
# Media and calls
# --------------------------------------------------------------------------------------------------


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


def sticker_emoji_counts(messages):
    """Count the emoji linked to each sticker, overall and per person, plus stickers without one."""
    result = {"overall": Counter(), "per_person": {}, "total": 0, "without_emoji": 0}
    for msg in messages:
        if msg["kind"] != "sticker":
            continue
        result["total"] += 1
        # Add the sender even when the emoji is empty, so everyone who sent stickers is listed.
        person_counts = result["per_person"].setdefault(msg["sender"], Counter())
        emoji = msg["sticker_emoji"]
        if emoji == "":
            result["without_emoji"] += 1
        else:
            result["overall"][emoji] += 1
            person_counts[emoji] += 1
    return result


def stickers_per_person(messages):
    """Count how many sticker messages each person sent, with or without an emoji."""
    counts = Counter()
    for msg in messages:
        if msg["kind"] == "sticker":
            counts[msg["sender"]] += 1
    return counts


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


# --------------------------------------------------------------------------------------------------
# What you write: repeated messages, tracked words and emoji
# --------------------------------------------------------------------------------------------------


def normalize_message(text):
    """Return the text in the form used to compare repeated messages."""
    # split() drops whitespace at both ends and turns inner runs of spaces and newlines into one space.
    joined = " ".join(normalize_text(text).split())
    # Strip again so "ok !" also becomes "ok".
    return joined.rstrip(TRAILING_PUNCTUATION).strip()


def repeated_messages(messages, how_many=10):
    """Return the texts sent at least twice, most repeated first, with each one's count and senders."""
    found = {}
    for msg in messages:
        key = normalize_message(msg["text"])
        if key == "":
            continue
        entry = found.get(key)
        if entry is None:
            entry = {"count": 0, "per_person": Counter(), "spellings": Counter()}
            found[key] = entry
        entry["count"] += 1
        entry["per_person"][msg["sender"]] += 1
        entry["spellings"][msg["text"].strip()] += 1

    repeated = []
    for entry in found.values():
        if entry["count"] < 2:
            continue
        # Show the spelling people used most; most_common keeps the first one seen on a tie.
        shown = entry["spellings"].most_common(1)[0][0]
        repeated.append({"text": shown, "count": entry["count"], "per_person": entry["per_person"]})
    # The dict keeps the order texts were first sent (messages come oldest first), and the
    # sort is stable, so on a tie the text that was first sent earliest stays ahead.
    repeated.sort(key=lambda item: item["count"], reverse=True)
    return repeated[:how_many]


def parse_tracked_words(lines):
    """Turn raw lines from the tracked words file into entries like {"label", "word", "prefix"}."""
    entries = []
    for line in lines:
        label = line.strip()
        if label == "" or label.startswith("#"):
            continue
        prefix = label.endswith("*")
        word = normalize_text(label.rstrip("*").strip())
        # A line that is only "*" would match every word, so it is skipped.
        if word == "":
            continue
        entries.append({"label": label, "word": word, "prefix": prefix})
    return entries


def build_word_lookup(entries):
    """Group entry positions by whole word and by prefix, so each message word is checked quickly."""
    whole = {}
    prefixes = {}
    for index, entry in enumerate(entries):
        if entry["prefix"]:
            prefixes.setdefault(entry["word"], []).append(index)
        else:
            whole.setdefault(entry["word"], []).append(index)
    prefix_lengths = sorted(set(len(prefix) for prefix in prefixes))
    return whole, prefixes, prefix_lengths


def matching_entries(word, whole, prefixes, prefix_lengths):
    """Return the positions of every entry that matches one normalized word."""
    matches = list(whole.get(word, []))
    for length in prefix_lengths:
        if len(word) < length:
            break
        matches.extend(prefixes.get(word[:length], []))
    return matches


def tracked_word_counts(messages, entries):
    """Count each entry overall and per sender, with the date it was first used (or None)."""
    results = []
    for entry in entries:
        results.append({"entry": entry, "total": 0, "per_person": Counter(), "first_used": None})
    whole, prefixes, prefix_lengths = build_word_lookup(entries)

    # Each message is split once and every word is looked up, instead of scanning the chat per entry.
    for msg in messages:
        if not msg["text"]:
            continue
        for word in split_words(msg["text"]):
            for index in matching_entries(word, whole, prefixes, prefix_lengths):
                result = results[index]
                result["total"] += 1
                result["per_person"][msg["sender"]] += 1
                day = msg["date"].date()
                if result["first_used"] is None or day < result["first_used"]:
                    result["first_used"] = day
    return results


def emoji_counts(messages):
    """Count the emoji typed in message text, overall and per person, and how many messages had any."""
    result = {"overall": Counter(), "per_person": {}, "messages_with_emoji": Counter(), "total": 0}
    for msg in messages:
        # Add everyone, so a person who never uses emoji still shows up in the report.
        person_counts = result["per_person"].setdefault(msg["sender"], Counter())
        found = find_emoji(msg["text"])
        if not found:
            continue
        result["messages_with_emoji"][msg["sender"]] += 1
        result["total"] += len(found)
        for emoji in found:
            result["overall"][emoji] += 1
            person_counts[emoji] += 1
    return result


def emoji_ratio(messages):
    """Count the emoji typed in message text and the messages sent, overall and per person."""
    result = {"overall": {"emoji": 0, "messages": 0}, "per_person": {}}
    for msg in messages:
        found = len(find_emoji(msg["text"]))
        # Add everyone, so a person who never uses emoji still shows up with 0.
        person = result["per_person"].setdefault(msg["sender"], {"emoji": 0, "messages": 0})
        person["emoji"] += found
        person["messages"] += 1
        result["overall"]["emoji"] += found
        result["overall"]["messages"] += 1
    return result


def emoji_per_day(messages):
    """Count the emoji typed and the messages sent on each day, oldest day first."""
    totals_by_day = {}
    for msg in messages:
        day = msg["date"].date()
        totals = totals_by_day.get(day)
        if totals is None:
            totals = {"day": day, "emoji": 0, "messages": 0}
            totals_by_day[day] = totals
        totals["emoji"] += len(find_emoji(msg["text"]))
        totals["messages"] += 1
    return sorted(totals_by_day.values(), key=lambda totals: totals["day"])


def emoji_per_message(totals):
    """Return the emoji per message for a day's {"emoji", "messages"} totals."""
    return totals["emoji"] / totals["messages"]


def emoji_heavy_days(messages, how_many=3):
    """Return the days with the most emoji per message, among days with enough messages."""
    days = emoji_per_day(messages)
    busy_days = []
    for totals in days:
        if totals["messages"] >= MIN_MESSAGES_PER_DAY:
            busy_days.append(totals)
    # A short chat may have no day that busy; using every day still gives an answer.
    if not busy_days:
        busy_days = days

    # The days are oldest first and Python's sort is stable (also with reverse), so ties keep the earlier day.
    heaviest = sorted(busy_days, key=emoji_per_message, reverse=True)
    return heaviest[:how_many]


# --------------------------------------------------------------------------------------------------
# Days and months
# --------------------------------------------------------------------------------------------------


def top_days(messages, how_many=10):
    """Return the days with the most messages, busiest first."""
    counts = Counter()
    for msg in messages:
        counts[msg["date"].date()] += 1
    return counts.most_common(how_many)


def quietest_days(messages, how_many=5):
    """Return the days with the fewest messages, quietest first, counting only days with at least one."""
    counts = Counter()
    for msg in messages:
        counts[msg["date"].date()] += 1
    # Sort by date first; the sort by count is stable, so on a tie the earlier day comes first.
    days = sorted(counts.items())
    days.sort(key=lambda item: item[1])
    return days[:how_many]


def messages_on_days(messages, days):
    """Group the messages sent on the given days, in one pass, as {day: [messages]}."""
    grouped = {}
    for day in days:
        grouped[day] = []
    for msg in messages:
        day = msg["date"].date()
        if day in grouped:
            grouped[day].append(msg)
    return grouped


def top_long_words(messages, how_many=3, min_length=5):
    """Return the most used words that have at least min_length letters, most used first."""
    counts = Counter()
    for msg in messages:
        # Long words are a cheap way to skip filler like "the", "si" or "ok".
        for word in split_words(msg["text"]):
            if len(word) >= min_length:
                counts[word] += 1
    top = []
    for word, _ in counts.most_common(how_many):
        top.append(word)
    return top


def day_summary(messages, day):
    """Summarize one calendar day: who wrote how much, the peak hour, media kinds, top words and emoji."""
    day_messages = []
    for msg in messages:
        if msg["date"].date() == day:
            day_messages.append(msg)

    summary = {
        "total": len(day_messages),
        "per_person": messages_per_person(day_messages).most_common(),
        "peak_hour": None,
        "kinds": Counter(),
        "words": top_long_words(day_messages),
        "emoji": [],
    }
    hours = busiest_hours(day_messages).most_common(1)
    if hours:
        summary["peak_hour"] = hours[0][0]
    for msg in day_messages:
        summary["kinds"][msg["kind"]] += 1
    for emoji, _ in emoji_counts(day_messages)["overall"].most_common(3):
        summary["emoji"].append(emoji)
    return summary


def messages_per_month(messages):
    """Count messages per month, sorted from oldest to newest."""
    counts = Counter()
    for msg in messages:
        month = msg["date"].strftime("%Y-%m")
        counts[month] += 1
    return sorted(counts.items())
