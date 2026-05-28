"""
courses.py — Recupera la lista dei corsi a cui lo studente è iscritto
             dal Portale della Didattica del Politecnico di Torino.

Il portale organizza i corsi nella home dello studente.
Questo modulo naviga alla pagina dei corsi e restituisce
una lista di dizionari con nome e URL di ogni corso.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.utils import log_info, log_warn, log_error

# URL della pagina corsi (home studente)
COURSES_URL = "https://didattica.polito.it/pls/portal30/sviluppo.pkg_web.portale_studente"

WAIT_TIMEOUT = 20


def get_courses(driver, filter_list: list = None) -> list:
    """
    Recupera tutti i corsi dello studente.

    Parametri:
        driver      : WebDriver Selenium
        filter_list : lista di stringhe (nomi parziali dei corsi da includere).
                      Se vuota o None, restituisce TUTTI i corsi.

    Ritorna:
        Lista di dict: [{"name": "...", "url": "..."}, ...]
    """
    log_info("Navigazione alla pagina dei corsi...")

    # Naviga alla home studente
    driver.get(COURSES_URL)
    time.sleep(3)

    # Se la pagina richiede di nuovo il login, segnala l'errore
    if "idp.polito.it" in driver.current_url:
        log_error("Sessione scaduta o login non riuscito. Riprova.")
        return []

    courses = _extract_courses(driver)

    if not courses:
        log_warn("Nessun corso trovato. Potrebbe essere un problema con la struttura del portale.")
        log_warn(f"URL corrente: {driver.current_url}")
        return []

    log_info(f"Trovati {len(courses)} corsi nel portale.")

    # Filtra se richiesto
    if filter_list:
        courses = _filter_courses(courses, filter_list)
        log_info(f"Corsi da scaricare dopo il filtro: {len(courses)}")

    return courses


def _extract_courses(driver) -> list:
    """
    Estrae i corsi dalla pagina corrente.
    Prova più strategie per trovare i link ai corsi,
    in modo da essere robusto ai cambiamenti del portale.
    """
    courses = []
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    # ── Strategia 1: link con "materiale" o "corso" nell'URL ──────────
    try:
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            href = link.get_attribute("href") or ""
            text = link.text.strip()

            if not text or not href:
                continue

            # I link ai corsi di solito contengono questi pattern nell'URL
            course_url_patterns = [
                "materiale",
                "materiali",
                "corso",
                "MATERIALE",
                "inizio.do",
                "guida_PCTO",
                "pkg_corso",
                "pkg_web.corso",
            ]

            is_course_link = any(pattern in href for pattern in course_url_patterns)

            # Oppure sono nella sezione "I miei corsi"
            if not is_course_link:
                continue

            # Evita duplicati
            if not any(c["url"] == href for c in courses):
                courses.append({"name": text, "url": href})

    except Exception as e:
        log_warn(f"Strategia 1 fallita: {e}")

    # ── Strategia 2: cerca sezione "I miei corsi" ─────────────────────
    if not courses:
        try:
            # Cerca heading con "corsi" o sezioni dedicate
            sections = driver.find_elements(
                By.CSS_SELECTOR,
                "[class*='corso'], [class*='course'], [id*='corso'], [id*='course']"
            )
            for section in sections:
                links = section.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    if text and href and href.startswith("http"):
                        if not any(c["url"] == href for c in courses):
                            courses.append({"name": text, "url": href})
        except Exception as e:
            log_warn(f"Strategia 2 fallita: {e}")

    # ── Strategia 3: cerca tabelle con elenco corsi ───────────────────
    if not courses:
        try:
            table_rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            for row in table_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                for cell in cells:
                    links = cell.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href") or ""
                        text = link.text.strip()
                        # I nomi dei corsi al PoliTo tendono ad essere in maiuscolo
                        if text and href and len(text) > 5 and text[0].isupper():
                            if not any(c["url"] == href for c in courses):
                                courses.append({"name": text, "url": href})
        except Exception as e:
            log_warn(f"Strategia 3 fallita: {e}")

    return courses


def _filter_courses(courses: list, filter_list: list) -> list:
    """
    Filtra i corsi tenendo solo quelli il cui nome contiene
    almeno una delle stringhe in filter_list (case-insensitive).
    """
    if not filter_list:
        return courses

    filtered = []
    for course in courses:
        name_lower = course["name"].lower()
        for filter_term in filter_list:
            if filter_term.lower() in name_lower:
                filtered.append(course)
                break

    if not filtered:
        log_warn("Nessun corso corrisponde ai filtri specificati in config.yaml.")
        log_warn("Corsi disponibili:")
        for c in courses:
            log_warn(f"  - {c['name']}")

    return filtered


def print_courses(courses: list):
    """Stampa la lista dei corsi trovati."""
    if not courses:
        print("  (nessun corso trovato)")
        return

    for i, course in enumerate(courses, 1):
        print(f"  {i:2}. {course['name']}")
