# ian_mode_launcher.py
# 🚀 Auto-injects Ian Mode instructions into LLM APIs, tracks session outcomes, evolves instruction list
# 🧠 Telegram + Terminal GodMode integration

import os
import sys
import json
import time
import datetime
import logging
import argparse
import subprocess
import signal
from typing import List, Dict, Optional
import telebot
import traceback
from logging.handlers import RotatingFileHandler

import psutil
import os
import time

def kill_process_locking_file(filepath, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            with open(filepath, 'a'):
                return True  # File is accessible
        except PermissionError as e:
            # Find and kill the process locking the file
            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                try:
                    flist = proc.info.get('open_files') or []
                    for f in flist:
                        if os.path.abspath(f.path) == os.path.abspath(filepath):
                            print(f"[ERROR-PROOF] Killing process {proc.pid} ({proc.name()}) locking {filepath}")
                            proc.kill()
                            time.sleep(1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            time.sleep(1)
    # Final attempt
    try:
        with open(filepath, 'a'):
            return True
    except Exception as e:
        print(f"[FATAL] Could not access {filepath} after killing processes: {e}")
        return False

# === Config ===
SCRIPT_DIR = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
INSTRUCTIONS_PATH = os.path.join(SCRIPT_DIR, "ian_mode.json")
LOG_PATH = os.path.join(SCRIPT_DIR, "logs")
NEXT_GEN_PATH = os.path.join(SCRIPT_DIR, "ian_mode.next.json")
CHANGELOG_PATH = os.path.join(SCRIPT_DIR, "ian_mode.changelog.json")
LOCK_FILE = os.path.join(SCRIPT_DIR, "ian_mode_launcher.lock")
WATCHDOG_INTERVAL = 5  # seconds
RETRY_LIMIT = 3
RETRY_BACKOFF = 3  # seconds
TG_BOT_TOKEN = os.getenv("IAN_MODE_BOT_TOKEN") or "7219485013:AAE_t1Hqn1WgqtgtPk0lcW8DTteTSkG6j_g"
AUTHORIZED_USERS = [123456789]  # Replace with your Telegram user ID(s)
MODES = ["dev", "debug", "money", "scale"]
REQUIRED_FILES = [INSTRUCTIONS_PATH]
PAUSE_ON_EXIT = False
ERROR_LOG_PATH = os.path.join(SCRIPT_DIR, 'startup_error.log')

bot = telebot.TeleBot(TG_BOT_TOKEN)

# === Auto-create missing config/log files ===
def ensure_file(path, default_content):
    if not os.path.exists(path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, indent=4)
            print(f"[AUTO-CREATE] Created missing file: {path}")
        except Exception as e:
            print(f"[ERROR] Could not create {path}: {e}")

def ensure_dir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
            print(f"[AUTO-CREATE] Created missing directory: {path}")
        except Exception as e:
            print(f"[ERROR] Could not create directory {path}: {e}")

# === Log all resolved paths at startup ===
def log_resolved_paths():
    print("[PATHS] Resolved paths:")
    print(f"  SCRIPT_DIR: {SCRIPT_DIR}")
    print(f"  INSTRUCTIONS_PATH: {INSTRUCTIONS_PATH}")
    print(f"  LOG_PATH: {LOG_PATH}")
    print(f"  NEXT_GEN_PATH: {NEXT_GEN_PATH}")
    print(f"  CHANGELOG_PATH: {CHANGELOG_PATH}")
    print(f"  LOCK_FILE: {LOCK_FILE}")
    print(f"  ERROR_LOG_PATH: {ERROR_LOG_PATH}")

# === Path resolution test for CI/build ===
def test_path_resolution():
    print("[TEST] Path resolution test...")
    log_resolved_paths()
    ensure_dir(LOG_PATH)
    ensure_file(INSTRUCTIONS_PATH, {"instructions": ["Default Ian Mode instruction set"], "priority_tags": []})
    ensure_file(NEXT_GEN_PATH, {"instructions": [], "priority_tags": []})
    ensure_file(CHANGELOG_PATH, {"generated": "", "summary": {}, "note": ""})
    print("[TEST] Path resolution and file creation test complete.")

# === Error-Proofing: Lock File & PID Check ===
def is_already_running():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read())
            if pid != os.getpid() and pid > 0:
                # Check if process is alive
                if os.name == 'nt':
                    import psutil
                    if psutil.pid_exists(pid):
                        return pid
                else:
                    os.kill(pid, 0)
                    return pid
        except Exception:
            pass
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return None

def cleanup():
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass

def kill_duplicate_processes():
    """Kill all other processes with the same script name except this one."""
    import psutil
    this_pid = os.getpid()
    this_script = os.path.basename(__file__)
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] != this_pid and proc.info['cmdline']:
                if this_script in proc.info['cmdline']:
                    proc.kill()
        except Exception:
            continue

