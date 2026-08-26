# Piano — directory-per-run + log di progresso (tier Light)

> Spec: `docs/design/2026-08-26-run-observability-directory-per-run-design.md`
> (council + grill completati). Tier Light: piano leggero, task indipendenti,
> council/grill già fatti sulla spec — qui si implementa, non si riapre.

**Goal**: dare a ogni run una directory con nome identificativo e farlo parlare
mentre gira (stderr + `run.log`), con heartbeat per caso ed errori in evidenza.

---

## Ordine di esecuzione (dipendenze)

1. **T1** — `run_id` + directory-per-run + `latest` (R1-R4)
2. **T2** — log di progresso: banner + heartbeat + summary + `run.log` (R5-R9, R15)
3. **T3** — `run_id` in provenance (R2)
4. **T4** — fail-loudly in `inspect_run`/`regenerate_report` (R16)
5. **T5** — pubblicazione `run.log` col report (R17)
6. **T6** — archivio legacy + ri-puntamento citazioni (§5, manuale)
7. **T7** — README + doc

---

## Task

### T1 — `run_id` + directory-per-run + `latest`

- **File**: `src/toy_agent/run_batch.py`
- **Test**: `tests/toy_agent/test_run_batch.py`
- **Cosa**: genera `run_id` (`YYYYMMDD-HHMMSS-<token6>` UTC); crea
  `run_output/<run_id>/`; passa quella directory a `execute_batch`/`provenance`/report;
  imposta `latest` symlink **dopo** `execute_batch` (salta se symlink fallisce).
- **Requisiti**: R1, R3, R4.

### T2 — log di progresso

- **File**: `src/toy_agent/run_batch.py`, `src/toy_agent/sequence.py`
- **Test**: `tests/toy_agent/test_run_batch.py`, `tests/toy_agent/test_sequence.py`
- **Cosa**: `progress_fn` iniettabile in `execute_sequence` (default silenzioso);
  heartbeat `starting`/`done` per caso; marker `*** CAUSA ***` per errori; banner
  iniziale; summary finale con `cumulative in_tokens`; `run.log` nel run dir + stderr.
- **Requisiti**: R5, R6, R7, R8, R9, R13, R15.

### T3 — `run_id` in provenance

- **File**: `src/toy_agent/provenance.py`, `src/toy_agent/run_batch.py`
- **Test**: `tests/toy_agent/test_provenance.py`, `tests/toy_agent/test_run_batch.py`
- **Cosa**: campo `run_id` in `collect_provenance`. NIENTE cambio a
  `format_provenance` (run_id non entra nel report, R11).
- **+ Reorder dal review di T1**: spostare `collect_provenance` + `write_provenance`
  **prima** del preflight (design §3, step 3/5 prima di step 6). Oggi sono dopo il
  preflight → un run con preflight fallito lascia una directory vuota senza
  `provenance.json`, contro §2.3. Trovato dal reviewer di T1 (Approved, finding
  Important): è un plan gap, qui assegnato a T3.
- **Requisiti**: R2, R11.

### T4 — fail-loudly nei tool

- **File**: `src/toy_agent/inspect_run.py`, `src/toy_agent/regenerate_report.py`
- **Test**: `tests/toy_agent/test_inspect_run.py`, `tests/toy_agent/test_regenerate_report.py`
- **Cosa**: se la directory data non contiene `raw/` e `verdicts.jsonl`, errore
  esplicito con messaggio ("punta a `run_output/<run_id>/`, non al root") invece di
  zero transcript/verdetti in silenzio.
- **Requisiti**: R16.

### T5 — pubblicazione `run.log`

- **File**: `src/toy_agent/run_batch.py` (o dove avviene la pubblicazione)
- **Test**: `tests/toy_agent/test_run_batch.py`
- **Cosa**: quando il run si pubblica in `docs/reports/`, copiare `run.log` accanto a
  `report.md`.
- **Requisiti**: R17.

### T6 — archivio legacy (manuale)

- **File**: nessuno in `src/`; operazione su disco + `docs/research/...`
- **Cosa**: sposta i file flat del run troncato in `run_output/legacy-20260825-troncato/`;
  ri-punta le citazioni in `docs/research/2026-08-25-detector-loop-e-attribuzione-tecnica.md`.
- **Requisiti**: §5 del design.

### T7 — README + doc

- **File**: `README.md`
- **Cosa**: documenta directory-per-run, `latest`, `run.log`, e come puntare
  `inspect_run`/`regenerate_report` alla directory giusta.

---

## Vincoli globali (dal progetto, non dal design)

- **Python >= 3.11**, **pytest >= 8.0.0**, nessuna nuova dipendenza.
- **Nessun messaggio raw di eccezione** raggiunge output — solo `__class__.__name__`.
- **Suite verde prima di ogni commit** (`python -m pytest tests/ -q`).
- **Un commit per task**, conventional commit, `git add` solo i file del task.
- **Determinismo del report**: `run_id` non entra nel report (R11).
- **`latest` non punta a run non partiti** (solo dopo `execute_batch`).

---

## Note di esecuzione

- T1, T2, T3, T4 sono indipendenti tra loro (tutti dipendono solo dalla spec), ma T2
  tocca `sequence.py` e T1 tocca `run_batch.py` — nessuna sovrapposizione di regioni,
  ordine comunque suggerito T1→T2 per testare il log già dentro la subdir.
- T6 è manuale, non passa dall'implementer.
- Ogni task: `implementer` + `reviewer` per-task (tier Light: review solo sui task di
  giudizio — T1, T2, T4; T3/T5/T7 meccanici).
