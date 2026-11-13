# Telegram Wrapped

Turn any Telegram chat into a "Wrapped"-style page of fun facts: who texts more, who starts the
conversations, how fast you each reply, your longest streak, your busiest hour, your favourite emoji,
and more.

Everything runs **on your own computer**. Your messages are never uploaded anywhere.

---

## Quick start

It takes about 5 minutes, and you only need to do steps 1 and 2 once.

### 1. Install Python (once)

- **Mac:** open **Terminal** (press `⌘ Space`, type `Terminal`, press Enter), then type `python3 --version`
  and press Enter. If a window asks to install "command line developer tools", click **Install** and
  wait for it to finish. You're done when it prints `Python 3.9` or higher.
- **Windows:** download Python from [python.org/downloads](https://www.python.org/downloads/) and run
  the installer. On the first screen, **tick "Add python.exe to PATH"**. Also install
  [Git for Windows](https://git-scm.com/download/win), keeping all the default options.

### 2. Export your chat from Telegram

Exporting only works in **Telegram Desktop**, the computer app from
[desktop.telegram.org](https://desktop.telegram.org). The phone apps can't export chats.

1. Open the chat you want.
2. Click the **⋮** (three dots) in the top-right corner, then **Export chat history**.
3. In the window that opens:
   - **Untick all the media:** Photos, Videos, Voice messages, Video messages, Stickers, GIFs and
     Files. Only the text is needed, and without media the export is small and quick.
   - If there's a **Size limit** slider, drag it **all the way to the right**.
   - Set **Format** to **Machine-readable JSON**, not HTML.
   - Leave the dates on the full range, from the first message to now.
4. Click **Export**. When it's done, click **Show my data**. You'll get a folder like
   `ChatExport_2024-05-16` with a file called **`result.json`** inside. Keep that window open.

### 3. Download and start it

Copy the line for your computer, paste it into the terminal and press Enter.

**Mac / Linux** (in Terminal):

```bash
git clone https://github.com/720kbps/telegram-parser.git && cd telegram-parser && python3 main.py
```

**Windows** (open **PowerShell** from the Start menu):

```powershell
git clone https://github.com/720kbps/telegram-parser.git; cd telegram-parser; py main.py
```

### 4. Get your Wrapped

1. It asks for your export: **drag the `ChatExport_...` folder** (or the `result.json` inside it)
   into the terminal window, then press **Enter**.
2. Type **`3`** and press Enter to save the Wrapped page.
3. Type **`y`** and press Enter to open it in your browser. 🎉

The page is saved in the `telegram-parser/reports/` folder, so you can open it again later.

**Next time**, open the terminal and run just this:

```bash
cd telegram-parser && python3 main.py
```

On Windows, use `cd telegram-parser; py main.py` instead.

<details>
<summary><b>Can't use Git? Download a ZIP instead</b></summary>

1. On this project's GitHub page, click the green **Code** button, then **Download ZIP**, and unzip it.
2. Open a terminal in that folder:
   - **Mac:** in Terminal, type `cd ` (with a space at the end), drag the unzipped folder into the
     window, and press Enter.
   - **Windows:** open the unzipped folder, click the address bar at the top, type `powershell` and
     press Enter.
3. Run `python3 main.py` on a Mac, or `py main.py` on Windows.

</details>

<details>
<summary><b>Something went wrong?</b></summary>

- **"command not found: git" or "python3 not found":** go back to step 1. On Windows, close and
  reopen PowerShell after installing.
- **"has no 'messages' list":** you exported your whole account instead of one chat. Use **Export
  chat history** from inside the chat, as in step 2.
- **"There's no result.json" or "Expecting value":** the chat was exported as HTML. Export it again
  with **Format: Machine-readable JSON**.
- **"No such file or directory":** drag the folder or file into the window instead of typing its
  path.

</details>

---

## The menu

```
1) Show all messages             every message in date order, as "Sender: text"
2) Show statistics               the full fun facts report, as text
3) Save the Wrapped page (HTML)  the same fun facts as a page of cards and charts
4) Exit
```

After options 1 and 2 you can also save the text to a file. Everything is saved in `reports/`, named
with the date and time (e.g. `statistics_2026-11-13_22-15.txt`), so a new save never overwrites an
old one.

### The Wrapped page

One self-contained web page with:

- a card for every fun fact
- charts for the busiest hour and messages per month
- each person in their own color
- light and dark themes that follow your computer's setting

It loads nothing from the internet, so it also works offline. To turn it into slides or a PDF,
screenshot the cards or use your browser's **Print → Save as PDF**. The page includes some of your
messages (the very first one and the most repeated ones), so share it carefully.

## What's in it

| Section | What it shows |
|---|---|
| **The basics** | First message ever, total messages, each person's share |
| **Conversations** | Who starts conversations, reply times, quoted replies, double-texting, edited messages |
| **Time** | Busiest hour (with a 24-hour chart), longest streak of days talking, longest silences |
| **Media and calls** | Voice and round video messages, stickers and favourite sticker emoji, calls and talk time |
| **What you write** | Most repeated messages, your tracked words, most used emoji, emoji per 100 messages |
| **Days and months** | Busiest days (each with a short description), quietest days, messages per month |

### Count your own words (optional)

To count how often certain words come up, make your own word list from the example. On a Mac, run:

```bash
cp tracked_words.example.txt tracked_words.txt
```

On Windows, copy the file in File Explorer and rename the copy to `tracked_words.txt`.

Then open `tracked_words.txt` and put one word per line. A word ending in `*` also matches longer
words, e.g. `capy*` matches "capybara". Capital letters and Romanian diacritics don't matter: "și",
"şi" and "si" all count as the same word.

## Privacy

- The program only reads the export file you give it. Nothing is sent anywhere.
- Your exports, saved reports and word list are kept out of git, so they can't be uploaded by
  accident: `chatExport/`, `data/`, `reports/` and `tracked_words.txt`.

---

## For developers

No third-party packages are needed. The project uses only Python 3.9+ and its standard library.

```
main.py                       the menu: load a chat, show or save the results
telegram_parser/
    loader.py                 reads the export into plain message and call dicts
    stats.py                  one small function per fun fact
    report.py                 turns the stats into the text report
    html_report.py            turns the stats into the Wrapped web page
    emoji_finder.py           finds emoji in text
    text_tools.py             words, lowercase, Romanian diacritics
docs/TELEGRAM_EXPORT_FORMAT.md  what's inside Telegram's export file
samples/sample_chat.json      a small fake chat used by the tests and demos
tests/                        unit tests
```

Settings such as the 6-hour conversation gap or the 1-hour double-text wait are constants at the top
of `telegram_parser/stats.py`.

To try it on the fake chat and run the tests:

```bash
python3 main.py samples/sample_chat.json
```

```bash
python3 -m unittest
```

## License

GPL-2.0. See [LICENSE](LICENSE).
