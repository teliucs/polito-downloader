#!/usr/bin/env python3
"""
polito_downloader.py — Script principale per scaricare i materiali
                        del Portale della Didattica del Politecnico di Torino.

Uso:
    python polito_downloader.py                     # usa config.yaml
    python polito_downloader.py --config altro.yaml  # usa un altro file di config
    python polito_downloader.py --list-courses       # mostra solo i corsi disponibili
    python polito_downloader.py --no-headless        # apre il browser visibile (debug)

Per iniziare:
    1. Copia config.yaml.example -> config.yaml
    2. Inserisci le tue credenziali PoliTo in config.yaml
    3. Esegui: python polito_downloader.py
"""

import sys
import os
import argparse
import getpass
import yaml
from colorama import init, Fore, Style

# Forza UTF-8 su Windows per evitare UnicodeEncodeError nella console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

init(autoreset=True)

from src.browser import create_driver
from src.auth import login
from src.courses import get_courses, print_courses
from src.materials import download_course_materials, print_summary, reset_stats
from src.utils import log_info, log_ok, log_warn, log_error, ensure_dir


# ─────────────────────────────────────────────────────────────
#  Banner ASCII
# ─────────────────────────────────────────────────────────────

BANNER = f"""
{Fore.CYAN}+-------------------------------------------------------+
|   {Fore.WHITE}PoliTo Material Downloader{Fore.CYAN}                        |
|   {Fore.WHITE}Portale della Didattica - Politecnico di Torino{Fore.CYAN}   |
|   {Fore.GREEN}github.com/loren/PoliTo-downloader{Fore.CYAN}                |
+-------------------------------------------------------+{Style.RESET_ALL}
"""


# ─────────────────────────────────────────────────────────────
#  Caricamento configurazione
# ─────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "download": {
        "output_folder": "./downloads",
        "headless": True,
        "browser": "firefox",
        "courses": [],
        "skip_existing": True,
    },
    "credentials": {
        "username": "",
        "password": "",
    }
}


def load_config(config_path: str) -> dict:
    """
    Carica il file di configurazione YAML.
    Il file e' opzionale: se non esiste vengono usati i valori di default.
    """
    merged = {
        "download": DEFAULT_CONFIG["download"].copy(),
        "credentials": DEFAULT_CONFIG["credentials"].copy()
    }

    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if config:
            if "download" in config:
                merged["download"].update(config["download"])
            if "credentials" in config:
                merged["credentials"].update(config["credentials"])
    else:
        log_warn(f"config.yaml non trovato, uso impostazioni di default.")
        log_warn("Copia config.yaml.example -> config.yaml per personalizzare le impostazioni.")

    return merged


def ask_credentials(config: dict) -> tuple:
    """
    Ottiene matricola e password.
    Se sono nel file config.yaml usa quelle, altrimenti le chiede interattivamente.
    La password viene chiesta in chiaro (richiesta utente) per evitare errori di digitazione.
    """
    credentials = config.get("credentials", {})
    username = credentials.get("username", "")
    password = credentials.get("password", "")

    if username and password:
        log_info("Credenziali caricate da config.yaml.")
        return str(username), str(password)

    print(f"\n{Fore.CYAN}--- Credenziali PoliTo ---{Style.RESET_ALL}")
    
    if not username:
        username = input(f"  Matricola (es. s123456): ").strip()
        if not username:
            log_error("Matricola non inserita.")
            sys.exit(1)
    else:
        print(f"  Matricola: {username} (da config.yaml)")

    if not password:
        password = input(f"  Password (in chiaro):   ").strip()
        if not password:
            log_error("Password non inserita.")
            sys.exit(1)
    else:
        print(f"  Password: [caricata da config.yaml]")
        
    print()
    return str(username), str(password)


def prompt_course_selection(courses: list) -> list:
    """
    Mostra un menu interattivo nel terminale per permettere all'utente
    di selezionare quali corsi scaricare.
    """
    print(f"{Fore.CYAN}--- Selezione Corsi da scaricare ---{Style.RESET_ALL}")
    print(f"  0. {Fore.GREEN}[Scarica TUTTI i corsi]{Style.RESET_ALL}")
    for i, course in enumerate(courses, 1):
        print(f"  {i}. {course['name']}")
    
    print()
    selection = input(f"  ➜ Inserisci i numeri dei corsi da scaricare separati da virgola (es. 1,3 o 0 per tutti): ").strip()
    
    if not selection or selection == "0":
        return courses
        
    selected_courses = []
    parts = selection.split(",")
    for part in parts:
        try:
            idx = int(part.strip())
            if 1 <= idx <= len(courses):
                selected_courses.append(courses[idx - 1])
        except ValueError:
            pass
            
    if not selected_courses:
        log_warn("Nessuna selezione valida. Verranno scaricati TUTTI i corsi.")
        return courses
        
    return selected_courses


