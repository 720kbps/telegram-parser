"""Build one self-contained HTML page in a "Wrapped" style from a loaded chat, with one card per fun fact."""

from datetime import datetime
from html import escape

from telegram_parser import report, stats

# Each person gets the same color everywhere on the page, in order of who sent the most messages.
PERSON_COLORS = ["var(--person-1)", "var(--person-2)", "var(--person-3)", "var(--person-4)"]

# Everything is inline (no fonts, scripts or images from the internet), so the page works offline
# and opening it never sends anything anywhere.
PAGE_STYLE = """
:root {
  --bg: #0f0f17; --card: #1a1a26; --text: #f2f2f7; --muted: #9a9ab0; --track: #2a2a3a;
  --accent: #8b7cff; --person-1: #8b7cff; --person-2: #ff7eb6; --person-3: #5ad1c8; --person-4: #ffc857;
}
@media (prefers-color-scheme: light) {
  :root { --bg: #f5f4fb; --card: #ffffff; --text: #1b1b29; --muted: #6b6b80; --track: #e6e4f2; }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text); line-height: 1.45;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 980px; margin: 0 auto; padding: 24px 16px 64px; }
.hero {
  border-radius: 28px; padding: 48px 32px; color: #fff;
  background: linear-gradient(135deg, #6d5dfc 0%, #c855d8 55%, #ff7eb6 100%);
}
.hero .eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .8rem; opacity: .85; }
.hero h1 { font-size: clamp(2.2rem, 7vw, 4rem); line-height: 1.05; margin: 8px 0 12px; overflow-wrap: anywhere; }
.hero .facts { display: flex; flex-wrap: wrap; gap: 8px 24px; font-size: 1.05rem; opacity: .95; }
h2.group {
  font-size: .8rem; letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
  margin: 44px 4px 12px;
}
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 16px; }
.card { background: var(--card); border-radius: 22px; padding: 22px; break-inside: avoid; min-width: 0; }
.card.wide { grid-column: 1 / -1; }
.card h3 { margin: 0 0 4px; font-size: .95rem; color: var(--muted); font-weight: 600; }
.big { font-size: clamp(2rem, 6vw, 2.9rem); font-weight: 800; line-height: 1.1; margin: 4px 0; overflow-wrap: anywhere; }
.sub { color: var(--muted); }
.split { display: flex; height: 14px; border-radius: 7px; overflow: hidden; background: var(--track); margin: 16px 0 10px; }
.split span { display: block; height: 100%; }
.legend { display: flex; flex-direction: column; gap: 4px; font-size: .95rem; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }
.rows { list-style: none; padding: 0; margin: 14px 0 0; }
.rows li { display: flex; justify-content: space-between; gap: 16px; padding: 8px 0; border-top: 1px solid var(--track); }
.rows li span:last-child { text-align: right; color: var(--muted); }
.days li { display: block; }
.days .when { display: flex; justify-content: space-between; gap: 16px; font-weight: 600; }
.days .what { color: var(--muted); font-size: .9rem; margin-top: 2px; overflow-wrap: anywhere; }
ol.rows { counter-reset: item; }
.quote { font-size: 1.15rem; border-left: 4px solid var(--accent); padding-left: 14px; margin: 14px 0 0; overflow-wrap: anywhere; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 14px; }
.tile { background: var(--bg); border-radius: 16px; padding: 14px; }
.tile .mid { font-size: 1.8rem; font-weight: 800; margin: 4px 0 2px; }
.emoji-row { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 14px; }
.emoji-row div { text-align: center; }
.emoji-row .e { font-size: 2.3rem; line-height: 1.1; }
.emoji-row .n { color: var(--muted); font-size: .85rem; }
.chart { width: 100%; height: auto; margin-top: 14px; display: block; }
.chart .bar { fill: var(--accent); opacity: .4; }
.chart .bar.top { opacity: 1; }
.chart .axis { fill: var(--muted); font-size: 13px; }
footer { text-align: center; color: var(--muted); font-size: .85rem; margin-top: 56px; }
@media print {
  body { background: #fff; color: #000; }
  .card { border: 1px solid #ddd; }
}
"""


