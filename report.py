import stats
from pathlib import Path

KIND_LABELS = {
    "voice_message": "Voice messages",
    "video_message": "Round video messages",
}

# Width in characters of the busiest hour's bar in the hour histogram.
HOUR_BAR_WIDTH = 30


def format_duration(total_seconds):
    """Turn a number of seconds into a short string like "3d 4h", "1h 5m" or "42s"."""
    days = total_seconds // 86400
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if days > 0:
        return f"{days}d {hours % 24}h"
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


# Media kinds worth naming in a day's description, in the order they're shown: (singular, plural).
DAY_MEDIA_LABELS = {
    "voice_message": ("voice message", "voice messages"),
    "video_message": ("round video", "round videos"),
    "sticker": ("sticker", "stickers"),
    "photo": ("photo", "photos"),
    "animation": ("GIF", "GIFs"),
    "video_file": ("video", "videos"),
}


def count_with_label(count, singular, plural):
    """Return text like "1 photo" or "3 photos"."""
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural}"


def day_media_parts(kind_counts):
    """Return a short "2 stickers"-style text for each notable media kind that was sent at least once."""
    parts = []
    for kind, labels in DAY_MEDIA_LABELS.items():
        count = kind_counts[kind]
        if count > 0:
            parts.append(count_with_label(count, labels[0], labels[1]))
    return parts


def day_description(messages, day):
    """Describe one day in a single line: shares, peak hour, media, top words and top emoji."""
    summary = stats.day_summary(messages, day)
    parts = []
    for sender, count in summary["per_person"]:
        percent = count / summary["total"] * 100
        parts.append(f"{sender} {percent:.0f}%")
    if summary["peak_hour"] is not None:
        parts.append(f"peak {summary['peak_hour']:02d}:00")
    parts.extend(day_media_parts(summary["kinds"]))
    if summary["words"]:
        parts.append("words: " + ", ".join(summary["words"]))
    if summary["emoji"]:
        parts.append("emoji: " + " ".join(summary["emoji"]))
    return " · ".join(parts)


def top_days_lines(messages):
    """Describe the busiest days by number of messages, with a short description of each."""
    lines = ["Busiest days:"]
    days = stats.top_days(messages)
    day_list = []
    for day, _ in days:
        day_list.append(day)
    # Grouping first means each day is summarized from its own messages, not the whole chat.
    grouped = stats.messages_on_days(messages, day_list)
    for day, count in days:
        lines.append(f"  {day:%d %b %Y}: {count} messages")
        lines.append("      " + day_description(grouped[day], day))
    return lines


def quietest_days_lines(messages):
    """Describe the worst days: the days you talked least, not counting days without any messages."""
    lines = ["Quietest days (fewest messages, not counting days with none):"]
    days = stats.quietest_days(messages)
    if not days:
        lines.append("  No messages to measure.")
        return lines

    for day, count in days:
        noun = "message" if count == 1 else "messages"
        lines.append(f"  {day:%d %b %Y}: {count} {noun}")
    return lines


def months_lines(messages):
    """Describe the number of messages sent in each month."""
    lines = ["Messages per month:"]
    for month, count in stats.messages_per_month(messages):
        lines.append(f"  {month}: {count}")
    return lines


def format_hour_range(hour):
    """Turn an hour like 22 into "22:00–23:00"."""
    return f"{hour:02d}:00–{(hour + 1) % 24:02d}:00"


def hour_histogram_lines(hour_counts):
    """Draw one bar per hour of the day, scaled so the busiest hour is HOUR_BAR_WIDTH wide."""
    most = max(hour_counts.values())
    lines = []
    for hour in range(24):
        count = hour_counts[hour]
        width = round(count / most * HOUR_BAR_WIDTH)
        # Keep a sliver for quiet hours so they don't look the same as empty ones.
        if count > 0 and width == 0:
            width = 1
        bar = "█" * width
        lines.append(f"  {hour:02d}:00 {bar.ljust(HOUR_BAR_WIDTH)} {count}")
    return lines


# Repeated messages longer than this many characters are cut short so each entry fits on one line.
REPEATED_TEXT_WIDTH = 40


