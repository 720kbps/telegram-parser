# Telegram export format (JSON)

This describes the `result.json` file that **Telegram Desktop** produces with
*chat menu → Export chat history → Format: JSON*.

Telegram doesn't publish an official schema for this file. This spec is based on Telegram Desktop
exports and was checked against a real 1:1 chat export with a few hundred thousand messages. Fields get
added over time, so treat every field as **optional** unless it's marked as always present, and ignore
fields you don't recognise.

A fake example covering most cases is in [`samples/sample_chat.json`](samples/sample_chat.json).

---

## 1. Top level (single-chat export)

```json
{
  "name": "Sam",
  "type": "personal_chat",
  "id": 1002,
  "messages": [ ... ]
}
```

| Field      | Type   | Notes |
|------------|--------|-------|
| `name`     | string | Chat title, or the other person's name in a 1:1 chat. `null` for a deleted account. |
| `type`     | string | `personal_chat`, `bot_chat`, `saved_messages`, `private_group`, `private_supergroup`, `public_supergroup`, `private_channel`, `public_channel` |
| `id`       | number | Chat id. |
| `messages` | array  | Every message in **chronological order** (oldest first). Always present. |

### Full-account export (not supported yet)

*Settings → Advanced → Export Telegram data* produces a different top level. The chats are nested
inside it:

```json
{
  "about": "...",
  "personal_information": { ... },
  "contacts": { ... },
  "chats": { "about": "...", "list": [ { "name": ..., "type": ..., "id": ..., "messages": [...] } ] },
  "left_chats": { ... }
}
```

Each item in `chats.list` has the same shape as a single-chat export. The loader currently rejects
this file with an error.

---

## 2. Message object: common fields

Every entry in `messages` has a `type`:

