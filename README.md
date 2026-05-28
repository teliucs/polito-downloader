# 🎓 PoliTo Material Downloader

> Scarica automaticamente tutti i materiali dei tuoi corsi dal Portale della Didattica del Politecnico di Torino direttamente sul tuo PC, mantenendo le cartelle organizzate.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-orange?logo=selenium)](https://selenium.dev/)

---

## ✨ Funzionalità

- 🔐 **Login automatico** via SSO del Politecnico (gestisce automaticamente MFA/Skip Setup)
- 📚 **Tutti i corsi o download selettivo** — scegli tu quali corsi scaricare tramite un comodo menu nel terminale
- 📁 **Organizzazione intelligente** — ricrea fedelmente la struttura a cartelle del portale (lezioni, esercizi, slide) sul tuo PC
- ⏭️ **Skip intelligente (Zero sprechi)** — rileva e salta i file che hai già scaricato, scaricando solo i nuovi materiali o aggiornamenti
- ⚡ **Velocità super** — scarica interi corsi in un singolo pacchetto ZIP protetto ed estrae tutto all'istante
- 🖥️ **Lavoro silenzioso (Headless)** — funziona in background senza aprire finestre (puoi attivare la finestra per debug con `--no-headless`)

---

## 📋 Requisiti per iniziare

Per far funzionare lo script hai bisogno di:
1. **Python** (il linguaggio di programmazione con cui è scritto lo script)
2. **Un browser web** tra **Firefox** e **Google Chrome** installati sul tuo PC.
   - *Nota:* Lo script è configurato per usare **Firefox** come default, ma ha un **sistema di fallback automatico**: se non trova Firefox sul tuo PC, proverà ad avviare **Google Chrome** in automatico (e viceversa), in modo che tutto funzioni al primo colpo senza configurazioni manuali!

---

## 🚀 Guida all'Installazione per principianti

Se non hai mai usato il terminale o non sai nulla di informatica, segui questi semplici passaggi passo-passo:

### 1. Installa Python sul tuo PC
* **Su Windows:** Apri il **Microsoft Store**, cerca **"Python"** e installa l'ultima versione disponibile (es. Python 3.11 o 3.12). È un'installazione con un solo click ed è completamente sicura.
* **Su macOS:** Python è spesso già presente. Se necessario, scaricalo e installalo dal [sito ufficiale Python](https://www.python.org/downloads/mac-osx/).

### 2. Scarica questo progetto sul tuo PC
Fai click sul pulsante verde in alto a destra **"Code"** su GitHub e seleziona **"Download ZIP"**. Estrai la cartella ZIP dove preferisci (es. sul Desktop o nei Documenti).

### 3. Apri il terminale nella cartella del progetto
* **Su Windows:** Apri la cartella che hai estratto, fai click sulla barra degli indirizzi in alto (dove c'è scritto il percorso della cartella), digita **`cmd`** e premi **INVIO**. Si aprirà il terminale di Windows posizionato nella cartella corretta.
* **Su macOS/Linux:** Apri l'app **Terminale**, scrivi `cd ` (con uno spazio dopo) e trascina la cartella del progetto all'interno della finestra del terminale, quindi premi **INVIO**.

### 4. Installa le dipendenze dello script
Nel terminale che hai appena aperto, incolla questo comando e premi **INVIO**:

```bash
pip install -r requirements.txt
```

---

## 🔐 Configurazione (Come inserire le tue credenziali in sicurezza)

Per evitare di scrivere la tua matricola e password ogni volta che avvii lo script, puoi salvarle in sicurezza sul tuo PC in un file di configurazione locale:

1. Trova il file **`config.yaml.example`** all'interno della cartella.
2. Rinominalo in **`config.yaml`** (rimuovendo `.example` alla fine).
3. Apri il file con un qualsiasi editor di testo (es. Blocco Note o TextEdit) e inserisci i tuoi dati:

```yaml
credentials:
  username: "s123456"             # Sostituisci s123456 con la tua matricola
  password: "LaTuaPasswordQui"    # Inserisci la tua password del portale
```

> [!IMPORTANT]
> **La sicurezza prima di tutto!** 
> Il file `config.yaml` è stato inserito all'interno del file di controllo `.gitignore`. Questo significa che **le tue credenziali rimarranno sul tuo PC** e non verranno **MAI** caricate su GitHub o condivise online. Lo script effettua la connessione direttamente ed esclusivamente con i server ufficiali del Politecnico di Torino (`didattica.polito.it` e `idp.polito.it`).

*Se preferisci non salvare la password su disco, lascia i campi vuoti: lo script ti chiederà la matricola e la password in chiaro nel terminale ogni volta che lo avvierai.*

---

## ▶️ Come utilizzare lo script

Apri il terminale nella cartella del progetto e scrivi:

```bash
python polito_downloader.py
```

### Cosa succederà ora?
1. Lo script caricherà le tue credenziali e si collegherà in background.
2. Ti mostrerà la lista di tutti i corsi a cui sei iscritto quest'anno.
3. Ti chiederà di inserire i numeri dei corsi che desideri scaricare:
   ```text
   ➜ Inserisci i numeri dei corsi da scaricare separati da virgola (es. 1,3 o 0 per tutti): 3
   ```
4. Lo script scaricherà tutti i materiali organizzandoli automaticamente per te!

---

## 💡 Comandi utili e avanzati

Se vuoi personalizzare l'esecuzione, puoi aggiungere delle opzioni al comando di avvio:

### Mostra solo la lista dei corsi (senza scaricare nulla)
```bash
python polito_downloader.py --list-courses
```

### Scarica solo un corso specifico (senza mostrare il menu di selezione)
```bash
python polito_downloader.py --course "Nome Corso"
```

### Rendi visibile il browser (utile per debug o se riscontri problemi)
```bash
python polito_downloader.py --no-headless
```

### Usa Google Chrome invece di Firefox
```bash
python polito_downloader.py --browser chrome
```

---

## 📁 Struttura dei materiali salvati

I materiali verranno salvati in una cartella chiamata **`downloads/`** creata all'interno del progetto, organizzata in questo modo:

```
downloads/
├── Nome Insegnamento 1/
│   ├── Programma del Corso.docx
│   ├── Slide Lezioni/
│   │   ├── Lezione 1 - Introduzione.pdf
│   │   └── Lezione 2.pdf
│   └── Esercitazioni/
│       ├── Esercizio 1.pdf
│       └── Soluzione Esercizio 1.pdf
└── ...
```

---

## ❓ Risoluzione dei problemi comuni

### 1. Ricevo un errore che dice "Python non trovato"
Assicurati di aver installato Python dal Microsoft Store (Windows) e di aver riavviato il terminale prima di eseguire lo script.

### 2. Ricevo un errore all'avvio del browser (es. Firefox/Chrome non trovato)
Lo script scarica e configura automaticamente i driver di connessione (Geckodriver / Chromedriver). Assicurati solo di avere almeno **Firefox** o **Google Chrome** installati sul computer.

Se desideri forzare l'uso di un browser specifico (ad esempio se li hai entrambi ma preferisci usarne uno specifico), puoi farlo avviando lo script con l'opzione apposita:
- Per usare Chrome: `python polito_downloader.py --browser chrome`
- Per usare Firefox: `python polito_downloader.py --browser firefox`

---

## 📄 Licenza & Note legali

Questo progetto è rilasciato sotto licenza MIT. 

> [!NOTE]
> Questo è un progetto **non ufficiale** sviluppato in modo indipendente e non è affiliato o sponsorizzato dal Politecnico di Torino. Usalo responsabilmente e nel rispetto del regolamento d'ateneo.
