"""
Auto Get Tunes - Conversion Module

This module handles the automated downloading and conversion of YouTube videos to MP3 format.
It processes entries from the database that have not been downloaded yet (done=False or done="timeout")
and attempts to download them using the y2mate.nu conversion service.

Key Features:
- Downloads songs from YouTube URLs stored in the database
- Uses Selenium WebDriver for web automation
- Provides progress tracking with tqdm
- Handles timeouts and errors gracefully
- Updates database with download status
- Closes unwanted popup tabs automatically

Author: Claude Sonnet 3.5 (Anthropic) under supervision of Guillaume Blain
"""

import time
import logging
import json
import os
import sys
from typing import List, Union, Tuple, Optional, Dict, Any
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Automatically installs the correct ChromeDriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("[INFO] tqdm not available. Recommended installation: pip install tqdm")


# =========================
# CONFIGURATION - HARDCODED SETTINGS
# =========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://y2mate.nu/R2lu/"           # <--- Conversion website
DATABASE_FILE = os.path.join(SCRIPT_DIR, 'tunes_database.json')  # <--- Database file
HEADLESS = True                           # Headless browser mode
PAGE_LOAD_TIMEOUT = 20                    # Page load timeout in seconds
IMPLICIT_WAIT = 1                         # Implicit wait for elements
EXPLICIT_WAIT = 2                         # Explicit wait for conditions
HIGHLIGHT_MS = 400                        # Element highlighting duration


# =========================
# LOGGING CONFIGURATION
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s"
)
log = logging.getLogger("selenium-generic")


# =========================
# CHROME WEBDRIVER SETUP
# =========================
def get_driver(headless: bool = False, download_dir: str = None) -> webdriver.Chrome:
    """
    Create and configure a Chrome WebDriver instance.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        download_dir (str): Directory for file downloads
        
    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance
    """
    # Create download directory if it doesn't exist
    if download_dir:
        os.makedirs(download_dir, exist_ok=True)
    
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Configure downloads
    if download_dir:
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        log.info("Download directory configured: %s", download_dir)
    
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.implicitly_wait(IMPLICIT_WAIT)
    
    return driver


# =========================
# DATABASE MANAGEMENT FUNCTIONS
# =========================
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

def update_database_entry(url, download_path, done_status=True):
    """
    Update a specific entry in the database.
    
    Args:
        url (str): YouTube URL to find in database
        download_path (str): Path where file was downloaded
        done_status (bool|str): Download status (True, False, or "timeout")
    """
    database = load_database()
    for entry in database:
        if entry['url'] == url:
            entry['done'] = done_status
            if download_path:
                entry['download_path'] = download_path
            break
    save_database(database)


# =========================
# UTILITY HELPER FUNCTIONS
# =========================
def is_visible(elem: WebElement) -> bool:
    """
    Check if a web element is visible on the page.
    
    Args:
        elem (WebElement): Element to check
        
    Returns:
        bool: True if element is visible and has size > 0
    """
    try:
        return elem.is_displayed() and elem.size.get("height", 0) > 0 and elem.size.get("width", 0) > 0
    except Exception:
        return False


def highlight(driver: webdriver.Chrome, elem: WebElement, ms: int = HIGHLIGHT_MS):
    """
    Add temporary visual border to element for debugging purposes.
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        elem (WebElement): Element to highlight
        ms (int): Highlight duration in milliseconds
    """
    try:
        driver.execute_script("arguments[0].setAttribute('data-old-style', arguments[0].getAttribute('style') || '');", elem)
        driver.execute_script("arguments[0].style.outline='3px solid magenta'; arguments[0].style.outlineOffset='2px';", elem)
        time.sleep(ms / 1000.0)
        driver.execute_script("arguments[0].setAttribute('style', arguments[0].getAttribute('data-old-style'));", elem)
    except Exception:
        pass


def short_label(elem: WebElement) -> str:
    """
    Build a short useful label for logging purposes.
    
    Args:
        elem (WebElement): Element to describe
        
    Returns:
        str: Short description of the element
    """
    tag = elem.tag_name.lower()
    id_ = elem.get_attribute("id") or ""
    name = elem.get_attribute("name") or ""
    placeholder = elem.get_attribute("placeholder") or ""
    aria = elem.get_attribute("aria-label") or ""
    text = (elem.text or "").strip()
    text = " ".join(text.split())
    if len(text) > 60:
        text = text[:57] + "..."
    return f"<{tag} id='{id_}' name='{name}' placeholder='{placeholder}' aria-label='{aria}' text='{text}'>"


