# telegram-parser

Python script that reads a Telegram chat export (JSON) and prints fun facts about the conversation.

It analyses **one chat at a time**. Each run takes the export of a single conversation. It doesn't
analyse a whole Telegram account (all of a user's chats together), and the full-account export file
isn't supported.

## Usage

1. In **Telegram Desktop**, open the chat → ⋮ menu → **Export chat history**.
   Pick **JSON** as the format; you can untick photos/videos/files, only `result.json` is needed.
2. Put the export somewhere outside git, e.g. a `data/` folder (it's ignored).
3. Run:

```bash
python3 main.py data/result.json
```

(Or run `python3 main.py` without a path and it will ask for one.)

This opens a menu:

```
1) Show all messages      every message in date order, as "Sender: text"
2) Show statistics        the fun facts report
3) Exit
```

After showing either one, you can export it to a text file, go back to the menu, or exit. Exports are
saved to `exports/` by default. That folder is git-ignored because the files can contain your
messages.

Try it on the included fake chat:

```bash
python3 main.py samples/sample_chat.json
```

Run the tests:

```bash
python3 -m unittest
```

No third-party packages needed (Python 3.9+).

## How it's organised

- `telegram_loader.py` turns the Telegram export into a plain list of message dicts:
  `platform`, `sender`, `date`, `text`, `kind`, `duration`.
- `stats.py` has one small function per fun fact. Each takes that list.
- `report.py` turns messages and stats into lines of text: the message list and the statistics report.
- `main.py` is the menu (TUI). It shows those lines and saves them to a file.

The structure of Telegram's `result.json` is documented in
[TELEGRAM_EXPORT_FORMAT.md](TELEGRAM_EXPORT_FORMAT.md).

To add another platform (e.g. Instagram), write a loader that returns the same message dicts
and every stat works on it unchanged.

## Roadmap

- [x] First message ever (Telegram)
- [ ] First message ever across Telegram + Instagram
- [x] Total number of messages
- [x] Messages per person and the percentage difference
- [x] Number of voice / round video messages ("lost information")
- [x] Top 10 days by number of messages
- [ ] Short description for each top day
- [x] Messages per month
- [ ] Number of memes sent on Instagram
- [ ] Most repeated messages and how often they appear
- [ ] Stats for specific words
- [ ] Messages-to-emoji ratio (and the worst days)
