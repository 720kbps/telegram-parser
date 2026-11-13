"""Load a chat export from either app: a Telegram .json, or a WhatsApp .txt or .zip."""

from pathlib import Path

from telegram_parser.loader import load_telegram
from telegram_parser.whatsapp_loader import load_whatsapp

# The app each kind of export comes from, as shown in the menu and on the Wrapped page.
SOURCE_NAMES = {"telegram": "Telegram", "whatsapp": "WhatsApp"}


def load_chat(path):
    """Load a Telegram or WhatsApp export, picking the right loader from the file type."""
    if Path(path).suffix.lower() in [".txt", ".zip"]:
        return load_whatsapp(path)
    return load_telegram(path)


def find_export_in_folder(folder):
    """Return the export file inside a folder someone dragged in, or None if there isn't one."""
    # Telegram saves result.json in its export folder; WhatsApp exports unzip to _chat.txt (iPhone)
    # or "WhatsApp Chat with <name>.txt" (Android).
    for name in ["result.json", "_chat.txt"]:
        if (folder / name).exists():
            return folder / name
    for path in sorted(folder.glob("WhatsApp Chat*.txt")):
        return path
    return None


def source_name(chat):
    """Return "Telegram" or "WhatsApp" for a loaded chat."""
    return SOURCE_NAMES.get(chat.get("source", "telegram"), "Chat")
