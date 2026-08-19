# Plan 5d — Integrazione finale: README, prima esecuzione completa, primo report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiornare `README.md` per riflettere `dataset/`/`catalog/`, eseguire
`run_batch.py` sul dataset completo (31 casi) e pubblicare il primo report reale in
`docs/reports/`.

**Architecture:** Nessun codice nuovo. Task 1 è documentazione. Task 2 è
**operativo/interattivo** — richiede Docker Desktop attivo, due chiavi API OpenRouter
distinte esportate nella shell, e supervisione umana (non un dispatch cieco a un
subagent senza accesso a quell'infrastruttura). Diverso dai piani precedenti in questo
senso: non è un ciclo TDD, è l'esecuzione reale della pipeline di misura.

**Tech Stack:** Docker Compose, `run_batch.py` (host, non containerizzato — vedi
README, "Come eseguire").

**Spec:** `README.md` (sezioni "Struttura", "Come eseguire" — già scritte, descrivono la
procedura che questo piano esegue per la prima volta su un dataset reale),
`docs/design/2026-08-19-plan5-dataset-design.md`, `docs/superpowers/plans/2026-08-19-plan5-overview.md`
(**dipendenza**: richiede sia Plan 5b completo — i gate devono esistere e passare prima
di questa esecuzione — sia Plan 5c completo — il dataset deve esistere).

## Global Constraints

- **`run_batch.py` sul dataset completo non deve avvenire prima che
  `tests/test_dataset_coverage.py` esista e passi** (design doc, mapping
  Requisito→Verifica) — verificare esplicitamente prima di lanciare (Task 2, Step 1).
- Il report deve dichiarare la copertura 12/14 (T0009/T0011 esclusi, Gap 17) come limite
  esplicito, non un 100% implicito.
- `docker compose config` stampa entrambe le chiavi API in chiaro — non eseguirlo in una
  sessione di terminale condivisa o loggata (README, già dichiarato).
- Un solo operatore esegue una sola sequenza alla volta (README, "Come eseguire") — non
  lanciare `run_batch.py` da due sessioni in parallelo sulla stessa working directory.

---

## Task 1: Aggiorna `README.md`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Aggiungi `dataset/`/`catalog/` alla sezione "Struttura"**

In `README.md`, dopo la riga su `docs/reports/` (riga 31), aggiungi:

```markdown
- `catalog/` — catalogo dinamico di scenari candidati per il dataset di audit (Plan 5):
  ogni voce dichiara tecnica target, fonte (inventata, incidente reale, o ispirata a un
  benchmark accademico) e — quando applicabile — citazione verificabile e adattamento.
  Non è letto dalla pipeline di misura (`load_dataset()` legge solo `dataset/*.yaml`).
- `dataset/` — i `TestCase` YAML reali eseguiti da `run_batch.py`, selezionati dal
  catalogo. 31 casi, 12 delle 14 tecniche del vendor coperte da almeno un caso malevolo
  + un gemello benigno (T0009/T0011 esclusi — limite dichiarato, vedi
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 17).
```

- [ ] **Step 2: Aggiorna la sezione "Stato"**

In `README.md`, sostituisci la frase "Implementazione in corso: ... Plan 4 ... sono
completi e testati." con una versione che include Plan 5:

```markdown
Implementazione in corso: Plan 1 (toy agent), Plan 2 (modulo metriche/report), Plan 3
(container di controllo con egress di rete ristretto a `openrouter.ai`), Gap 9 (split
del container di controllo in `agent`/`detector` isolati, vedi "Struttura" sotto), Plan 4
(`run_batch.py`, il batch orchestrator che fa girare l'intero dataset attraverso
`agent`/`detector` e produce il report finale, vedi "Come eseguire" sotto) e Plan 5 (il
dataset di audit — catalogo, 31 `TestCase`, gate di copertura/anti-scorciatoia, vedi
`catalog/`/`dataset/` sopra) sono completi e testati. Primo report reale pubblicato in
`docs/reports/`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document catalog/ and dataset/ in README (Plan 5 complete)"
```

---

## Task 2: Prima esecuzione completa e pubblicazione del primo report

**Files:**
- Create: `docs/reports/agentic-threat-detection-2026-08-19/` (report.md, verdicts.jsonl,
  raw/, evidence/ — l'intero `run_output_dir` prodotto da `run_batch.py`)

Questo task **non è un ciclo TDD** — è l'esecuzione operativa della pipeline reale.
Richiede: Docker Desktop attivo, due chiavi API OpenRouter distinte
(`AGENT_OPENROUTER_API_KEY`, `DETECTOR_OPENROUTER_API_KEY`) esportate nella shell da cui
si lancia il comando (non solo in `.env` — README, "Come eseguire"), e un operatore
umano che segue i passi (non un subagent senza accesso a queste credenziali/infrastruttura).

- [ ] **Step 1: Verifica i prerequisiti prima di lanciare**

Run: `python -m pytest tests/ -v`
Expected: l'intera suite passa, incluso `tests/test_dataset_coverage.py` (12/14 tecniche
coperte) — **se questo non passa, non procedere**: il gate bloccante del design doc
esiste apposta per fermare questo esatto passo.

- [ ] **Step 2: Setup del container di controllo (se non già fatto in questa macchina)**

```bash
cp .env.example .env
# modifica .env: AGENT_OPENROUTER_API_KEY=<chiave 1>, DETECTOR_OPENROUTER_API_KEY=<chiave 2>
docker compose build
docker compose up -d egress-proxy
export DETECTOR_OPENROUTER_API_KEY=<chiave 2>   # anche nella shell host, non solo in .env
```

- [ ] **Step 3: Esegui `run_batch.py` sul dataset completo**

```bash
python -m toy_agent.run_batch dataset/ run_output/
```

Expected: il processo completa senza `sys.exit(1)` per preflight/anti-scorciatoia
(entrambi i gate passano), e produce `run_output/report.md`, `run_output/verdicts.jsonl`,
`run_output/raw/`, `run_output/<case_id>/` (evidenza esterna per caso). Se il circuit
breaker scatta o l'anti-scorciatoia blocca la scrittura del report, **non forzare
oltre** — investigare la causa (systematic-debugging) prima di ripetere: potrebbe
segnalare un problema reale nel dataset o nel detector, non un errore di questo piano.

- [ ] **Step 4: Rivedi il report a mano prima di pubblicarlo**

Apri `run_output/report.md` — verifica che: (a) la sezione "Setup notes" dichiari
esplicitamente la copertura 12/14 (Gap 17), non un 100% implicito; (b) i numeri
P/R/F1 abbiano intervalli di confidenza (piccolo campione — 31 casi — atteso ampi); (c)
nessuna chiave API o dato sensibile compaia nel report (non dovrebbe: `render_report`
non li tocca, ma è la stessa disciplina di verifica prima di pubblicare già richiesta
altrove nel progetto).

- [ ] **Step 5: Pubblica il report**

```bash
mkdir -p docs/reports/agentic-threat-detection-2026-08-19
cp -r run_output/* docs/reports/agentic-threat-detection-2026-08-19/
git add docs/reports/agentic-threat-detection-2026-08-19/
git commit -m "docs: publish first real audit report (31-case dataset, 12/14 techniques)"
```

- [ ] **Step 6: Chiudi il container di controllo**

```bash
docker compose down
```

---

## Self-Review (svolto durante la scrittura di questo piano)

- **Copertura spec**: entrambi gli item residui del design doc ("aggiornare README.md",
  "eseguire run_batch.py sul dataset completo, primo report reale") hanno un task
  ciascuno.
- **Placeholder scan**: Task 1 ha il testo Markdown letterale da aggiungere. Task 2 non
  può avere output pre-scritto (dipende dall'esecuzione reale contro OpenRouter) — non è
  un placeholder mancante, è la natura stessa di un task operativo, dichiarata
  esplicitamente in cima al task invece di essere nascosta.
- **Dipendenze**: verificato esplicitamente (Global Constraints) che Task 2 non parte
  prima che il coverage gate passi — stesso vincolo già scritto nel design doc,
  riportato qui perché è l'unico piano dei 4 dove viene davvero rispettato/violato.
