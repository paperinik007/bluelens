# Run osservabile e identificabile — directory-per-run + log di progresso

Data: 2026-08-26. Stato: design proposto, da validare (council leggero / review utente) prima
dell'implementazione. Tier: **Light** (feature media, tocca l'entrypoint `run_batch.main()`
e il loop `execute_sequence`, ma nessun contratto tra moduli cambia).

---

## 1. Perché

Due esigenze emerse da un run reale (2026-08-25, troncato a 13/31 per esaurimento credito):

**A. Il run è muto mentre gira.** `run_batch` non stampa nulla per caso: per ~20-30 minuti
l'operatore non sa se il batch è vivo, bloccato, o se sta bruciando credito su casi inutili.
Gli errori (infra, model_error, transcript_unusable) si scoprono solo a fine run, o mai.

**B. I run non hanno identità.** `run_output/` è una directory piatta dove ogni run mescola
i propri file con quelli del precedente. L'abbiamo pagato concretamente: dopo il run
troncato, `raw/` conteneva 18 transcript del 21 agosto mescolati ai 13 nuovi (gap già
registrato in `registro-limiti-aperti.md`). L'associazione "questo artefatto appartiene a
questo run" è ricostruibile a mano (timestamp, provenance) ma non è strutturale.

**Il fix unico**: dare a ogni run una directory con nome identificativo (`run_id`) e farlo
parlare mentre gira. Le due esigenze sono facce della stessa necessità — il run deve essere
osservabile *mentre* accade e identificabile *dopo*.

---

## 2. Decisioni di design

### 2.1 `run_id` — formato ordinabile + suffisso univoco

```
YYYYMMDD-HHMMSS-<token6>
```

- **`YYYYMMDD-HHMMSS`** in **UTC** (non ora locale): due run su macchine diverse restano
  ordinabili e confrontabili per nome, e l'ordinamento lessicografico coincide con quello
  cronologico.
- **`<token6>`** = `secrets.token_hex(3)` (6 caratteri hex): disambigua due run nello stesso
  secondo, senza alcuna dipendenza da stato condiviso. Non è il commit (che sta già in
  provenance): il commit non distingue due run identici.

Esempio: `20260826-143012-a1b2c3`.

**Vincolo di determinismo** (importante): il `run_id` è un **input** del report, non una
data generata dentro `render_report`. Il report resta deterministico (nessun timestamp nel
suo contenuto) — il `run_id` viene letto da `provenance.json`, mai da `datetime.now()`
chiamata dentro il rendering. Rigenerare il report da una directory produce lo stesso file.

### 2.2 directory-per-run

```
run_output/
├── 20260826-143012-a1b2c3/     ← il run
│   ├── provenance.json          (con campo run_id)
│   ├── run.log                  (narrativa + per-caso)
│   ├── verdicts.jsonl
│   ├── report.md
│   ├── raw/<case_id>.transcript.json
│   └── <case_id>/  (evidence, vendor_proxy, logs, diff, stats)
├── latest -> 20260826-143012-a1b2c3/   (symlink, o file LATEST su Windows)
└── legacy-20260825-troncato/    (archivio una tantum del run precedente, vedi §5)
```

Ogni run nasce in una directory **vuota**: il gap "raw/ non pulito" sparisce per costruzione
(nessun file da pulire), e `run.log` è per definizione di un solo run (overwrite, niente
append, niente separatori — il dibattito append/tronca era un artefatto della directory
piatta).

### 2.3 `latest` — puntatore al run più recente

- Prova `os.symlink(run_dir, run_output_dir / "latest")`.
- Se fallisce (Windows: permessi/developer mode) → scrive il file testuale
  `run_output/LATEST` contenente il `run_id` (una riga).
- Entrambi sono **comodità per l'umano**. `inspect_run` e `regenerate_report` prendono già
  un path esplicito e restano invariati: l'utente punta a `run_output/<run_id>/` o
  (su Unix) a `run_output/latest/`.

### 2.4 log di progresso — narrativa a fasi + per-caso

Tutto su **stderr** con `flush=True` **e** su `run.log` (stesso contenuto, due canali).
Mai su stdout: stdout resta pulito (il report va su file, non su stdout).

**Il run.log è anche l'evidenza forense**: se il run muore a metà, il log mostra fino a dove
era arrivato — cosa che oggi non lascia alcuna traccia (lo si scopre solo contando i
transcript).

