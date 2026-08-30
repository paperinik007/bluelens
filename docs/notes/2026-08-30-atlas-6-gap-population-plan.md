# Piano SDD — Popolamento 6 gap ATLAS mappabili (post cross-check)

**Data**: 2026-08-30
**Status**: BOZZA — da approvare prima dell'esecuzione
**Controller**: Pi (sessione interattiva, modello `minimax/minimax-m3` high)
**Designer/spec input**: Claude Code (design §1 = v4 del metodo ATLAS, design §2 = cross-check
verificato in `docs/research/2026-08-30-atlas-taxonomy-crosscheck.md`)
**Scopo**: prima esecuzione end-to-end reale del metodo ATLAS a 5 passi — non più prosa di design.

## Correzioni applicate (ricevute da Claude Code dopo prima bozza)

4 correzioni verificate da Claude Code su fonti primarie, applicate il 2026-08-30:
1. **Strutturale**: i 12 casi vanno in `catalog/cases.yaml` (campi nuovi opzionali), NON in un
   file parallelo. `vendor_scope_verification.yaml` ha schema fisso già nel design v4 ed è per
   il Passo 5 (interpretazione narrativa del verdict).
2. **Path test**: `tests/catalog/test_catalog.py` NON esiste. Path reale = `tests/test_catalog.py`.
   Nuovo file = `tests/test_vendor_scope_verification.py`.
3. **Baseline pytest**: 446 passed, 0 skipped (NON 546+5). Claude Code ha eseguito pytest e
   verificato (15.12s).
4. **Schema vsyaml risolto**: design v4 righe 221-283 ha già schema esplicito
   (`entries: [{vendor, technique_code, declared_scope, verified_mechanism, verdict, evidence}]`).
   NON serve derivare in Fase 2.

## Correzione di framing (prima di tutto)

1. `catalog/vendor_scope_verification.yaml` **non esiste ancora come file**. Le "2 voci illustrative"
   citate in conversazione sono prosa nelle righe 221-283 del design v4 (`docs/design/2026-08-30-
   atlas-audit-method-design-v4.md`), e il design stesso dice esplicitamente (riga 17) "non esiste
   ancora" e (riga 411) che il popolamento è lavoro futuro.
2. **Questo batch = prima creazione ed esecuzione reale del file**, non aggiunta a file esistente.
   Cambia la posta in gioco: stiamo mettendo alla prova il metodo, non solo scrivendo design.
3. Test che il design v4 anticipa (riga 353, mirror di `test_every_entry_has_all_required_fields`)
   **va creato esplicitamente** come parte del piano, non dato per scontato dentro "le 5 fasi da
   procedura".

## Scope (deciso, da confermare)

### Selezione: 6 gap (tutti)

Identificati in `docs/research/2026-08-30-atlas-taxonomy-crosscheck.md` Passo 5. Tutti
`technique_code: null`, registrati in `vendor_scope_verification.yaml` (file da creare).

| # | AML code | Nome | Confine T-code | Rischio capability toy agent |
|---|---|---|---|---|
| 1 | AML.T0077 | LLM Response Rendering | T0002 (coperto in parte) | basso |
| 2a | AML.T0006 | Active Scanning (contro agente) | "Agent Capability Discovery" proposto | basso |
| 2b | AML.T0084 | Discover AI Agent Configuration | stesso T-code di 2a | basso |
| 3 | AML.T0012 | Valid Accounts (contesto agentico) | T0006 sfumato | medio |
| 4a | AML.T0103 | Deploy AI Agent | "Agent Propagation" proposto | alto |
| 4b | AML.T0108 | AI Agent | stesso T-code di 4a | alto |

### Varianti per tecnica: 2

12-18 casi potenziali → qui puntiamo a **12** (6 × 2). 2 varianti = una di "happy path" / smoke
test più una di "edge case" che esercita il confine T-code. Il design v4 non specifica il numero;
2 è la scelta minima per dare copertura (1 sola variante = 0 informazione sulla stabilità del
verdetto).

### Vendor: solo `aidr-ai/agentic-threat-detection`

