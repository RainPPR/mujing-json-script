import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConcurrencyManager:
    """Manages adaptive thread counts based on error rates."""
    def __init__(self, initial_limit: int = 8):
        self.max_limit = initial_limit
        self.current_limit = initial_limit
        self.success_streak = 0
        self.lock = threading.Lock()
        self.semaphore = threading.BoundedSemaphore(initial_limit)
        self.recovery_threshold = 10 # Increase limit after 10 consecutive successes

    def report_error(self):
        with self.lock:
            old_limit = self.current_limit
            self.current_limit = max(1, self.current_limit // 2)
            self.success_streak = 0
            if old_limit != self.current_limit:
                logger.warning(f"Error detected. Scaling down concurrency: {old_limit} -> {self.current_limit}")

    def report_success(self):
        with self.lock:
            self.success_streak += 1
            if self.success_streak >= self.recovery_threshold and self.current_limit < self.max_limit:
                self.current_limit += 1
                self.success_streak = 0
                logger.info(f"Stable performance detected. Scaling up concurrency: {self.current_limit}")

    def get_active_semaphore(self):
        # This is a simplified way to restrict concurrency dynamically
        return threading.Semaphore(self.current_limit)

class YoudaoClient:
    """Enhanced Client for Youdao Dictionary API with retry logic and adaptive concurrency support."""
    BASE_URL = "https://dict.youdao.com/jsonapi"
    
    def __init__(self, manager: ConcurrencyManager):
        self.session = requests.Session()
        self.manager = manager
        # Optimization: Reuse headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self.params = {
            "dicts": json.dumps({"count": 99, "dicts": [["syno", "ec"]]})
        }

    def fetch_word_info(self, word: str) -> Optional[Dict[str, Any]]:
        """Fetch word information with retries and adaptive concurrency."""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            # Dynamic throttling based on current manager limit
            with self.manager.get_active_semaphore():
                try:
                    params = self.params.copy()
                    params["q"] = word
                    response = self.session.get(self.BASE_URL, params=params, timeout=10)
                    
                    # Typical rate limit check (Youdao might return 403 or 429)
                    if response.status_code in [403, 429]:
                        self.manager.report_error()
                        time.sleep(2 ** attempt) # Backoff
                        continue

                    response.raise_for_status()
                    data = response.json()
                    
                    # Check if it's a valid response or an API-level error
                    if not data or (isinstance(data, dict) and 'ec' not in data):
                        # Some words just might not exist, but if it happens too much it might be a block
                        pass 

                    self.manager.report_success()
                    return data

                except (requests.RequestException, json.JSONDecodeError) as e:
                    logger.debug(f"Attempt {attempt} failed for word '{word}': {e}")
                    self.manager.report_error()
                    
                    if attempt == max_retries:
                        logger.error(f"FATAL: Failed to fetch word '{word}' after {max_retries} attempts.")
                        sys.exit(1) # Requirement: Force quit on persistent non-rate-limit errors
                    
                    time.sleep(1) # Simple retry delay
        return None

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON data from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        sys.exit(1)

def write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """Write data to a JSON file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to write JSON to {file_path}: {e}")
        sys.exit(1)

def display_progress(label: str, current: int, total: int, lock: threading.Lock) -> None:
    """Thread-safe progress bar display."""
    bar_len = 40
    progress = current / total
    filled = int(bar_len * progress)
    bar = "█" * filled + "░" * (bar_len - filled)
    percent = progress * 100
    with lock:
        print(f"\r{label}: |{bar}| {current}/{total} ({percent:.1f}%)", end="", flush=True)
        if current == total:
            print()

def process_word(client: YoudaoClient, item: Dict[str, Any]) -> None:
    """Process a single word item and update it with info from Youdao."""
    word = item.get("value")
    if not word:
        return

    info = client.fetch_word_info(word)
    if not info:
        return

    try:
        ec_data = info.get("ec", {}).get("word", [{}])[0]
        
        # Phonetics
        if "usphone" in ec_data:
            item["usphone"] = f"/{ec_data['usphone']}/"
        if "ukphone" in ec_data:
            item["ukphone"] = f"/{ec_data['ukphone']}/"
            
        # Translations
        trs = ec_data.get("trs", [])
        translations = []
        for tr in trs:
            l_data = tr.get("tr", [{}])[0].get("l", {}).get("i", [])
            if l_data:
                translations.append(l_data[0])
        
        if translations:
            item["translation"] = "\n".join(translations)
            
        item["definition"] = ""
        item["pos"] = ""
        
    except (IndexError, KeyError, TypeError):
        pass

def action(file_path_str: str) -> None:
    """Main action for a single JSON file processing using multiple threads."""
    file_path = Path(file_path_str)
    data = load_json(file_path)
    word_list = data.get("wordList", [])
    total = len(word_list)
    
    if total == 0:
        logger.warning(f"No words found in {file_path}")
        return

    # Use a shared manager and client for this file's word list
    manager = ConcurrencyManager(initial_limit=8)
    client = YoudaoClient(manager)
    progress_lock = threading.Lock()
    processed_count = 0

    logger.info(f"Starting multi-threaded processing for {file_path.name}...")
    
    # Process words in parallel
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_word, client, item): item for item in word_list}
        
        for future in as_completed(futures):
            # No matter if it succeeded or item was skipped, update progress
            processed_count += 1
            display_progress(file_path.name, processed_count, total, progress_lock)
            
            try:
                future.result()
            except Exception as e:
                logger.error(f"\nWorker thread execution error: {e}")
                # We don't necessarily want to kill the whole process here 
                # unless it's the specific "failure after 3 retries" handled in YoudaoClient
    
    write_json(file_path, data)
    logger.info(f"Done: {file_path.name}")
