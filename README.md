# 🎓 PoliTo Material Downloader

> Scarica automaticamente tutti i materiali dei tuoi corsi dal Portale della Didattica del Politecnico di Torino.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-orange?logo=selenium)](https://selenium.dev/)

---

## ✨ Funzionalità

- 🔐 **Login automatico** via SSO del Politecnico (supporta anche la 2FA)
- 📚 **Tutti i corsi** — scarica i materiali di uno o più corsi (o tutti in una volta)
- 📁 **Struttura originale** — mantiene la struttura a cartelle del portale
- ⏭️ **Skip intelligente** — salta i file già scaricati (solo i nuovi)
- 🖥️ **Browser invisibile** — funziona in background, senza aprire finestre
- 🔄 **Multi-browser** — supporta Firefox e Chrome

---

## 📋 Requisiti

- **Python 3.8+**
- **Firefox** (consigliato) oppure **Chrome**

---

## 🚀 Installazione

### 1. Clona il repository

```bash
git clone https://github.com/TUO_USERNAME/PoliTo-downloader.git
cd PoliTo-downloader
```

### 2. Installa le dipendenze Python

```bash
pip install -r requirements.txt
```

### 3. Configura le tue credenziali

Copia il file di configurazione di esempio e modifica le credenziali:

```bash
# Su Linux/macOS
cp config.yaml.example config.yaml

# Su Windows
copy config.yaml.example config.yaml
```

Apri `config.yaml` con un editor di testo e inserisci:

```yaml
polito:
  username: "s123456"       # La tua matricola
  password: "tuapassword"   # La tua password

download:
  output_folder: "./downloads"
  headless: true            # true = browser invisibile
  browser: "firefox"        # "firefox" o "chrome"
  courses: []               # [] = tutti i corsi
  skip_existing: true
```

> ⚠️ **Importante**: non committare mai `config.yaml` su Git! È già nel `.gitignore`.

---

## ▶️ Utilizzo

### Scarica tutti i materiali

```bash
python polito_downloader.py
```

### Mostra solo la lista dei corsi (senza scaricare)

```bash
python polito_downloader.py --list-courses
```

### Scarica solo un corso specifico

```bash
python polito_downloader.py --course "Analisi Matematica"
```

### Apri il browser in modo visibile (utile per debug)

```bash
python polito_downloader.py --no-headless
```

### Usa un file di configurazione diverso

```bash
python polito_downloader.py --config mio_config.yaml
```

---

## 📁 Struttura dell'output

I file vengono organizzati in cartelle:

```
downloads/
├── Analisi Matematica II/
│   ├── Lezioni/
│   │   ├── Lezione_01.pdf
│   │   └── Lezione_02.pdf
│   └── Esercizi/
│       └── Esercizi_cap1.pdf
├── Fisica I/
│   ├── Slide_Meccanica.pptx
│   └── Formulario.pdf
└── ...
```

---

## 🔧 Opzioni di configurazione

| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `polito.username` | Matricola PoliTo (es. `s123456`) | — |
| `polito.password` | Password del portale | — |
| `download.output_folder` | Cartella dove salvare i file | `./downloads` |
| `download.headless` | Browser invisibile (`true`/`false`) | `true` |
| `download.browser` | Browser da usare (`firefox`/`chrome`) | `firefox` |
| `download.courses` | Lista corsi da scaricare (vuota = tutti) | `[]` |
| `download.skip_existing` | Salta file già scaricati | `true` |

---

## 🔐 Nota sulla sicurezza

- Le credenziali vengono salvate **solo** in `config.yaml` (locale, non caricato su Git)
- Lo script **non invia** le tue credenziali ad alcun server terzo
- Lo script simula un normale utente che naviga nel portale

---

## ❓ Problemi comuni

### Il driver del browser non viene trovato
Lo script installa automaticamente il driver via `webdriver-manager`. Assicurati di avere Firefox (o Chrome) installato.

```bash
# Se hai problemi, installa manualmente geckodriver (Firefox):
# https://github.com/mozilla/geckodriver/releases
```

### Il login fallisce
- Verifica username e password in `config.yaml`
- Prova con `--no-headless` per vedere cosa succede nel browser
- Se hai la 2FA attiva, lo script ti chiederà il codice OTP in console

### Nessun corso trovato
Il portale didattica cambia struttura di tanto in tanto. Apri una [Issue](https://github.com/TUO_USERNAME/PoliTo-downloader/issues) con il messaggio di errore.

---

## 🤝 Contribuire

Pull request benvenute! Se il portale cambia struttura e lo script smette di funzionare, apri una Issue o una PR.

---

## 📄 Licenza

MIT — vedi [LICENSE](LICENSE)

---

> **Nota**: questo è un progetto non ufficiale, non affiliato con il Politecnico di Torino.
> Usalo responsabilmente e nel rispetto del regolamento dell'ateneo.
