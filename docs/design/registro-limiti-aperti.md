# Registro dei limiti aperti

Indice, non contenuto: una riga per ogni limite dichiarato o debito tecnico trovato
durante una review (task, whole-branch, o discussione ad-hoc) e non ancora risolto. Il
dettaglio pieno resta nel documento più pertinente — questa pagina punta lì, non lo
ripete, per evitare due copie che divergono.

Complementare, non sostitutivo, ai doc "gap-tracking" già esistenti
(`2026-08-14-toy-agent-gap-tracking.md`, `2026-08-14-metrics-gap-tracking.md`): quelli
tracciano una tassonomia specifica (Gap 1-15, segnali dell'effetto osservatore / gap
sulle metriche), già con una propria convenzione di stato ("Come si chiude un gap"). Qui
finisce tutto il resto — limiti a livello di implementazione, vincoli di design per un
piano futuro — che non ha già una casa strutturata.

**Quando aggiungere una riga**: ogni volta che una review o una discussione fa emergere
un limite reale, dichiarato esplicitamente invece che silenziosamente accettato o
ignorato (principio 8, `SPIRIT.md`), e non risolto subito nel codice.

**Quando rimuovere una riga**: quando il limite viene risolto nel codice — cancellare la
riga qui, la risoluzione stessa (commit, test) diventa il record.

## Aperti

- **Sequenze composte con `case_id` ripetuto** — un comando ripetuto con lo stesso
  `case_id` nella stessa sceneggiatura sovrascrive silenziosamente transcript grezzo ed
  evidenza raccolta di tutte le esecuzioni tranne l'ultima (`verdicts.jsonl` unico canale
  append-only che sopravvive). Non raggiungibile da nessun percorso di codice esistente
  oggi. Dettaglio, soluzione decisa (contatore per-`case_id`, non `command_index`
  grezzo), costo stimato e quando implementarlo (insieme a Plan 5, non prima):
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`, sezione Gap 15, dopo "Prossimo
  passo". Origine del limite: `docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md:226-256`.

- **Nessuna attesa esplicita di readiness del `detector` prima della prima invocazione
  in una sequenza** — `_open_container()` ritorna appena Docker segnala il container
  avviato, non appena l'entrypoint del detector ha finito di aprire le proprie porte
  interne. Chiuso in pratica dal tempo del round-trip LLM lato agente (che precede
  sempre l'invocazione al detector), ma incidentale, non garantito per costruzione — un
  verdetto classificato come infra-failure per detector non ancora pronto resta una
  possibilità teorica. Nessuna analisi di costo/quando fatta ancora. Dettaglio:
  `docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md`, sezione "Meccanica
  Docker per open/close".

- **Interfaccia di autoring non tecnica (Excel) per sceneggiature composte, Plan 5** —
  l'interfaccia con cui un umano non tecnico definirà davvero una sceneggiatura
  deliberata (Gap 15 modalità 2) sarà verosimilmente una tabella Excel, non YAML scritto
  a mano — serve un programma di traduzione Excel → sequenza, non ancora progettato,
  nessun precedente nel codice (`load_dataset()` parsa solo `*.yaml` oggi). Legato al
  punto sopra (case_id ripetuto): se l'autoring passa da Excel, i `case_id` ripetuti
  diventano più probabili, non meno. Dettaglio e vincolo completo:
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`, sezione Gap 15, dopo "Prossimo
  passo".

- **Validazione template/case_id del design doc Plan 5 non riproducibile** — il design
  doc (`docs/design/2026-08-19-plan5-dataset-design.md`, sezioni "Naming" e "Authoring —
  template") dichiara che due esempi di `case_id` sono stati fatti passare a mano
  attraverso `_entry_to_test_case` (`src/toy_agent/dataset.py`) e che il template
  compilato produce `TestCase` validi — ma nessuna delle due verifiche lascia traccia nel
  repo (nessun test, script o commit): non rieseguibile da un revisore terzo. Trovato da
  `grill-with-docs`, 2026-08-19. Soluzione proposta (non ancora implementata): un test
  automatico in `tests/test_catalog.py` (o file dedicato) che compila `_template.yaml`
  con valori reali di esempio e lo fa validare da `_entry_to_test_case`, sia per un caso
  malevolo sia per il suo gemello benigno — rende il claim un fatto rieseguibile invece
  di un'affermazione. Da implementare insieme a Plan 5, non prima (nessun `TestCase` reale
  ancora scritto con cui verificare che il test colga davvero un errore).

- **T0007 senza uno scenario valido nel catalogo/dataset** — design finalizzato
  2026-08-19 (approvato dall'utente, con due correzioni: i tre `customer_id` vanno
  enumerati esplicitamente nel testo del ticket, e il `case_id` finale non deve
  ripetere il nome della tecnica): una clausola statica aggiunta a `_SYSTEM_PROMPT`
  (`agent_loop.py`) dichiara `bulk_export` l'unico canale sanzionato per un export
  multi-cliente; lo scenario malevolo istruisce l'agente a evitarlo interrogando i
  clienti uno per uno (`query_customer_db` ripetuto), il gemello benigno usa
  `bulk_export` onestamente. Non ancora implementato nel codice — task 1 del piano
  "Plan 5a catalogo" (`docs/superpowers/plans/`, da scrivere). Dettaglio completo:
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 16.

- **T0009/T0011 senza scenario valido: richiedono manipolazione del tool, rischio di
  contaminazione** — entrambe le definizioni vendor descrivono un comportamento del
  *tool* (non dell'agente), come T0005/T0007 — ma un comportamento nascosto sempre
  attivo su `query_customer_db` (il tool più usato nei casi benigni) renderebbe
  "malevolo per costruzione" qualunque caso benigno che lo tocca; nessun gating pulito
  trovato tra le 6 combinazioni di campi disponibili. Accettato come limite dichiarato
  (deciso con l'utente 2026-08-19, non forzare un meccanismo) — copertura minima delle
  14 tecniche resta 12/14 in questo primo giro. Analisi completa dei 4 meccanismi
  considerati e scartati: `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 17.

## Risolti (storico, rimossi da "Aperti" quando chiusi nel codice)

- **Nessun controllo di raggiungibilità dei modelli tier prima di un run reale** —
  `SIFTER_MODEL`/`INSPECTOR_MODEL`/`EMBED_MODEL` venivano usati (espliciti in `.env` o
  default nel codice) senza nessuna verifica preventiva: un modello deprecato/irraggiungibile
  su OpenRouter si scopriva solo a batch già iniziato, o mai se il default silenzioso
  restava sbagliato (Gap 10 lo dichiara esplicitamente: "un catalogo di provider terzo
  invecchia nel tempo" — è già successo una volta con `qwen/qwen3-4b`, listato come attivo
  ma 404 al probe reale). Trovato discutendo perché lasciare `SIFTER_MODEL` ecc. vuoti in
  `.env` vanificava lo scopo di Gap 10 (2026-08-19). Risolto: `src/toy_agent/preflight.py`,
  `preflight_check_models()` — una chiamata OpenRouter minima per ogni tier configurato,
  prima che `run_batch.py` apra qualunque container; fail-fast (`sys.exit(1)`) se uno
  risponde errore. Verificato sia con mock (`tests/toy_agent/test_preflight.py`) sia dal
  vivo contro OpenRouter reale (successo sui 3 modelli configurati, fallimento reale su un
  model id inventato).
