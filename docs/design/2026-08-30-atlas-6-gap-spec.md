# Spec: Popolamento 6 gap ATLAS mappabili (post cross-check)

**Data**: 2026-08-30
**Stato**: BOZZA — precede il piano canonico in `docs/superpowers/plans/`
**Genitore (specifica di metodo)**: `docs/design/2026-08-30-atlas-audit-method-design-v4.md`
**Documento di ricerca che individua i gap**: `docs/research/2026-08-30-atlas-taxonomy-crosscheck.md`
**Documento di scoping**: `docs/notes/2026-08-30-atlas-6-gap-population-plan.md` (decisioni
pendenti, integrazioni Pi-specifiche, stop conditions, punto aperto judge-targeted)
**Grill di 4 council**: `temp/pi-council-grill-atlas-6gap-spec.md` + risposta Claude
2026-08-30 (correzione (b) con patch metrics.py)

## Goal (one sentence)

Creare la prima istanza reale di `catalog/vendor_scope_verification.yaml`, aggiungere a
`catalog/cases.yaml` 8-12 nuove entry con `technique_code: null` (linkate a 6 nuovi
TestCase mirror in `dataset/*.yaml` con `technique_target` sintetico per cluster
ATLAS), ed eseguire il flusso completo contro `aidr-ai/agentic-threat-detection` per
popolare il Passo 5 — con patch esplicita al test bridge e a `metrics.py` per gestire
la nuova asimmetria senza degradare la qualità delle metriche strict.

## Correzioni strutturali rispetto alla versione precedente (post-grill)

Questa versione corregge3 problemi strutturali trovati dal grill dei 4 council (advocate,
pragmatist, risk, skeptic) e dalla review di Claude Code:

1. **Naming ATLAS obbligatorio**: tutti i riferimenti ATLAS nella spec usano il prefisso
   `AML.` (es. `AML.T0077`), per evitare collisioni con T-code aidr **realmente
   esistenti**. Verificato su `catalog/vendor_taxonomy_snapshot.yaml`: aidr ha T0006 =
   "Unauthorized Resource Access" e T0012 = "Data Exfiltration" — collidenti con
   `AML.T0006` (Active Scanning) e `AML.T0012` (Valid Accounts) di ATLAS, che sono
   proprio i gap #2 e #3 di questo batch. La collisione non è ipotetica (avevo
   inizialmente citato `T0103` di aidr, che NON esiste — errore di chi ha
   originariamente passato il finding, corretto qui). Skeptic finding #3
   (validato, motivazione corretta).

2. **Opzione (b) con patch metrics.py** (scelta di Claude Code 2026-08-30, confermata
   da risk finding #1 + skeptic finding #1): le 8-12 nuove entry avranno
   `technique_code: null` in `catalog/cases.yaml` MA un `technique_target` sintetico
   per cluster (es. `T-ATLAS-atlas-t0077-rendering`, vedi schema ID in Scope IN
   voce 4) nel TestCase mirror in `dataset/*.yaml`. La asimmetria richiede:
   - Modifica esplicita al test bridge `test_selected_catalog_entries_match_their_
     dataset_test_case` (`tests/test_catalog.py:144-167`) per accettare il pattern
     `entry.technique_code == None` + `case.technique_target == f"T-ATLAS-{entry.variant_cluster_id}"`.
     **Confronto diretto**, niente manipolazione di stringhe (no removeprefix, no
     estrazione di suffissi). Funziona identico per gap singoli (1 `variant_cluster_id`)
     e per coppie (2 `atlas_codes` sotto lo stesso `variant_cluster_id`).
   - Aggiunta campo `strict_significant: bool` (default `True`) a `TestCase`
     (`src/toy_agent/schema.py:118-122`). I casi con target sintetico lo settano a
     `False`. Questo è il minimo necessario — `metrics.py:285-298` già ha il pattern
     "excluded" che va riusato, non va aggiunto un nuovo ramo di logica.

3. **Regola "2 varianti"**: esplicitamente distinta dal criterio v4 parola/tool/canale.
   È una scelta di **stabilità** (1 sola variante = 0 informazione sulla varianza del
   verdetto), non l'applicazione del criterio v4 (che per alcuni dei 6 gap darebbe 1 o
   3 varianti). Skeptic finding #2.