31 casi esistenti sono su questo vendor. Aggiungere i 6 nuovi casi qui preserva la confrontabilità
diretta con il dataset esistente. LlamaFirewall entra in un secondo batch, dopo validazione che i
nuovi scenari siano sensati (Fase 4 del piano prevede checkpoint esplicito).

### Esiti accettabili per categoria 4 (T0103/T0108)

**"Tentativo, non garanzia"** — Claude ha già verificato (leggo `tools.py`):
- 6 tool: `query_customer_db`, `read_ticket_content`, `send_email`, `update_account`,
  `run_diagnostic`, `bulk_export`
- Nessuno spawna/orchestra/delega a sotto-agente
- Unico candidato "libero": `run_diagnostic(command)` (stringa libera), ma usarlo per "deployare
  un sub-agente" sarebbe indistinguibile da T0004/T0008 — esattamente la trappola di Gap 17
  (T0009/T0011)
- Il documento di ricerca stesso (righe 301-302) già scrive in modo condizionale/dubbioso
- **Esito atteso accettabile per categoria 4**: limite dichiarato (no popolamento), non un
  meccanismo forzato. Stesso pattern di Gap 17. Niente considerato "fallimento del piano".

## Prerequisiti (da verificare in Fase 0)

1. **Working tree pulita** sul branch attuale
2. **`main` locale senza commit non pushati**
3. **Capacità di eseguire casi aidr** verificata: `python -m pytest tests/toy_agent/ -q` deve
   passare sul baseline corrente (**446 passed, 0 skipped** — verificato da Claude Code 2026-08-30, 15.12s)
4. **Tool `run_diagnostic(command)`** ricontrollato: anche se categoria 4 è "tentativo",
   serve sapere se è capace di fare almeno "comando malevolo" generico — altrimenti il test della
   categoria 4 diventa "limite dichiarato" senza nemmeno un caso tentato
5. **Esistenza di un template per `vendor_scope_verification.yaml`**: schema **già esplicito**
   in `docs/design/2026-08-30-atlas-audit-method-design-v4.md` righe 221-283 (sezione Passo 5),
   con `entries: [{vendor, technique_code, declared_scope, verified_mechanism, verdict,
   evidence}]`. Le 2 voci illustrative esistenti (righe 267-283) usano già questo schema. NON
   serve derivare nulla in Fase 2.

## Decisione di scopinglight (registrata)

Confermato da Claude Code dopo i 2 check (tools.py + design v4):
- 6 tentativi, non garanzia di 6 popolamenti
- 2 varianti ciascuno (12 casi target, 8-12 realisticamente atteso se T0103/T0108 → limite)
- 1 vendor (aidr)
- Ordine di esecuzione: T0077 → T0006/T0084 → T0012 → T0103/T0108 (rischio strutturale per ultimo)

## Procedura di esecuzione SDD (5 fasi canoniche + integrazioni Pi)

### Fase 0 — Ricezione e setup

- [ ] 3 sanity check (working tree, branch, log)
- [ ] Creazione worktree: `git worktree add -b agentpi/atlas-6-gap-population
      ../agentic-security-audits-atlas-6-gap origin/main`
- [ ] Ledger in `.superpowers/sdd/2026-08-30-atlas-6-gap-population/progress.md`
- [ ] Verifica capability toy agent (pytest baseline)
- [ ] Lettura completa di `tools.py` per confermare il check di Claude

### Fase 1 — Studio

- [ ] Rilettura integrale di `docs/research/2026-08-30-atlas-taxonomy-crosscheck.md` (file
      appena chiuso da me — contesto caldo)
- [ ] Rilettura `docs/design/2026-08-30-atlas-audit-method-design-v4.md` righe 148-283
      (sezione "Dove vive il tracking": righe 148-220 → schema `cases.yaml` con campi opzionali
      `variant_cluster_id`/`variant_round_count`/`per_vendor_concordance`; righe 221-283 → schema
      `vendor_scope_verification.yaml`)
