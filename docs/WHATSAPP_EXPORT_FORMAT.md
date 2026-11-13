# WhatsApp export format (text)

This describes the file WhatsApp produces with **Export chat → Without media**, and how
`telegram_parser/whatsapp_loader.py` reads it. Unlike Telegram's JSON, it's a plain text file meant
for people to read, so its layout depends on the phone and its language settings. WhatsApp
doesn't document it, so everything here comes from real exports and is handled defensively.

Fake examples:

- [`WhatsApp Chat - Sam.txt`](../samples/WhatsApp%20Chat%20-%20Sam.txt): iPhone layout
- [`WhatsApp Chat with Sam.txt`](../samples/WhatsApp%20Chat%20with%20Sam.txt): Android layout

## The files

| Phone | What you get | Chat file inside |
|---|---|---|
| iPhone | `WhatsApp Chat - <name>.zip` | `_chat.txt` |
| Android | `WhatsApp Chat with <name>.txt`, sometimes zipped | the file itself |

The loader reads the `.zip` directly, so there's no need to unzip it. The chat's name is taken from the file name.

## One line per message

```text
iPhone:   [05/01/2023, 21:14:03] Alex: hey, is this the right chat?
Android:  05/01/2023, 21:14 - Alex: hey, is this the right chat?
```

```text
line
├── date      05/01/2023 · 1/5/23 · 05.01.23 · 2023-01-05   (order depends on the phone's region)
├── time      21:14:03 · 21:14 · 9:14 PM · 9:14 p.m. · 21.14 (Android has no seconds)
├── sender    the name as saved in the phone's contacts, or a phone number
└── text      everything after "sender: "
```

- **Date order:** day/month/year, month/day/year or year/month/day. The loader looks at every date
  and picks the only order that fits, e.g. `2/14/23` can only be month first. If every date fits
  both ways, it assumes day first.
- **12-hour clocks:** `AM`/`PM` may come after a normal space, an invisible narrow space
  (`U+202F`), or be written as `a.m.`/`p.m.`.
- **Multi-line messages:** a message written over several lines continues on the next lines, with no
  date in front. Those lines are added to the message before them.
- **Invisible characters:** the iPhone app puts a left-to-right mark (`U+200E`) in front of
  attachments and notices, and phone numbers come wrapped in direction marks. The loader strips
  them, along with the `~` WhatsApp shows before names that aren't in your contacts.

## What the text can be

| Text after the sender | Phone | Read as `kind` |
|---|---|---|
| normal text | both | `text` |
| `image omitted` | iPhone | `photo` |
| `video omitted` | iPhone | `video_file` |
| `video note omitted` | iPhone | `video_message` (round video note) |
| `audio omitted` | iPhone | `voice_message` |
| `sticker omitted` | iPhone | `sticker` |
| `GIF omitted` | iPhone | `animation` |
| `document omitted`, `Contact card omitted` | iPhone | `file` |
| `<Media omitted>` | Android | `media` (Android doesn't say which kind) |
| `<attached: 00000012-PHOTO-….jpg>`, `IMG-…jpg (file attached)` | exports *with* media | from the file name |
| starts with `This message was deleted`, `You deleted this message` | both | `deleted` |
| `You received a view once message`, `You sent a view once…` | iPhone | `media` |
| `POLL:` followed by the question and options | iPhone | `poll` |
| `Location: https://maps…` | iPhone | `location` |
| text ending in `<This message was edited>` | newer versions | `text`, with `edited` set to true |

On iPhone, the last five rows only count when the text starts with the invisible mark, so a message
someone typed starting with "Location:" stays normal text.

**Skipped completely:**
- **Lines without a sender:** Android notices like "Messages and calls are end-to-end encrypted",
  "Alex added Sam" and so on.
- **iPhone lines whose text starts with the invisible mark** but isn't one of the items above:
  - the encryption notice
  - group changes ("Alex changed the group name"), people joining
  - "Missed voice call" and "Video call. 38 min"
  - "security code changed"

## What's missing compared to Telegram

| Telegram field | In a WhatsApp export? | What the loader sets |
|---|---|---|
| `reply_to` (quoted message) | no | `None` |
| calls with durations | no (only some "Missed voice call" lines) | `calls` is an empty list |
| `duration` of voice notes | no | `0` |
| `sticker_emoji` | no | `""` |
| message `id` | no | numbered 1, 2, 3, … in file order |
| seconds in times | iPhone only | `0` seconds on Android |

The loader also sets `chat["source"] = "whatsapp"`. The text report and the Wrapped page use that to
leave out the sections built on missing data: quoted replies, calls, voice note lengths and sticker
emoji.

WhatsApp also limits how many messages one export holds. Without media it's the most recent tens of
thousands, so very long chats may be cut off at the start.