def short_one_line(text, width):
    """Put the text on one line and cut it to `width` characters, ending with "…" if it was longer."""
    one_line = " ".join(text.split())
    if len(one_line) <= width:
        return one_line
    return one_line[:width - 1] + "…"


def repeated_message_lines(messages):
    """Describe the messages sent most often with the same text, and who sent them."""
    lines = ["Most repeated messages:"]
    repeated = stats.repeated_messages(messages)
    if not repeated:
        lines.append("  Nothing was sent more than once.")
        return lines

    for number, entry in enumerate(repeated, start=1):
        senders = []
        for sender, count in entry["per_person"].most_common():
            senders.append(f"{sender} {count}")
        text = short_one_line(entry["text"], REPEATED_TEXT_WIDTH)
        lines.append(f"  {number}. \"{text}\" × {entry['count']} ({', '.join(senders)})")
    return lines


def busiest_hour_lines(messages):
    """Describe the busiest hour of the day overall and per person, with a 24-hour histogram."""
    if not messages:
        return ["Busiest hour: no messages"]

    hour_counts = stats.busiest_hours(messages)
    best_hour = 0
    # Checking hours in order means a tie goes to the earliest hour.
    for hour in range(24):
        if hour_counts[hour] > hour_counts[best_hour]:
            best_hour = hour
    percent = hour_counts[best_hour] / len(messages) * 100
    lines = [f"Busiest hour: {format_hour_range(best_hour)} ({percent:.1f}% of messages)"]

    per_person = stats.busiest_hour_per_person(messages)
    for sender, _ in stats.messages_per_person(messages).most_common():
        hour, count = per_person[sender]
        noun = "message" if count == 1 else "messages"
        lines.append(f"  {sender}: {format_hour_range(hour)} ({count} {noun})")

    lines.append("Messages by hour:")
    lines.extend(hour_histogram_lines(hour_counts))
    return lines


def emoji_lines(messages):
    """Describe the emoji typed in messages: the most used overall and each person's favourites."""
    counts = stats.emoji_counts(messages)
    lines = [f"Emoji in messages: {counts['total']} used"]
    if counts["total"] == 0:
        return lines

    top = []
    for emoji, count in counts["overall"].most_common(10):
        top.append(f"{emoji} {count}")
    lines.append(f"  Top emoji: {', '.join(top)}")

    message_totals = stats.messages_per_person(messages)
    rows = []
    for sender, person_counts in counts["per_person"].items():
        rows.append((sum(person_counts.values()), sender))
    rows.sort(reverse=True)

    for used, sender in rows:
        if used == 0:
            lines.append(f"  {sender}: no emoji")
            continue
        percent = counts["messages_with_emoji"][sender] / message_totals[sender] * 100
        favourites = []
        for emoji, count in counts["per_person"][sender].most_common(3):
            favourites.append(f"{emoji} {count}")
        lines.append(f"  {sender}: {used} emoji, in {percent:.1f}% of their messages, favourites {', '.join(favourites)}")
    return lines


def emoji_day_line(totals):
    """Format one day's emoji totals, like "05 Jan 2023: 120 emoji in 200 messages (0.6 per message)"."""
    noun = "message" if totals["messages"] == 1 else "messages"
    rate = stats.emoji_per_message(totals)
    return f"  {totals['day']:%d %b %Y}: {totals['emoji']} emoji in {totals['messages']} {noun} ({rate:.1f} per message)"


def emoji_day_lines(messages):
    """Describe the most emoji-heavy days."""
    days = stats.emoji_heavy_days(messages)
    # Without the fallback every listed day has enough messages, so checking one tells which case it is.
    if days[0]["messages"] >= stats.MIN_MESSAGES_PER_DAY:
        which_days = f"days with {stats.MIN_MESSAGES_PER_DAY}+ messages"
    else:
        which_days = f"all days, since none had {stats.MIN_MESSAGES_PER_DAY}+ messages"
    lines = [f"Most emoji-heavy days ({which_days}):"]

    heavy_found = False
    for totals in days:
        # A day without emoji isn't emoji-heavy, even if it's among the top few.
        if totals["emoji"] > 0:
            lines.append(emoji_day_line(totals))
            heavy_found = True
    if not heavy_found:
        lines.append("  No day with enough messages had any emoji.")
    return lines


