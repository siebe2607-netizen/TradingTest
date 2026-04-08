"""Simple JSON-based cache for fundamental data."""

import json
import os
import time
from typing import Optional, Dict

class FundamentalCache:
    """Caches ticker fundamentals to avoid rate-limiting and redundant fetching."""

    def __init__(self, cache_file: str = "fundamentals_cache.json", expiry_days: int = 90):
        self.cache_file = cache_file
        self.expiry_seconds = expiry_days * 24 * 60 * 60
        self.data = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Cache save error: {e}")

    def get(self, ticker: str) -> Optional[Dict]:
        """Get cached data if not expired."""
        entry = self.data.get(ticker)
        if not entry:
            return None
        
        # Check expiry
        timestamp = entry.get("timestamp", 0)
        if time.time() - timestamp > self.expiry_seconds:
            return None
            
        return entry.get("data")

    def set(self, ticker: str, data: Dict):
        """Save data to cache."""
        self.data[ticker] = {
            "timestamp": time.time(),
            "data": data
        }
        self._save()
