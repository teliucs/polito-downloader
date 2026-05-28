"""
materials.py — Naviga le pagine dei corsi e scarica tutti i materiali.

Il modulo:
  1. Apre la pagina di un corso
  2. Trova la sezione "Materiale didattico" o "Materiali"
  3. Naviga ricorsivamente le cartelle
  4. Scarica ogni file trovato (PDF, ZIP, PPTX, ecc.)
  5. Replica la struttura delle cartelle in locale

Il portale PoliTo usa un sistema a cartelle/sottocartelle
con link per scaricare i file direttamente.
"""

import os
import time
import requests
from urllib.parse import urljoin, urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils import (
    log_info, log_ok, log_warn, log_error, log_skip, log_dl,
    sanitize_filename, ensure_dir, file_exists, format_size
)

WAIT_TIMEOUT = 20

# Estensioni di file da scaricare
DOWNLOADABLE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".zip", ".rar", ".7z", ".tar", ".gz",
    ".txt", ".csv", ".json", ".xml",
    ".py", ".java", ".c", ".cpp", ".h", ".m", ".r",
    ".mp4", ".mp3", ".avi", ".mkv",
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".ipynb", ".nb", ".m",
}

# Pattern URL che indicano link a file scaricabili nel portale
FILE_URL_PATTERNS = [
    "download",
    "scarica",
    "allegato",
    "file",
    "documento",
]

# Contatori globali per il riepilogo finale
stats = {"downloaded": 0, "skipped": 0, "errors": 0, "total_bytes": 0}


def download_course_materials(
    driver,
    course: dict,
    output_folder: str,
    skip_existing: bool = True,
):
    """
    Scarica tutti i materiali di un corso.

    Parametri:
        driver        : WebDriver Selenium
        course        : dict con "name" e "url"
        output_folder : cartella radice dove salvare i file
        skip_existing : se True, salta i file già presenti
    """
    course_name = sanitize_filename(course["name"])
    course_folder = os.path.join(output_folder, course_name)
    ensure_dir(course_folder)

    log_info(f"Elaborazione corso: {course['name']}")
    log_info(f"Cartella destinazione: {course_folder}")

    # Naviga alla pagina del corso
    driver.get(course["url"])
    time.sleep(2)

    # Trova la pagina dei materiali (potrebbe richiedere un click aggiuntivo)
    _navigate_to_materials(driver)
    time.sleep(2)

    # Recupera i cookie di sessione per usarli nei download diretti
    session_cookies = {c["name"]: c["value"] for c in driver.get_cookies()}

    # Avvia la navigazione ricorsiva
    _process_page(driver, course_folder, skip_existing, session_cookies, depth=0)

    log_ok(f"Corso '{course['name']}' completato.")


def _navigate_to_materials(driver):
    """
    Cerca e naviga alla sezione Materiali del corso.
    Prova diversi selettori per essere robusto.
    """
    material_keywords = [
        "materiale", "materiali", "material", "files",
        "dispense", "slides", "documenti", "allegati"
    ]

    try:
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            text = link.text.strip().lower()
            href = link.get_attribute("href") or ""

            # Controlla il testo del link
            if any(kw in text for kw in material_keywords):
                log_info(f"Trovata sezione materiali: '{link.text.strip()}'")
                driver.get(href)
                return

            # Controlla l'URL del link
            if any(kw in href.lower() for kw in material_keywords):
                log_info(f"Trovato link materiali: {href}")
                driver.get(href)
                return

    except Exception as e:
        log_warn(f"Navigazione materiali: {e}")

    # Se non troviamo un link specifico, lavoriamo sulla pagina corrente
    log_info("Lavorando sulla pagina corrente del corso.")


def _process_page(driver, current_folder: str, skip_existing: bool, cookies: dict, depth: int):
    """
    Processa la pagina corrente:
    - Scarica tutti i file trovati
    - Entra nelle sottocartelle ricorsivamente
    """
    if depth > 10:  # Protezione contro loop infiniti
        log_warn("Profondità massima raggiunta, salto questa cartella.")
        return

    current_url = driver.current_url
    page_source = driver.page_source

    # Trova tutti i link nella pagina
    links = driver.find_elements(By.TAG_NAME, "a")
    
    # DIAGNOSTICA MATERIALI
    log_info(f"Processo pagina materiali. URL: {driver.current_url}")
    log_info(f"Trovati {len(links)} link totali nel documento principale.")
    count = 0
    for l in links:
        try:
            href = l.get_attribute("href") or ""
            text = l.text.strip().replace("\n", " ")
            if text or href:
                log_info(f"  Link {count}: text='{text}' | href='{href}'")
                count += 1
                if count >= 100:
                    break
        except Exception:
            pass

    # Controlliamo se ci sono iframe (il portale didattica incorpora spesso i materiali in iframe)
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        log_info(f"Trovati {len(iframes)} iframe sulla pagina.")
        for idx, iframe in enumerate(iframes):
            iframe_id = iframe.get_attribute("id")
            iframe_src = iframe.get_attribute("src")
            log_info(f"  Iframe {idx}: id='{iframe_id}' | src='{iframe_src}'")
    except Exception as e:
        log_error(f"Errore controllo iframe: {e}")

    file_links = []
    folder_links = []

    for link in links:
        href = link.get_attribute("href") or ""
        text = link.text.strip()

        if not href or href == "#" or href.startswith("javascript:") or href.startswith("mailto:"):
            continue

        # Controlla se è un file scaricabile
        if _is_file_link(href, text):
            file_links.append({"url": href, "name": text or _extract_filename_from_url(href)})

        # Controlla se è una cartella/sottosezione
        elif _is_folder_link(href, text, current_url):
            folder_links.append({"url": href, "name": text})

    # Scarica i file trovati
    for file_info in file_links:
        _download_file(file_info["url"], file_info["name"], current_folder, skip_existing, cookies)

    # Entra nelle sottocartelle
    for folder_info in folder_links:
        folder_name = sanitize_filename(folder_info["name"]) or f"cartella_{depth}"
        sub_folder = os.path.join(current_folder, folder_name)
        ensure_dir(sub_folder)

        log_info(f"  {'  ' * depth}→ Cartella: {folder_info['name']}")

        # Naviga nella sottocartella
        driver.get(folder_info["url"])
        time.sleep(2)

        # Processa ricorsivamente
        _process_page(driver, sub_folder, skip_existing, cookies, depth + 1)

        # Torna indietro
        driver.get(current_url)
        time.sleep(1)