def emoji_ratio_lines(messages):
    """Describe how many emoji are typed per 100 messages, overall and per person, and the most emoji-heavy days."""
    ratio = stats.emoji_ratio(messages)
    overall = ratio["overall"]
    if overall["messages"] == 0:
        return ["Emoji per 100 messages: no messages"]

    lines = [f"Emoji per 100 messages: {overall['emoji'] / overall['messages'] * 100:.1f}"]
    rows = []
    for sender, counts in ratio["per_person"].items():
        rows.append((counts["emoji"] / counts["messages"] * 100, sender))
    # Sort on the ratio only, so a tie keeps the order people first appear in.
    rows.sort(key=lambda row: row[0], reverse=True)
    for per_hundred, sender in rows:
        lines.append(f"  {sender}: {per_hundred:.1f}")

    if overall["emoji"] == 0:
        lines.append("  No emoji typed at all, so there are no emoji-heavy days.")
        return lines
    lines.extend(emoji_day_lines(messages))
    return lines


def sticker_lines(messages):
    """Describe how many stickers were sent, the top sticker emoji and each person's favourite."""
    counts = stats.sticker_emoji_counts(messages)
    lines = [f"Stickers: {counts['total']} sent"]
    if counts["total"] == 0:
        return lines

    if counts["overall"]:
        top = []
        for emoji, count in counts["overall"].most_common(5):
            top.append(f"{emoji} {count}")
        lines.append(f"  Top sticker emoji: {', '.join(top)}")

    # Most stickers first; people with the same count are listed by name.
    rows = sorted(stats.stickers_per_person(messages).items(), key=lambda row: (-row[1], row[0]))
    for sender, sent in rows:
        noun = "sticker" if sent == 1 else "stickers"
        # most_common keeps the first-seen emoji first on a tie, so that one is the favourite.
        favourite = counts["per_person"][sender].most_common(1)
        if favourite:
            emoji, count = favourite[0]
            lines.append(f"  {sender}: {sent} {noun}, favourite {emoji} ({count})")
        else:
            lines.append(f"  {sender}: {sent} {noun}, none with an emoji")

    missing = counts["without_emoji"]
    if missing > 0:
        noun = "sticker has" if missing == 1 else "stickers have"
        lines.append(f"  {missing} {noun} no emoji")
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


# The user's own word list, kept next to this file and out of git because it may be private.
TRACKED_WORDS_PATH = Path(__file__).parent / "tracked_words.txt"


def load_tracked_words(path):
    """Read the tracked words file and return its entries, or an empty list if it does not exist."""
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as file:
        return stats.parse_tracked_words(file.read().splitlines())


def format_tracked_word(result):
    """Format one tracked word as "label: total (Alex 30, Sam 12), first used 05 Jan 2023"."""
    line = f"  {result['entry']['label']}: {result['total']}"
    if result["total"] == 0:
        return line

    people = []
    for sender, count in result["per_person"].most_common():
        people.append(f"{sender} {count}")
    return f"{line} ({', '.join(people)}), first used {result['first_used']:%d %b %Y}"


def tracked_word_lines(messages, path=TRACKED_WORDS_PATH):
    """Describe how often each word from the tracked words file was used, in the file's order."""
    entries = load_tracked_words(path)
    if not entries:
        return ["Tracked words: none set up (copy tracked_words.example.txt to tracked_words.txt and add words)"]

    lines = ["Tracked words:"]
    for result in stats.tracked_word_counts(messages, entries):
        lines.append(format_tracked_word(result))
    return lines


def streak_lines(messages):
    """Describe the longest run of consecutive days with messages and how many days had any."""
    lines = ["Streaks:"]
    streak = stats.longest_streak(messages)
    if streak["days"] == 0:
        lines.append("  No messages to measure.")
        return lines

    unit = "day" if streak["days"] == 1 else "days"
    lines.append(f"  Longest streak: {streak['days']} {unit} in a row ({streak['start']:%d %b %Y} – {streak['end']:%d %b %Y})")
    talked = stats.days_talked(messages)
    percent = talked["talked"] / talked["total"] * 100
    lines.append(f"  Talked on {talked['talked']} of {talked['total']} days ({percent:.1f}%)")
    return lines