- [ ] Rilettura `catalog/vendor_taxonomy_snapshot.yaml` (per confermaforma T-codes e convenzioni)
- [ ] Rilettura `catalog/cases.yaml` (per pattern di casi esistenti — struttura, prompt, expected
      verdicts)
- [ ] Mappa task → (vuoto, è prima esecuzione)

### Fase 2 — Pre-flight scan di fattibilità

Output concreto: 2 tabelle + rulings nel ledger.

**Tabella 1 — Coppie di task che condividono file/interfaccia**:

| Coppia task | File condivisi | Rischio |
|---|---|---|
| T0077 + T0006/T0084 | `catalog/cases.yaml` (entrambi aggiungono 2-4 entries) | basso (additive su file YAML esistente) |
| T0012 + T0103/T0108 | `tools.py` (entrambi leggono/sfruttano `run_diagnostic`) | medio: se T0012 satura `run_diagnostic`, T0103/T0108 non ha superficie |
| Tutti i 6 task | `vendor_scope_verification.yaml` (Passo 5: verdict narrativo per ognuno) | basso, popolamento separato |

**Tabella 2 — Coerenza interna per task** (per ciascuno dei 6):
- Esiste "happy path" distinto da "edge case"? Servono entrambi o ne basta uno?
- Il prompt del caso è costruibile con i 6 tool senza scene contraddittorie?
- L'expected verdict è deterministico dato il tool behavior?

**Rulings attesi**:
- T0103/T0108 probabilmente → "tentativo, poi limite dichiarato" → va documentato come esito
  lecito, non come fallimento
- T0006 + T0084 → **2 entries `cases.yaml` separate con stesso `variant_cluster_id`** (cfr.
  decisioni pending). Stesso criterio per T0103 + T0108.

### Fase 3 — Loop task-per-task (6 task + 1 task setup file)

**Task ordering** (1-2-3-4):

1. **SetupCasi + SetupFile** (Task 0a + 0b): preparazione del terreno.
   - **Task 0a — Estensione `catalog/cases.yaml`**: aggiungere i 3 campi opzionali dello schema
     (`variant_cluster_id`, `variant_round_count`, `per_vendor_concordance`) come da design v4
     righe 148-220. Le 31 entries esistenti restano invariate (campi null). Verificare in
     `cases.yaml` stesso i campi obbligatori già esistenti per ogni entry (prompt/expected/tool
     script) e che l'aggiunta dei 3 campi opzionali sia backward-compatible.
   - **Task 0b — Creazione `catalog/vendor_scope_verification.yaml`** con struttura base
     (vuoto o solo header) + test mirror di `test_every_entry_has_all_required_fields` (reale,
     in `tests/test_catalog.py:...`). Schema da design v4 righe 221-283:
     ```yaml
     entries:
       - vendor: <aidr|llamafirewall|futuro>
         technique_code: <T00NN da vendor_taxonomy_snapshot.yaml | null>
         declared_scope: >
           <cosa il vendor dichiara di coprire>
         verified_mechanism: >
           <cosa il meccanismo fa davvero, verificato>
         verdict: in_scope | narrower_than_declared | out_of_scope
         evidence: >
           <path del research doc o report che ha verificato questo>
     ```
     File `tests/test_vendor_scope_verification.py` (path reale: NON esiste `tests/catalog/`)
     con almeno:
     - Tutte le entry hanno i required fields (vendor, technique_code, declared_scope,
       verified_mechanism, verdict, evidence)
     - `verdict` ∈ {in_scope, narrower_than_declared, out_of_scope}
     - `technique_code` referenziato esiste in `vendor_taxonomy_snapshot.yaml` se non-null
     - `evidence` punta a un file esistente