def _is_file_link(href: str, text: str) -> bool:
    """
    Controlla se il link punta a un file scaricabile.
    """
    href_lower = href.lower()

    # Controlla l'estensione nell'URL
    for ext in DOWNLOADABLE_EXTENSIONS:
        if href_lower.endswith(ext) or f"{ext}?" in href_lower:
            return True

    # Controlla pattern nel URL che indicano file del portale
    file_patterns = [
        "allegati",
        "download.php",
        "scarica",
        "getfile",
        "get_file",
        "documento",
        "/file/",
        "attachment",
    ]
    for pattern in file_patterns:
        if pattern in href_lower:
            return True

    return False


def _is_folder_link(href: str, text: str, current_url: str) -> bool:
    """
    Controlla se il link punta a una sottocartella/sottosezione.
    Esclude link a pagine esterne, ancora ('#'), ecc.
    """
    if not href or not text:
        return False

    href_lower = href.lower()
    text_lower = text.lower()

    # Esclude link che puntano fuori dal dominio
    current_domain = urlparse(current_url).netloc
    link_domain = urlparse(href).netloc
    if link_domain and link_domain != current_domain:
        return False

    # Esclude link che sono chiaramente file
    for ext in DOWNLOADABLE_EXTENSIONS:
        if href_lower.endswith(ext):
            return False

    # Pattern che suggeriscono una cartella
    folder_patterns = ["cartella", "folder", "sezione", "categoria", "categoria"]
    folder_url_patterns = ["id=", "cat=", "dir=", "folder=", "cartella="]

    if any(p in text_lower for p in folder_patterns):
        return True

    if any(p in href_lower for p in folder_url_patterns):
        return True

    return False


def _extract_filename_from_url(url: str) -> str:
    """Estrae il nome del file dall'URL."""
    path = urlparse(url).path
    filename = path.split("/")[-1]
    return filename if filename else "file_senza_nome"


def _download_file(url: str, name: str, folder: str, skip_existing: bool, cookies: dict):
    """
    Scarica un singolo file.

    Usa requests con i cookie Selenium per mantenere la sessione autenticata.
    """
    global stats

    # Determina il nome del file
    filename = sanitize_filename(name)
    if "." not in filename:
        # Prova a ricavare l'estensione dall'URL
        url_filename = _extract_filename_from_url(url)
        if "." in url_filename:
            ext = "." + url_filename.rsplit(".", 1)[-1]
            filename = filename + ext

    if not filename:
        filename = "file_senza_nome"

    file_path = os.path.join(folder, filename)

    # Salta se già esiste
    if skip_existing and file_exists(file_path):
        log_skip(f"{filename}")
        stats["skipped"] += 1
        return

    # Scarica
    try:
        log_dl(f"Download: {filename}")

        response = requests.get(
            url,
            cookies=cookies,
            stream=True,
            timeout=60,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Referer": "https://didattica.polito.it/",
            }
        )

        if response.status_code == 200:
            # Controlla se il nome file è specificato nell'header Content-Disposition
            content_disposition = response.headers.get("Content-Disposition", "")
            if "filename=" in content_disposition:
                cd_filename = content_disposition.split("filename=")[-1].strip().strip('"').strip("'")
                if cd_filename:
                    filename = sanitize_filename(cd_filename)
                    file_path = os.path.join(folder, filename)

            # Scrivi il file
            total_size = 0
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)

            stats["downloaded"] += 1
            stats["total_bytes"] += total_size
            log_ok(f"  ✓ {filename} ({format_size(total_size)})")

        elif response.status_code == 401:
            log_error(f"Accesso negato a {filename} (401). Sessione scaduta?")
            stats["errors"] += 1
        elif response.status_code == 404:
            log_warn(f"File non trovato: {filename} (404)")
            stats["errors"] += 1
        else:
            log_warn(f"Errore HTTP {response.status_code} per {filename}")
            stats["errors"] += 1

    except requests.Timeout:
        log_error(f"Timeout scaricando {filename}")
        stats["errors"] += 1
    except Exception as e:
        log_error(f"Errore scaricando {filename}: {e}")
        stats["errors"] += 1


def print_summary():
    """Stampa il riepilogo finale dei download."""
    print("\n" + "=" * 50)
    print("  RIEPILOGO DOWNLOAD")
    print("=" * 50)
    print(f"  ✅ Scaricati:  {stats['downloaded']} file ({format_size(stats['total_bytes'])})")
    print(f"  ⏭️  Saltati:    {stats['skipped']} file (già presenti)")
    print(f"  ❌ Errori:     {stats['errors']} file")
    print("=" * 50)


def reset_stats():
    """Azzera le statistiche (utile per più run)."""
    global stats
    stats = {"downloaded": 0, "skipped": 0, "errors": 0, "total_bytes": 0}