# --------------------------------------------------------------------------------------------------
# Building blocks: cards, bars, legends and charts
# --------------------------------------------------------------------------------------------------


def card(title, big="", sub="", body="", wide=False):
    """Return one fun-fact card; title, big and sub are plain text, body is ready-made (escaped) HTML."""
    css = "card wide" if wide else "card"
    parts = [f'<section class="{css}">', f"<h3>{escape(title)}</h3>"]
    if big:
        parts.append(f'<div class="big">{escape(big)}</div>')
    if sub:
        parts.append(f'<div class="sub">{escape(sub)}</div>')
    parts.append(body)
    parts.append("</section>")
    return "\n".join(parts)


def people_colors(messages):
    """Give each sender a color, in order of who sent the most messages."""
    colors = {}
    for index, (sender, _) in enumerate(stats.messages_per_person(messages).most_common()):
        colors[sender] = PERSON_COLORS[index % len(PERSON_COLORS)]
    return colors


def split_bar(rows, colors):
    """Draw one bar split into each person's share, from (sender, count) rows."""
    total = 0
    for _, count in rows:
        total += count
    if total == 0:
        return ""
    segments = []
    for sender, count in rows:
        width = count / total * 100
        segments.append(f'<span style="width:{width:.2f}%;background:{colors[sender]}" title="{escape(sender)}"></span>')
    return f'<div class="split">{"".join(segments)}</div>'


def legend(rows, colors):
    """List each person with their count and share, matching the colors of split_bar."""
    total = 0
    for _, count in rows:
        total += count
    items = []
    for sender, count in rows:
        percent = count / total * 100 if total else 0
        dot = f'<span class="dot" style="background:{colors[sender]}"></span>'
        items.append(f"<div>{dot}{escape(sender)} · {count:,} ({percent:.1f}%)</div>")
    return f'<div class="legend">{"".join(items)}</div>'


def row_list(rows, css="rows"):
    """Return a list where each (left, right) pair of plain-text strings is one line."""
    items = []
    for left, right in rows:
        items.append(f"<li><span>{escape(left)}</span><span>{escape(right)}</span></li>")
    return f'<ul class="{css}">{"".join(items)}</ul>'


