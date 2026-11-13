import json
from datetime import datetime


def load_telegram(path):
    """Load a single-chat Telegram export and return {"messages": [...], "calls": [...]}, oldest first."""
    with open(path, encoding="utf-8") as f:
        export = json.load(f)

    if "messages" not in export:
        raise ValueError(
            f"{path} has no 'messages' list. Export a single chat from Telegram Desktop "
            "(chat menu > Export chat history > JSON), not your whole account."
        )

    raw_messages = []
    raw_calls = []
    for entry in export["messages"]:
        if entry.get("type") == "message":
            raw_messages.append(entry)
        elif entry.get("action") == "phone_call":
            raw_calls.append(entry)
        # Other service entries (pins, theme changes, ...) are skipped.

    latest_names = find_latest_names(raw_messages)

    messages = []
    for msg in raw_messages:
        messages.append(make_message(msg, latest_names))
    # Exports are already in date order, but several stats depend on it, so make sure.
    messages.sort(key=lambda msg: msg["date"])

    calls = []
    for call in raw_calls:
        calls.append(make_call(call, latest_names))
    return {"messages": messages, "calls": calls}


def make_message(msg, latest_names):
    """Turn one raw "message" entry into a plain message dict."""
    return {
        "platform": "telegram",
        "id": msg.get("id"),
        "sender": latest_names.get(msg["from_id"], "Deleted account"),
        "date": datetime.fromisoformat(msg["date"]),
        "text": extract_text(msg),
        "kind": find_kind(msg),
        "duration": msg.get("duration_seconds", 0),
        "edited": "edited" in msg,
        # The id of the message this one replies to, or None. It can point outside the export.
        "reply_to": msg.get("reply_to_message_id"),
        "sticker_emoji": msg.get("sticker_emoji", ""),
    }


def make_call(entry, latest_names):
    """Turn one phone_call service entry into a plain call dict."""
    # The actor is whoever started the call. Prefer their newest name, like for messages.
    fallback_name = entry.get("actor") or "Deleted account"
    return {
        "caller": latest_names.get(entry["actor_id"], fallback_name),
        "date": datetime.fromisoformat(entry["date"]),
        # Calls that were never answered have no duration in the export.
        "duration": entry.get("duration_seconds", 0),
        "outcome": entry.get("discard_reason", "unknown"),
    }


def find_latest_names(raw_messages):
    """Map each sender id to the newest display name it had."""
    # People rename themselves over time. Grouping by id and using the newest name
    # keeps one person from being counted as two.
    names = {}
    for msg in raw_messages:
        name = msg.get("from")
        if name:
            names[msg["from_id"]] = name
    return names


def extract_text(msg):
    """Return the full message text from either the new or the old export format."""
    # Newer exports always have text_entities as a list of {"type", "text"} pieces.
    if "text_entities" in msg:
        parts = []
        for entity in msg["text_entities"]:
            parts.append(entity["text"])
        return "".join(parts)

    # Older exports only have "text", which is a plain string, or a list mixing
    # strings and dicts when the message has links, bold text, mentions, etc.
    text = msg.get("text", "")
    if isinstance(text, str):
        return text

    parts = []
    for piece in text:
        if isinstance(piece, str):
            parts.append(piece)
        else:
            parts.append(piece["text"])
    return "".join(parts)


def find_kind(msg):
    """Return what kind of message this is: its media_type, "photo", "file" or "text"."""
    if "media_type" in msg:
        # voice_message, video_message, sticker, animation, video_file, audio_file
        return msg["media_type"]
    if "photo" in msg:
        return "photo"
    if "file" in msg:
        return "file"
    return "text"
