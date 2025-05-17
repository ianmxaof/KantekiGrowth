import os
import hashlib
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler('logs/log_prompt_sync.log', maxBytes=5*1024*1024, backupCount=3, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO)

def sync_to_cloud():
    # Stub: Upload logs/prompts to cloud (S3/Supabase)
    logging.info("Syncing logs/prompts to cloud (stub)")
    # Implement actual upload logic here
    pass

def repair_logs():
    # Stub: Repair corrupt log files
    logging.info("Repairing logs (stub)")
    logs_dir = 'logs'
    for fname in os.listdir(logs_dir):
        if not fname.endswith('.log'): continue
        fpath = os.path.join(logs_dir, fname)
        try:
            with open(fpath, 'r') as f:
                f.read()
        except Exception:
            logging.warning(f"Corrupt log: {fname}, recreating.")
            with open(fpath, 'w') as f:
                f.write('')
    # Deduplication stub
    seen_hashes = set()
    for fname in os.listdir(logs_dir):
        if not fname.endswith('.log'): continue
        fpath = os.path.join(logs_dir, fname)
        with open(fpath, 'rb') as f:
            h = hashlib.sha256(f.read()).hexdigest()
        if h in seen_hashes:
            os.remove(fpath)
            logging.info(f"Removed duplicate log: {fname}")
        else:
            seen_hashes.add(h) 