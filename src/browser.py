"""
browser.py — Avvio del browser Selenium (Firefox o Chrome)
             con supporto headless e download automatico del driver.
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

try:
    from webdriver_manager.firefox import GeckoDriverManager
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    GeckoDriverManager = None
    ChromeDriverManager = None

from src.utils import log_info, log_error, log_warn


def create_driver(browser: str = "firefox", headless: bool = True, download_folder: str = None):
    """
    Crea e restituisce un WebDriver Selenium.

    Parametri:
        browser         : "firefox" o "chrome"
        headless        : True per browser invisibile
        download_folder : cartella per i download diretti del browser
                          (usato come fallback per alcuni file)

    Ritorna:
        Istanza WebDriver pronta all'uso, o None in caso di errore.
    """
    browser = browser.lower().strip()

    if browser == "firefox":
        return _create_firefox(headless, download_folder)
    elif browser in ("chrome", "chromium"):
        return _create_chrome(headless, download_folder)
    else:
        log_error(f"Browser non supportato: '{browser}'. Usa 'firefox' o 'chrome'.")
        return None


def _create_firefox(headless: bool, download_folder: str = None):
    """Crea un WebDriver Firefox."""
    log_info(f"Avvio Firefox {'(headless)' if headless else '(visibile)'}...")

    options = FirefoxOptions()

    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")

    # Profilo Firefox per gestire i download automatici
    if download_folder:
        os.makedirs(download_folder, exist_ok=True)
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", os.path.abspath(download_folder))
        options.set_preference("browser.download.useDownloadDir", True)
        options.set_preference("browser.helperApps.alwaysAsk.force", False)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk",
            "application/pdf,application/zip,application/octet-stream,"
            "application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation,"
            "application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
            "application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
            "text/plain,text/csv"
        )
        # Disabilita il PDF viewer interno (scarica invece di aprire)
        options.set_preference("pdfjs.disabled", True)

    # Sopprime log inutili
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("app.update.enabled", False)

    try:
        if GeckoDriverManager:
            service = FirefoxService(GeckoDriverManager().install())
        else:
            # Prova a usare geckodriver dal PATH
            service = FirefoxService()

        driver = webdriver.Firefox(service=service, options=options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(5)
        log_info("Firefox avviato con successo.")
        return driver

    except Exception as e:
        log_error(f"Impossibile avviare Firefox: {e}")
        log_warn("Assicurati di aver installato Firefox e che geckodriver sia disponibile.")
        log_warn("Prova: pip install webdriver-manager")
        return None


def _create_chrome(headless: bool, download_folder: str = None):
    """Crea un WebDriver Chrome."""
    log_info(f"Avvio Chrome {'(headless)' if headless else '(visibile)'}...")

    options = ChromeOptions()

    if headless:
        options.add_argument("--headless=new")  # Nuovo formato headless Chrome ≥ v109
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")

    # Disabilita notifiche e popup
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # Imposta cartella di download
    if download_folder:
        os.makedirs(download_folder, exist_ok=True)
        prefs = {
            "download.default_directory": os.path.abspath(download_folder),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
        }
        options.add_experimental_option("prefs", prefs)

    try:
        if ChromeDriverManager:
            service = ChromeService(ChromeDriverManager().install())
        else:
            service = ChromeService()

        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(5)
        log_info("Chrome avviato con successo.")
        return driver

    except Exception as e:
        log_error(f"Impossibile avviare Chrome: {e}")
        log_warn("Assicurati di aver installato Chrome/Chromium.")
        return None
