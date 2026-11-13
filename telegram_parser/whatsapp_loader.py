"""Load a WhatsApp "Export chat" file (the .txt, or the .zip it comes in) into the same dicts as the Telegram loader."""

import re
import zipfile
from datetime import datetime
from pathlib import Path

# A message line starts with its date and time. The iPhone app writes "[13/11/2026, 22:15:03] Alex: hey",
# Android writes "13/11/2026, 22:15 - Alex: hey". The date order, separators and 12/24h clock depend on
# the phone's language settings, so the patterns accept all of them.
DATE = r"(?P<date>\d{1,4}[./-]\d{1,2}[./-]\d{1,4})"
TIME = r"(?P<time>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:[\s \xa0]*[AaPp]\.?\s?[Mm]\.?)?)"
IPHONE_LINE = re.compile(r"^‎?\[" + DATE + r",? " + TIME + r"\] (?P<rest>.*)$")
ANDROID_LINE = re.compile(r"^" + DATE + r",? " + TIME + r" [-–] (?P<rest>.*)$")

# Invisible direction marks WhatsApp puts around phone numbers and before attachments and notices.
DIRECTION_MARKS = re.compile("[‎‏‪-‮⁦-⁩]")

EDITED_MARKER = "<this message was edited>"

# Placeholders for media in an export made "without media", by the text after the sender (lowercased).
MEDIA_PLACEHOLDERS = {
    "image omitted": "photo",
    "video omitted": "video_file",
    "video note omitted": "video_message",
    "audio omitted": "voice_message",
    "sticker omitted": "sticker",
    "gif omitted": "animation",
    "document omitted": "file",
    "contact card omitted": "file",
    "<media omitted>": "media",
}

# Parts of attached file names (exports "with media") that tell what kind of file it is.
ATTACHMENT_NAME_PARTS = [
    ("-photo-", "photo"),
    ("img-", "photo"),
    ("-audio-", "voice_message"),
    ("ptt-", "voice_message"),
    ("-sticker-", "sticker"),
    ("stk-", "sticker"),
    ("-gif-", "animation"),
    ("-video-", "video_file"),
    ("vid-", "video_file"),
]

# Things people sent that the iPhone app writes like notices (with the invisible mark in front).
# They're counted as messages, unlike real notices such as "Missed voice call".
SENT_ITEM_PREFIXES = [
    ("this message was deleted", "deleted"),
    ("you deleted this message", "deleted"),
    ("you received a view once", "media"),
    ("you sent a view once", "media"),
    ("poll:", "poll"),
    ("location:", "location"),
]

# Deleted messages on Android have no invisible mark, so these are checked for every message.
DELETED_PREFIXES = ["this message was deleted", "you deleted this message"]


def read_export_text(path):
    """Return the chat text from a WhatsApp .txt export, or from the .txt inside a .zip export."""
    if path.suffix.lower() != ".zip":
        return path.read_text(encoding="utf-8-sig")

    with zipfile.ZipFile(path) as archive:
        text_files = []
        for name in archive.namelist():
            if name.lower().endswith(".txt"):
                text_files.append(name)
        if not text_files:
            raise ValueError(f"{path} has no chat .txt file inside.")
        # The iPhone app always calls the chat "_chat.txt"; Android names it after the chat.
        chosen = text_files[0]
        for name in text_files:
            if Path(name).name == "_chat.txt":
                chosen = name
        return archive.read(chosen).decode("utf-8-sig")


def split_entries(lines):
    """Group the export's lines into entries, adding lines without a date to the message before them."""
    entries = []
    for line in lines:
        match = IPHONE_LINE.match(line)
        if match is None:
            match = ANDROID_LINE.match(line)
        if match is not None:
            entries.append({"date": match.group("date"), "time": match.group("time"), "rest": match.group("rest")})
        elif entries:
            # A message written over several lines continues here without a date in front.
            entries[-1]["rest"] += "\n" + line
    return entries


def find_date_order(date_texts):
    """Work out from all the dates whether they're day/month/year, month/day/year or year/month/day."""
    for text in date_texts:
        parts = re.split(r"[./-]", text)
        if len(parts[0]) == 4:
            return "ymd"
        if int(parts[0]) > 12:
            return "dmy"
        if int(parts[1]) > 12:
            return "mdy"
    # Every date works both ways (a short chat on days 1-12 of the month). Day first is the most common.
    return "dmy"


