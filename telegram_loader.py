import json
from datetime import datetime


def load_telegram(path):
    with open(path, encoding="utf-8") as f:
        export = json.load(f)

    if "messages" not in export:
        raise ValueError(
            f"{path} has no 'messages' list. Export a single chat from Telegram Desktop "
            "(chat menu > Export chat history > JSON), not your whole account."
        )

    raw_messages = []
    for msg in export["messages"]:
        # Skip service entries like calls, pins and "X joined", they aren't real messages.
        if msg.get("type") == "message":
            raw_messages.append(msg)

    latest_names = find_latest_names(raw_messages)

    messages = []
    for msg in raw_messages:
        messages.append({
            "platform": "telegram",
            "sender": latest_names.get(msg["from_id"], "Deleted account"),
            "date": datetime.fromisoformat(msg["date"]),
            "text": extract_text(msg),
            "kind": find_kind(msg),
            "duration": msg.get("duration_seconds", 0),
        })
    return messages


def find_latest_names(raw_messages):
    # People rename themselves over time. Grouping by id and using the newest name
    # keeps one person from being counted as two.
    names = {}
    for msg in raw_messages:
        name = msg.get("from")
        if name:
            names[msg["from_id"]] = name
    return names


def extract_text(msg):
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
    if "media_type" in msg:
        # voice_message, video_message, sticker, animation, video_file, audio_file
        return msg["media_type"]
    if "photo" in msg:
        return "photo"
    if "file" in msg:
        return "file"
    return "text"
