import json
import threading
import os

class ProcessedHashesStore:
    def __init__(self, filename="processed_hashes.json"):
        self.filename = filename
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    self.hashes = set(json.load(f))
            except Exception:
                self.hashes = set()
        else:
            self.hashes = set()

    def add(self, tx_hash):
        with self.lock:
            self.hashes.add(tx_hash)
            self._save()

    def __contains__(self, tx_hash):
        return tx_hash in self.hashes

    def _save(self):
        with self.lock:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(list(self.hashes), f) 