def bar_chart_svg(values, labels, axis_labels, highlight=None):
    """Draw a bar chart as inline SVG; hovering a bar shows its label and value."""
    width = 640
    height = 200
    chart_height = 165
    # Room on both sides so the first and last axis labels aren't cut off.
    side = 24
    most = max(values) if values and max(values) > 0 else 1
    slot = (width - 2 * side) / len(values)
    bar_width = slot * 0.72
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img">']
    for index, value in enumerate(values):
        bar_height = value / most * chart_height
        # Keep quiet-but-not-empty bars visible.
        if value > 0 and bar_height < 2:
            bar_height = 2
        x = side + index * slot + (slot - bar_width) / 2
        css = "bar top" if index == highlight else "bar"
        parts.append(
            f'<rect class="{css}" x="{x:.1f}" y="{chart_height - bar_height:.1f}" width="{bar_width:.1f}" '
            f'height="{bar_height:.1f}" rx="3"><title>{escape(labels[index])}: {value:,}</title></rect>'
        )
    # Label only some bars so the axis doesn't get crowded.
    label_every = max(1, len(values) // 8)
    for index in range(0, len(values), label_every):
        x = side + index * slot + slot / 2
        parts.append(f'<text class="axis" x="{x:.1f}" y="{height - 8}" text-anchor="middle">{escape(axis_labels[index])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def emoji_row(counter, how_many=5):
    """Show the most used emoji large, each with its count underneath."""
    items = []
    for emoji, count in counter.most_common(how_many):
        items.append(f'<div><div class="e">{escape(emoji)}</div><div class="n">{count:,}</div></div>')
    return f'<div class="emoji-row">{"".join(items)}</div>'


def duration(seconds):
    """Format seconds like the text report does, e.g. "3d 4h" or "1m 7s"."""
    return report.format_duration(round(seconds))


def counted(count, singular, plural):
    """Return text like "1 sticker" or "2,488 stickers"."""
    if count == 1:
        return f"1 {singular}"
    return f"{count:,} {plural}"


# --------------------------------------------------------------------------------------------------
# The basics
# --------------------------------------------------------------------------------------------------


def hero(chat):
    """Return the big header with the chat's name, the dates it covers and the headline numbers."""
    messages = chat["messages"]
    first_day = messages[0]["date"]
    last_day = messages[-1]["date"]
    talked = stats.days_talked(messages)
    facts = [
        f"{first_day:%d %b %Y} – {last_day:%d %b %Y}",
        f"{len(messages):,} messages",
        f"{len(chat['calls']):,} calls",
        f"{talked['talked']:,} days talked",
    ]
    fact_html = "".join(f"<span>{escape(fact)}</span>" for fact in facts)
    return (
        '<header class="hero">'
        '<div class="eyebrow">Telegram chat, wrapped</div>'
        f"<h1>{escape(chat['name'])}</h1>"
        f'<div class="facts">{fact_html}</div>'
        "</header>"
    )


def messages_card(messages, colors):
    """Show the total number of messages and each person's share."""
    ranked = stats.messages_per_person(messages).most_common()
    sub = "messages in total"
    if len(ranked) == 2 and ranked[1][1] > 0:
        more = (ranked[0][1] - ranked[1][1]) / ranked[1][1] * 100
        sub = f"messages in total. {ranked[0][0]} sent {more:.0f}% more than {ranked[1][0]}."
    body = split_bar(ranked, colors) + legend(ranked, colors)
    return card("Messages", f"{len(messages):,}", sub, body)


def first_message_card(messages):
    """Show who sent the very first message, when, and what it said."""
    first = stats.first_message(messages)
    text = first["text"] or f"[{first['kind'].replace('_', ' ')}]"
    body = f'<p class="quote">{escape(report.short_one_line(text, 280))}</p>'
    return card("The very first message", first["sender"], f"{first['date']:%d %B %Y, %H:%M}", body)


# --------------------------------------------------------------------------------------------------
# Conversations
# --------------------------------------------------------------------------------------------------


def starters_card(messages, colors):
    """Show who usually starts the conversation after a long silence."""
    starters = stats.conversation_starters(messages)
    total = sum(starters.values())
    rows = []
    for sender in colors:
        rows.append((sender, starters[sender]))
    rows.sort(key=lambda row: row[1], reverse=True)

    gap_hours = int(stats.CONVERSATION_GAP.total_seconds() // 3600)
    percent = rows[0][1] / total * 100
    sub = f"of {total:,} conversations were started by {rows[0][0]} (a new one starts after {gap_hours}+ hours of silence)"
    return card("Who starts the conversation", f"{percent:.0f}%", sub, split_bar(rows, colors) + legend(rows, colors))


def reply_time_card(messages, colors):
    """Show how fast each person usually replies, as one tile per person."""
    summary = stats.reply_times(messages)
    if not summary:
        return ""
    tiles = []
    for sender, times in summary.items():
        dot = f'<span class="dot" style="background:{colors[sender]}"></span>'
        tiles.append(
            f'<div class="tile">{dot}{escape(sender)}'
            f'<div class="mid">{escape(duration(times["median"]))}</div>'
            f'<div class="sub">usually · {escape(duration(times["average"]))} on average</div></div>'
        )
    body = f'<div class="tiles">{"".join(tiles)}</div>'
    return card("Reply time", "", "How long it usually takes to answer the other person", body)


def double_text_card(messages):
    """Show who texts again most often after being left without a reply for over an hour."""
    totals = stats.double_texts(messages)
    ranked = sorted(totals.items(), key=lambda item: item[1]["count"], reverse=True)
    top_sender, top = ranked[0]
    if top["count"] == 0:
        return ""
    gap_hours = int(stats.DOUBLE_TEXT_GAP.total_seconds() // 3600)
    sub = f"times {top_sender} texted again after more than {gap_hours}h without a reply"
    rows = []
    for sender, result in ranked:
        if result["count"] == 0:
            rows.append((sender, "never"))
        else:
            rows.append((sender, f"{counted(result['count'], 'time', 'times')} · longest wait {duration(result['longest_wait'])}"))
    return card("Double-texting", f"{top['count']:,}", sub, row_list(rows))


def replies_edits_card(messages):
    """Show how often each person quotes a message in a reply and how often they edit messages."""
    replies = stats.replies_per_person(messages)
    edits = stats.edited_per_person(messages)
    total_edited = 0
    rows = []
    for sender, counts in edits.items():
        total_edited += counts["edited"]
        percent = counts["edited"] / counts["total"] * 100
        quoted = replies[sender]["replies"]
        quoted_text = counted(quoted, "quoted reply", "quoted replies")
        edited_text = counted(counts["edited"], "edit", "edits")
        rows.append((sender, f"{quoted_text} · {edited_text} ({percent:.0f}%)"))
    percent_all = total_edited / len(messages) * 100
    sub = f"messages were edited after sending ({percent_all:.1f}% of all of them)"
    return card("Replies and edits", f"{total_edited:,}", sub, row_list(rows))


# --------------------------------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------------------------------


def busiest_hour_card(messages, colors):
    """Show the busiest hour of the day, each person's busiest hour and a 24-hour chart."""
    counts = stats.busiest_hours(messages)
    best = 0
    for hour in range(24):
        if counts[hour] > counts[best]:
            best = hour
    values = []
    labels = []
    for hour in range(24):
        values.append(counts[hour])
        labels.append(f"{hour:02d}:00")

    rows = []
    per_person = stats.busiest_hour_per_person(messages)
    for sender in colors:
        hour, count = per_person[sender]
        rows.append((sender, f"{report.format_hour_range(hour)} · {counted(count, 'message', 'messages')}"))
    sub = f"is the busiest hour, with {counts[best] / len(messages) * 100:.1f}% of all messages"
    body = bar_chart_svg(values, labels, labels, best) + row_list(rows)
    return card("Busiest hour of the day", report.format_hour_range(best), sub, body, wide=True)


def streak_card(messages):
    """Show the longest run of days in a row with messages and how many days you talked at all."""
    streak = stats.longest_streak(messages)
    talked = stats.days_talked(messages)
    unit = "day" if streak["days"] == 1 else "days"
    sub = f"in a row, from {streak['start']:%d %b %Y} to {streak['end']:%d %b %Y}"
    percent = talked["talked"] / talked["total"] * 100
    body = (
        f'<div class="split"><span style="width:{percent:.2f}%;background:var(--accent)"></span></div>'
        f'<div class="sub">Talked on {talked["talked"]:,} of {talked["total"]:,} days ({percent:.1f}%)</div>'
    )
    return card("Longest streak", f"{streak['days']:,} {unit}", sub, body)


def silence_card(messages):
    """Show the longest gap without any messages and who broke it."""
    silences = stats.longest_silences(messages)
    if not silences:
        return ""
    top = silences[0]
    sub = f"without a message, {top['start']:%d %b %Y} → {top['end']:%d %b %Y}. {top['broken_by']} broke the silence."
    rows = []
    for silence in silences[1:]:
        rows.append((f"{silence['start']:%d %b %Y} → {silence['end']:%d %b %Y}", duration(silence["seconds"])))
    body = row_list(rows) if rows else ""
    return card("Longest silence", duration(top["seconds"]), sub, body)


# --------------------------------------------------------------------------------------------------
# Media and calls
# --------------------------------------------------------------------------------------------------


def calls_card(calls):
    """Show the total time on calls, the longest call and the calls nobody picked up."""
    summary = stats.call_summary(calls)
    if summary["total"] == 0:
        return ""
    rows = []
    for caller, count in summary["started_by"].most_common():
        rows.append((f"Calls started by {caller}", f"{count:,}"))
    if summary["answered"] > 0:
        longest = summary["longest"]
        rows.append(("Average call", duration(summary["seconds"] / summary["answered"])))
        rows.append(("Longest call", f"{duration(longest['duration'])} on {longest['date']:%d %b %Y}"))
    unanswered = summary["total"] - summary["answered"]
    if unanswered > 0:
        rows.append(("Not answered", f"{unanswered:,}"))
    sub = f"on the phone, across {counted(summary['answered'], 'answered call', 'answered calls')}"
    return card("Calls", duration(summary["seconds"]), sub, row_list(rows))


def lost_information_card(messages):
    """Show how much voice and round video there is, which the export can't show as text."""
    totals = stats.voice_and_video(messages)
    seconds = totals["voice_message"]["seconds"] + totals["video_message"]["seconds"]
    if seconds == 0:
        return ""
    rows = []
    for kind, label in report.KIND_LABELS.items():
        rows.append((label, f"{totals[kind]['count']:,} · {duration(totals[kind]['seconds'])}"))
    return card("Voice and video notes", duration(seconds), "of voice and round video messages", row_list(rows))


def sticker_card(messages, colors):
    """Show how many stickers were sent, the top sticker emoji and each person's favourite."""
    counts = stats.sticker_emoji_counts(messages)
    if counts["total"] == 0:
        return ""
    rows = []
    for sender, sent in stats.stickers_per_person(messages).most_common():
        favourite = counts["per_person"][sender].most_common(1)
        sent_text = counted(sent, "sticker", "stickers")
        if favourite:
            rows.append((sender, f"{sent_text} · favourite {favourite[0][0]}"))
        else:
            rows.append((sender, sent_text))
    body = emoji_row(counts["overall"]) + row_list(rows)
    return card("Stickers", f"{counts['total']:,}", "stickers sent", body)


# --------------------------------------------------------------------------------------------------
# What you write
# --------------------------------------------------------------------------------------------------


def emoji_card(messages):
    """Show the most used emoji, and how many emoji each person types per 100 messages."""
    counts = stats.emoji_counts(messages)
    if counts["total"] == 0:
        return ""
    ratio = stats.emoji_ratio(messages)
    rows = []
    for sender, person in ratio["per_person"].items():
        per_hundred = person["emoji"] / person["messages"] * 100
        favourite = counts["per_person"][sender].most_common(1)
        favourite_text = f" · favourite {favourite[0][0]}" if favourite else ""
        rows.append((sender, f"{per_hundred:.1f} per 100 messages{favourite_text}"))
    body = emoji_row(counts["overall"]) + row_list(rows)
    return card("Emoji", f"{counts['total']:,}", "emoji typed in messages", body)


def repeated_card(messages):
    """List the messages sent most often with the same text."""
    repeated = stats.repeated_messages(messages)
    if not repeated:
        return ""
    rows = []
    for entry in repeated:
        text = report.short_one_line(entry["text"], 60)
        rows.append((f"“{text}”", f"× {entry['count']:,}"))
    return card("Most repeated messages", "", "Same text, sent again and again", row_list(rows, "rows"), wide=True)


def tracked_words_card(messages, path):
    """Show the counts for the words in the tracked words file, if it has any."""
    entries = report.load_tracked_words(path)
    if not entries:
        return ""
    rows = []
    for result in stats.tracked_word_counts(messages, entries):
        people = []
        for sender, count in result["per_person"].most_common():
            people.append(f"{sender} {count:,}")
        detail = f"{result['total']:,}"
        if people:
            detail += f" ({', '.join(people)})"
        rows.append((result["entry"]["label"], detail))
    return card("Tracked words", "", "The words you chose to count", row_list(rows))


# --------------------------------------------------------------------------------------------------
# Days and months
# --------------------------------------------------------------------------------------------------


def busiest_days_card(messages):
    """List the busiest days, each with its short automatic description."""
    top = stats.top_days(messages)
    days = []
    for day, _ in top:
        days.append(day)
    grouped = stats.messages_on_days(messages, days)
    items = []
    for day, count in top:
        description = report.day_description(grouped[day], day)
        items.append(
            f'<li><div class="when"><span>{day:%d %b %Y}</span><span>{counted(count, "message", "messages")}</span></div>'
            f'<div class="what">{escape(description)}</div></li>'
        )
    return card("Busiest days", "", "", f'<ul class="rows days">{"".join(items)}</ul>', wide=True)


def quietest_days_card(messages):
    """List the days you talked least (not counting days with no messages at all)."""
    rows = []
    for day, count in stats.quietest_days(messages):
        noun = "message" if count == 1 else "messages"
        rows.append((f"{day:%d %b %Y}", f"{count:,} {noun}"))
    return card("Quietest days", "", "The days you talked least", row_list(rows))


def months_card(messages):
    """Show messages per month as a chart, with the busiest month as the headline."""
    months = stats.messages_per_month(messages)
    values = []
    labels = []
    axis_labels = []
    best = 0
    for index, (month, count) in enumerate(months):
        values.append(count)
        labels.append(month)
        axis_labels.append(f"{datetime.strptime(month, '%Y-%m'):%b %y}")
        if count > values[best]:
            best = index
    best_month = datetime.strptime(months[best][0], "%Y-%m")
    sub = f"was the busiest month, with {months[best][1]:,} messages"
    body = bar_chart_svg(values, labels, axis_labels, best)
    return card("Messages per month", f"{best_month:%B %Y}", sub, body, wide=True)


# --------------------------------------------------------------------------------------------------
# The whole page
# --------------------------------------------------------------------------------------------------


def page_sections(chat, tracked_words_path):
    """Return the page body: every group heading with its cards, leaving out cards with nothing to show."""
    messages = chat["messages"]
    colors = people_colors(messages)
    groups = [
        ("The basics", [messages_card(messages, colors), first_message_card(messages)]),
        ("Conversations", [
            starters_card(messages, colors),
            reply_time_card(messages, colors),
            double_text_card(messages),
            replies_edits_card(messages),
        ]),
        ("Time", [busiest_hour_card(messages, colors), streak_card(messages), silence_card(messages)]),
        ("Media and calls", [calls_card(chat["calls"]), lost_information_card(messages), sticker_card(messages, colors)]),
        ("What you write", [emoji_card(messages), repeated_card(messages), tracked_words_card(messages, tracked_words_path)]),
        ("Days and months", [busiest_days_card(messages), quietest_days_card(messages), months_card(messages)]),
    ]
    sections = []
    for title, cards in groups:
        filled = []
        for html_card in cards:
            if html_card:
                filled.append(html_card)
        if filled:
            sections.append(f'<h2 class="group">{escape(title)}</h2>\n<div class="grid">\n' + "\n".join(filled) + "\n</div>")
    return "\n".join(sections)


def build_page(chat, tracked_words_path=report.TRACKED_WORDS_PATH):
    """Return the complete HTML page for a loaded chat, as a string."""
    title = f"{chat['name']} · Telegram wrapped"
    if chat["messages"]:
        body = hero(chat) + "\n" + page_sections(chat, tracked_words_path)
    else:
        body = '<header class="hero"><h1>No messages in this chat</h1></header>'
    footer = (
        f"Made with telegram-parser on {datetime.now():%d %b %Y}. "
        "This page contains your private messages, so share it carefully."
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n<style>{PAGE_STYLE}</style>\n</head>\n<body>\n<main>\n"
        f"{body}\n<footer>{escape(footer)}</footer>\n</main>\n</body>\n</html>\n"
    )
