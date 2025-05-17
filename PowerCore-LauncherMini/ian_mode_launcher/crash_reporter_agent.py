import logging
from logging.handlers import RotatingFileHandler
import requests
import traceback

handler = RotatingFileHandler('logs/ian_mode_launcher.log', maxBytes=5*1024*1024, backupCount=3, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO)

def report_crash(exc_info):
    # Bundle logs and crash info
    try:
        with open('logs/ian_mode_launcher.log', 'r') as f:
            log_data = f.read()
    except Exception:
        log_data = ''
    crash_data = ''.join(traceback.format_exception(*exc_info))
    payload = {
        'log': log_data,
        'crash': crash_data
    }
    # Send to stub endpoint
    try:
        # Replace with real endpoint or Telegram bot
        requests.post('https://example.com/crash_report', json=payload)
        logging.info("Crash report sent.")
    except Exception as e:
        logging.error(f"Failed to send crash report: {e}") 