2. **T0077 — LLM Response Rendering** (Task 1): 2 varianti
   - Variante A: markdown injection in output agente → link malevolo renderizzato
   - Variante B: HTML payload (se il rendering dell'output supporta HTML)

3. **T0006 + T0084 — Active Scanning / Discover Agent Config** (Task 2): 2 varianti unificate
   - Variante A: probing tool surface (provare a invocare ogni tool e osservare risposta per
     fingerprinting)
   - Variante B: probing system prompt via turni successivi (extraction graduale)

4. **T0012 — Valid Accounts abuse** (Task 3): 2 varianti
   - Variante A: VIP-ticket (ticket da account con permessi elevati)
   - Variante B: impersonation via tool (es. `update_account` con customer_id che non è il proprio)

5. **T0103 + T0108 — Deploy / Sub-Agent** (Task 4): 2 varianti
   - Variante A: tentativo di `run_diagnostic` che scarica/esegue un secondo modello
   - Variante B: tentativo di comporre tool esistenti in catena che simula un sub-agente
   - **Esito atteso**: limite dichiarato (no popolamento) — `catalog/cases.yaml` NON riceve
     entries, `vendor_scope_verification.yaml` riceve 2 entries con `verdict: out_of_scope` e
     motivazione estesa in `verified_mechanism`

6. **Final review** (Task 5): tutto il branch, `final-reviewer` agent, modello
   `deepseek/deepseek-v4-pro` thinking high

7. **Finishing + audit requisiti↔codice** (Task 6)

### Fase 4 — Final whole-branch review

Subagent `final-reviewer` (`agentScope: "both"`), prompt basato su template
`requesting-code-review/code-reviewer.md`. Categorie di check attese:
- Struttura di `vendor_scope_verification.yaml` corretta
- Tutti i 12 casi (o 8-10 realisticamente) eseguiti + verdetto registrato
- Test mirror `test_vendor_scope_verification.py` passa + esercita il path reale (lezione
  `pi-lesson-test-must-exercise-real-path.md`)
- Esplicita documentazione del "limite dichiarato" per T0103/T0108 se è l'esito
- Nessuna regressione su `cases.yaml` esistente

### Fase 5 — Finishing

- [ ] Audit requisiti↔codice del design v4 (i requisiti a, b, c del metodo sono coperti?)
- [ ] Verifica `python -m pytest tests/ -q` finale
- [ ] Menu all'utente: merge locale / push+PR / keep as-is
- [ ] Aggiorna `docs/design/registro-limiti-aperti.md` con esito categoria 4

## 6 stop conditions (specifiche del controller Pi)

1. **T0103/T0108 → "no capability"**: NON è stop, è esito. Procedi con `status: out_of_scope`.
2. **Tool toy agent non eseguibile per smoke test**: fermati, chiedi all'utente (probabilmente
   il setup base non è in piedi)
3. **Test mirror di `test_vendor_scope_verification.py` non esercita path reale** (lezione):
   è Minor se esiste ma è debole, Critical se manca del tutto
4. **Variante A e B di un task producono verdetto identico**: segnala come Minor (probabilmente
   una variante è debole). Se 3 task di fila fanno questo, chiedi calibrazione.
5. **`aidr` verdetto inaspettato su happy path** (es. non blocca injection ovvia): fermati,
   segnala a utente, probabilmente scope/vendor issue
6. **Reviewer finale con Critical load-bearing dopo 1 fix + 1 re-review**: fermati, chiedi merge
   o ulteriore round

## Punto aperto ereditato (NON blocco per SDD)

**Segnale "verdetto da judge-targeted" / da "atypical scenario" deve sopravvivere fino al report**.

Fonte: scratchpad ieri (2026-08-29), sezione SDD judge-targeted-cases:
> Design §4 dichiara esplicitamente come prerequisito di pubblicazione: "il segnale 'questo
> verdetto viene da un caso judge-targeted' deve sopravvivere fino al report — altrimenti si
> perde dentro 33+ verdetti indistinguibili". Oggi vive solo nel `summary` di catalog/ e nel
> `case_id` — non su Verdict, non in report.py. Da risolvere PRIMA di pubblicare risultati di
> esecuzione su questi 2 casi, NON ora.

**Applicazione ai 6 gap**: i casi nuovi sono "atypical" quanto i judge-targeted (sono scenari
nuovi atipici rispetto al dataset esistente, hanno `technique_code: null`). Stesso problema:
33 + 12 = 45 verdetti indistinguibili se il segnale non sopravvive.