- `"message"`: something a person sent. **This is what the stats count.**
- `"service"`: an event such as a call, a pin or someone joining. See [section 6](#6-service-messages).

| Field                 | Type          | Present on | Notes |
|-----------------------|---------------|------------|-------|
| `id`                  | number        | always     | Unique within the chat. |
| `type`                | string        | always     | `"message"` or `"service"`. |
| `date`                | string        | always     | `"2023-01-05T21:14:03"`: ISO 8601 **local time of the exporting computer**, no timezone. |
| `date_unixtime`       | string        | newer exports | Same moment as a Unix timestamp, **stored as a string**. |
| `edited`              | string        | if edited  | ISO date of the last edit. |
| `edited_unixtime`     | string        | if edited  | |
| `from`                | string / null | messages   | Sender's display name **at export time**. `null` for deleted accounts. |
| `from_id`             | string        | messages   | Stable sender id: `"user123"`, or `"channel123"` for channel posts. **Use this to identify people**, because names change. |
| `author`              | string        | channel posts | Signature, if the channel shows authors. |
| `forwarded_from`      | string / null | forwards   | Original sender's name. |
| `saved_from`          | string        | Saved Messages | |
| `via_bot`             | string        | inline bot messages | e.g. `"@gif"` |
| `reply_to_message_id` | number        | replies    | `id` of the message being replied to. |
| `reply_to_peer_id`    | string        | replies to another chat | |
| `text`                | string / array | always    | See [section 3](#3-text-and-text_entities). |
| `text_entities`       | array         | newer exports | See [section 3](#3-text-and-text_entities). |
| `reactions`           | array         | newer exports | See [section 5](#5-reactions). |

---

## 3. `text` and `text_entities`

The message text appears in two forms.

**`text`** is either:

- a plain **string** when the message has no formatting: `"hello"`, or `""` for media-only messages
- an **array** mixing plain strings and entity objects when it has links, bold text, mentions, etc.:

```json
"text": ["check this out ", {"type": "link", "text": "https://example.com"}]
```

**`text_entities`** is **always an array** of `{type, text, ...}` objects, including plain parts. This
makes it the easier one to use:

```json
"text_entities": [
  {"type": "plain", "text": "check this out "},
  {"type": "link",  "text": "https://example.com"}
]
```

To get the full text, join every entity's `text`. In the checked export this gave exactly the same
string as joining `text` for every message. If `text_entities` is missing (older exports), fall back to
`text`. `telegram_loader.extract_text` does both.

Service messages have `text: ""` and `text_entities: []` too.

The most common reason `text` becomes an array is **custom emoji**, not links or formatting. A message
containing one premium emoji is enough.

### Entity types

| `type`          | Extra fields | Meaning |
|-----------------|--------------|---------|
| `plain`         |              | Normal text |
| `bold`, `italic`, `underline`, `strikethrough`, `spoiler` | | Formatting |
| `code`          |              | Inline code |
| `pre`           | `language`   | Code block |
| `link`          |              | URL written in the text |
| `text_link`     | `href`       | Text with a hidden link |
| `mention`       |              | `@username` |
| `mention_name`  | `user_id`    | Mention of a user without a username |
| `hashtag`, `cashtag`, `bot_command`, `email`, `phone`, `bank_card` | | Auto-detected |
| `custom_emoji`  | `document_id` | Premium custom emoji. `text` is the fallback emoji. |
| `blockquote`    |              | Quote block |

---

## 4. Media and attachments

A message can have text **and** one attachment. With the default export settings, the media files are
saved in sub-folders next to `result.json` (`photos/`, `voice_messages/`, `stickers/`, etc.). If a media
type was unticked during export, its path in `file`, `photo` or `thumbnail` is replaced by the placeholder
string `"(File not included. Change data exporting settings to download.)"`. The size fields
(`file_size`, `photo_file_size`, `thumbnail_file_size`) only appear when the media was actually
exported. Everything else (`media_type`, `mime_type`, `duration_seconds`, `width`/`height`,
`sticker_emoji`) is still there, so **media stats work without downloading any media**.

### Photos

Photos have **no `media_type`**. They're recognised by the `photo` key.

| Field             | Notes |
|-------------------|-------|
| `photo`           | Relative path, e.g. `"photos/photo_1@14-02-2023_18-30-00.jpg"` |
| `photo_file_size` | Bytes |
| `width`, `height` | Pixels |

### Files, video, audio, stickers, GIFs

| Field                | Notes |
|----------------------|-------|
| `file`               | Relative path, or the placeholder string above |
| `file_name`          | Original file name |
| `file_size`          | Bytes |
| `thumbnail`, `thumbnail_file_size` | Preview image |
| `media_type`         | See table below. Missing for plain documents (PDF, zip, …). |
| `mime_type`          | e.g. `"audio/ogg"` |
| `duration_seconds`   | Voice notes, video, audio, round videos |
| `width`, `height`    | Video, GIFs, stickers |
| `sticker_emoji`      | The emoji linked to a sticker. Missing on a few stickers. |
| `performer`, `title` | Audio files with tags |

| `media_type`      | What it is |
|-------------------|------------|
| `voice_message`   | Voice note (`voice_messages/`) |
| `video_message`   | Round video note (`round_video_messages/`) |
| `video_file`      | Regular video |
| `audio_file`      | Music / audio file |
| `animation`       | GIF |
| `sticker`         | Sticker: static (`image/webp`), animated (`application/x-tgsticker`) or video (`video/webm`) |

Documents such as PDFs and zips have `file` and `mime_type` but **no `media_type`**.

### Other message content

| Field                          | Shape |
|--------------------------------|-------|
| `poll`                         | `{question, closed, total_voters, answers: [{text, voters, chosen}]}` |
| `location_information`         | `{latitude, longitude}`, plus `live_location_period_seconds` for live locations |
| `place_name`, `address`        | Venue shares |
| `contact_information`          | `{first_name, last_name, phone_number}`, plus `contact_vcard` |
| `game_title`, `game_description`, `game_link` | Games |
| `invoice_information`          | Payments |
| `self_destruct_period_seconds` | Disappearing media |

---

## 5. Reactions

Only in newer exports, and only on messages that have reactions. The checked export (made in 2024)
had **no `reactions` field at all**, so this part hasn't been confirmed against a real file:

```json
"reactions": [
  {
    "type": "emoji",
    "count": 2,
    "emoji": "❤",
    "recent": [ {"from": "Sam", "from_id": "user1002", "date": "2023-01-05T21:16:00"} ]
  }
]
```

`type` can also be `"custom_emoji"` (with `document_id` instead of `emoji`) or `"paid"`. `recent` may
list only some of the people who reacted, not everyone.

---

## 6. Service messages

Service messages use `actor` / `actor_id` instead of `from` / `from_id`. The `action` field says what
happened:

| `action`                  | Extra fields |
|---------------------------|--------------|
| `phone_call`              | `discard_reason` (`hangup`, `busy`, `missed`, `disconnect`); `duration_seconds` only if the call was answered |
| `group_call`              | `duration` |
| `pin_message`             | `message_id` |
| `take_screenshot`         | (someone screenshotted the chat) |
| `set_chat_wallpaper`      | |
| `edit_chat_theme`         | `emoticon` |
| `send_premium_gift`       | `cost` (string, e.g. a price), `months` |
| `suggest_profile_photo`   | `photo`, `width`, `height` |
| `create_group`            | `title`, `members` |
| `invite_members`, `remove_members` | `members` (list of names) |
| `join_group_by_link`      | `inviter` |
| `edit_group_title`        | `title` |
| `edit_group_photo`, `delete_group_photo` | `photo` |
| `migrate_to_supergroup`, `migrate_from_group` | |
| `clear_history`           | |
| `set_messages_ttl`        | `period` |

The loader skips all service messages. Calls (`phone_call`) and screenshots (`take_screenshot`) could
become fun facts later.

---

## 7. What the loader uses

`telegram_loader.py` turns each `"message"` entry into:

| Output key | Source |
|------------|--------|
| `platform` | always `"telegram"` |
| `sender`   | newest non-null `from` seen for that `from_id`, else `"Deleted account"` |
| `date`     | `date`, parsed with `datetime.fromisoformat` |
| `text`     | joined `text_entities`, falling back to `text` |
| `kind`     | `media_type` → `"photo"` if `photo` → `"file"` if `file` → `"text"` |
| `duration` | `duration_seconds`, or `0` |

### Gotchas

- `date` has no timezone. All stats use the exporting computer's local time. Messages are already
  sorted by `date`.
- `date_unixtime` is a string, not a number.
- Photos have no `media_type`.
- A `from` name is the name at export time. Old messages show the new name, but the same person can
  still appear with different names in places like reactions or forwards.
- Exports can be large (hundreds of MB for years of chat). `json.load` reads it all into memory, which
  is fine for a 1:1 chat.
