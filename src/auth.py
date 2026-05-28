"""
auth.py — Login al Portale della Didattica del Politecnico di Torino
        tramite il sistema SSO (idp.polito.it)

Flusso di autenticazione:
  1. Naviga su https://didattica.polito.it
  2. Click su "Login" → redirect a idp.polito.it
  3. Inserisce matricola e password
  4. Gestisce eventuale OTP (2FA) chiedendolo all'utente in console
  5. Verifica che il login sia andato a buon fine
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
)

from src.utils import log_info, log_ok, log_warn, log_error

# URL del portale e dell'IDP
PORTAL_URL   = "https://didattica.polito.it/pls/portal30/sviluppo.pkg_web.portale_studente"
LOGIN_URL    = "https://idp.polito.it/idp/x509mixed-user-password-login"
IDP_DOMAIN   = "idp.polito.it"

# Timeout massimo (secondi) per ogni attesa elemento
WAIT_TIMEOUT = 20


def login(driver, username: str, password: str) -> bool:
    """
    Esegue il login al Portale della Didattica.

    Parametri:
        driver   : istanza Selenium WebDriver già avviata
        username : matricola (es. "s123456") o username Polito
        password : password del portale

    Ritorna:
        True  se il login è andato a buon fine
        False in caso di errore
    """
    try:
        log_info("Navigazione al Portale della Didattica...")
        driver.get("https://didattica.polito.it/")
        time.sleep(2)

        # ── Step 1: click sul pulsante Login / Accedi ─────────────────
        log_info("Click su 'Login'...")
        _click_login_button(driver)
        time.sleep(2)

        # ── Step 2: siamo su idp.polito.it, compiliamo il form ────────
        log_info("Inserimento credenziali...")
        wait = WebDriverWait(driver, WAIT_TIMEOUT)

        # Campo username
        username_field = wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        username_field.clear()
        username_field.send_keys(username)

        # Campo password
        password_field = driver.find_element(By.ID, "password")
        password_field.clear()
        password_field.send_keys(password)

        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        submit_btn.click()
        time.sleep(3)

        # ── Step 3: gestione eventuale 2FA / OTP ─────────────────────
        if _is_otp_required(driver):
            log_warn("Richiesto codice OTP (autenticazione a due fattori).")
            otp_code = input("  ➜ Inserisci il codice OTP e premi INVIO: ").strip()
            _submit_otp(driver, otp_code)
            time.sleep(3)

        # ── Step 4: verifica login riuscito ──────────────────────────
        if _login_successful(driver):
            log_ok("Login effettuato con successo!")
            return True
        else:
            log_error("Login fallito. Controlla username e password in config.yaml")
            return False

    except TimeoutException:
        log_error("Timeout durante il login. Il portale potrebbe essere lento o offline.")
        return False
    except Exception as e:
        log_error(f"Errore imprevisto durante il login: {e}")
        return False


def _click_login_button(driver):
    """
    Cerca e clicca il pulsante di login nel portale.
    Usa JavaScript click per bypassare elementi nascosti o sovrapposti.
    """
    # 1. Prova prima a cercare link che contengono "idp.polito.it" o hanno testo "Login" o "Accedi"
    try:
        # Cerca prima link con href all'IDP
        links = driver.find_elements(By.XPATH, "//a[contains(@href, 'idp.polito.it')]")
        if not links:
            # Fallback a testo "Login" o "Accedi" (case-insensitive)
            links = driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'ACEDI', 'acedi'), 'login') or contains(translate(text(), 'ACEDI', 'acedi'), 'accedi')]")
        
        if links:
            # Clicchiamo sul primo link trovato tramite JS per essere sicuri che funzioni anche se nascosto/coperto
            login_link = links[0]
            log_info("Clicco sul link di login tramite JavaScript...")
            driver.execute_script("arguments[0].click();", login_link)
            return
    except Exception as e:
        log_warn(f"Errore durante la ricerca/click del login link: {e}")

    # 2. Se non riusciamo, proviamo il vecchio metodo standard come fallback
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    try:
        login_link = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Login"))
        )
        login_link.click()
        return
    except Exception:
        pass

    # 3. Fallback estremo
    log_warn("Pulsante Login non trovato, navigo direttamente all'IDP...")
    driver.get(LOGIN_URL)


def _is_otp_required(driver) -> bool:
    """
    Controlla se la pagina corrente richiede un codice OTP.
    Cerca campi input per OTP o messaggi tipici della 2FA.
    """
    page_source = driver.page_source.lower()

    otp_indicators = [
        "one-time password",
        "otp",
        "codice di verifica",
        "second factor",
        "authentication code",
        "verifica in due passaggi",
        "two-factor",
        "2fa",
    ]

    for indicator in otp_indicators:
        if indicator in page_source:
            return True

    # Controlla la presenza di un campo OTP
    try:
        driver.find_element(By.CSS_SELECTOR, "input[name='otp'], input[name='passcode'], input[id*='otp']")
        return True
    except NoSuchElementException:
        return False


def _submit_otp(driver, otp_code: str):
    """Inserisce il codice OTP e fa submit."""
    try:
        # Cerca il campo OTP
        otp_field = driver.find_element(
            By.CSS_SELECTOR,
            "input[name='otp'], input[name='passcode'], input[id*='otp'], input[type='tel'], input[autocomplete='one-time-code']"
        )
        otp_field.clear()
        otp_field.send_keys(otp_code)

        # Submit
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        submit_btn.click()
    except NoSuchElementException:
        log_warn("Campo OTP non trovato automaticamente. Inserisci il codice manualmente nel browser.")
        input("  ➜ Premi INVIO quando hai completato il login nel browser...")


def _login_successful(driver) -> bool:
    """
    Verifica che il login sia andato a buon fine controllando:
    - Non siamo più su idp.polito.it
    - Non c'è un messaggio di errore nella pagina
    - Siamo su una pagina del portale studente
    """
    current_url = driver.current_url.lower()
    page_source = driver.page_source.lower()

    # Se siamo ancora sull'IDP con un errore → login fallito
    if IDP_DOMAIN in current_url:
        error_indicators = ["invalid", "error", "errore", "incorrect", "failed", "scorretto"]
        for indicator in error_indicators:
            if indicator in page_source:
                return False
        # Siamo sull'IDP ma senza errori → probabilmente OTP non gestito
        return False

    # Controlla che siamo su una pagina del portale
    portal_indicators = [
        "didattica.polito.it",
        "studente",
        "corsi",
        "logout",
        "disconnetti",
    ]
    for indicator in portal_indicators:
        if indicator in current_url or indicator in page_source:
            return True

    # In ogni caso, se non siamo sull'IDP, probabilmente il login è ok
    return IDP_DOMAIN not in current_url