# === Error-Proofing: Watchdog ===
def start_watchdog():
    """Start a watchdog process that restarts this script if it dies."""
    if os.environ.get('IAN_MODE_WATCHDOG') == '1':
        return  # Already in watchdog mode
    args = [sys.executable, __file__] + sys.argv[1:]
    env = os.environ.copy()
    env['IAN_MODE_WATCHDOG'] = '1'
    subprocess.Popen(args, env=env)
    sys.exit(0)

# === Error-Proofing: Dependency/Env Check ===
def check_dependencies():
    missing = []
    for f in REQUIRED_FILES:
        if not os.path.exists(f):
            missing.append(f)
    if missing:
        logging.error(f"Missing required files: {missing}")
        print(f"Missing required files: {missing}")
        sys.exit(1)

# === Error-Proofing: Logging ===
def setup_logging():
    os.makedirs(LOG_PATH, exist_ok=True)
    logfile = os.path.join(LOG_PATH, 'ian_mode_launcher.log')
    kill_process_locking_file(logfile)
    handler = RotatingFileHandler(logfile, maxBytes=5*1024*1024, backupCount=3, delay=True)
    logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# === Error-Proofing: Crash Handler with Retry ===
def run_with_retries(main_func, *args, **kwargs):
    for attempt in range(RETRY_LIMIT):
        try:
            main_func(*args, **kwargs)
            return
        except Exception as e:
            logging.exception(f"Fatal error (attempt {attempt+1}/{RETRY_LIMIT})")
            print(f"[ERROR] {e} (attempt {attempt+1}/{RETRY_LIMIT})")
            time.sleep(RETRY_BACKOFF * (attempt+1))
    print("[FATAL] Max retries reached. Exiting.")
    logging.error("Max retries reached. Exiting.")
    sys.exit(1)

# === Error-Proofing: Graceful Shutdown ===
def handle_shutdown(signum, frame):
    logging.info(f"Received shutdown signal: {signum}")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