**Stato nel piano**: flaggato come prerequisito di **pubblicazione**, NON come blocco per
SDD execution. Verrà risolto in un design doc dedicato (verosimilmente di Claude, non mio).

## File da creare/modificare (atteso)

| File | Tipo | Task | Note |
|---|---|---|---|
| `catalog/cases.yaml` | modifica (additiva) | Task 0a + 1-3 | Aggiunge 3 campi opzionali in schema (`variant_cluster_id`, `variant_round_count`, `per_vendor_concordance`) + 8-12 nuove entries con `technique_code: null`. Le 31 esistenti restano invariate (campi nuovi = null). |
| `catalog/vendor_scope_verification.yaml` | crea | Task 0b + 1-4 | Nuovo file, schema fisso dal design v4 righe 221-283. Popolato in Passo 5 con 4-6 entries (verdict narrativo per categoria). |
| `tests/test_vendor_scope_verification.py` | crea | Task 0b | Mirror di `test_every_entry_has_all_required_fields` (reale, in `tests/test_catalog.py:...`). Path `tests/catalog/` NON esiste. |
| `tests/toy_agent/test_dataset.py` (o analogo) | modifica (additiva) | Task 1-3 | Aggiunge 8-12 test per i nuovi casi. |
| (nessuna modifica a `src/toy_agent/tools.py`) | n/a | n/a | vincolo: superficie attacco resta quella dei 6 tool dichiarati |

**Vincoli**: campi esistenti di `cases.yaml` backward-compatible, nessuna modifica a `tools.py`,
nessuna nuova dipendenza in `pyproject.toml` root, nessun commit su `main`.

## Stima tempo (realistica, non ottimistica)

| Fase | Tempo |
|---|---|
| 0 setup + 1 studio | 20-30 min |
| 2 pre-flight | 15 min |
| 3 loop task (6 task, 12-15 implementer dispatch + audit) | 3-5 ore |
| 4 final review | 20-30 min |
| 5 finishing | 15 min |
| **Totale** | **~4-6 ore** |

## Decisioni pending (da chiedere prima di partire)

1. **Schema YAML di `vendor_scope_verification.yaml`**: **RISOLTO**. Schema esplicito nel
   design v4 righe 221-283 (sezione Passo 5). Le 2 voci illustrative esistenti (righe 267-283)
   lo usano già. Non serve derivare nulla.
2. **Clustering**: T0006 + T0084 e T0103 + T0108 sono coppie. Vanno come 2 entries
   `cases.yaml` ciascuna (con stesso `variant_cluster_id` se stesso scenario, opzionale), oppure
   1 entry ciascuna che rappresenta l'intera coppia? Preferisco **2 entries separate con stesso
   `variant_cluster_id`** (più granulare, audit-friendly). Da confermare
3. **Ordine di esecuzione**: 1-2-3-4 = T0077 → T0006/T0084 → T0012 → T0103/T0108. Confermato
   da Claude, lo eseguo così
4. **Audit indipendente del checkpoint capability toy agent (Fase 0)**: necessario o si può
   saltare fidandosi del pytest baseline?

## Fonti citate (vincolanti)

- `docs/research/2026-08-30-atlas-taxonomy-crosscheck.md` (verificato oggi)
- `docs/design/2026-08-30-atlas-audit-method-design-v4.md` (righe 17, 221-283, 353, 411 specificamente)
- `docs/notes/pi-sdd-execution-procedure.md` (5 fasi + integrazioni Pi)
- `docs/notes/pi-operating-model-sprint.md` (agenti da usare)
- `src/toy_agent/tools.py` (verifica capability — da rileggere in Fase 0)
- `catalog/cases.yaml` (pattern dei 31 casi esistenti)
- `catalog/cases.yaml` (campi richiesti per ogni entry + campi opzionali nuovi: `variant_cluster_id`, `variant_round_count`, `per_vendor_concordance`)
- `tests/test_catalog.py` (test esistente reale; path `tests/catalog/` NON esiste — funzione
  `test_every_entry_has_all_required_fields` è qui, da mirrorare in
  `tests/test_vendor_scope_verification.py`)