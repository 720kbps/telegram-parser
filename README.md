# Chat Wrapped for Telegram and WhatsApp

Turn any Telegram or WhatsApp chat into a "Wrapped"-style page of fun facts: who texts more, who
starts the conversations, how fast you each reply, your longest streak, your busiest hour, your
favourite emoji, and more.

Everything runs **on your own computer**. Your messages are never uploaded anywhere.

---

## Quick start

It takes about 5 minutes, and you only need to do steps 1 and 2 once.

### 1. Install Python (once)

Download Python from [python.org/downloads](https://www.python.org/downloads/) (the big yellow
button) and run the installer like any other app.

- **Mac:** just click through the installer.
  > If you typed `python3` in Terminal before this and a window offered to install the "command line
  > developer tools" (which can claim to take hours), click **Cancel**. You don't need those.
- **Windows:** on the installer's first screen, **tick "Add python.exe to PATH"** before clicking
  Install.

Afterwards, close any open Terminal or PowerShell windows, so the next one finds the new Python.

### 2. Export your chat

Follow the steps for the app your chat is in.

<details open>
<summary><b>Telegram</b></summary>

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

</details>

<details open>
<summary><b>WhatsApp</b></summary>

WhatsApp exports chats from the **phone app**.

- **iPhone:** open the chat, tap the person's or group's **name** at the top, scroll down and tap
  **Export Chat**, then choose **Without Media**.
- **Android:** open the chat, tap **⋮** (top right), then **More → Export chat**, and choose
  **Without media**.

Then send the file to your computer, e.g. AirDrop it, email it to yourself or save it to iCloud
Drive / Google Drive. You'll get a file like **`WhatsApp Chat - Alex.zip`** (iPhone) or
**`WhatsApp Chat with Alex.txt`** (Android). You don't need to unzip it.

> WhatsApp exports have less detail than Telegram's. They don't include quoted replies, calls,
> how long voice notes are, or sticker emoji, so those parts are left out. WhatsApp also limits
> how many messages an export holds (tens of thousands, the most recent ones), so very long chats
> may not go all the way back to the start.

</details>

### 3. Download and start it

Open a terminal, then copy the line for your computer, paste it in and press Enter. It downloads the
project into a folder called `telegram-parser-main` and starts it.

**Mac / Linux:** open **Terminal** (press `⌘ Space`, type `Terminal`, press Enter):

```bash
curl -fL -o telegram-parser.zip https://github.com/720kbps/telegram-parser/archive/refs/heads/main.zip && unzip -oq telegram-parser.zip && cd telegram-parser-main && python3 main.py
```

**Windows:** open **PowerShell** from the Start menu:

```powershell
curl.exe -fL -o telegram-parser.zip https://github.com/720kbps/telegram-parser/archive/refs/heads/main.zip; tar -xf telegram-parser.zip; cd telegram-parser-main; py main.py
```

### 4. Get your Wrapped

1. It asks for your export. **Drag it into the terminal window**, then press **Enter**:
   - **Telegram:** the `ChatExport_...` folder, or the `result.json` inside it.
   - **WhatsApp:** the `.zip` or `.txt` file.
2. Type **`3`** and press Enter to save the Wrapped page.
3. Type **`y`** and press Enter to open it in your browser. 🎉

The page is saved in the `telegram-parser-main/reports/` folder, so you can open it again later.

**Next time**, open the terminal and run just this:

```bash
cd telegram-parser-main && python3 main.py
```

On Windows, use `cd telegram-parser-main; py main.py` instead. To get a newer version later, run the
long line from step 3 again. Your saved reports are kept.

<details>
<summary><b>Prefer clicking? Download it by hand</b></summary>

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

- **A Mac asks to install "command line developer tools":** click **Cancel**, install Python from
  python.org as in step 1, then open a new Terminal window and try again.
- **"python3 not found", or Windows opens the Microsoft Store:** go back to step 1. On Windows, make
  sure "Add python.exe to PATH" was ticked, then close and reopen PowerShell.
- **Telegram, "has no 'messages' list":** you exported your whole account instead of one chat. Use
  **Export chat history** from inside the chat, as in step 2.
- **Telegram, "There's no chat export" or "Expecting value":** the chat was exported as HTML. Export
  it again with **Format: Machine-readable JSON**.
- **WhatsApp, "doesn't look like a WhatsApp chat export":** make sure you dragged in the file you
  got from **Export Chat**, not a different text file.
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

For WhatsApp chats, the parts the export doesn't include are left out: quoted replies, calls, voice
note lengths and sticker emoji.

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
  accident: `chatExport/`, `data/`, `reports/`, `tracked_words.txt`, and WhatsApp exports saved in
  the project folder.

---

## For developers

No third-party packages are needed. The project uses only Python 3.9+ and its standard library. With
Git installed, clone it instead of downloading the ZIP:

```bash
git clone https://github.com/720kbps/telegram-parser.git
```

```
main.py                       the menu: load a chat, show or save the results
telegram_parser/
    chat_loader.py            picks the right loader for a Telegram or WhatsApp export
    loader.py                 reads a Telegram export into plain message and call dicts
    whatsapp_loader.py        reads a WhatsApp export into the same dicts
    stats.py                  one small function per fun fact
    report.py                 turns the stats into the text report
    html_report.py            turns the stats into the Wrapped web page
    emoji_finder.py           finds emoji in text
    text_tools.py             words, lowercase, Romanian diacritics
docs/                         what's inside Telegram's and WhatsApp's export files
samples/                      small fake chats (Telegram, WhatsApp iPhone and Android) for tests and demos
tests/                        unit tests
```

The stats and both reports only see the plain message dicts, so they work the same for both apps.
The package is still called `telegram_parser` from before WhatsApp support.

Settings such as the 6-hour conversation gap or the 1-hour double-text wait are constants at the top
of `telegram_parser/stats.py`.

To try it on the fake chats and run the tests:

```bash
python3 main.py samples/sample_chat.json
```

```bash
python3 main.py "samples/WhatsApp Chat - Sam.txt"
```

```bash
python3 -m unittest
```

## License

GPL-2.0. See [LICENSE](LICENSE).
