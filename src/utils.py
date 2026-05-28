"""
utils.py — Funzioni di utilità (logging, path, ecc.)
"""

import os
import sys
import re
from colorama import init, Fore, Style

init(autoreset=True)  # Inizializza colorama (necessario su Windows)


# ─────────────────────────────────────────────
#  Logging colorato
# ─────────────────────────────────────────────

def log_info(msg: str):
    print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL}  {msg}")

def log_ok(msg: str):
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL}    {msg}")

def log_warn(msg: str):
    print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL}  {msg}")

def log_error(msg: str):
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")

def log_skip(msg: str):
    print(f"{Fore.WHITE}[SKIP]{Style.RESET_ALL}  {msg}")

def log_dl(msg: str):
    print(f"{Fore.MAGENTA}[DL]{Style.RESET_ALL}    {msg}")


# ─────────────────────────────────────────────
#  Gestione percorsi file
# ─────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    """
    Rimuove caratteri non validi dal nome file/cartella.
    Utile per nomi che vengono dal portale e contengono
    caratteri non permessi su Windows/Linux.
    """
    # Sostituisce caratteri non validi con underscore
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    # Rimuove spazi iniziali/finali e punti finali (problema su Windows)
    name = name.strip().rstrip('.')
    # Limita lunghezza a 200 caratteri per sicurezza
    return name[:200]


def ensure_dir(path: str):
    """Crea la directory (e le parent) se non esiste."""
    os.makedirs(path, exist_ok=True)


def file_exists(path: str) -> bool:
    """Restituisce True se il file esiste già."""
    return os.path.isfile(path)


def format_size(bytes_count: int) -> str:
    """Converte bytes in stringa leggibile (KB, MB, ecc.)."""
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 ** 2:
        return f"{bytes_count / 1024:.1f} KB"
    elif bytes_count < 1024 ** 3:
        return f"{bytes_count / 1024 ** 2:.1f} MB"
    else:
        return f"{bytes_count / 1024 ** 3:.1f} GB"
