# 🎓 PoliTo Material Downloader

> Downloader automatico ed efficiente per i materiali dei corsi dal Portale della Didattica del Politecnico di Torino.

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?style=flat-square&logo=selenium&logoColor=white)](https://selenium.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

---

## ⚡ Caratteristiche

- 🔐 **SSO & MFA Bypass**: Login automatico con gestione intelligente dei passaggi ridondanti (Skip MFA Setup).
- 📦 **Download Ultra-Rapido**: Scarica l'albero dei materiali in pacchetti ZIP ed estrae tutto all'istante mantenendo l'organizzazione originale delle cartelle.
- ⏭️ **Incremental Sync (Zero Sprechi)**: Rileva automaticamente i file già scaricati e scarica solo le novità, azzerando i tempi delle sincronizzazioni successive.
- 🔄 **Dual Browser & Auto-Fallback**: Supporto nativo per **Firefox** e **Google Chrome** con fallback automatico (se uno manca, usa l'altro).
- 🖥️ **Headless Execution**: Esecuzione silenziosa in background di default, con modalità visiva opzionale per il debug.

---

## 🚀 Quick Start

### 1. Clona e Installa
Apri il terminale ed esegui:
```bash
git clone https://github.com/teliucs/polito-downloader.git
cd polito-downloader
pip install -r requirements.txt
```

### 2. Configura le credenziali
Crea il tuo file di configurazione locale partendo dal template:
```bash
cp config.yaml.example config.yaml
```
Modifica il file `config.yaml` inserendo matricola e password del portale:
```yaml
credentials:
  username: "sXXXXXX"
  password: "la_tua_password"
```
> [!NOTE]
> Il file `config.yaml` è git-ignored di default. Le tue credenziali rimangono esclusivamente in locale sul tuo PC e non saranno mai caricate su GitHub.
> Se preferisci non salvare la password su disco, lascia i campi vuoti: ti verranno chiesti interattivamente al lancio dello script.

### 3. Esegui lo script
```bash
python polito_downloader.py
```

---

## ⚙️ Opzioni CLI

Puoi personalizzare l'esecuzione passando argomenti da riga di comando:

| Opzione | Scorciatoia | Descrizione |
| :--- | :--- | :--- |
| `--help` | `-h` | Mostra l'elenco dei comandi ed esce. |
| `--list-courses` | | Mostra solo la lista dei corsi disponibili senza scaricare nulla. |
| `--course "Nome"` | | Scarica direttamente solo il corso specificato (anche parziale). |
| `--browser <nome>` | `-b` | Forza il browser da usare: `firefox` o `chrome` (default: automatico/firefox). |
| `--no-headless` | | Rende visibile la finestra del browser (utile per debug o verifica 2FA). |

---

## 📁 Struttura Directory Generata

I materiali vengono scaricati ed estratti all'interno della cartella `downloads/` ricreando l'albero esatto del Portale:

```text
downloads/
├── Corso A/
│   ├── Syllabus.pdf
│   └── Lezioni/
│       ├── Slide_Lezione_1.pdf
│       └── Esercitazione_1.zip
└── Corso B/
    └── Slide/
        └── Presentazione.pptx
```

---

## 📄 Licenza & Note Legali

Rilasciato sotto licenza [MIT](LICENSE).

*Questo è un progetto indipendente e non ufficiale. Non è affiliato, sponsorizzato o supportato in alcun modo dal Politecnico di Torino.*
