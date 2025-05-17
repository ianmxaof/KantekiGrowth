import os
import psutil
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

PROJECTS_ROOT = r'E:/projects'
LOG_FILE = os.path.join(PROJECTS_ROOT, 'swarm_health.log')

handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, delay=True)
logging.basicConfig(handlers=[handler], level=logging.INFO)

def scan_agents():
    agent_statuses = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'cwd']):
        try:
            cwd = proc.info.get('cwd')
            if cwd and cwd.startswith(PROJECTS_ROOT.replace('/', os.sep)):
                name = proc.info['name']
                cmd = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                cpu = proc.cpu_percent(interval=0.1)
                mem = proc.memory_info().rss // 1024
                status = f"PID {proc.info['pid']} | {name} | {cmd} | CPU {cpu:.1f}% | Mem {mem} KB | CWD {cwd}"
                agent_statuses.append(status)
        except Exception as e:
            logging.warning(f"Error scanning process: {e}")
    return agent_statuses

def log_health():
    statuses = scan_agents()
    if statuses:
        logging.info("=== Swarm Health Check ===")
        for s in statuses:
            logging.info(s)
    else:
        logging.info("No agents found running in projects directory.")

if __name__ == '__main__':
    log_health() 