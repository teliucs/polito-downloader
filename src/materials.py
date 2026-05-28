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
import zipfile
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

    # Naviga alla pagina del corso
    driver.get(course["url"])
    time.sleep(4)

    # Trova la pagina dei materiali (potrebbe richiedere un click aggiuntivo)
    _navigate_to_materials(driver)
    time.sleep(2)

    # Avvia l'elaborazione dei materiali tramite l'iframe del File Manager
    _process_iframe_materials(driver, course_folder, skip_existing, output_folder)

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
                driver.get(href)
                return

            # Controlla l'URL del link
            if any(kw in href.lower() for kw in material_keywords):
                driver.get(href)
                return

    except Exception as e:
        log_warn(f"Navigazione materiali: {e}")

    pass


def _process_iframe_materials(driver, course_folder: str, skip_existing: bool, output_folder: str) -> bool:
    """
    Gestisce l'iframe dei materiali (DevExtreme File Manager):
    - Trova l'iframe
    - Si sposta nel suo contesto
    - Seleziona tutto ("SELEZIONA TUTTO")
    - Clicca su "Download"
    - Attende il completamento del download del file ZIP
    - Estrae il file ZIP nella cartella locale del corso
    - Pulisce i file temporanei
    """
    try:
        # Cerca l'iframe del file manager
        iframe_elements = driver.find_elements(By.TAG_NAME, "iframe")
        target_iframe = None
        for iframe in iframe_elements:
            src = iframe.get_attribute("src") or ""
            if "file_manager" in src:
                target_iframe = iframe
                break
        
        if not target_iframe:
            log_warn("File Manager dei materiali non trovato su questa pagina.")
            return False

        driver.switch_to.frame(target_iframe)
        
        # Attende che il file manager sia caricato ed elementi renderizzati
        try:
            # Attende che gli elementi del file manager siano renderizzati (fino a 10s)
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CLASS_NAME, "dx-filemanager-thumbnails-item")) > 0
            )
            time.sleep(1) # Piccolo assestamento finale
        except TimeoutException:
            time.sleep(3)

        # Controlla se ci sono elementi da scaricare
        items = driver.find_elements(By.CLASS_NAME, "dx-filemanager-thumbnails-item")
        if not items:
            log_info("Nessun materiale disponibile per questo corso.")
            driver.switch_to.default_content()
            return True

        # Cerca il pulsante "SELEZIONA TUTTO"
        select_all_btn = None
        try:
            select_all_btn = driver.find_element(
                By.XPATH, 
                "//div[contains(text(), 'SELEZIONA TUTTO') or contains(text(), 'Seleziona tutto') or @aria-label='Seleziona tutto' or @aria-label='Select all']"
            )
        except Exception:
            # Fallback: cerca tra tutti i bottoni DevExtreme
            buttons = driver.find_elements(By.CLASS_NAME, "dx-button")
            for btn in buttons:
                text = btn.text.strip().lower()
                val = (btn.get_attribute("aria-label") or "").lower()
                if "seleziona tutto" in text or "select all" in text or "seleziona tutto" in val or "select all" in val:
                    select_all_btn = btn
                    break

        if not select_all_btn:
            log_error("Impossibile selezionare i materiali.")
            driver.switch_to.default_content()
            return False

        driver.execute_script("arguments[0].click();", select_all_btn)
        time.sleep(2)

        # Cerca il pulsante di Download
        download_btn = None
        try:
            download_btn = driver.find_element(
                By.XPATH,
                "//div[@aria-label='Download' or @aria-label='Scarica' or contains(@class, 'dx-icon-download')]"
            )
        except Exception:
            # Fallback
            buttons = driver.find_elements(By.CLASS_NAME, "dx-button")
            for btn in buttons:
                val = (btn.get_attribute("aria-label") or "").lower()
                if "download" in val or "scarica" in val:
                    download_btn = btn
                    break

        if not download_btn:
            log_error("Impossibile avviare il download.")
            driver.switch_to.default_content()
            return False

        log_info("Generazione e download dell'archivio materiali (ZIP)...")
        # Prepara e pulisce la cartella temporanea
        tmp_dl_dir = os.path.join(output_folder, "_tmp_browser_dl")
        os.makedirs(tmp_dl_dir, exist_ok=True)
        for f in os.listdir(tmp_dl_dir):
            try:
                os.remove(os.path.join(tmp_dl_dir, f))
            except Exception:
                pass

        driver.execute_script("arguments[0].click();", download_btn)

        # Attende il completamento del download
        zip_file_path = _wait_for_zip_download(tmp_dl_dir, timeout=90)
        
        if not zip_file_path:
            log_error("Errore o timeout durante il download del pacchetto ZIP dal portale.")
            driver.switch_to.default_content()
            return False

        log_ok("Pacchetto materiali scaricato con successo.")
        
        # Estrae e logga i file tracciando statistiche
        _extract_and_log_zip(zip_file_path, course_folder, skip_existing)

        # Rimuove il file zip temporaneo
        try:
            os.remove(zip_file_path)
        except Exception as e:
            log_warn(f"Impossibile rimuovere il file temporaneo {zip_file_path}: {e}")

        # Torna al frame principale
        driver.switch_to.default_content()
        return True

    except Exception as e:
        log_error(f"Errore durante l'elaborazione dell'iframe del File Manager: {e}")
        try:
            driver.switch_to.default_content()
        except Exception:
            pass
        return False


def _wait_for_zip_download(directory: str, timeout: int = 90) -> str:
    """
    Attende che nella directory indicata compaia un file ZIP completo e non temporaneo.
    Ritorna il path assoluto del file ZIP, o None in caso di timeout.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        files = os.listdir(directory)
        
        # Controlla file temporanei Firefox o Chrome in corso
        temp_exists = any(
            f.endswith(".part") or f.endswith(".crdownload") or f.startswith(".lk")
            for f in files
        )
        if temp_exists:
            time.sleep(1)
            continue
            
        zip_files = [f for f in files if f.endswith(".zip")]
        if zip_files:
            file_path = os.path.join(directory, zip_files[0])
            try:
                size_1 = os.path.getsize(file_path)
                time.sleep(1.5)
                size_2 = os.path.getsize(file_path)
                if size_1 == size_2 and size_1 > 0:
                    return file_path
            except Exception:
                pass
                
        time.sleep(1)
    return None


def _extract_and_log_zip(zip_path: str, target_folder: str, skip_existing: bool):
    """
    Estrae i file dallo ZIP tracciando i progressi, saltando i già presenti
    se richiesto e aggiornando le statistiche globali dei download.
    """
    global stats
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            # Filtra solo i file effettivi (esclude le cartelle vuote)
            members = [m for m in z.infolist() if not m.is_dir()]
            
            log_info(f"Estrazione ed analisi di {len(members)} file...")
            
            for member in members:
                filename = member.filename
                dest_path = os.path.join(target_folder, filename)
                dest_dir = os.path.dirname(dest_path)
                ensure_dir(dest_dir)
                
                # Controlla se saltare
                if skip_existing and file_exists(dest_path):
                    stats["skipped"] += 1
                    continue
                    
                # Estrae
                try:
                    z.extract(member, target_folder)
                    
                    size = member.file_size
                    stats["downloaded"] += 1
                    stats["total_bytes"] += size
                    log_ok(f"✓  {filename} ({format_size(size)})")
                except Exception as ex:
                    log_error(f"Errore durante l'estrazione di {filename}: {ex}")
                    stats["errors"] += 1
                    
    except Exception as e:
        log_error(f"Impossibile leggere o estrarre l'archivio ZIP scaricato: {e}")
        stats["errors"] += 1


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