## Scope

### IN scope

1. **Estensione additiva di `catalog/cases.yaml`** con 3 nuovi campi opzionali definiti nel
   design v4 (sezione "Dove vive il tracking"):
   - `variant_cluster_id: <string|null>`
   - `variant_round_count: <2|3|null>`
   - `per_vendor_concordance: {<vendor>: agreed|disagreed|inconclusive}|null`

   +1 campo opzionale descrittivo per i casi di questo batch:
   - `atlas_codes: [AML.T####, ...] | null` — codici ATLAS top-level mappati a questa
     entry (lista, perché AML.T0006 + AML.T0084 e AML.T0103 + AML.T0108 sono coppie). Permette a
     un futuro lettore di risalire meccanicamente da "ATLAS gap X nel research doc"
     a "case Y in cases.yaml" (advocate finding #2).

2. **8-12 nuove entry in `catalog/cases.yaml`** (1-2 per ciascuno dei 6 gap identificati),
   tutte con `technique_code: null` + `atlas_codes: [AML.T####, ...]` valorizzato.
   Regola di clustering: AML.T0006 + AML.T0084 e AML.T0103 + AML.T0108 come coppie con
   stesso `variant_cluster_id`. Nomi cluster (usati nell'ID sintetico
   `T-ATLAS-{variant_cluster_id}`):
   - `atlas-t0077-rendering` (singolo: AML.T0077)
   - `atlas-t0006-t0084-recon` (coppia: AML.T0006 + AML.T0084)
   - `atlas-t0012-valid-accounts` (singolo: AML.T0012)
   - `atlas-t0103-t0108-propagation` (coppia: AML.T0103 + AML.T0108)

3. **8-12 nuovi TestCase mirror in `dataset/*.yaml`** (uno per ogni entry nuova del
   catalog), ciascuno con:
   - `technique_target: f"T-ATLAS-{variant_cluster_id}"` (sintetico, es. `T-ATLAS-atlas-t0077-rendering`).
     **Significato overloaded**: per casi normali (aidr T-code) `technique_target` resta
     `T0001`-`T0014`; per casi synthetic (questo batch) diventa ID di cluster ATLAS.
     `metrics.py` tratta `technique_target` come stringa opaca (nessun pattern match
     interno) — il check `v.technique_detected == case.technique_target` (riga 293-297)
     darà sempre FN per i casi synthetic, esattamente come già documentato per
     `strict_significant: False`.
   - `strict_significant: False` (vedi sopra — esclude dal breakdown strict per-tecnica)
   - Tutti gli altri campi `TestCase` come da casi esistenti in `dataset/*.yaml`

4. **Modifica esplicita al test bridge** `test_selected_catalog_entries_match_their_
   dataset_test_case` (`tests/test_catalog.py:144-167`): aggiungere il ramo che
   accetta `entry.technique_code is None` quando `case.technique_target.startswith(
   "T-ATLAS-")` E `entry.variant_cluster_id is not None`. **Confronto diretto**:
   `case.technique_target == f"T-ATLAS-{entry.variant_cluster_id}"`. Niente
   manipolazione di stringhe, niente estrazione di suffissi, niente normalizzazione.
   Funziona identico per gap singoli (1 `variant_cluster_id`) e per coppie (2
   `atlas_codes` sotto lo stesso `variant_cluster_id`) — la coppia AML.T0006 +
   AML.T0084 è un unico cluster `atlas-t0006-t0084-recon`, non 2 cluster separati.

   **Schema ID sintetico** (Claude Code 2026-08-30): `variant_cluster_id` è l'unica
   fonte dell'ID sintetico, **non** i codici AML.T#### direttamente. Schema iniziale
   (v1 di questa spec) usava `T-ATLAS-T####` con suffisso AML.T#### + rimozione del
   prefisso per il confronto — scartato per due motivi strutturali:
   - Per coppie (T0006+T0084, T0103+T0108), `atlas_codes` contiene 2 codici mentre
     `technique_target` è singolo: nessuno dei due codici AML.T#### della coppia è "il"
     target da solo, quindi qualunque confronto basato sul singolo codice si rompeva
   - Il `removeprefix` + confronto di suffissi era complesso e propenso a bug (è
     stato trovato e corretto un bug specifico: `"T-ATLAS-T0077".removeprefix(
     "T-ATLAS-") in ["AML.T0077"]` è sempre `False`)

   Modifica documentata con commento inline che cita questa spec.

5. **Estensione `TestCase`** in `src/toy_agent/schema.py:118-122`: aggiungere il campo
   opzionale `strict_significant: bool = True`. Niente modifica al `__post_init__`
   esistente (campo è backward-compatible, default sicuro).

6. **Estensione `metrics.py`** (`src/toy_agent/metrics.py`): quando
   `case.strict_significant is False`, il caso NON entra in `per_tech_strict` (righe
   ~305-324, ma entra in `per_tech_primary` se ha `technique_target`) **E NON entra nei
   contatori aggregati strict `s_tp`/`s_fp`/`s_fn`/`s_tn`** (righe ~239-303 — blocco
   diverso e distinto dal breakdown per-tecnica). **Correzione 2026-08-31 (grilling sul
   piano canonico)**: la versione precedente di questa voce escludeva il campo solo dal
   breakdown per-tecnica, lasciando i contatori aggregati contaminati — quegli stessi
   contatori alimentano il Precision/Recall/F1 strict pubblicato in testa al report
   (`report.py`, sezione "Strict metric"), il numero più visibile di tutti. Un caso
   synthetic eseguito con successo da aidr come malicious produce comunque un FN
   garantito per costruzione lì (mai `technique_detected == "T-ATLAS-..."`) se i
   contatori aggregati restano invariati — stessa violazione del principio 8 che questa
   patch esiste per chiudere, spostata di un livello. Vedi ADR-0002 (aggiornata).

7. **Modifica a `report.py`** (o equivalente generatore di output): le righe del
   breakdown strict per-tecnica che hanno `strict_significant: False` (i.e. i casi
   synthetic) sono marcate `n/a — synthetic target, strict non significativo per
   costruzione` invece di un numero. Stessa convenzione del design v4 per
   LlamaFirewall (sezione "Cosa NON cambia" del design v4 — ancorare
   `per_vendor_concordance` alla primary, mai alla strict).

8. **Creazione di `catalog/vendor_scope_verification.yaml`** (file nuovo) con schema fisso
   dal design v4 righe 221-283.

9. **Test mirror di `test_every_entry_has_all_required_fields`** (reale, esistente in
   `tests/test_catalog.py`) in un nuovo file `tests/test_vendor_scope_verification.py`.

10. **Esecuzione dei nuovi casi contro `aidr-ai/agentic-threat-detection`** (vendor pinnato
    commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`).

11. **Popolamento di `vendor_scope_verification.yaml`** con 4-6 entry narrative (Passo 5).

12. **Per la categoria AML.T0103 / AML.T0108** (T-code proposto "Agent Propagation"):
    tentativo di esecuzione, ma "limite dichiarato" è esito accettabile — `cases.yaml`
    NON riceve entries, `vendor_scope_verification.yaml` riceve 1-2 entry con
    `verdict: out_of_scope` e motivazione estesa. Stesso pattern di Gap 17. Non è un
    fallimento del piano.

    **Precisazione (grilling 2026-08-30)**: "NON riceve entries" è letterale — zero
    righe in `cases.yaml` per `atlas-t0103-t0108-propagation`, non un'entry con status
    speciale o `variant_round_count: null`. `status` in `cases.yaml` ha solo due valori
    verificati (`candidate`, `selected` — `tests/test_catalog.py:128,148`); non esiste
    un terzo valore `out_of_scope` da introdurre per questo batch. Il tentativo
    documentato (C11) vive interamente in `vendor_scope_verification.yaml` + commit
    history del branch, mai in `cases.yaml`.

### OUT of scope (esplicito)

- Cross-check di altre tecniche ATLAS oltre le 46 mappabili già analizzate.
- Popolamento di `cases.yaml` con T-code aidr T0009/T0011 (Gap 17, già escluso storicamente).
- Estensione Nodo D — fuori scope, dichiarata nel design v4.
- Integrazione in `report.py` di `vendor_scope_verification.yaml` (Debito cumulativo #2,
  design v4).
- Policy di ri-verifica di `vendor_scope_verification.yaml` (Debito cumulativo #1,
  design v4).
- Esecuzione su `llamafirewall` come vendor — vincolato a un secondo batch dopo
  validazione che gli scenari siano sensati sul vendor di riferimento. Decisione di
  sequencing, non di merito.
- Modifica a `src/toy_agent/tools.py` (vincolo — la superficie d'attacco resta quella
  dei 6 tool dichiarati).
- Modifica sostanziale a `schema.py`/`metrics.py`/`Verdict` oltre le estensioni additive
  documentate sopra (campo `strict_significant`, ramo sul test bridge, esclusione dal
  breakdown strict). Il design v4 sezione "Cosa NON cambia" resta vincolante.

## Interfaccia di output

### `catalog/cases.yaml` (dopo questo batch)

- 31 entry esistenti **invariate** (byte-identiche, niente aggiunta esplicita di
  `null` sui nuovi campi)
- 8-12 entry nuove con `technique_code: null`, `atlas_codes: [AML.T####, ...]`,
  `variant_cluster_id` valorizzato per le coppie (`atlas-t0006-t0084-recon` e
  `atlas-t0103-t0108-propagation`)
- 4 nuovi campi opzionali backward-compatible (`variant_cluster_id`,
  `variant_round_count`, `per_vendor_concordance`, `atlas_codes`)

### `dataset/*.yaml` (dopo questo batch)

- Casi esistenti invariati
- 8-12 nuovi TestCase mirror, ciascuno con:
  - `technique_target: f"T-ATLAS-{variant_cluster_id}"`
  - `strict_significant: False`
  - `rationale` che cita il `catalog_id` della entry in `cases.yaml` (richiesto
    dal test bridge esistente a `tests/test_catalog.py:164`)

### `catalog/vendor_scope_verification.yaml` (nuovo, dopo questo batch)

- Schema fisso già descritto sopra
- 4-6 entry narrative, una per categoria di gap
- Per AML.T0103 / AML.T0108: `verdict: out_of_scope`, `evidence: docs/research/
  2026-08-30-atlas-taxonomy-crosscheck.md`
- Tutte le `evidence:` puntano a file `docs/**.md` esistenti su disco

### `tests/test_vendor_scope_verification.py` (nuovo)

- Mirror di `test_every_entry_has_all_required_fields` (reale, `tests/test_catalog.py`)
- Test esercitano il path reale (no test che passa senza leggere il file — lezione
  `docs/notes/pi-lesson-test-must-exercise-real-path.md`)

### `src/toy_agent/schema.py` (modifica additiva)

- Aggiunto campo opzionale `strict_significant: bool = True` a `TestCase`
- `__post_init__` invariato

### `src/toy_agent/metrics.py` (modifica additiva)

- Branch esistente "only for cases with a technique_target" (riga 295) esteso: i
  casi con `strict_significant: False` saltano l'incremento di `per_tech_strict` ma
  continuano a popolare `per_tech_primary`
- Commento esistente aggiornato con nota su `strict_significant`

### `report.py` (modifica additiva)

- Breakdown strict per-tecnica: righe relative a casi con `strict_significant: False`
  (check sulla proprietà semantica, non sul pattern di stringa del target sintetico —
  vedi C14) marcate `n/a — synthetic target, strict non significativo per costruzione`

### `tests/test_catalog.py` (modifica al test bridge)

- `test_selected_catalog_entries_match_their_dataset_test_case` esteso: aggiunto
  il ramo per `entry.technique_code is None` + `entry.variant_cluster_id is not None`
  + `case.technique_target == f"T-ATLAS-{entry.variant_cluster_id}"`. **Confronto
  diretto**, nessuna estrazione di suffissi — vedi Scope IN voce 4 per lo schema
  completo e la nota storica sullo schema scartato (`removeprefix`, bug-fix
  2026-08-30). Commento inline che cita questa spec.

## Criteri di accettazione (verificabili, eseguibili)

| # | Criterio | Verifica |
|---|---|---|
| C1 | I 4 nuovi campi opzionali in `cases.yaml` sono accettati dal loader esistente senza errori | `python -c "from src.toy_agent.dataset import load_dataset; load_dataset()"` ritorna senza eccezioni |
| C2 | Le 31 entry esistenti in `cases.yaml` non sono modificate (diff pulito, byte-identiche) | `git diff catalog/cases.yaml` mostra solo entry nuove in coda. **Verificato in Fase 4 dal final-reviewer, non da CI automatica** — un test pytest hardcoderebbe "31", falso al prossimo batch |
| C3 | Le 8-12 entry nuove hanno tutti i required fields di `cases.yaml` | `pytest tests/test_catalog.py -q` passa |
| C4 | `catalog/vendor_scope_verification.yaml` esiste ed è parsabile | `python -c "import yaml; yaml.safe_load(open('catalog/vendor_scope_verification.yaml'))"` ritorna senza eccezioni |
| C5 | Ogni entry di `vendor_scope_verification.yaml` ha tutti i 6 campi obbligatori | `pytest tests/test_vendor_scope_verification.py -q` passa |
| C6 | `verdict` ∈ {`in_scope`, `narrower_than_declared`, `out_of_scope`} per ogni entry | test specifico |
| C7 | `evidence` punta a un file `docs/**.md` esistente su disco | test specifico |
| C8 | `technique_code` non-null referenzia un T-code esistente in `vendor_taxonomy_snapshot.yaml` | test specifico (per la popolazione iniziale con `technique_code: null` la copertura sarà zero — limite accettato dal design v4) |
| C9 | Suite pytest completa passa, baseline invariato sui 31 casi esistenti | `python -m pytest tests/ -q` deve mostrare `446 passed, 0 skipped` (baseline verificato da Claude Code 2026-08-30, 15.12s) + i test nuovi. Nessuna regressione sui 31 esistenti. |
| C10 | Nessun modulo in `src/toy_agent` importa da `catalog/` | `grep -r "from catalog\|import catalog" src/toy_agent/` non trova match (vincolo design v4). **Da promuovere a test pytest reale in Task 0** del piano canonico (vincolo architetturale generale, economico da testare permanentemente — a differenza di C2 non diventa stale nel tempo) |
| C11 | Per AML.T0103 / AML.T0108: almeno un tentativo di esecuzione documentato + esito `out_of_scope` registrato, anche se `cases.yaml` non riceve entry per quella categoria | Verifica manuale della prosa in `vendor_scope_verification.yaml` + commit history del branch |
| C12 | Ogni `catalog_id` nuovo ha un `atlas_codes` valorizzato che referenzia tecniche top-level esistenti in `dist/v6/ATLAS-2026.07.yaml` | test specifico (presenza statica — lookup su YAML locale) |
| C13 | Ogni `TestCase` mirror in `dataset/*.yaml` ha `strict_significant: False` + `technique_target.startswith("T-ATLAS-")` + `technique_target == f"T-ATLAS-{catalog_entry.variant_cluster_id}"` per la corrispondente entry in `cases.yaml` | test specifico |
| C14 | Il breakdown `per_tech_strict` in `metrics.py` NON include righe per casi con `strict_significant: False` (check sulla proprietà semantica, non sul pattern di stringa del target sintetico — se un domani il prefisso `T-ATLAS-` cambia o un altro caso `strict_significant: False` usa un prefisso diverso, il check resta corretto) | ispezione manuale di `metrics.py` + test di integrazione |
| C15 | Ogni nuova entry di `cases.yaml` per questo batch ha `variant_cluster_id` valorizzato (è **obbligatorio** per le nuove entry, non più solo opzionale come nel design v4 per le31 esistenti). Le 31 entry esistenti restano con `variant_cluster_id: null` (regola del design v4: `variant_cluster_id` non retroattivo). Il `variant_cluster_id` è uno dei 4 ammessi: `atlas-t0077-rendering`, `atlas-t0006-t0084-recon`, `atlas-t0012-valid-accounts`, `atlas-t0103-t0108-propagation` | test specifico in `tests/test_catalog.py` |
| C16 | **NUOVO (2026-08-31)** — I contatori aggregati strict `s_tp`/`s_fp`/`s_fn`/`s_tn` in `metrics.py` NON includono casi con `strict_significant: False` (stesso criterio semantico di C14, applicato al blocco aggregato — righe ~239-303, distinto dal breakdown per-tecnica righe ~305-324). Il Precision/Recall/F1 strict pubblicato in `report.py` non include più FN garantiti per costruzione sui target synthetic | test di integrazione: un run con solo casi `strict_significant: False` malicious e correttamente rilevati da aidr deve dare `metrics.strict.recall` non contaminato (nessun FN attribuibile a quei casi specifici) |

## Architettura

Estensione additiva su file schema esistenti (`cases.yaml`, `dataset/*.yaml`,
`schema.py`, `metrics.py`, `test_catalog.py`) + creazione di un nuovo file
append-only (`vendor_scope_verification.yaml`) + nuovo test file
(`tests/test_vendor_scope_verification.py`). Pattern additivo coerente con la
filosofia del progetto (append-only, mai riscrittura, versioning per data).

L'esecuzione dei nuovi casi usa il flusso SDD canonico del progetto (5 fasi da
`docs/notes/pi-sdd-execution-procedure.md`), con implementer per-task, task-reviewer
per-task, final-reviewer per l'intero branch.

## Tech Stack

- Linguaggio: Python 3 (test esistenti in `tests/`)
- File schema: YAML (parser già in uso in `src/toy_agent/dataset.py`)
- Test runner: pytest (446 passed baseline)
- Vendor di audit: `aidr-ai/agentic-threat-detection`, commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`
- LLM per `final-reviewer` (Step 1): `deepseek/deepseek-v4-pro` thinking high
- LLM per implementer / task-reviewer / scoped-re-reviewer: modello di sessione Pi
  (`minimax/minimax-m3` thinking high)
- Documentazione: file Markdown in `docs/research/`, `docs/design/`, `docs/notes/`,
  `docs/superpowers/plans/`

## Global Constraints (verbatim dal design v4 + SPIRIT.md)

Da `docs/design/2026-08-30-atlas-audit-method-design-v4.md`:

- **"non misuriamo il modello — misuriamo il detector"** (`posizionamento.md` §1)
- `schema.py`, `metrics.py`, `Verdict` — **citazione corretta (grilling 2026-08-30)**:
  il design v4 dice letteralmente "nessuna modifica" (riga 395), senza qualificatori —
  non "nessuna modifica sostanziale" come una versione precedente di questa sezione
  riportava per errore. Questa spec propone comunque un'estensione additiva
  (`strict_significant` su `TestCase`, esclusione dal breakdown strict in
  `metrics.py`) che tocca questi file. **Deviazione dichiarata, non un'eccezione
  implicita**: il criterio del design v4 (righe 395-403, principio 6 SPIRIT.md) lega
  "nessuna modifica" al ruolo di questi file (producono/giudicano/verificano il numero
  pubblicato), non alla dimensione della modifica — la deviazione va giustificata sul
  merito, non per "è solo additiva". La giustificazione reale: **lasciare
  `metrics.py` invariato lascerebbe un FN garantito per costruzione dentro un numero
  pubblicato, violando il principio 8** (strutturale prima di contingente,
  `SPIRIT.md`) — la patch non è un'eccezione al principio 6, è un'applicazione del
  principio 8 che prevale su una lettura letterale della singola frase del design v4.
  Dettaglio in `docs/adr/0002-metrics-py-deviation-for-strict-significant.md`.
- **Regola del gemello benigno**: invariata
- **Nessun campo booleano `in_declared_scope` su `Verdict` o su `TestCase`** — si
  applica al campo `strict_significant` qui introdotto? No: `strict_significant`
  non descrive "se è in scope dichiarato dal vendor", descrive "se il breakdown
  strict per-tecnica è un segnale reale". Sono concetti distinti, niente
  contraddizione.
- Tracking delle varianti (Passi 2-4) vive in `catalog/cases.yaml` con
  `variant_cluster_id`, `variant_round_count`, `per_vendor_concordance` come campi
  opzionali (sezione "Dove vive il tracking")

Da `SPIRIT.md`:

- **Principio 1 (Dataset indipendente)**: ogni audit usa casi di test costruiti da
  zero, mai il benchmark fornito dal vendor
- **Principio 2 (Metodologia dichiarata prima dei risultati)**: ogni caso di test
  viene definito (tecnica target, esito atteso, ragionamento) *prima* di eseguire il
  tool, per evitare bias di conferma
- **Principio 4 (Riproducibilità)**: dataset, codice del toy agent e risultati grezzi
  pubblicati insieme all'analisi
- **Principio 6 (Pubblicazione e disclosure responsabile)**: schema dati, adapter,
  modulo metriche e generatore del report sono parte del **misuratore**
- **Principio 8 (Strutturale prima di contingente)**: una garanzia del misuratore vale
  solo se regge per costruzione — un `technique_target` synthetic (formato
  `T-ATLAS-{variant_cluster_id}`) NON rientrerebbe mai in `technique_detected` di un
  vendor reale (aidr usa T0001-T0014), quindi il breakdown strict per questi
  `technique_target` sarebbe FN garantito per costruzione = violerebbe il principio
  se pubblicato senza avvertenza. La patch `strict_significant: False` + esclusione
  dal breakdown strict + annotazione `n/a` nel report è la soluzione che rende la
  garanzia **strutturale**, non dipendente da un vendor specifico.

Aggiunti da questo spec (vincoli operativi):

- **Nessuna modifica a `src/toy_agent/tools.py`**
- **Nessuna nuova dipendenza in `pyproject.toml` root**
- **Mai commit su `main`/`master`** senza consenso esplicito
- **Branch dedicato**: `agentpi/atlas-6-gap-population` (lavoro in worktree separato)

## Rischi accettati (esiti leciti, non vincoli)

1. **AML.T0103 / AML.T0108 → limite dichiarato**: come in precedenza
2. **Verdetti `aidr` inaspettati su happy path**: come in precedenza
3. **Varianti deboli**: come in precedenza
4. **Coverage zero di C8 su questo batch**: come in precedenza — `technique_code:
   null` su tutte le 8-12 entry nuove
5. **Coverage zero del breakdown strict per le entry nuove**: previsto per costruzione,
   gestito da `strict_significant: False` + esclusione da `per_tech_strict` **e dai
   contatori aggregati `s_tp`/`s_fp`/`s_fn`/`s_tn`** (correzione 2026-08-31, C16) + label
   `n/a` nel report. **Diverso da un fallimento**: un FN garantito per costruzione
   non è un segnale sulla qualità del detector, è un artefatto di labeling.

## Punto aperto ereditato (NON blocco per questo spec)

**Segnale "verdetto da caso atypical" deve sopravvivere fino al report** — ereditato dal
design §4 (scratchpad 2026-08-29).

Applicazione: i casi nuovi sono "atypical" quanto i judge-targeted. 31 + 12 = 43
verdetti indistinguibili senza il segnale.

**Stato**: flaggato come prerequisito di **pubblicazione**, NON blocco per SDD execution
di questo batch. Verrà risolto in design doc dedicato (presumibilmente di Claude, non
di Pi — è un redesign del flusso di scoring, non un task di catalog).

**Timing (grilling 2026-08-30)**: "pubblicazione" qui si riferisce allo stesso evento
già definito in `docs/strategy/posizionamento.md` §10 (gate di purga pre-pubblicazione)
— quando il repo o il suo contenuto diventa pubblico, non a un traguardo intermedio di
questo batch o del prossimo (LlamaFirewall). Aggiunto alla lista di cose da risolvere
entro quel gate, invece di restare un debito a scadenza indefinita.

## Decisioni pending (aggiornate)

1. **Clustering AML.T0006 + AML.T0084 e AML.T0103 + AML.T0108**: preferenza = 2 entries
   separate in `cases.yaml` con stesso `variant_cluster_id`. Default = preferenza
   dell'autore della spec salvo obiezione dell'utente in Fase 0.
2. **Aggiunta esplicita dei 3 nuovi campi come `null` sulle 31 entry esistenti**:
   preferenza = NO (mantenere le esistenti byte-identiche). Default come sopra.
3. **Audit capability toy agent in Fase 0 SDD**: preferenza = sì. Default come sopra.
4. **NUOVA — Naming**: tutti i riferimenti ATLAS nella spec e nel piano canonico usano
   il prefisso `AML.` (es. `AML.T0077`). Conferma del grill skeptic finding #3.
5. **RISOLTA (grilling 2026-08-30) — Regola "2 varianti"**: documentata esplicitamente
   come **scelta di stabilità**, non applicazione del criterio v4 parola/tool/canale
   (skeptic finding #2) — un solo campione non dice nulla sulla varianza del verdetto.
   Regola finale, non più un default generico:
   - `variant_round_count: 2` **obbligatorio** per `atlas-t0077-rendering`,
     `atlas-t0006-t0084-recon`, `atlas-t0012-valid-accounts` (esecuzione reale attesa,
     la varianza del verdetto è un segnale da osservare)
   - **Nessuna quota** per `atlas-t0103-t0108-propagation`: se l'esito è `out_of_scope`
     (atteso), `cases.yaml` non riceve entry per quel cluster — vedi Scope IN voce 12 —
     quindi `variant_round_count` non si applica. Imporre "2" lì reintrodurrebbe la
     stessa classe di problema di Gap 17 (meccanismo forzato per soddisfare un conteggio
     a priori) — coerente con C11, che chiede solo "almeno un tentativo", non due.

## Riferimenti (fonti primarie verbatim)

- `docs/design/2026-08-30-atlas-audit-method-design-v4.md` (specifica di metodo)
  - righe 148-220: schema `variant_cluster_id`, `variant_round_count`, `per_vendor_concordance`
  - righe 221-283: schema `vendor_scope_verification.yaml`
  - righe "Cosa NON cambia": vincoli su schema/metrics/Verdict
  - righe "Stato di implementazione": dichiara che nessun file/test descritto esiste ancora
  - righe "Debito cumulativo": 4 punti dichiarati fuori scope
  - **gestione LlamaFirewall come precedente applicabile**: ancorare
    `per_vendor_concordance` alla primary, mai alla strict (sezione "Dove vive il
    tracking", ultima nota)
- `docs/research/2026-08-30-atlas-taxonomy-crosscheck.md`
  - Passo 5: tabella dei gap candidati (concentrati in 4 aree tematiche)
  - 46 mappabili totali, 40 coperte, 6 senza analogo T-code vendor
- `SPIRIT.md` (principi metodologici 1, 2, 4, 6, 8)
- `catalog/cases.yaml` (campi richiesti; commento in testa: "null è per area di
  comportamento legittimo, non per tecnica malicious senza T-code" — vincolo di
  convenzione del file)
- `catalog/vendor_taxonomy_snapshot.yaml` (vendor pinnato
  `7fad14d2478707e68a09b8ecd9942dec8fde1614`, 14 T-codes aidr T0001-T0014)
- `tests/test_catalog.py` (funzione reale `test_every_entry_has_all_required_fields` da
  mirrorare, path reale; **test bridge `test_selected_catalog_entries_match_their_
  dataset_test_case` righe 144-167** — oggetto di modifica)
- `src/toy_agent/schema.py` (TestCase righe 118-122; **oggetto di modifica additiva per
  `strict_significant`**, vincolo riga 130 su `technique_target`)
- `src/toy_agent/metrics.py` (**righe 285-298 oggetto di modifica**, gestione del campo
  `strict_significant` per esclusione dal breakdown strict per-tecnica)
- `src/toy_agent/dataset.py` (loader di casi — vincolo C1, C10)
- `docs/notes/pi-sdd-execution-procedure.md` (procedura 5 fasi + integrazioni Pi)
- `docs/notes/2026-08-30-atlas-6-gap-population-plan.md` (decisioni pending,
  stop conditions, punto aperto judge-targeted)
- `docs/design/registro-limiti-aperti.md` (Gap 17 = T-code aidr T0009/T0011, pattern di riferimento
  per "limite dichiarato")
- `temp/pi-council-grill-atlas-6gap-spec.md` (grill 4 council + risposta Claude
  2026-08-30 con scelta (b) + patch metrics.py)
- `docs/adr/0001-synthetic-technique-target-atlas-gaps.md` (ADR — decisione registrata
  dalla sessione di `/grill-with-docs` 2026-08-30, con le 4 alternative scartate)