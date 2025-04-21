import json
import random
import os
import pyperclip
import keyboard
from win10toast_click import ToastNotifier
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image
from datetime import datetime

# === Configuration ===
CONFIG_PATH = "config.json"
RAW_PROMPTS_FILE = "raw_prompts.txt"
PROMPT_REPO_PATH = "prompt_repo.json"

# === Config Management ===
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("hotkey", "ctrl+shift+a")
    return "ctrl+shift+a"

def save_config(hotkey):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"hotkey": hotkey}, f)

# === Prompt Functions ===
def load_prompts():
    if not os.path.exists(PROMPT_REPO_PATH):
        print("⚠️ No prompt repository found. Run auto_import_prompts.py first.")
        return []

    with open(PROMPT_REPO_PATH, "r", encoding="utf-8") as f:
        repo = json.load(f)

    if not repo:
        print("⚠️ Prompt repository is empty. Add prompts via auto_import_prompts.py.")
        return []

    return repo

def get_random_prompt(prompts):
    if not prompts:
        print("⚠️ No prompts to choose from.")
        return None
    return random.choice(prompts)

def save_prompt_to_file(text):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(RAW_PROMPTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {text}\n")

# === Clipboard Handling ===
def capture_and_append_prompt():
    clipboard_text = pyperclip.paste().strip()
    if clipboard_text:
        save_prompt_to_file(clipboard_text)
        print("✅ Prompt captured and added to raw_prompts.txt")

        toaster = ToastNotifier()
        toaster.show_toast(
            "Prompt Saved 🧠",
            "Captured and added to raw_prompts.txt ✅",
            duration=3,
            threaded=True
        )
    else:
        print("⚠️ Clipboard is empty.")

# === Hotkey Management ===
def bind_hotkey(hotkey_combo):
    global current_hotkey
    try:
        keyboard.remove_hotkey(current_hotkey)
    except KeyError:
        pass
    current_hotkey = hotkey_combo
    keyboard.add_hotkey(current_hotkey, capture_and_append_prompt)
    save_config(current_hotkey)
    print(f"🎯 New hotkey assigned and saved: {current_hotkey}")

def set_new_hotkey(icon, item):
    print("⌨️ Waiting for new hotkey combo... (press your new keys)")
    toaster = ToastNotifier()
    toaster.show_toast(
        "Change Hotkey 🎯",
        "Press a new hotkey combo...",
        duration=3,
        threaded=True
    )
    new_combo = keyboard.read_hotkey(suppress=True)
    bind_hotkey(new_combo)
    toaster.show_toast(
        "Hotkey Updated ✅",
        f"New hotkey set to: {new_combo}",
        duration=3,
        threaded=True
    )

# === Tray Menu ===
def quit_app(icon, item):
    print("Exiting program...")
    icon.stop()
    os._exit(0)

def tray_icon():
    try:
        icon_path = os.path.join(os.path.dirname(__file__), "PS_icon.png")
        image = Image.open(icon_path)
    except Exception:
        image = Image.new("RGB", (64, 64), color=(40, 40, 40))

    menu = (
        item('Set Hotkey', set_new_hotkey),
        item('Exit', quit_app),
    )
    icon = pystray.Icon("PromptSelector", image, "Prompt Selector Running", menu)
    icon.run()

# === Main Execution ===
def main():
    print(">>> Prompt Selector Booted ✅")

    prompts = load_prompts()
    if prompts:
        selected_prompt = get_random_prompt(prompts)
        if selected_prompt:
            print("\n📌 Selected Prompt:")
            print(selected_prompt)

    global current_hotkey
    current_hotkey = load_config()
    bind_hotkey(current_hotkey)

    print(f"🎯 Hotkey active: Press {current_hotkey.upper()} to save clipboard prompt.")
    print("🔚 Press ESC to exit or use tray icon.")

    tray_thread = threading.Thread(target=tray_icon, daemon=True)
    tray_thread.start()

    keyboard.wait('esc')

if __name__ == "__main__":
    main()
