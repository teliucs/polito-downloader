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
COURSES_URL = "https://didattica.polito.it/pls/static/studente/#/"

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
    log_info("Verifica pagina dei corsi...")

    # Naviga alla home studente solo se non ci siamo già, per evitare che Selenium si blocchi (hang) 
    # caricando un URL con hash (#) su cui siamo già posizionati.
    if "static/studente" not in driver.current_url.lower():
        log_info("Navigazione alla pagina dei corsi...")
        driver.get(COURSES_URL)
        time.sleep(5)
    else:
        log_info("Siamo già sulla pagina corretta del portale studente. Salto la navigazione diretta.")
        # Diamo comunque un piccolo tempo di assestamento per il caricamento dei dati asincroni
        time.sleep(4)

    # Se la pagina richiede di nuovo il login, segnala l'errore
    if "idp.polito.it" in driver.current_url:
        log_error("Sessione scaduta o login non riuscito. Riprova.")
        return []

    courses = _extract_courses(driver)

    if not courses:
        log_warn("Nessun corso trovato. Potrebbe essere un problema con la struttura del portale.")
        log_warn(f"URL corrente: {driver.current_url}")
        
        # DUMP DI DIAGNOSTICA
        log_info("--- DIAGNOSTICA: Elenco di tutti i link visibili sulla pagina ---")
        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            count = 0
            for l in all_links:
                href = l.get_attribute("href") or ""
                text = l.text.strip().replace("\n", " ")
                if text or href:
                    log_info(f"Link: text='{text}' | href='{href}'")
                    count += 1
                    if count > 45:
                        break
        except Exception as e:
            log_error(f"Errore durante la diagnostica dei link: {e}")
            
        return []

    log_info(f"Trovati {len(courses)} corsi nel portale.")

    # Filtra se richiesto
    if filter_list:
        courses = _filter_courses(courses, filter_list)
        log_info(f"Corsi da scaricare dopo il filtro: {len(courses)}")

    return courses


def _extract_courses(driver) -> list:
    """
    Estrae i corsi dalla pagina corrente eseguendo un JavaScript super-veloce
    nel browser, evitando rallentamenti o hang dovuti a roundtrip Selenium.
    """
    js_code = """
    const links = document.getElementsByTagName('a');
    const courses = [];
    const patterns = ["materiale", "materiali", "corso", "MATERIALE", "inizio.do", "pkg_corso", "pkg_web.corso"];
    for (let i = 0; i < links.length; i++) {
        const link = links[i];
        const href = link.href || '';
        let text = link.innerText || link.textContent || '';
        text = text.trim().replace(/\\s+/g, ' ');
        if (!text || !href) continue;
        
        // Verifica se l'URL e' relativo a un corso
        const isCourse = patterns.some(p => href.includes(p)) || 
                         href.includes('/corso/') || 
                         href.includes('/didattica/') ||
                         (href.includes('static/studente') && (href.includes('/0') || href.includes('/1')));
                         
        if (isCourse) {
            // Evita duplicati e link di sistema generici
            if (!courses.some(c => c.url === href) && 
                !href.endsWith('/didattica/') && 
                !href.endsWith('/didattica') &&
                !href.includes('/home') &&
                !href.includes('/servizi') &&
                !href.includes('/carriera') &&
                !href.includes('/area_personale')) {
                courses.push({ name: text, url: href });
            }
        }
    }
    return courses;
    """
    try:
        courses = driver.execute_script(js_code)
        if not courses:
            return []
            
        # Converti chiavi in stringhe pulite
        cleaned_courses = []
        for c in courses:
            if c.get("name") and c.get("url"):
                cleaned_courses.append({
                    "name": str(c["name"]).strip(),
                    "url": str(c["url"]).strip()
                })
        return cleaned_courses
    except Exception as e:
        log_warn(f"Errore durante l'estrazione JS dei corsi: {e}")
        return []


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