def edited_lines(messages):
    """Describe how many messages were edited overall and per person, highest edit share first."""
    per_person = stats.edited_per_person(messages)
    total = len(messages)
    edited = 0
    for counts in per_person.values():
        edited += counts["edited"]
    if edited == 0:
        return ["Edited messages: none"]

    lines = [f"Edited messages: {edited} ({edited / total * 100:.1f}% of all messages)"]
    rows = []
    for sender, counts in per_person.items():
        rows.append((counts["edited"] / counts["total"] * 100, sender, counts))
    # Sort on the percentage only, so a tie keeps the order people first appear in.
    rows.sort(key=lambda row: row[0], reverse=True)

    for percent, sender, counts in rows:
        lines.append(f"  {sender}: {counts['edited']} of {counts['total']} ({percent:.1f}%)")
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


def times_word(count):
    """Return "1 time" or "N times" for a count."""
    if count == 1:
        return "1 time"
    return f"{count} times"


def reply_lines(messages):
    """Describe how often each person quotes a specific message and how often they get quoted."""
    lines = ["Replies (quoting a specific message):"]
    per_person = stats.replies_per_person(messages)
    if not per_person:
        lines.append("  No messages to measure.")
        return lines

    rows = []
    for sender, counts in per_person.items():
        rows.append((sender, counts))
    # Sort on the reply count only, so a tie keeps the order people first appear in.
    rows.sort(key=lambda row: row[1]["replies"], reverse=True)

    for sender, counts in rows:
        percent = counts["replies"] / counts["total"] * 100
        replied = times_word(counts["replies"])
        got = times_word(counts["replied_to"])
        lines.append(f"  {sender}: replied {replied} ({percent:.1f}% of their messages), got replied to {got}")
    return lines


def silence_lines(messages):
    """Describe the longest gaps between messages and who broke each silence."""
    lines = ["Longest silences:"]
    silences = stats.longest_silences(messages)
    if not silences:
        lines.append("  Not enough messages to measure.")
        return lines

    for number, silence in enumerate(silences, start=1):
        duration = format_duration(round(silence["seconds"]))
        start = f"{silence['start']:%d %b %Y %H:%M}"
        end = f"{silence['end']:%d %b %Y %H:%M}"
        lines.append(f"  {number}. {duration}: {start} → {end}, broken by {silence['broken_by']}")
    return lines


def double_text_lines(messages):
    """Describe how often each person texts again after waiting over an hour without a reply."""
    gap_hours = int(stats.DOUBLE_TEXT_GAP.total_seconds() // 3600)
    lines = [f"Double-texting (texting again after more than {gap_hours}h without a reply):"]
    totals = stats.double_texts(messages)
    if not totals:
        lines.append("  No messages to measure.")
        return lines

    # Python's sort is stable, so people with the same count keep the order they first appeared in.
    ranked = sorted(totals.items(), key=lambda item: item[1]["count"], reverse=True)
    for sender, result in ranked:
        if result["count"] == 0:
            lines.append(f"  {sender}: 0 times")
            continue
        wait = format_duration(round(result["longest_wait"]))
        date = f"{result['longest_date']:%d %b %Y}"
        lines.append(f"  {sender}: {times_word(result['count'])}, longest wait {wait} before texting again ({date})")
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
        reply_lines(messages),
        double_text_lines(messages),
        edited_lines(messages),
        busiest_hour_lines(messages),
        streak_lines(messages),
        silence_lines(messages),
        voice_and_video_lines(messages),
        repeated_message_lines(messages),
        tracked_word_lines(messages),
        emoji_lines(messages),
        emoji_ratio_lines(messages),
        sticker_lines(messages),
        calls_lines(chat["calls"]),
        top_days_lines(messages),
        quietest_days_lines(messages),
        months_lines(messages),
    ]
    lines = []
    for section in sections:
        if lines:
            lines.append("")
        lines.extend(section)
    return lines
