# telegram-parser

Turn a Telegram chat export into a report full of fun facts about the conversation: who texts more,
who starts the conversations, how fast you reply, your longest streak, your favourite emoji, and more.

It works on **one chat at a time**: the JSON export of a single conversation from Telegram Desktop.
Everything runs locally, and it needs only Python 3.9+ with no extra packages.

```
===== Conversations =====

Who starts conversations (first message after 6+ hours of silence): 3 conversations
  Alex: 3 (100.0%)
  Sam: 0 (0.0%)

Reply time:
  Sam: usually 1m 7s, on average 1m 39s (3 replies)
  Alex: usually 22s, on average 22s (1 reply)

Double-texting (texting again after more than 1h without a reply):
  Alex: 1 time, longest wait 11h 46m before texting again (06 Jan 2023)
  Sam: 0 times
```
<sub>From the fake chat in `samples/`.</sub>

## Quick start

1. **Export a chat.** In Telegram Desktop, open the chat, then **⋮ → Export chat history**.
   Choose **JSON** as the format. You can untick photos, videos and files, since only the `.json`
   file is used.
2. **Put the export in the project folder**, e.g. in `chatExport/`. That folder is git-ignored.
3. **Run it:**

   ```bash
   python3 main.py chatExport/result.json
   ```

   Without a path, it asks for one. To try it first on the fake chat:

   ```bash
   python3 main.py samples/sample_chat.json
   ```

## The menu

```
1) Show all messages      every message in date order, as "Sender: text"
2) Show statistics        the full fun facts report
3) Exit
```

After either view you can **export it to a file**, go back to the menu, or exit. Files are saved in
`reports/`, named like `statistics_2026-11-13_22-15.txt` so a new save never overwrites an old one.

## What's in the report

| Section | What it shows |
|---|---|
| **The basics** | First message ever, total messages, each person's share |
| **Conversations** | Who starts conversations, reply times, quoted replies, double-texting, edited messages |
| **Time** | Busiest hour (with a 24-hour chart), longest streak of days talking, longest silences |
| **Media and calls** | Voice and round video messages, stickers and favourite sticker emoji, calls and talk time |
| **What you write** | Most repeated messages, your tracked words, most used emoji, emoji per 100 messages |
| **Days and months** | Busiest days (each with a short description), quietest days, messages per month |

### Tracked words

To count specific words, create your own list from the example and put one word per line in it:

```bash
cp tracked_words.example.txt tracked_words.txt
```

A word ending in `*` also matches longer words, e.g. `capy*` matches "capybara". Case and Romanian
diacritics don't matter: "și", "şi" and "si" all count as the same word.

## Privacy

Chat exports are private. The project keeps them out of git:

- `chatExport/` and `data/`: put your exports here
- `reports/`: saved reports, which can contain your messages
- `tracked_words.txt`: your word list

Nothing is uploaded anywhere. The parser only reads the file you give it.

## Project layout

```
main.py                       the menu: load a chat, show or save the results
telegram_parser/
    loader.py                 reads the export into plain message and call dicts
    stats.py                  one small function per fun fact
    report.py                 turns the stats into the text report
    emoji_finder.py           finds emoji in text (standard library only)
    text_tools.py             words, lowercase, Romanian diacritics
docs/TELEGRAM_EXPORT_FORMAT.md  what's inside Telegram's export file
samples/sample_chat.json      a small fake chat used by the tests and demos
tests/                        unit tests
```

Settings such as the 6-hour conversation gap or the 1-hour double-text wait are constants at the top
of `telegram_parser/stats.py`.

## Tests

```bash
python3 -m unittest
```

## License

GPL-2.0. See [LICENSE](LICENSE).
