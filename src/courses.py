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
COURSES_URL = "https://didattica.polito.it/pls/static/studente/#/didattica"

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
    # Naviga alla home studente solo se non ci siamo già, per evitare che Selenium si blocchi (hang) 
    # caricando un URL con hash (#) su cui siamo già posizionati.
    if "static/studente/#/didattica" not in driver.current_url.lower():
        driver.get(COURSES_URL)
        time.sleep(5)
    else:
        # Diamo comunque un piccolo tempo di assestamento per il caricamento dei dati asincroni
        time.sleep(4)

    # Se la pagina richiede di nuovo il login, segnala l'errore
    if "idp.polito.it" in driver.current_url:
        log_error("Sessione scaduta o login non riuscito. Riprova.")
        return []

    # Attende che gli elementi dei corsi siano renderizzati nella Single Page App
    try:
        WebDriverWait(driver, 15).until(
            lambda d: len(d.find_elements(By.XPATH, "//a[contains(@onclick, 'chiama_materia')]")) > 0
        )
        time.sleep(2)  # Diamo un piccolo tempo per completare la renderizzazione di tutte le card
    except TimeoutException:
        log_warn("Timeout attendendo il caricamento grafico dei corsi. Procedo comunque.")

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
    che analizza l'evento 'onclick' delle card dei corsi per recuperare l'URL reale
    e isolare il nome del corso, escludendo notifiche, avvisi e linguette di navigazione.
    """
    js_code = """
    const links = document.getElementsByTagName('a');
    const courses = [];
    for (let i = 0; i < links.length; i++) {
        const link = links[i];
        const onclick = link.getAttribute('onclick') || '';
        
        // Verifica se e' la card reale di un corso
        if (!onclick || !onclick.includes('chiama_materia')) continue;
        
        // Estrae l'URL dal parametro del gestore javascript click (markAsReadAndRedirect)
        const urlMatch = onclick.match(/'(https?:\\/\\/[^']+)'/);
        if (!urlMatch) continue;
        const url = urlMatch[1].replace(/&amp;/g, '&');
        
        // Estrae il codice insegnamento
        const codMatch = url.match(/cod_ins=([^&]+)/);
        if (!codMatch) continue;
        const cod_ins = codMatch[1];
        
        // Estrae il testo interno alla card (contiene nome del corso e dettagli)
        let text = link.innerText || link.textContent || '';
        text = text.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').trim();
        
        // Isola il nome pulito del corso tagliando via il codice corso e quello che segue
        const codeIndex = text.indexOf(cod_ins);
        if (codeIndex > 0) {
            text = text.substring(0, codeIndex).trim();
        }
        
        // Pulisce eventuali caratteri di punteggiatura residui (es. trattini finali)
        if (text.endsWith('-')) {
            text = text.substring(0, text.length - 1).trim();
        }
        
        if (!text) {
            text = "Corso " + cod_ins;
        }
        
        // Aggiunge all'elenco se non e' gia' presente
        if (!courses.some(c => c.url === url)) {
            courses.push({ name: text, url: url });
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