Formato (inglese, coerente col resto dello strumento):

```
=== agentic-security-audits — run ===
run_id: 20260826-143012-a1b2c3
dataset: dataset/ (31 cases)
output:  run_output/20260826-143012-a1b2c3/
measurer: c1bd371 (clean)   vendor: 7fad14d
agent: openai/gpt-4o-mini
detector: qwen3-8b / qwen3-30b-a3b / qwen3-embedding-4b
lifecycle: reused

--- preflight ---
checking 4 models...  OK

--- containers ---
opening: agent, detector, egress-proxy
running 31 cases...

  [ 1/31] account_deactivation_explicitly_requested       benign    28.5s  in=14542
  [ 2/31] account_disabled_after_misread_opt_out          benign     7.3s  in=550
  [ 3/31] hidden_instruction_triggers_unauthorized_export *** MODEL_ERROR (transcript unusable) ***

--- closing ---
closing: agent, detector, egress-proxy

=== summary ===
31 cases: 28 judged, 3 excluded (model_error=2, transcript_missing=1)
circuit breaker: not tripped
report.md written to run_output/20260826-143012-a1b2c3/
```

### 2.5 riga per-caso

**Caso normale** — mostra esito, latenza, e `in_tokens` (il segnale di spike: un caso a
14.5K token si vede *mentre* succede, non dopo):

```
  [n/total] {case_id:<45} {status} {label:<8} {latency:>6.1f}s  in={in_tokens}
```

**Caso con errore** — marker `*** CAUSA ***`, niente latenza/verdetto (non pertinenti):

```
  [n/total] {case_id:<45} *** {causa} ***
```

Cause possibili (già tutte nel codice):
- `INFRA` (error_kind dal verdict)
- `MODEL_ERROR (transcript unusable)` — `stop_reason == "model_error"`
- `MAX_COST (transcript unusable)`
- `TRANSCRIPT_MISSING`
- `ARGUMENTS_PARSE_FAILED`
- `VERDICT_CONVERSION_FAILED`

**Nessuna soglia magica su `in_tokens`**: mostriamo sempre il valore; lo spike lo riconosce
l'occhio umano. Evita un altro numero da dichiarare in `_setup_notes()`.

### 2.6 iniettabilità per i test

`execute_sequence` guadagna un parametro `progress_fn: Callable[[str], None] = None`
(default: nessun output, i test non inquinano stderr). `run_batch.main()` costruisce una
closure che scrive su stderr **e** appende a `run.log`, e la passa sia a `execute_sequence`
sia alle fasi di banner/preflight/summary.

---

## 3. Ordine delle operazioni in `main()`

```
1. load_dataset, leggi chiavi
2. genera run_id, crea run_output/<run_id>/, imposta latest (symlink/LATEST), apri run.log
3. prov = provenance.collect_provenance(env)  → aggiungi campo run_id
4. banner (usa prov + parsed args)
5. write_provenance(prov, run_dir)
6. preflight → logga ogni esito; se fallisce: logga + sys.exit(1)
7. result = execute_batch(..., progress_fn=closure)
8. summary (giudicati/esclusi/breaker)
9. gate transcript_unusable → messaggio (stderr, già esistente)
10. gate anti-shortcut → messaggio (stderr, già esistente)
11. compute_metrics + render_report + scrivi report.md dentro run_dir
```

Nota sull'ordine: la directory e `run.log` nascono **prima** del preflight, così anche un
preflight fallito lascia traccia (un `run.log` che spiega perché non è partito nulla) — più
osservabilità, che è lo scopo del task.

---

## 4. Mapping Requisito → Verifica

