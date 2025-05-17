import logging
import re

def scan_plugin(path):
    try:
        with open(path, 'r') as f:
            code = f.read()
        # Scan for dangerous patterns
        dangerous = [r'import os', r'import subprocess', r'eval\(', r'exec\(', r'open\(', r'requests', r'socket']
        for pattern in dangerous:
            if re.search(pattern, code):
                logging.warning(f"Dangerous pattern found in {path}: {pattern}")
                return False
        logging.info(f"Plugin {path} passed security scan.")
        return True
    except Exception as e:
        logging.error(f"Failed to scan plugin {path}: {e}")
        return False 