def parse_date_time(date_text, time_text, order):
    """Turn the date and time texts of one line into a datetime."""
    parts = re.split(r"[./-]", date_text)
    if order == "ymd":
        year, month, day = parts
    elif order == "mdy":
        month, day, year = parts
    else:
        day, month, year = parts
    year = int(year)
    if year < 100:
        year += 2000

    clean = time_text.lower()
    numbers = re.findall(r"\d+", clean)
    hour = int(numbers[0])
    minute = int(numbers[1])
    second = int(numbers[2]) if len(numbers) > 2 else 0
    # 12-hour clocks: "10:15 PM", "10:15 p.m." or with a narrow no-break space before PM.
    if "p" in clean and hour < 12:
        hour += 12
    if "a" in clean and hour == 12:
        hour = 0
    return datetime(year, int(month), int(day), hour, minute, second)


def attachment_kind(lowered):
    """Return the kind of an attached file, from its name, or "" if the text isn't an attachment."""
    if not (lowered.startswith("<attached:") or lowered.endswith("(file attached)")):
        return ""
    for part, kind in ATTACHMENT_NAME_PARTS:
        if part in lowered:
            return kind
    return "file"


def read_body(body):
    """Return {"kind", "text", "edited"} for a message's text, or None for notices like call lines."""
    # The iPhone app puts an invisible mark in front of everything that isn't typed text.
    is_notice = body.startswith("‎")
    clean = DIRECTION_MARKS.sub("", body).strip()

    edited = False
    if clean.lower().endswith(EDITED_MARKER):
        edited = True
        clean = clean[:-len(EDITED_MARKER)].strip()

    lowered = clean.lower()
    if lowered in MEDIA_PLACEHOLDERS:
        return {"kind": MEDIA_PLACEHOLDERS[lowered], "text": "", "edited": edited}
    kind = attachment_kind(lowered)
    if kind:
        return {"kind": kind, "text": "", "edited": edited}
    for prefix in DELETED_PREFIXES:
        if lowered.startswith(prefix):
            return {"kind": "deleted", "text": "", "edited": edited}
    if is_notice:
        for prefix, kind in SENT_ITEM_PREFIXES:
            if lowered.startswith(prefix):
                return {"kind": kind, "text": "", "edited": edited}
        # Encryption notices, calls, "security code changed" and similar.
        return None
    return {"kind": "text", "text": clean, "edited": edited}


def clean_sender(name):
    """Remove direction marks and the "~" WhatsApp shows before names that aren't in your contacts."""
    name = DIRECTION_MARKS.sub("", name)
    name = name.strip().lstrip("~").strip("  \xa0")
    return name or "Unknown"


def chat_name(path):
    """Guess the chat's name from the export's file name, e.g. "WhatsApp Chat - Alex.zip" gives "Alex"."""
    stem = path.stem
    for prefix in ["WhatsApp Chat - ", "WhatsApp Chat with "]:
        if stem.startswith(prefix) and stem[len(prefix):].strip():
            return stem[len(prefix):].strip()
    if stem.startswith("_chat") or stem.startswith("WhatsApp"):
        return "WhatsApp chat"
    return stem


def load_whatsapp(path):
    """Load a WhatsApp .txt or .zip export and return {"source", "name", "messages", "calls"}, oldest first."""
    path = Path(path)
    entries = split_entries(read_export_text(path).splitlines())
    if not entries:
        raise ValueError(f"{path} doesn't look like a WhatsApp chat export (no dated messages found).")

    date_texts = []
    for entry in entries:
        date_texts.append(entry["date"])
    order = find_date_order(date_texts)

    messages = []
    for entry in entries:
        sender, separator, body = entry["rest"].partition(": ")
        if separator == "":
            # Lines without a sender are notices like "Alex added Sam" or the encryption message.
            continue
        read = read_body(body)
        if read is None:
            continue
        messages.append(make_message(len(messages) + 1, sender, entry, order, read))

    messages.sort(key=lambda msg: msg["date"])
    # WhatsApp exports don't list calls in a reliable way, so there are no call stats for them.
    return {"source": "whatsapp", "name": chat_name(path), "messages": messages, "calls": []}


def make_message(number, sender, entry, order, read):
    """Build one message dict with the same keys the Telegram loader uses."""
    return {
        "id": number,
        "sender": clean_sender(sender),
        "date": parse_date_time(entry["date"], entry["time"], order),
        "text": read["text"],
        "kind": read["kind"],
        "duration": 0,
        "edited": read["edited"],
        # WhatsApp exports don't say which message a reply quotes, or which emoji a sticker has.
        "reply_to": None,
        "sticker_emoji": "",
    }
