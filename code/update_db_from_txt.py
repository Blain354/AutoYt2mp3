"""
Auto Get Tunes - Database Update Module

This module handles YouTube search and database updates from text files.
It searches for songs on YouTube, extracts video URLs, detects duplicates,
and updates the centralized database with new entries.

Key Features:
- Automated YouTube search using Selenium WebDriver
- Intelligent duplicate detection based on YouTube video IDs
- Progress tracking with tqdm
- Handles YouTube consent pages automatically
- Updates centralized JSON database
- Preserves existing database entries

Author: Claude Sonnet 3.5 (Anthropic) under supervision of Guillaume Blain
"""

import sys, time, os, json
from urllib.parse import quote_plus, urlparse, parse_qs
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Absolute path to the JSON database (in the same folder as this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(SCRIPT_DIR, 'tunes_database.json')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("[INFO] tqdm not available. Recommended installation: pip install tqdm")

# Known YouTube consent page hostnames
CONSENT_HOSTS = ("consent.youtube.com", "consent.google.com")

def extract_video_id(youtube_url):
    """
    Extract YouTube video ID from URL.
    
    Args:
        youtube_url (str): YouTube URL to parse
        
    Returns:
        str|None: Video ID if found, None otherwise
    """
    parsed_url = urlparse(youtube_url)
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
    return None

def load_database():
    """
    Load the existing database from JSON file.
    
    Returns:
        list: Database entries or empty list if file doesn't exist
    """
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_database(data):
    """
    Save the database to JSON file.
    
    Args:
        data (list): Database entries to save
    """
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_duplicate(new_url, database):
    """
    Check if URL already exists in database based on video ID.
    
    Args:
        new_url (str): YouTube URL to check
        database (list): Current database entries
        
    Returns:
        dict|None: Existing entry if duplicate found, None otherwise
    """
    new_video_id = extract_video_id(new_url)
    if not new_video_id:
        return None
    
    for entry in database:
        existing_video_id = extract_video_id(entry['url'])
        if existing_video_id == new_video_id:
            return entry
    return None

@dataclass
class Config:
    """
    Configuration class for YouTube search parameters.
    
    Attributes:
        headless (bool): Run browser in headless mode
        timeout (int): Timeout in seconds for web operations
        pause_between_queries (float): Delay between searches to avoid rate limiting
        region_code (str): YouTube region code (optional, YouTube auto-adjusts)
    """
    headless: bool = True
    timeout: int = 15           # seconds for waits
    pause_between_queries: float = 0.8  # light throttling
    region_code: str = "CA"     # optional (YouTube adjusts anyway)

def build_driver(cfg: Config) -> webdriver.Chrome:
    """
    Create and configure a Chrome WebDriver instance for YouTube search.
    
    Args:
        cfg (Config): Configuration object with browser settings
        
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    chrome_opts = Options()
    if cfg.headless:
        chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1200,1200")
    chrome_opts.add_argument("--lang=en-US,en;q=0.9")
    chrome_opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/120.0.0.0 Safari/537.36")

    # Selenium Manager via webdriver-manager
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),
                              options=chrome_opts)
    driver.set_page_load_timeout(cfg.timeout + 10)
    return driver

def maybe_handle_consent(driver: webdriver.Chrome, cfg: Config):
    """
    Handle YouTube consent page if it appears by clicking the accept button.
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        cfg (Config): Configuration object
    """
    try:
        current_host = driver.current_url.split("/")[2]
    except Exception:
        current_host = ""
    if not any(h in current_host for h in CONSENT_HOSTS):
        return
    wait = WebDriverWait(driver, cfg.timeout)
    # Try multiple possible button labels
    candidates = [
        "//button//*[contains(text(),'I agree')]/ancestor::button",
        "//button//*[contains(text(),'Accept all')]/ancestor::button",
        "//button[contains(.,'I agree')]",
        "//button[contains(.,'Accept all')]",
        "//button[contains(.,'J’accepte tout') or contains(.,'J’accepte')]",
    ]
    for xp in candidates:
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            time.sleep(0.5)
            return
        except TimeoutException:
            continue
    # Si pas trouvé, on tente d’appuyer sur la première action visible
    try:
        any_btn = wait.until(EC.element_to_be_clickable((By.TAG_NAME, "button")))
        any_btn.click()
    except TimeoutException:
        pass

def first_video_url_from_results(driver: webdriver.Chrome, cfg: Config) -> Optional[str]:
    """
    Sur une page de résultats, retourne l'URL du 1er élément organique:
    - ytd-video-renderer (on évite ytd-promoted-* = pubs, ytd-reel-shelf = shorts, ytd-playlist-renderer = playlists).
    """
    wait = WebDriverWait(driver, cfg.timeout)
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-item-section-renderer")))
    except TimeoutException:
        return None

    # Lister tous les ytd-video-renderer visibles, prendre le premier
    try:
        items = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer a#video-title")
        for a in items:
            href = a.get_attribute("href")
            if href and "/watch" in href:
                return href
        return None
    except NoSuchElementException:
        return None

def search_query_and_get_first_url(driver: webdriver.Chrome, query: str, cfg: Config) -> Optional[str]:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    try:
        driver.get(url)
    except WebDriverException:
        # Retry unique si ça plante
        time.sleep(1.0)
        driver.get(url)

    maybe_handle_consent(driver, cfg)
    return first_video_url_from_results(driver, cfg)

def read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    return lines

def main(in_txt: str):
    # Configuration hardcodée
    cfg = Config(headless=True)  # Toujours en mode headless
    queries = read_lines(in_txt)
    if not queries:
        print("[ERREUR] Le fichier d'entrée ne contient aucune ligne.")
        sys.exit(2)

    # Charger la base de données existante
    database = load_database()
    
    print(f"[INFO] {len(queries)} requêtes à traiter")
    
    # Initialiser les variables de progression
    start_time = datetime.now()
    processed_count = 0
    new_entries = []
    duplicates_found = []
    
    # Initialize progress bar
    if TQDM_AVAILABLE:
        progress_bar = tqdm(
            total=len(queries),
            desc="YouTube Search",
            unit="query",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
    
    driver = build_driver(cfg)
    
    try:
        for idx, q in enumerate(queries, 1):
            # Calculate time estimation
            if processed_count > 0:
                elapsed_time = datetime.now() - start_time
                avg_time_per_item = elapsed_time / processed_count
                remaining_items = len(queries) - processed_count
                estimated_remaining = avg_time_per_item * remaining_items
                estimated_end = datetime.now() + estimated_remaining
                
                progress_info = f"ETA: {estimated_end.strftime('%H:%M:%S')}"
            else:
                progress_info = "Calculating..."
            
            # Update progress bar
            if TQDM_AVAILABLE:
                progress_bar.set_description(f"Search: {q[:25]}...")
                progress_bar.set_postfix_str(f"New: {len(new_entries)}, Duplicates: {len(duplicates_found)}")
            
            print(f"[{idx}/{len(queries)}] Search: {q}")
            url = search_query_and_get_first_url(driver, f"song: {q}", cfg)

            if url:
                # Check if this URL already exists in the database
                duplicate = check_duplicate(url, database)
                if duplicate:
                    print(f" -> DUPLICATE DETECTED: '{q}'")
                    print(f"    Existing title: {duplicate['title']}")
                    print(f"    Existing URL: {duplicate['url']}")
                    print(f"    Download path: {duplicate.get('download_path', 'Not specified')}")
                    print(f"    Project: {duplicate.get('project', 'Not specified')}")
                    duplicates_found.append({
                        'new_query': q,
                        'existing_entry': duplicate
                    })
                else:
                    print(f" -> NEW: {url}")
                    
                    # Create object for each new result (only if not duplicate)
                    result_obj = {
                        "title": q,
                        "url": url,
                        "done": False,
                        "download_path": "",  # Hardcoded empty
                        "project": ""  # To be filled manually
                    }
                    new_entries.append(result_obj)
            else:
                print(" -> No results found")
            
            # Update counters
            processed_count += 1
            
            # Update progress bar
            if TQDM_AVAILABLE:
                progress_bar.update(1)
            
            time.sleep(cfg.pause_between_queries)
    finally:
        driver.quit()
        # Close progress bar
        if TQDM_AVAILABLE:
            progress_bar.close()

    # Update database with new entries only
    if new_entries:
        database.extend(new_entries)
        save_database(database)
    
    # Calculate final statistics
    total_time = datetime.now() - start_time
    
    # Display summary
    print(f"\n=== SUMMARY ===")
    print(f"Total time: {str(total_time).split('.')[0]}")
    print(f"Queries processed: {processed_count}/{len(queries)}")
    print(f"New entries added: {len(new_entries)}")
    print(f"Duplicates detected: {len(duplicates_found)}")
    if processed_count > 0:
        avg_time = total_time / processed_count
        print(f"Average time per query: {str(avg_time).split('.')[0]}")
    
    if duplicates_found:
        print("\nDuplicates detected:")
        for dup in duplicates_found:
            print(f"  - '{dup['new_query']}' already exists as '{dup['existing_entry']['title']}'")
            print(f"    Path: {dup['existing_entry'].get('download_path', 'Not specified')}")
            print(f"    Project: {dup['existing_entry'].get('project', 'Not specified')}")
    
    print(f"Database updated: {DATABASE_FILE}")
    print(f"Total entries in database: {len(database)}")
    
    if new_entries:
        print(f"[OK] {len(new_entries)} new entries added to database")
    else:
        print("[INFO] No new entries added")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_db_from_txt.py <input.txt>")
        print("  input.txt : text file containing search queries (one per line)")
        sys.exit(1)
    
    in_txt = sys.argv[1]
    
    # Check that input file exists
    if not os.path.exists(in_txt):
        print(f"[ERROR] File '{in_txt}' does not exist.")
        sys.exit(1)
    
    print(f"[INFO] Analyzing file: {in_txt}")
    print(f"[INFO] Database: {DATABASE_FILE}")
    
    main(in_txt)