# ─────────────────────────────────────────────────────────────
#  Argomenti da riga di comando
# ─────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Scarica i materiali del Portale della Didattica del Politecnico di Torino.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python polito_downloader.py                     # Scarica tutti i corsi
  python polito_downloader.py --list-courses       # Mostra corsi disponibili
  python polito_downloader.py --no-headless        # Apre il browser visibile
  python polito_downloader.py --config altro.yaml  # Usa altro file di config
        """
    )

    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Percorso al file di configurazione (default: config.yaml)"
    )
    parser.add_argument(
        "--list-courses",
        action="store_true",
        help="Mostra solo la lista dei corsi disponibili senza scaricare"
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Apre il browser in modo visibile (utile per debug o 2FA)"
    )
    parser.add_argument(
        "--course",
        type=str,
        help="Scarica solo un corso specifico (nome parziale, sovrascrive config.yaml)"
    )
    parser.add_argument(
        "--browser", "-b",
        type=str,
        choices=["firefox", "chrome"],
        help="Browser da usare: 'firefox' o 'chrome' (sovrascrive config.yaml)"
    )

    return parser.parse_args()


# ─────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────

def main():
    print(BANNER)

    # Parsing argomenti
    args = parse_args()

    # Carica configurazione (impostazioni, NON credenziali)
    config = load_config(args.config)

    # Override da argomenti CLI
    if args.no_headless:
        config["download"]["headless"] = False
    if args.course:
        config["download"]["courses"] = [args.course]
    if args.browser:
        config["download"]["browser"] = args.browser

    # Chiedi credenziali in modo interattivo o caricale da config
    username, password = ask_credentials(config)

    # Impostazioni
    output_folder = config["download"]["output_folder"]
    headless      = config["download"]["headless"]
    browser_name  = config["download"].get("browser", "firefox")
    course_filter = config["download"].get("courses", [])
    skip_existing = config["download"].get("skip_existing", True)

    # Crea cartella output
    ensure_dir(output_folder)

    # ── Avvio browser ───────────────────────────────────────────────
    driver = create_driver(
        browser=browser_name,
        headless=headless,
        download_folder=os.path.join(output_folder, "_tmp_browser_dl")
    )
    if driver is None:
        log_error("Impossibile avviare il browser. Controlla l'installazione.")
        sys.exit(1)

    try:
        # ── Login ────────────────────────────────────────────────────
        log_info(f"Login come: {username}")
        success = login(driver, username, password)

        if not success:
            log_error("Login fallito. Verifica le credenziali in config.yaml.")
            sys.exit(1)

        print()

        # ── Lista corsi ──────────────────────────────────────────────
        courses = get_courses(driver, filter_list=course_filter if course_filter else None)

        if not courses:
            log_warn("Nessun corso trovato. Il portale potrebbe avere una struttura diversa.")
            log_warn("Prova ad eseguire con --no-headless per vedere cosa succede nel browser.")
            sys.exit(1)

        print()
        log_ok(f"Corsi trovati ({len(courses)}):")
        print_courses(courses)
        print()

        # Se richiesto solo elenco corsi, esci qui
        if args.list_courses:
            log_info("Modalità --list-courses: nessun download effettuato.")
            return

        # Chiedi selezione corsi se non ci sono filtri preimpostati (CLI o config)
        if not course_filter:
            courses = prompt_course_selection(courses)
            print()

        # ── Download materiali ───────────────────────────────────────
        log_info("Avvio download materiali...")
        print("─" * 50)

        reset_stats()
        for i, course in enumerate(courses, 1):
            print()
            print(f"{Fore.CYAN}[{i}/{len(courses)}]{Style.RESET_ALL} {course['name']}")
            try:
                download_course_materials(
                    driver=driver,
                    course=course,
                    output_folder=output_folder,
                    skip_existing=skip_existing,
                )
            except Exception as e:
                log_error(f"Errore nel corso '{course['name']}': {e}")
                continue

        # Riepilogo finale
        print_summary()
        log_ok(f"Materiali salvati in: {os.path.abspath(output_folder)}")

    except KeyboardInterrupt:
        print()
        log_warn("Download interrotto dall'utente (Ctrl+C).")
        print_summary()

    finally:
        log_info("Chiusura browser...")
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