| # | Requisito | Verifica eseguibile |
|---|---|---|
| R1 | `run_id` ordinabile: `YYYYMMDD-HHMMSS` + token, UTC | Test: il nome generato matcha `\d{8}-\d{6}-[0-9a-f]{6}` e due chiamate consecutive differiscono |
| R2 | `run_id` dentro `provenance.json` | Test: `collect_provenance` include il campo `run_id` |
| R3 | Ogni run crea la propria directory vuota | Test: `main()` con `run_output_dir` pulito → i file stanno in `run_output/<run_id>/`, non flat |
| R4 | `latest` punta al run più recente | Test: dopo `main()`, `latest` (symlink o `LATEST`) → il run_id appena creato |
| R5 | `run.log` esiste nel run dir, uno per run | Test: `run.log` presente; due run → due file separati, ognuno col proprio contenuto |
| R6 | `run.log` contiene banner, preflight, per-caso, summary | Test: stringhe sentinella presenti (`=== ... run ===`, `--- preflight ---`, `[ 1/`, `=== summary ===`) |
| R7 | Riga per-caso con esito, latenza, in_tokens | Test: riga di un caso benigno contiene `benign`, latenza formattata, `in=` |
| R8 | Errori marcati `*** CAUSA ***` | Test: caso con `stop_reason=model_error` → riga contiene `*** MODEL_ERROR` |
| R9 | Log su stderr E su run.log, mai su stdout | Test: `progress_fn` scrive su entrambi i canali; stdout resta vuoto |
| R10 | Nessun messaggio raw di eccezione nel log | Test: eccezione sentinella → il log contiene solo `__class__.__name__`, mai il messaggio |
| R11 | Report deterministico (run_id letto, non generato) | Test: `render_report` con lo stesso provenance produce file identico in due run |
| R12 | I messaggi gate esistenti restano su stderr | Test: gate fallito → messaggio su stderr, exit code 1 (comportamento invariato) |
| R13 | `progress_fn` iniettabile, default silenzioso | Test: `execute_sequence` senza `progress_fn` non scrive nulla su stderr |
| R14 | `inspect_run` e `regenerate_report` restano invariati | Test: suite esistente verde senza modifiche a quei due moduli |

---

## 5. Archivio del run legacy (una tantum, manuale)

I file flat del run troncato 2026-08-25 vanno spostati in
`run_output/legacy-20260825-troncato/` (non cancellati — sono evidenza):
`raw/`, `verdicts.jsonl`, `report.md`, `provenance.json`, e le 13 directory `<case_id>/`.

Operazione manuale documentata qui, non codice: va fatta una volta, prima del primo run
post-refactor. I 13 casi sono l'evidenza su cui poggia
`docs/research/2026-08-25-detector-loop-e-attribuzione-tecnica.md`.

---

## 6. Cosa non facciamo (YAGNI)

- **Nessuna soglia automatica su `in_tokens`** — mostra il valore, l'anomalia la giudica
  l'umano.
- **Nessun costo per-caso nel log** — il campo `cost_usd` è `None` (limite 7 già registrato);
  non lo risolviamo qui.
- **Nessun cambiamento a `inspect_run`/`regenerate_report`** oltre all'`--help` — sono già
  path-agnostici e prendono path espliciti.
- **Nessuna risoluzione automatica di `latest` dentro i tool** — è una comodità per l'umano,
  non un contratto.
- **Nessun timestamp dentro il report** — il determinismo del report non si tocca.
- **Nessuna pulizia automatica dei run vecchi** — l'accumulo è un problema di retention,
  non di questo task.

---

## 7. File toccati

| File | Cambio |
|---|---|
| `src/toy_agent/run_batch.py` | genera run_id + crea subdir + latest + run.log + banner/summary; passa `progress_fn` a `execute_sequence` |
| `src/toy_agent/sequence.py` | parametro `progress_fn`; logga per-caso e apertura/chiusura container |
| `src/toy_agent/provenance.py` | campo `run_id` in `collect_provenance` |
| `tests/toy_agent/test_run_batch.py` | aggiorna i ~8 test che assumono directory piatta; nuovi test per run_id/latest/run.log |
| `tests/toy_agent/test_sequence.py` | nuovi test per `progress_fn` e righe per-caso |
| `tests/toy_agent/test_provenance.py` | test campo `run_id` |
| `README.md` | documenta directory-per-run e `latest` |

---

## 8. Questioni aperte

1. **Nome del suffisso**: `secrets.token_hex(3)` (6 hex) — sufficiente, ma si può valutare
   8 hex se si teme collisione (irrisorio a questi volumi).
2. **`LATEST` file su Windows**: solo se il symlink fallisce. Nessun tool lo risolve
   automaticamente — è per l'umano. Se un giorno serve, si aggiunge risoluzione.
3. **Retention dei run vecchi**: non affrontata (YAGNI). Quando `run_output/` cresce,
   servirà una policy (es. tenere N run) — decisione separata.
