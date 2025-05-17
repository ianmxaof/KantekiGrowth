import psutil
import logging
from logging.handlers import RotatingFileHandler
import os
import time

AGENT_NAMES = ["ian_mode_launcher.exe"]  # Add more agent process names as needed
handler = RotatingFileHandler('logs/agent_health.log', maxBytes=5*1024*1024, backupCount=3, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO)

def monitor_agents():
    for agent in AGENT_NAMES:
        found = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == agent:
                found = True
                break
        if not found:
            logging.warning(f"Agent {agent} not running. Restarting...")
            # Restart logic (stub)
            os.system(f'start dist/{agent}')
        else:
            logging.info(f"Agent {agent} is healthy.")

def get_status():
    status = {}
    for agent in AGENT_NAMES:
        status[agent] = any(proc.info['name'] == agent for proc in psutil.process_iter(['name']))
    return status 