def wait_dom_ready(driver: webdriver.Chrome, timeout: int = EXPLICIT_WAIT):
    """
    Wait for DOM to be ready (interactive or complete state).
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        timeout (int): Maximum wait time in seconds
    """
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
    )


# =========================
# CORE FUNCTIONS: ELEMENT DISCOVERY
# =========================
def list_text_boxes(driver: webdriver.Chrome, do_highlight: bool = True) -> List[WebElement]:
    """
    Return a list of visible text input fields:
    - input[type=text|search|email|url|number|tel|password]
    - textarea
    - [contenteditable=true]
    
    Args:
        driver (webdriver.Chrome): WebDriver instance
        do_highlight (bool): Whether to highlight found elements
        
    Returns:
        List[WebElement]: List of visible text input elements
    """
    selectors = [
        "input[type='text']",
        "input[type='search']", 
        "input[type='email']",
        "input[type='url']",
        "input[type='number']",
        "input[type='tel']",
        "input[type='password']",
        "textarea",
        "[contenteditable='true']",
    ]
    elems: List[WebElement] = []
    for sel in selectors:
        try:
            elems.extend(driver.find_elements(By.CSS_SELECTOR, sel))
        except Exception:
            pass

    # Filter for visible, unique elements (by id)
    uniq: List[WebElement] = []
    seen = set()
    for e in elems:
        if not is_visible(e):
            continue
        key = (e.id, e.get_attribute("outerHTML")[:120])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)

    log.info("== Text boxes found (%d) ==", len(uniq))
    for i, e in enumerate(uniq):
        if do_highlight:
            highlight(driver, e)
        log.info("[%02d] %s", i, short_label(e))
    return uniq


def list_buttons(driver: webdriver.Chrome, do_highlight: bool = True) -> List[WebElement]:
    """
    Retourne une liste de boutons visibles:
    - <button>
    - input[type=button|submit|reset|image]
    - [role=button]
    - éléments cliquables avec tabindex et onclick (best effort)
    """
    selectors = [
        "button",
        "input[type='button']",
        "input[type='submit']",
        "input[type='reset']",
        "input[type='image']",
        "[role='button']",
        "*[onclick]",
        "*[tabindex]",
    ]
    elems: List[WebElement] = []
    for sel in selectors:
        try:
            elems.extend(driver.find_elements(By.CSS_SELECTOR, sel))
        except Exception:
            pass

    # Filtrer visibles et semblant cliquables
    uniq: List[WebElement] = []
    seen = set()
    for e in elems:
        if not is_visible(e):
            continue
        # éliminer des doublons grossiers
        key = (e.id, e.get_attribute("outerHTML")[:120])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(e)

    log.info("== Boutons trouvés (%d) ==", len(uniq))
    for i, e in enumerate(uniq):
        if do_highlight:
            highlight(driver, e)
        log.info("[%02d] %s", i, short_label(e))
    return uniq


# =========================
# CORE: ACTIONS
# =========================
def enter_text_in_box(driver: webdriver.Chrome,
                      index_or_elem: Union[int, WebElement],
                      text: str,
                      clear: bool = True) -> bool:
    """
    Entre du texte dans une boîte (par index retourné par list_text_boxes ou directement par WebElement).
    """
    try:
        if isinstance(index_or_elem, int):
            boxes = list_text_boxes(driver, do_highlight=False)
            elem = boxes[index_or_elem]
        else:
            elem = index_or_elem

        highlight(driver, elem)
        if clear:
            elem.clear()
        elem.click()
        elem.send_keys(text)
        log.info("Texte entré dans %s", short_label(elem))
        return True
    except IndexError:
        log.error("Index de boîte invalide.")
    except Exception as e:
        log.error("Erreur enter_text_in_box: %s", e)
    return False


def click_button(driver: webdriver.Chrome,
                 index_or_elem: Union[int, WebElement]) -> bool:
    """
    Clique un bouton (par index retourné par list_buttons ou directement par WebElement).
    """
    try:
        if isinstance(index_or_elem, int):
            btns = list_buttons(driver, do_highlight=False)
            elem = btns[index_or_elem]
        else:
            elem = index_or_elem

        highlight(driver, elem)
        elem.click()
        log.info("Bouton cliqué: %s", short_label(elem))
        return True
    except IndexError:
        log.error("Index de bouton invalide.")
    except Exception as e:
        log.error("Erreur click_button: %s", e)
    return False


