import os
import requests
import hashlib
import logging
from logging.handlers import RotatingFileHandler

UPDATE_URL = "https://example.com/ian_mode_launcher_update.json"  # Replace with real endpoint
LAUNCHER_EXE = "dist/ian_mode_launcher.exe"

handler = RotatingFileHandler('logs/auto_updater.log', maxBytes=5*1024*1024, backupCount=3, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO)

def check_for_update():
    try:
        resp = requests.get(UPDATE_URL)
        resp.raise_for_status()
        data = resp.json()
        latest_version = data.get('version')
        download_url = data.get('download_url')
        expected_hash = data.get('sha256')
        # Read local version (stub)
        with open('ian_mode.json') as f:
            local_version = f.read().split(':')[1].replace('"','').replace('}','').strip()
        if latest_version > local_version:
            logging.info(f"Update available: {latest_version}")
            return download_url, expected_hash
        else:
            logging.info("No update needed.")
            return None, None
    except Exception as e:
        logging.error(f"Update check failed: {e}")
        return None, None

def apply_update(download_url, expected_hash):
    try:
        r = requests.get(download_url)
        r.raise_for_status()
        with open('update_tmp.exe', 'wb') as f:
            f.write(r.content)
        # Verify hash (stub)
        sha256 = hashlib.sha256(r.content).hexdigest()
        if sha256 != expected_hash:
            logging.error("Hash mismatch! Aborting update.")
            os.remove('update_tmp.exe')
            return False
        # Replace launcher
        os.replace('update_tmp.exe', LAUNCHER_EXE)
        logging.info("Launcher updated successfully.")
        return True
    except Exception as e:
        logging.error(f"Update failed: {e}")
        return False 