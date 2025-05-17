@echo off
cd E:\projects\PowerCore-LauncherMini\ian_mode_launcher
python rest_api.py 

import logging
from logging.handlers import RotatingFileHandler

log_path = './logs/ian_mode_launcher.log'
handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s') 