def press_key(driver: webdriver.Chrome,
              key: str,
              target: str = "page") -> bool:
    """
    Envoie une touche:
      - target="page": envoie sur <body> (focus page)
      - target="active": envoie à l'élément actif (document.activeElement)
    key: nom dans selenium.webdriver.common.keys.Keys (ex: 'ENTER', 'ESCAPE', 'TAB', 'F5')
    """
    try:
        key_value = getattr(Keys, key.upper())
    except AttributeError:
        log.error("Touche invalide: %s (exemples: ENTER, ESCAPE, TAB, F5)", key)
        return False

    try:
        if target == "active":
            active = driver.switch_to.active_element
            highlight(driver, active)
            active.send_keys(key_value)
        else:
            body = driver.find_element(By.TAG_NAME, "body")
            highlight(driver, body)
            body.send_keys(key_value)
        log.info("Touche envoyée: %s sur %s", key, target)
        return True
    except Exception as e:
        log.error("Erreur press_key: %s", e)
        return False


# =========================
# DOWNLOAD HELPERS
# =========================
def wait_for_download(download_dir: str, timeout: int = 30) -> Optional[str]:
    """Attend qu'un fichier soit téléchargé et retourne son nom."""
    log.info("Attente du téléchargement dans: %s", download_dir)
    start_time = time.time()
    initial_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
    
    while time.time() - start_time < timeout:
        if os.path.exists(download_dir):
            current_files = set(os.listdir(download_dir))
            new_files = current_files - initial_files
            
            # Filtrer les fichiers temporaires (.crdownload, .tmp)
            completed_files = [f for f in new_files if not f.endswith(('.crdownload', '.tmp', '.part'))]
            
            if completed_files:
                downloaded_file = completed_files[0]
                log.info("Fichier téléchargé: %s", downloaded_file)
                return downloaded_file
        
        time.sleep(1)
    
    log.warning("Aucun téléchargement détecté après %d secondes", timeout)
    return None


# =========================
# PIPELINE PRINCIPAL
# =========================
def find_input_by_id(driver: webdriver.Chrome, target_id: str) -> Optional[WebElement]:
    """Trouve un input par son ID."""
    try:
        elem = driver.find_element(By.ID, target_id)
        if is_visible(elem):
            return elem
    except Exception:
        pass
    return None


def find_button_by_text(driver: webdriver.Chrome, text: str) -> Optional[WebElement]:
    """Trouve un bouton contenant le texte spécifié (insensible à la casse)."""
    buttons = list_buttons(driver, do_highlight=False)
    for btn in buttons:
        btn_text = (btn.text or "").strip().lower()
        value = (btn.get_attribute("value") or "").strip().lower()
        if text.lower() in btn_text or text.lower() in value:
            return btn
    return None


def wait_for_button_with_text(driver: webdriver.Chrome, text: str, timeout: int = 60) -> Optional[WebElement]:
    """Attend qu'un bouton avec le texte spécifié apparaisse."""
    log.info("Attente du bouton contenant '%s'...", text)
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Utiliser XPath pour chercher plus largement
            xpath_queries = [
                f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]",
                f"//input[@type='button'][contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]",
                f"//input[@type='submit'][contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]",
                f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')][@onclick or @role='button']",
                f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]"
            ]
            
            for xpath in xpath_queries:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for elem in elements:
                        if is_visible(elem):
                            log.info("Bouton '%s' trouvé avec XPath!", text)
                            return elem
                except Exception:
                    continue
                    
            # Si pas trouvé avec XPath, essayer la méthode classique
            btn = find_button_by_text(driver, text)
            if btn:
                log.info("Bouton '%s' trouvé avec méthode classique!", text)
                return btn
                
        except Exception as e:
            log.debug("Erreur lors de la recherche du bouton: %s", e)
            
        time.sleep(1)
        
        # Log du progrès toutes les 10 secondes
        elapsed = time.time() - start_time
        if int(elapsed) % 10 == 0:
            log.info("Recherche en cours... %d/%d secondes", int(elapsed), timeout)
    
    log.error("Timeout: bouton '%s' non trouvé après %d secondes", text, timeout)
    return None