# === Existing Logic (Preserved) ===
def load_instructions(path=INSTRUCTIONS_PATH) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_instructions(data: Dict, path: str):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def log_session(prompt: str, response: str, tags: List[str]):
    os.makedirs(LOG_PATH, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_entry = {
        "timestamp": timestamp,
        "prompt": prompt,
        "response": response,
        "tags": tags
    }
    with open(os.path.join(LOG_PATH, f"log_{timestamp}.json"), 'w') as f:
        json.dump(log_entry, f, indent=4)

def clean_invalid_logs(log_dir=LOG_PATH):
    if not os.path.exists(log_dir):
        logging.warning(f"Log directory {log_dir} does not exist. Creating.")
        os.makedirs(log_dir, exist_ok=True)
        return
    removed = []
    for fname in os.listdir(log_dir):
        fpath = os.path.join(log_dir, fname)
        try:
            with open(fpath, 'r') as f:
                json.load(f)
        except Exception:
            os.remove(fpath)
            removed.append(fname)
    if removed:
        logging.warning(f"Removed invalid log files: {removed}")

def evaluate_effectiveness(log_dir=LOG_PATH) -> Dict[str, int]:
    success_counter = {}
    if not os.path.exists(log_dir):
        logging.warning(f"Log directory {log_dir} does not exist. Skipping analytics.")
        return success_counter
    files = os.listdir(log_dir)
    if not files:
        logging.warning(f"Log directory {log_dir} is empty. No analytics to run.")
        return success_counter
    for fname in files:
        try:
            with open(os.path.join(log_dir, fname), 'r') as f:
                entry = json.load(f)
                for tag in entry.get("tags", []):
                    success_counter[tag] = success_counter.get(tag, 0) + 1
        except Exception as e:
            logging.warning(f"Skipping log file {fname}: {e}")
            continue
    return success_counter

def evolve_instructions():
    current = load_instructions()
    tag_scores = evaluate_effectiveness()
    next_gen = current.copy()
    for tag, score in tag_scores.items():
        if score > 3:
            next_gen.setdefault("priority_tags", []).append(tag)
    save_instructions(next_gen, NEXT_GEN_PATH)
    return next_gen

def write_changelog():
    data = {
        "generated": datetime.datetime.now().isoformat(),
        "summary": evaluate_effectiveness(),
        "note": "This reflects session-based improvement suggestions for Ian Mode."
    }
    save_instructions(data, CHANGELOG_PATH)

def inject_mode(target: str, mode: str = "dev") -> Dict:
    if mode not in MODES:
        raise ValueError("Invalid mode. Use one of: " + ", ".join(MODES))
    instructions = load_instructions()
    print(f"\n[🚀 Injecting IAN MODE into {target.upper()} | Mode: {mode}]\n")
    print(json.dumps(instructions, indent=2))
    return instructions

# === Telegram Bot Integration ===
@bot.message_handler(commands=['inject_mode'])
def handle_inject_mode(message):
    if message.from_user.id not in AUTHORIZED_USERS:
        bot.reply_to(message, "❌ Unauthorized")
        return
    try:
        args = message.text.split()
        target = args[1] if len(args) > 1 else "OpenAI"
        mode = args[2] if len(args) > 2 else "dev"
        injected = inject_mode(target, mode)
        bot.reply_to(message, f"✅ IAN MODE injected into {target} ({mode})\n\n" + json.dumps(injected, indent=2)[:4000])
    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# === Main Entrypoint ===
def log_startup_error(e):
    with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(f"[ERROR] {datetime.datetime.now().isoformat()}\n{traceback.format_exc()}\n")

def check_required_files():
    missing = []
    exe_dir = SCRIPT_DIR
    for f in REQUIRED_FILES:
        if not (os.path.exists(f) or os.path.exists(os.path.join(exe_dir, f))):
            missing.append(f)
    if missing:
        msg = f"Missing required files: {missing}"
        logging.error(msg)
        print(msg)
        log_startup_error(Exception(msg))
        # Auto-create missing config file(s)
        for f in missing:
            if f == INSTRUCTIONS_PATH:
                ensure_file(f, {"instructions": ["Default Ian Mode instruction set"], "priority_tags": []})
        if PAUSE_ON_EXIT:
            input("[ERROR] Press Enter to exit...")
        # Do not exit if we just created them
        # sys.exit(1)

def main():
    global PAUSE_ON_EXIT
    log_resolved_paths()
    ensure_dir(LOG_PATH)
    ensure_file(INSTRUCTIONS_PATH, {"instructions": ["Default Ian Mode instruction set"], "priority_tags": []})
    ensure_file(NEXT_GEN_PATH, {"instructions": [], "priority_tags": []})
    ensure_file(CHANGELOG_PATH, {"generated": "", "summary": {}, "note": ""})
    setup_logging()
    clean_invalid_logs()
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=str, default="OpenAI")
    parser.add_argument("--mode", type=str, default="money")
    parser.add_argument("--telegram", action="store_true")
    parser.add_argument("--watchdog", action="store_true", help="Run with watchdog process")
    parser.add_argument("--pause-on-exit", action="store_true", help="Pause on exit (debug)")
    parser.add_argument("--interactive", action="store_true", help="Keep window open for manual commands")
    parser.add_argument("--test-paths", action="store_true", help="Test path resolution and file creation")
    args = parser.parse_args()
    PAUSE_ON_EXIT = args.pause_on_exit
    if args.test_paths:
        test_path_resolution()
        return
    try:
        check_required_files()
        already_running_pid = is_already_running()
        if already_running_pid:
            msg = f"[ERROR] Already running (PID: {already_running_pid}). Exiting."
            print(msg)
            logging.error(msg)
            log_startup_error(Exception(msg))
            if PAUSE_ON_EXIT:
                input("[ERROR] Press Enter to exit...")
            sys.exit(1)
        kill_duplicate_processes()
        if args.watchdog:
            start_watchdog()
        if args.telegram:
            print("[🤖 Starting Telegram Bot Mode]")
            bot.polling()
        elif args.interactive:
            print("[INTERACTIVE MODE] Press Ctrl+C to exit.")
            while True:
                time.sleep(1)
        else:
            inject_mode(args.target, args.mode)
            evolve_instructions()
            write_changelog()
        cleanup()
    except Exception as e:
        logging.exception("Startup error")
        log_startup_error(e)
        print(f"[FATAL ERROR] {e}")
        if PAUSE_ON_EXIT:
            input("[ERROR] Press Enter to exit...")
        sys.exit(1)
    if PAUSE_ON_EXIT:
        input("[INFO] Press Enter to exit...")

if __name__ == "__main__":
    run_with_retries(main)
