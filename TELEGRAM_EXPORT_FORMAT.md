# Telegram export format (JSON)

This describes the `result.json` file that **Telegram Desktop** produces with
*chat menu → Export chat history → Format: JSON*.

The project only does **per-chat analysis**, so this single-chat export is the only input format it
supports. Account-wide exports are out of scope (see [below](#full-account-export-out-of-scope)).

Telegram doesn't publish an official schema for this file. This spec is based on Telegram Desktop
exports and was checked against a real 1:1 chat export with a few hundred thousand messages. Fields get
added over time, so treat every field as **optional** unless it's marked as always present, and ignore
fields you don't recognise.

A fake example covering most cases is in [`samples/sample_chat.json`](samples/sample_chat.json).

## At a glance

```text
result.json
├── name, type, id                 about the chat                              §1
└── messages[]                     one entry per message or event, oldest first
    ├── common fields              id, type, date, sender, replies, edits…     §2
    ├── text, text_entities[]      what was written                            §3
    ├── media fields               photos, voice notes, stickers, files…       §4
    ├── reactions[]                who reacted with what                       §5
    └── actor, action, …           service events only                         §6
```

In the trees below, `[]` means an array of objects with the fields listed under it.

---

## 1. Top level (single-chat export)

```text
result.json
├── name        string | null   chat title, or the other person's name in a 1:1 chat
│                               (null for a deleted account)
├── type        string          personal_chat, bot_chat, saved_messages,
│                               private_group, private_supergroup, public_supergroup,
│                               private_channel, public_channel
├── id          number          chat id
└── messages[]                  always present, in chronological order (oldest first)
```

### Full-account export (out of scope)

*Settings → Advanced → Export Telegram data* exports a whole account, with every chat a user has. It
produces a different top level, with the chats nested inside it:

```text
result.json  (full-account export)
├── about
├── personal_information
├── contacts
├── frequent_contacts
├── chats
│   ├── about
│   └── list[]                  each item has the same shape as a single-chat export
│       ├── name, type, id
│       └── messages[]
└── left_chats
```

This project does per-chat analysis only, so it won't support this file. The loader rejects it with an
error that says to export a single chat instead.

---

## 2. Message object: common fields

Every entry in `messages` has a `type`:

- `"message"`: something a person sent. **This is what the stats count.**
- `"service"`: an event such as a call, a pin or someone joining. See [section 6](#6-service-messages).

```text
messages[]
├── id                    number          always · unique within the chat
├── type                  string          always · "message" or "service"
├── date                  string          always · "2023-01-05T21:14:03", local time of the
│                                         exporting computer, no timezone
├── date_unixtime         string          newer exports · Unix timestamp, stored as a string
├── text                  string | array  always · see §3
├── text_entities[]                       newer exports · see §3
│
│   who sent it ("message" entries only; service entries use actor / actor_id, §6)
├── from                  string | null   sender's name at export time (null = deleted account)
├── from_id               string          "user123" or "channel123" · stable, use this to
│                                         identify people because names change
├── author                string          channel posts that show a signature
│
│   context
├── edited                string          if edited · date of the last edit
├── edited_unixtime       string          if edited
├── reply_to_message_id   number          replies · id of the message being replied to
├── reply_to_peer_id      string          replies to a message in another chat
├── forwarded_from        string | null   forwards · original sender's name
├── saved_from            string          Saved Messages only
├── via_bot               string          inline bot messages, e.g. "@gif"
│
├── reactions[]                           see §5
└── (media and other content)             see §4
```

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

```text
text_entities[]
├── type          string   see the table below
├── text          string   this piece of the message
├── href          string   text_link only
├── user_id       number   mention_name only
├── language      string   pre only
└── document_id   number   custom_emoji only
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

```text
messages[]  (media fields, all optional)
│
│   photos (these have no media_type, they're recognised by the photo key)
├── photo                          string   path, e.g. "photos/photo_1@14-02-2023_18-30-00.jpg",
│                                           or the placeholder
├── photo_file_size                number   bytes · only if the photo was exported
├── width, height                  number   pixels
│
│   everything else: voice notes, round videos, video, audio, stickers, GIFs, documents
├── file                           string   path, or the placeholder
├── file_name                      string   original file name
├── file_size                      number   bytes · only if the file was exported
├── thumbnail                      string   preview path, or the placeholder
├── thumbnail_file_size            number   only if the thumbnail was exported
├── media_type                     string   see the table below · missing for documents
├── mime_type                      string   e.g. "audio/ogg"
├── duration_seconds               number   voice notes, round videos, video, audio
├── width, height                  number   video, GIFs, stickers
├── sticker_emoji                  string   emoji linked to a sticker · missing on a few
├── performer, title               string   audio files with tags
└── self_destruct_period_seconds   number   disappearing media
```

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

```text
messages[]  (other content, all optional)
├── poll
│   ├── question                   string
│   ├── closed                     bool
│   ├── total_voters               number
│   └── answers[]
│       ├── text                   string
│       ├── voters                 number
│       └── chosen                 bool     whether the exporting user picked it
├── location_information
│   ├── latitude                   number
│   └── longitude                  number
├── live_location_period_seconds   number   live locations only
├── place_name, address            string   venue shares
├── contact_information
│   ├── first_name                 string
│   ├── last_name                  string
│   └── phone_number               string
├── contact_vcard                  string   path to the .vcf file
├── game_title, game_description, game_link
└── invoice_information                     payments
```

---

## 5. Reactions

Only in newer exports, and only on messages that have reactions. The checked export (made in 2024)
had **no `reactions` field at all**, so this part hasn't been confirmed against a real file:

```text
messages[]
└── reactions[]
    ├── type          string   "emoji", "custom_emoji" or "paid"
    ├── count         number   how many people reacted with this
    ├── emoji         string   type "emoji" only, e.g. "❤"
    ├── document_id   string   type "custom_emoji" only
    └── recent[]               may list only some of the people who reacted
        ├── from      string
        ├── from_id   string
        └── date      string
```

---

## 6. Service messages

```text
messages[]  (type = "service")
├── id, type, date, date_unixtime   same as §2
├── text, text_entities             always "" and []
├── actor                string     who did it (instead of from)
├── actor_id             string     instead of from_id
├── action               string     what happened, see the table below
└── (extra fields)                  depend on the action, see the table below
```

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

The loader keeps `phone_call` entries for the call stats and skips every other service message.
Screenshots (`take_screenshot`) could become a fun fact later.

The `actor` of a `phone_call` is whoever started the call.

---

## 7. What the loader uses

`load_telegram` returns a dict with two lists, both oldest first:

```text
chat
├── messages[]   one per "message" entry
└── calls[]      one per "phone_call" service entry
```

Each `"message"` entry becomes:

| Output key | Source |
|------------|--------|
| `platform` | always `"telegram"` |
| `sender`   | newest non-null `from` seen for that `from_id`, else `"Deleted account"` |
| `date`     | `date`, parsed with `datetime.fromisoformat` |
| `text`     | joined `text_entities`, falling back to `text` |
| `kind`     | `media_type` → `"photo"` if `photo` → `"file"` if `file` → `"text"` |
| `duration` | `duration_seconds`, or `0` |

Each `phone_call` entry becomes:

| Output key | Source |
|------------|--------|
| `caller`   | newest name seen for `actor_id` in the messages, else `actor`, else `"Deleted account"` |
| `date`     | `date`, parsed with `datetime.fromisoformat` |
| `duration` | `duration_seconds`, or `0` for calls that were never answered |
| `outcome`  | `discard_reason`, or `"unknown"` |

### Gotchas

- `date` has no timezone. All stats use the exporting computer's local time. Messages are already
  sorted by `date`, but the loader sorts them again anyway because reply time and conversation
  starters depend on the order.
- `date_unixtime` is a string, not a number.
- Photos have no `media_type`.
- A `from` name is the name at export time. Old messages show the new name, but the same person can
  still appear with different names in places like reactions or forwards.
- Exports can be large (hundreds of MB for years of chat). `json.load` reads it all into memory, which
  is fine for a 1:1 chat.