def close_new_tabs(driver: webdriver.Chrome, original_window: str):
    """Ferme tous les nouveaux onglets ouverts sauf l'onglet original."""
    try:
        current_windows = driver.window_handles
        if len(current_windows) > 1:
            log.info("Détection de %d onglets ouverts, fermeture des nouveaux onglets", len(current_windows))
            for window in current_windows:
                if window != original_window:
                    driver.switch_to.window(window)
                    driver.close()
                    log.info("Onglet fermé")
            # Retourner sur l'onglet original
            driver.switch_to.window(original_window)
            log.info("Retour sur l'onglet original")
    except Exception as e:
        log.error("Erreur lors de la fermeture des onglets: %s", e)


def process_file(driver: webdriver.Chrome, base_url: str, download_dir: str):
    # Lire les données depuis la base de données
    data = load_database()
    log.info("Base de données '%s' : %d entrées", DATABASE_FILE, len(data))
    
    # Compter les entrées à traiter
    entries_to_process = [item for item in data if item.get("done", False) is not True]
    total_entries = len(entries_to_process)
    
    if total_entries == 0:
        log.info("Toutes les entrées sont déjà traitées!")
        return
    
    log.info("Entrées à traiter: %d sur %d", total_entries, len(data))
    
    # Initialiser les variables de progression
    start_time = datetime.now()
    processed_count = 0
    successful_downloads = 0
    
    # Initialiser la barre de progression
    if TQDM_AVAILABLE:
        progress_bar = tqdm(
            total=total_entries,
            desc="Téléchargement",
            unit="fichier",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
    
    for idx, item in enumerate(data, 1):
        title = item.get("title", "")
        url = item.get("url", "")
        done_status = item.get("done", False)
        
        # Ignorer les éléments déjà traités avec succès
        if done_status is True:
            log.info("=== [Entrée %d/%d] '%s' - DÉJÀ TRAITÉE ===", idx, len(data), title)
            continue
            
        # Calculer l'estimation de temps
        elapsed_time = datetime.now() - start_time
        if processed_count > 0:
            avg_time_per_item = elapsed_time / processed_count
            remaining_items = total_entries - processed_count
            estimated_remaining = avg_time_per_item * remaining_items
            estimated_end = datetime.now() + estimated_remaining
            
            progress_info = f"ETA: {estimated_end.strftime('%H:%M:%S')} ({estimated_remaining})"
        else:
            progress_info = "Calcul en cours..."
        
        log.info("=== [Entrée %d/%d] '%s' ===", idx, len(data), title)
        if TQDM_AVAILABLE:
            progress_bar.set_description(f"Traitement: {title[:30]}...")
            progress_bar.set_postfix_str(progress_info)
        
        # Marquer comme en cours de traitement
        timeout_detected = False
        success = False
        
        try:
            # Aller sur la page de base
            log.info("Navigation vers %s", base_url)
            driver.get(base_url)
            wait_dom_ready(driver)
            time.sleep(3)  # Laisser le temps à la page de se charger complètement

            # 1. Trouver l'input avec id="v" et y entrer l'URL
            input_elem = find_input_by_id(driver, "v")
            if not input_elem:
                log.error("Input avec id='v' non trouvé sur la page")
                continue
            
            log.info("Saisie de l'URL dans l'input id='v'")
            highlight(driver, input_elem)
            input_elem.clear()
            input_elem.click()
            input_elem.send_keys(url)
            time.sleep(1)

            # 2. Cliquer sur le bouton "Convert"
            convert_btn = find_button_by_text(driver, "Convert")
            if not convert_btn:
                log.error("Bouton 'Convert' non trouvé")
                continue
            
            log.info("Clic sur le bouton Convert")
            highlight(driver, convert_btn)
            convert_btn.click()
            time.sleep(3)  # Attendre que la conversion commence

            # 3. Attendre et cliquer sur le bouton "Download"
            download_btn = wait_for_button_with_text(driver, "Download", timeout=60)
            if not download_btn:
                log.error("Bouton 'download' non trouvé - TIMEOUT détecté")
                timeout_detected = True
            else:
                log.info("Clic sur le bouton download")
                highlight(driver, download_btn)
                download_btn.click()
                
                # # 4. Attendre 2 secondes puis appuyer sur Enter
                # log.info("Attente de 2 secondes puis pression de Enter")
                # time.sleep(2)
                
                # Sauvegarder l'onglet actuel avant d'appuyer sur Enter
                original_window = driver.current_window_handle
                
                # try:
                #     press_key(driver, "ENTER", target="active")
                #     log.info("Touche Enter envoyée avec succès")
                # except Exception as e:
                #     log.warning("Erreur lors de l'envoi de Enter: %s", e)
                #     # Essayer sur le body si l'élément actif ne fonctionne pas
                #     try:
                #         press_key(driver, "ENTER", target="page")
                #         log.info("Touche Enter envoyée sur la page")
                #     except Exception as e2:
                #         log.error("Impossible d'envoyer Enter: %s", e2)
                
                # Wait for new tabs to open then close them
                time.sleep(1)
                close_new_tabs(driver, original_window)
                
                # Check if download started
                downloaded_file = wait_for_download(download_dir, timeout=10)
                if downloaded_file:
                    log.info("Download confirmed: %s", downloaded_file)
                else:
                    log.warning("No download detected, but process considered successful")
                
                success = True
            
            # Update status in database with new download_path
            if timeout_detected:
                item["done"] = "timeout"
                log.warning("Status updated: timeout for '%s'", title)
                update_database_entry(url, download_dir, "timeout")
            elif success:
                item["done"] = True
                log.info("Status updated: success for '%s'", title)
                update_database_entry(url, download_dir, True)
                # Update download_path in current entry as well
                item["download_path"] = download_dir
                successful_downloads += 1
            
            # Update progress counters
            processed_count += 1
            
            # Update progress bar
            if TQDM_AVAILABLE:
                progress_bar.update(1)
                success_rate = (successful_downloads / processed_count) * 100
                progress_bar.set_postfix_str(f"Success: {successful_downloads}/{processed_count} ({success_rate:.1f}%)")
            
            # Small pause before next entry
            time.sleep(2)
            if success:
                log.info("Processing of entry %d completed successfully", idx)

        except Exception as e:
            log.error("Error on entry '%s': %s", title, e)
            # Mark as timeout in case of unexpected error
            item["done"] = "timeout"
            processed_count += 1
            
            # Update progress bar even on error
            if TQDM_AVAILABLE:
                progress_bar.update(1)
                success_rate = (successful_downloads / processed_count) * 100
                progress_bar.set_postfix_str(f"Success: {successful_downloads}/{processed_count} ({success_rate:.1f}%)")
            
            # Try to recover by reloading the page
            try:
                log.info("Attempting recovery...")
                driver.get(base_url)
                time.sleep(2)
            except Exception:
                log.error("Unable to recover, moving to next entry")
            continue
        
        # Save database after each processed entry
        try:
            save_database(data)
            log.info("Database saved with new status")
        except Exception as e:
            log.error("Error saving database: %s", e)
    
    # Close progress bar
    if TQDM_AVAILABLE:
        progress_bar.close()
    
    # Display final statistics
    total_time = datetime.now() - start_time
    log.info("=== FINAL SUMMARY ===")
    log.info("Total time: %s", str(total_time).split('.')[0])
    log.info("Entries processed: %d/%d", processed_count, total_entries)
    log.info("Successful downloads: %d", successful_downloads)
    if processed_count > 0:
        success_rate = (successful_downloads / processed_count) * 100
        log.info("Success rate: %.1f%%", success_rate)
        avg_time = total_time / processed_count
        log.info("Average time per entry: %s", str(avg_time).split('.')[0])
    
    # Final save
    try:
        save_database(data)
        log.info("Final database save completed")
    except Exception as e:
        log.error("Error during final save: %s", e)


# =========================
# MAIN ENTRY POINT
# =========================
if __name__ == "__main__":
    # Command line arguments handling
    if len(sys.argv) != 2:
        print("Usage: python conversion.py <download_directory>")
        print("  download_directory : folder where to download files")
        sys.exit(1)
    
    download_dir = sys.argv[1]
    print(f"[INFO] Download directory: {download_dir}")
    
    # Check that database exists
    if not os.path.exists(DATABASE_FILE):
        print(f"[ERROR] Database '{DATABASE_FILE}' does not exist.")
        sys.exit(1)
    
    # Create download directory if it doesn't exist
    if not os.path.exists(download_dir):
        os.makedirs(download_dir, exist_ok=True)
        print(f"[INFO] Download directory created: {download_dir}")
    
    print(f"[INFO] Database: {DATABASE_FILE}")
    
    driver = get_driver(headless=HEADLESS, download_dir=download_dir)
    try:
        process_file(driver, BASE_URL, download_dir)
        log.info("Completed.")
    finally:
        driver.quit()
