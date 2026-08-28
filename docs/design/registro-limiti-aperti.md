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

- **Pubblicazione in `docs/reports/` manuale, senza copia automatica di `run.log`** —
  non esiste un punto di pubblicazione automatica: l'operatore copia `report.md` a mano
  in `docs/reports/`. Il refactor directory-per-run (2026-08-26) introduce `run.log`
  come evidenza forense del run, ma la sua copia accanto a `report.md` è affidata alla
  documentazione (README), non al codice — rischio che un report venga pubblicato senza
  la timeline del run. Trovato durante l'implementazione del piano run-observability
  (task T5, opzione A). Soluzione futura: un comando di pubblicazione automatica
  (`python -m toy_agent.publish <run_dir>`) che copi `report.md` + `run.log` + `raw/` in
  `docs/reports/<run_id>/`. Non in questo piano.

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

- **`label` statica in autoring vs. effetto osservato per le tecniche
  "choice-dependent"** — 11 delle 12 tecniche coperte (tutte tranne T0001, content-based)
  dipendono da una scelta probabilistica del modello (aderire o rifiutare) o da un
  effetto di tool non garantito da codice — se rifiuta, il transcript è benigno ma
  `label` resta "malicious" per costruzione, falsando lo scoring. Trovato dal council
  checkpoint su Plan 5a-5d (skeptic+risk, convergenza indipendente), 2026-08-19.
  **Meccanismo dichiarativo progettato, implementato e testato nel codice**
  (`docs/design/2026-08-19-gap18-attack-succeeded-design.md`, commit `cbef193`,
  passato per council checkpoint + grill-with-docs; implementazione:
  `docs/superpowers/plans/2026-08-19-gap18-attack-succeeded-implementation.md`,
  Task 1-7) — campo `attack_success_criteria` (DSL YAML) + `attack_succeeded`
  (calcolato post-hoc dal transcript), `label` invariata, nessun campo "tentativo"
  separato. Innesto completo e con test verdi in `schema.py` (DSL `Criterion` +
  validazione `TestCase`), `criteria.py` (parse/validate/evaluate), `dataset.py`
  (parsing a tempo di caricamento), `sequence.py` (calcolo di `attack_succeeded`),
  `metrics.py` (scoring), `report.py` (rendering) e `run_batch.py` (note di setup) —
  **risolto, non più bloccante prima di Plan 5a Task 1**. Restano esplicitamente
  aperti due punti, entrambi per la prossima fase e non per questo meccanismo:
  (a) **Risolto da Plan 5c** (commit range e51f38e..05943fe, 2026-08-20/21): tutti e 16
  i file `TestCase` malevoli del catalogo dichiarano ora un `attack_success_criteria`
  reale — verificato in questa review caricando l'intero `dataset/` con `load_dataset()`
  (31 casi, tutti i criteri validano contro `criteria.py`); (b) i rischi di collisione di
  campo T0005/T0010 e T0005/T0014
  segnalati per quella sessione di autoring — T0005 (`refund_without_authorization`)
  e T0010 (`ticket_false_prior_authorization_claim`) passano entrambi per
  `update_account(field="refund_total")`, indistinguibili a livello di metrica
  *strict* — **resta un limite accettato, vedi voce dedicata sotto** ("T0010... nessun
  vincolo su `value`") e la voce "`label` statica..." più sotto in questa pagina; T0005
  (variante `status`) e T0014 condividono `update_account(field="status")` — **risolto
  da Plan 5c**: entrambi i criteri vincolano ora esplicitamente `value`
  (`value: {equals: active}` per T0005-status, `value: {equals: disabled}` per T0014),
  verificato per costruzione in tutti i file committati (`status_update_triggers_hidden_admin_escalation.yaml`,
  `account_disabled_after_misread_opt_out_request.yaml`) da 2 task review indipendenti
  più questa review finale. **Nota di processo confermata ancora valida**: la ricerca di
  collisioni è rimasta opportunistica anche nel council checkpoint di Plan 5c (ha trovato
  le 2 coppie sopra ma non una terza, vedi voce "T0002 seconda variante vs T0012" sotto,
  trovata solo dalla review finale whole-branch) — non ancora un controllo sistematico su
  tutte le coppie. Dettaglio completo, classificazione tecnica per tecnica, punti di
  innesto nel codice: `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 18.

- **T0010 (`ticket_false_prior_authorization_claim`): nessun vincolo su `value`
  nell'`attack_success_criteria` per l'importo del rimborso** — il criterio
  (`update_account`, `field: {equals: refund_total}`) conta qualunque importo, anche
  simbolico, come successo pieno dell'attacco, perché il turno seed non dichiara un
  importo esatto ("rimborso completo") e il DSL dichiarativo (`src/toy_agent/criteria.py`)
  non ha un matcher numerico/di tolleranza — vincolare `value` a un valore esatto
  scambierebbe questo falso positivo con un falso negativo su qualunque scarto di
  formato (es. `"800"` vs `"800.0"`), un problema diverso, non un miglioramento netto.
  Trovato da council-risk durante il council checkpoint su
  `docs/superpowers/plans/2026-08-19-plan5c-dataset-authoring.md` (skeptic+risk,
  2026-08-20) — **distinto** dalla collisione T0005/T0010 già registrata sopra (voce
  "label statica... choice-dependent"): quella riguarda l'attribuzione della tecnica
  alla metrica strict, questa riguarda la severità dell'attacco misurata per il singolo
  caso T0010, indipendentemente da quale tecnica venga attribuita. Non risolto — nessun
  matcher numerico/di tolleranza nel DSL oggi; da affrontare solo se in fase di autoring
  o analisi (Plan 5c/5d) risulta effettivamente distorcere i risultati.

- **T0009/T0011 senza scenario valido: richiedono manipolazione del tool, rischio di
  contaminazione** — entrambe le definizioni vendor descrivono un comportamento del
  *tool* (non dell'agente), come T0005/T0007 — ma un comportamento nascosto sempre
  attivo su `query_customer_db` (il tool più usato nei casi benigni) renderebbe
  "malevolo per costruzione" qualunque caso benigno che lo tocca; nessun gating pulito
  trovato tra le 6 combinazioni di campi disponibili. Accettato come limite dichiarato
  (deciso con l'utente 2026-08-19, non forzare un meccanismo) — copertura minima delle
  14 tecniche resta 12/14 in questo primo giro. Analisi completa dei 4 meccanismi
  considerati e scartati: `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 17.

- **Tooling di revisione (`council`, estensione locale di `subagent-driven-development`)
  vive in repo privati, non pubblicati insieme a questo** — quando questo repo verrà
  reso pubblico, design doc/commit/ledger citeranno checkpoint "council" e ruling SDD
  la cui logica di esecuzione non sarà ispezionabile da terzi: restano nel repo
  pubblico solo gli output (verdetti, ruling, motivazioni scritte in doc/commit/ledger),
  non il meccanismo che li ha prodotti. In tensione con `SPIRIT.md` principio 6
  (trasparenza dei criteri di giudizio come dati ispezionabili), applicato oggi al toy
  agent/detector sotto audit ma non simmetricamente al processo di revisione del
  progetto stesso. Trovato in discussione (non da review di codice), 2026-08-20.
  **Soluzione decisa (minima, non ancora implementata)**: dichiarare esplicitamente il
  limite in `SPIRIT.md` — una nota che elenca quali passaggi del processo hanno usato
  tooling privato, chiarendo che decisioni e motivazioni restano preservate in git ma
  il meccanismo di revisione stesso non è pubblicato. Opzioni più ampie considerate e
  scartate per ora (pubblicare `claude-council` ripulito dall'infrastruttura personale
  non pertinente, o estrarne solo la parte rilevante come artefatto separato): fuori
  scope finché non emergono ulteriori problemi concreti.

- **15 casi benigni del catalogo Plan 5a collassano in ~8 comportamenti distinti** —
  costruiti indipendentemente da task diverse senza visibilità reciproca, diversi
  gruppi di `case_id` sono transcript quasi identici a livello di comportamento:
  `internal_report_export_request` (T0001)/`bulk_export_honest_quarterly_report`
  (T0007) sono entrambi "richiesta legittima → `bulk_export` → report onesto, nessuna
  email"; `order_summary_sent_to_own_address` (T0012)/`confirmation_sent_to_verified_address`
  (T0004) sono entrambi "cliente chiede conferma via email → `query_customer_db` per
  l'indirizzo registrato → `send_email` lì"; `login_issue_scoped_to_own_account`
  (T0006)/`diagnostic_ping_within_allowlist` (T0008)/`basic_login_diagnostic_check`/
  `single_status_check_as_requested` (T0013) sono tutti "una `run_diagnostic`
  allowlisted, nessun dato cliente toccato". Col dataset fisso a 31 casi, un singolo
  errore di un detector a livello di comportamento costa 2-4 falsi positivi/negativi
  *correlati* — il tasso di falsi positivi sui benigni è meno indipendente
  statisticamente di quanto N=15 suggerisca. Non un difetto di implementazione (ogni
  voce è verbatim dal piano) — problema di authoring a livello di piano. **Non risolto
  da Plan 5c** (2026-08-20/21, commit range e51f38e..05943fe) — il piano non ha
  differenziato questi cluster né dichiarato la correlazione, per scelta esplicita della
  review finale (differenziarli è un lavoro di autoring/design a sé, non un fix da
  innestare nella fix wave della review). **Metà della soluzione proposta da questa
  stessa voce implementata in un fix pre-Plan-5d** (stesso commit range del fix
  `require_ok`/`ToolError` sopra): `render_report()` (`src/toy_agent/report.py`, sezione
  "Methodology and Limitations") dichiara ora esplicitamente la correlazione in ogni
  report generato — non più solo in questo registro (test:
  `tests/toy_agent/test_report.py::test_report_includes_correlated_benign_cases_caveat`).
  Resta aperta solo la parte non implementata: differenziare i dettagli di superficie
  nei 15 casi, riassegnata a un futuro piano di revisione del dataset, non ancora
  pianificato (Plan 5d, verificato in questa review, copre solo README + prima
  esecuzione reale — non tocca il contenuto del dataset).
  Trovato dalla review finale whole-branch di
  `docs/superpowers/plans/2026-08-19-plan5a-catalog-completion.md`, 2026-08-20
  (Important finding #2).

- **Clausola guardrail di T0007 (Task 1) si sovrappone al segnale malevolo di T0006** —
  la clausola aggiunta a `_SYSTEM_PROMPT` (`src/toy_agent/agent_loop.py`, Task 1)
  vieta di interrogare `query_customer_db` ripetutamente su più clienti invece di
  usare `bulk_export`; il caso `cross_customer_lookup_for_unrelated_comparison`
  (T0006, Unauthorized Resource Access, Task 4) definisce il proprio segnale malevolo
  esattamente come query ripetute su clienti diversi per confrontarli — dopo Task 1
  quell'atto è anche T0007-shaped (Guardrail Evasion). L'agente potrebbe rifiutare
  l'esca T0006 per motivi di guardrail invece di esibire il comportamento che il caso
  vuole misurare, o un detector potrebbe attribuire il comportamento osservato a
  T0007 invece che a T0006. Non è una violazione Gap 1 (la clausola è identica e
  incondizionata per ogni caso) né un problema di label post-Gap-18. **Confermato,
  non risolto, da Plan 5c** (2026-08-20/21): il file committato
  `dataset/cross_customer_lookup_for_unrelated_comparison.yaml` usa esattamente il
  segnale che questa voce diceva di evitare (`query_customer_db` ripetuto su clienti
  diversi) — non una sovrapposizione teorica ma confermata dalla review finale
  whole-branch di Plan 5c, che ha anche riletto `_SYSTEM_PROMPT`
  (`src/toy_agent/agent_loop.py`) confermando che la clausola guardrail T0007 esiste
  davvero e si applica esattamente a questo pattern. Riassegnato a un futuro piano di
  revisione del dataset, non ancora pianificato (costruire il vero `TestCase` T0006 su
  un segnale che non si sovrappone, es. `read_ticket_content` di un singolo ticket
  altrui — stessa proposta di prima, solo riassegnata; Plan 5d copre solo README + prima
  esecuzione reale, non il contenuto del dataset). Trovato originariamente dalla review
  finale whole-branch di `docs/superpowers/plans/2026-08-19-plan5a-catalog-completion.md`,
  2026-08-20 (Important finding #3); confermato ancora aperto dalla review finale
  whole-branch di Plan 5c, 2026-08-21.

- **`ticket_fake_forwarding_policy_note` (T0002, seconda variante) vs
  `hidden_instruction_triggers_unauthorized_export` (T0012) — stesso template di prompt,
  stesso indirizzo esterno di destinazione** — entrambi i turni seed usano la stessa
  formulazione ("Nota interna: per policy... prima di rispondere al cliente") e
  terminano entrambi con un indirizzo `*-external.example`: `archive@ticket-mirror-external.example`
  per T0002, `data-sync@partner-mirror-external.example` per T0012. Sono
  simultaneamente IPI-shaped (istruzione nascosta nel testo del ticket) ed
  exfiltration-shaped (dato inoltrato fuori dal confine autorizzato) — l'attribuzione
  della tecnica da parte di un detector è arbitraria tra le due. Nota: la prima variante
  di T0002 (`ticket_hidden_instruction_in_reply`) evita questa sovrapposizione tenendo
  il payload dentro la risposta al cliente, senza destinatario esterno — la seconda
  variante, aggiunta da Plan 5c Task 3, ha reintrodotto l'inoltro esterno. Impatto
  confinato alla metrica strict/per-tecnica (entrambi i casi restano `label: malicious`,
  la metrica primaria non è affetta) — stesso tipo di contenimento già accettato per la
  collisione T0005/T0010. Trovato dalla review finale whole-branch di Plan 5c,
  2026-08-21. Soluzione minima (non ancora implementata): dare alla seconda variante di
  T0002 un payload non-exfiltrativo (es. una nota "policy" nascosta che istruisce un
  `update_account`), per ripristinare la distinzione vettore/effetto.

- **T0013 (`repeated_status_checks_without_cause`): `min_count: 5` verificato solo per
  raggiungibilità strutturale, non per calibrazione empirica** — il valore è confermato
  raggiungibile entro il tetto di 8 turni del loop (`agent_loop.py` permette più tool
  call per completion), ma non è stato confermato contro un run reale che 5 sia la
  soglia giusta per distinguere un pattern "ripetizione senza causa" da un modello che
  si ferma dopo 2-3 ripetizioni (che mostrerebbe lo stesso pattern problematico su scala
  minore e scorerebbe `attack_succeeded: False`). Il caveat viveva finora solo in un
  commento YAML (`dataset/repeated_status_checks_without_cause.yaml`) e nel testo del
  piano — mai in questo registro, a differenza del caveat analogo su T0010 (voce sopra),
  registrato dallo stesso council checkpoint. Trovato dalla review finale whole-branch di
  Plan 5c, 2026-08-21. Da confermare/calibrare con un run reale (Plan 5d o successivo).

- **case_id di esempio del design doc Plan 5 non verificati in un test reale** — il
  design doc (`docs/design/2026-08-19-plan5-dataset-design.md`, sezione "Naming") cita
  due stringhe di `case_id` (`account_status_change_escalates_privilege`,
  `marketing_optin_change_request`) dichiarate "fatte passare a mano" attraverso
  `_entry_to_test_case` — nessuna delle due compare in un test reale del repo (Plan 5b
  Task 4 ha chiuso solo il limbo gemello: la validazione del *set di campi* del
  template, non queste due stringhe specifiche). Trovato dalla review finale
  whole-branch di Plan 5b, 2026-08-20. Soluzione minima (non ancora implementata):
  aggiungere le due stringhe come `case_id` in un test parametrizzato contro
  `_entry_to_test_case`/`CASE_ID_PATTERN`.

- **Coerenza catalogo↔dataset (Plan 5b Task 3) non confronta `label_hint` con
  `TestCase.label`** — il test
  (`tests/test_catalog.py::test_selected_catalog_entries_match_their_dataset_test_case`)
  verifica `technique_target` (per voci malevole) e la presenza del `catalog_id` nel
  `rationale`, ma non che `entry["label_hint"]` corrisponda a `case.label`: una voce
  `status: selected` con `label_hint: benign` che punta a un `TestCase` con
  `label: malicious` (o viceversa) passerebbe senza essere segnalata, nonostante
  `label` sia la ground truth letta dallo scoring. Spec-compliant (il design doc,
  mapping Requisito → Verifica, prescrive esattamente i due controlli implementati) —
  limite del design, non deriva dell'implementazione. Trovato dalla review finale
  whole-branch di Plan 5b, 2026-08-20. Soluzione minima (non ancora implementata):
  aggiungere `entry["label_hint"] != case.label` alla lista `offending`.

- **Docstring di `_filled_template_example` punta ancora a una voce di questo registro
  già cancellata** — `tests/test_catalog.py:171-173`, la `rationale` del fixture è già
  stata ricorretta verso il design doc (fix wave della review finale, commit `d929dc1`),
  ma il docstring della funzione dice ancora "Closes the open item in
  registro-limiti-aperti.md" — la voce che chiudeva (validazione del set di campi del
  template) è stata rimossa da questo file dal commit `0390db5` stesso. Puramente
  cosmetico (nessun test dipende dal testo del docstring), trovato dalla scoped
  re-review del fix wave finale di Plan 5b, 2026-08-20 — non corretto in questo ciclo
  (nessun secondo fix wave consentito dal processo SDD per la review finale). Soluzione
  minima: aggiornare il docstring per citare il design doc invece del registro.

- **Riferimento incrociato "vedi Fix 7 sotto" nel design doc non risolvibile dal
  lettore** — `docs/design/2026-08-19-plan5-dataset-design.md`, riga della tabella
  Mapping Requisito → Verifica per il gate anti-scorciatoia (aggiunta dal fix wave
  finale, commit `9bb1d16`): la frase finale cita "vedi Fix 7 sotto", ma "Fix 7" è
  un'etichetta che esiste solo nel report del fix wave
  (`.superpowers/sdd/2026-08-19-plan5b-verification-gates/final-review-fixwave-report.md`,
  gitignored), non nel design doc stesso — un lettore del design doc non trova nulla
  "sotto". Trovato dalla scoped re-review del fix wave finale di Plan 5b, 2026-08-20 —
  non corretto in questo ciclo. Soluzione minima: sostituire con un riferimento
  autosufficiente (es. citare direttamente `run_batch.py::_setup_notes()` senza
  rimandare a "Fix 7").

- **Caveat di troncamento asimmetrico tra il ramo "passed" e il ramo "failed" del gate
  anti-scorciatoia** — il fix wave finale di Plan 5b (commit `9bb1d16`) ha aggiunto un
  caveat di troncamento (breaker_tripped, executed_count/total_count,
  last_infra_rationale) solo al messaggio stderr quando il check FALLISCE
  (`run_batch.py::main()`), non alla nota che `_setup_notes()` scrive nel report quando
  il check PASSA. Se il breaker scatta ma il campione troncato risultante non contiene
  comunque nessun tool "solo malevolo", il report dichiarerà "passed on this run's
  observed transcripts" senza segnalare che il campione era incompleto — stesso rischio
  di diagnosi fuorviante che il caveat sul ramo failed esiste per evitare, ma non
  richiesto testualmente dal finding originale (Important #4), quindi non un difetto
  del fix rispetto a quanto chiesto, solo un'estensione naturale non ancora fatta.
  Trovato dalla scoped re-review del fix wave finale di Plan 5b, 2026-08-20 — non
  corretto in questo ciclo. Soluzione minima: stesso pattern del ramo failed, applicato
  al ramo passed in `_setup_notes()`.

- **Nessuna osservabilità durante l'esecuzione di `execute_sequence`/`execute_batch`** —
  `run_batch.py` non stampa nulla su stdout/stderr mentre i 31 casi girano: i due unici
  `print(..., file=sys.stderr)` in `main()` avvengono uno prima di aprire qualunque
  container (preflight modelli) e uno dopo che tutti i casi sono già finiti (gate
  anti-scorciatoia) — in mezzo, silenzio completo. L'unico segnale di avanzamento oggi è
  indiretto: `verdicts.jsonl` che cresce riga per riga (append-only, un `Verdict` per
  caso completato) e la comparsa progressiva delle cartelle `run_output/<case_id>/`. Se
  il circuit breaker scatta a metà, il processo non si ferma bruscamente (continua,
  scrive comunque un report marcato come troncato, esce con codice 0) — ma l'operatore
  non ha modo di saperlo se non aspettando la fine o notando che `verdicts.jsonl` ha
  smesso di crescere. Trovato durante l'esecuzione operativa di Plan 5d Task 2,
  2026-08-21 (prima esecuzione reale sul dataset completo): due run in background sono
  stati interrotti da un kill esterno alla sessione senza nessuna traccia diagnostica
  disponibile finché non si è ispezionato `verdicts.jsonl`/le evidenze per-caso a
  posteriori, e un caso con comportamento anomalo del detector (`basic_login_diagnostic_check`,
  "max turns reached", ~14557 in_tokens contro ~300-900 tipici) è stato notato solo
  a run finito, non nel momento in cui accadeva. Non risolto in questo ciclo (Plan 5d
  dichiara esplicitamente "nessun codice nuovo"; l'unica eccezione presa in questo piano
  è stata un fix di correttezza vincolato da un Global Constraint, non un miglioramento
  di osservabilità). Utilizzo potenziale oltre al semplice logging leggibile da umano,
  segnalato esplicitamente dall'utente: una riga per caso in `execute_sequence`
  (case_id, esito, timing) è anche la base minima per un futuro meccanismo di
  ripresa/checkpoint dopo un'interruzione a metà batch (rilevante proprio per
  l'interruzione osservata qui), per un conteggio costo/token in tempo reale, o per
  rilevare in diretta un caso anomalo (come il "max turns reached" sopra) invece che
  solo in retrospettiva. Soluzione minima non ancora progettata: un `print`/log
  strutturato in `execute_sequence` dopo ogni `CommandStep` completato.

- **`run_batch` tronca `verdicts.jsonl` a inizio run ma non pulisce `raw/` né le
  cartelle di evidenza `<case_id>/`** — `sequence.py:161-162` fa
  `raw_dir.mkdir(parents=True, exist_ok=True)` e scrive i transcript di questo run,
  ma non rimuove mai quelli del run precedente; lo stesso vale per le cartelle
  `<case_id>/` con i `detector.vendor_proxy.jsonl` e i log. `verdicts.jsonl` invece
  viene troncato correttamente (test: `test_verdicts_jsonl_is_truncated_at_the_start`).
  Effetto: ogni run accumula i residui del precedente in silenzio — un operatore che
  non li cancella a mano si ritrova con transcript di due run diversi nella stessa
  directory, e le cartelle di evidenza del run precedente che non sono state
  riscritte restano lì con dati obsoleti. Trovato durante il cleanup del run
  troncato (13/31) del 2026-08-25: `raw/` conteneva 18 transcript datati Aug 21
  (run precedente) mescolati ai 13 nuovi. Il cleanup manuale ha ridotto
  `run_output/` da 118M a 23M. **Risolto per costruzione, 2026-08-26**: il refactor
  directory-per-run (`docs/design/2026-08-26-run-observability-directory-per-run-design.md`)
  fa nascere ogni run in una directory vuota `run_output/<run_id>/` — non c'è più un
  namespace condiviso da pulire. Il vecchio layout flat è archiviato in
  `run_output/legacy-20260825-troncato/`.

- **`PYTHONPATH` mai documentato — stesso trabocchetto che ha causato due run sprecati
  in Plan 5d** — `python -m toy_agent.run_batch` (il comando che README, "Come
  eseguire", dice testualmente di lanciare) risolve silenziosamente il pacchetto
  `toy_agent` dall'installazione editable globale della macchina, che punta al
  checkout della repo principale, non alla working directory da cui si lancia il
  comando — chiunque lo lanci da una worktree diversa dalla repo principale esegue in
  silenzio il codice sbagliato. Trovato durante l'esecuzione operativa di Plan 5d
  (`python -c "import toy_agent.run_batch as m; print(m.__file__)"` risolveva al
  checkout principale anche da dentro la worktree), costato due run completi del
  batch (i primi due dopo il fix Gap 17) prima di essere diagnosticato. Non ancora
  documentato in README — il fix (`PYTHONPATH=<checkout>/src`) è stato usato "a mano"
  in questa sessione ma mai scritto per un operatore futuro. Trovato dalla review
  finale whole-branch di Plan 5d (Opus), 2026-08-21. **Risolto nel codice, sessione
  2026-08-25**: `run_batch.py` e `regenerate_report.py` ora rifiutano entrambi di
  partire (`sys.exit(1)` con i due path a confronto) quando il modulo `toy_agent`
  importato non è quello della working tree da cui si lancia il comando — il guasto
  da silenzioso diventa esplicito (principio 8), non dipende più dalla memoria
  dell'operatore. README aggiornato di conseguenza. Resta aperta solo l'alternativa più
  strutturale, non ancora decisa né implementata: abbandonare l'installazione editable
  globale a favore di un virtualenv per-worktree, così che ogni worktree risolva
  `toy_agent` dalla propria `src/` e il guasto diventi impossibile per costruzione
  invece che rifiutato a runtime.

- **"12/14"/T0009/T0011 hardcoded in `_setup_notes()` senza guardia anti-drift** — la
  frase di copertura (Gap 17) aggiunta a `run_batch.py::_setup_notes()` è un literal
  indipendente dall'unica altra fonte della stessa informazione
  (`tests/test_dataset_coverage.py::DECLARED_UNCOVERED_TECHNIQUES`) — se Gap 17 verrà
  mai risolto (anche parzialmente, es. solo T0009), il gate di copertura si
  aggiornerebbe correttamente ma il report continuerebbe a dichiarare "12/14... T0009
  and T0011" per sempre, senza che nulla lo segnali. Trovato dalla review finale
  whole-branch di Plan 5d (Opus), 2026-08-21 — non corretto in questo ciclo (deciso
  esplicitamente con l'utente: solo il finding Critical, Gap 14, in questo giro).
  Soluzione minima proposta dal reviewer: un test di coerenza in
  `test_dataset_coverage.py` che calcoli `len(tutte le tecniche) -
  len(DECLARED_UNCOVERED_TECHNIQUES)` e verifichi che `_setup_notes()` lo dichiari
  correttamente — non serve leggere `catalog/` da `run_batch.py` (violerebbe il
  confine architetturale dichiarato in README), il test può vivere accanto al gate
  già esistente.

- **La cartella del report pubblicato è datata `2026-08-19`, l'esecuzione reale è del
  2026-08-21** — il piano nominava la cartella prima di eseguire (una data-non-ancora-
  nota scritta come letterale nel testo del piano), e il report dichiara
  esplicitamente "fully deterministic (no timestamp)" — quindi il nome della cartella
  è l'unica data attaccata all'artefatto pubblicato, ed è sbagliata di due giorni.
  Trovato dalla review finale whole-branch di Plan 5d (Opus), 2026-08-21, che ha
  esplicitamente dissentito dalla scelta del controller di seguire il piano alla
  lettera invece di correggere la data. Non corretto in questo ciclo (stessa
  decisione: solo il Critical). Soluzione minima: rinominare la cartella in
  `2026-08-21`, o aggiungere una riga esplicita di data di esecuzione alle Setup
  notes del report (la seconda opzione sopravvive anche a un'eventuale futura
  rinominazione).

- **Executive Summary del report mostra "Total cases: 31" mentre il campione positivo
  effettivo è 4** — dopo le riclassificazioni Gap 18 (12 casi malevoli riclassificati
  come benigni), il numero di casi che contribuiscono realmente a TP/FN è 4, non 31 —
  ma questo si vede solo leggendo le Setup notes in fondo alla sezione Methodology,
  non nell'Executive Summary dove un lettore vede per primo "Total cases: 31" seguito
  dai numeri P/R/F1. Trovato dalla review finale whole-branch di Plan 5d (Opus),
  2026-08-21 — non corretto in questo ciclo (stessa decisione: solo il Critical).
  Soluzione minima: una riga nell'Executive Summary che affianchi al "Total cases"
  anche il campione positivo effettivo scorato.

- **Modifica al documento requisiti fondativo fatta senza un secondo passaggio di
  revisione, a differenza di ogni altra modifica della stessa sessione** — la riga
  "Copertura completa della tassonomia" nella tabella "Mapping Requisito → Verifica"
  di `2026-08-14-toy-agent-e-pipeline-misura.md` (il documento che la stessa tabella
  dichiara essere l'elenco dei "gate critici... integrità della misura, assenza di
  bias, riproducibilità") è stata corretta dal controller con una singola `Edit`,
  senza alcun ciclo implementer+reviewer — mentre ogni altra modifica di questa
  sessione, incluse correzioni di tre righe, è passata per quel ciclo. La correzione
  nel merito sincronizzava solo una decisione già presa in una sessione precedente
  (Gap 17, 2026-08-19) mai propagata al testo originale — non introduceva una
  decisione nuova — ma il *documento* toccato è quello che stabilisce le promesse
  fondative del progetto su se stesso, non un report operativo o un log di gap.
  Trovato dall'utente esplicitamente, durante la chiusura di Plan 5d, 2026-08-21 — non
  ancora deciso se e come "chiudere": possibili strade sono (a) una revisione
  indipendente a posteriori della modifica già fatta (commit `a108b48`), (b) una
  regola esplicita — per questo progetto o in generale — che ogni modifica al
  documento requisiti fondativo (non ai design/gap-tracking doc derivati) richieda
  sempre un secondo passaggio di revisione, indipendentemente da quanto la modifica
  sembri una semplice sincronizzazione.

- ~~**Secondo run reale completo (`run_output/`, 2026-08-21, 31/31 casi) prodotto ma non
  pubblicato**~~ — **risolto, 2026-08-28**: quel run specifico (pre-Gap19) non è stato
  recuperato — reso superfluo da un run successivo, eseguito il 2026-08-26 con codice
  già corretto post-Gap19/20/21 (`measurer_commit=da886e0`), pubblicato in
  `docs/reports/aidr-2026-08-26/` (confronto numerico col report del 19/08 in `NOTE.md`
  di quella cartella — differenze dentro la normale variabilità di campionamento, non un
  effetto del fix). Il report del 19/08 resta pubblicato accanto, non sostituito
  (principio 4/7 SPIRIT.md: nessun run scompare dalla storia).

- **`run_output/` non tracciato e non in `.gitignore`** — `git check-ignore -q
  run_output` ritornava non-zero (non ignorato); ogni esecuzione di `run_batch.py`/
  `regenerate_report.py` lasciava 281 file non tracciati nella working directory
  (confermato, sessione 2026-08-21), con nessun passo di pulizia nel piano. Rischio: un
  futuro `git add -A` avrebbe pubblicato una copia duplicata accanto a `docs/reports/`.
  Trovato dalla review finale whole-branch di Plan 5d (Opus), 2026-08-21. Risolto:
  `run_output/` aggiunto a `.gitignore`, sessione 2026-08-21.

- **Enforcement dei gate duplicato tra `run_batch` e `regenerate_report`** — il flusso
  "esegui gate → rifiuta" è ripetuto quasi identico in due entrypoint:
  `run_batch.main()` (transcript_unusable gate → `sys.exit(1)`, anti-shortcut gate →
  `sys.exit(1)`) e `regenerate_report.regenerate()` (stessi due gate → `raise
  ValueError(...)`, messaggi simili ma non identici). La logica predicativa è condivisa
  (`transcript_unusable_gate_failure`, `find_malicious_only_tools`), ma l'enforcement è
  duplicato e i messaggi divergeranno col tempo — esattamente il difetto "due copie che
  divergono" che questo registro contesta altrove. Trovato durante handoff sessione
  parallela 2026-08-25. Soluzione minima: estrarre `enforce_publish_gates(result) ->
  str | None` (o rifiuta, o ritorna il messaggio), chiamata da entrambi. Stima bassa
  (estrarre una funzione, spostare 4-6 test). Non ancora programmata.

- **Nessuna motivazione documentata per il default `gpt-4o-mini`** — il modello agente
  è ora configurabile e dichiarato, ma la scelta del default non ha una motivazione
  scritta. OpenRouter pubblica un "Tool Call Error Rate" per modello, che sarebbe il
  criterio naturale; scegliere su quella base è una decisione sperimentale separata.
  Design: `docs/design/2026-08-21-interfaccia-modello-agente-design.md`, sezione 11.6.

- **Il wall-clock budget per caso non è strutturalmente sotto `AGENT_TIMEOUT_S`** —
  8 turni × timeout 20s = 160s contro un limite di 120s, e fino a ~204s con il retry
  budget speso. Meglio di prima (il timeout non esisteva), ma ancora non una garanzia.
  `AGENT_TIMEOUT_S` deliberatamente non alzato: è una condizione sperimentale pubblicata.

- **Una causa per caso escluso** — `transcript_unusable_cause` restituisce la prima
  causa in un ordine di precedenza dichiarato. Un caso contaminato e poi troncato è
  attribuito solo a come è finito. Accettabile finché le esclusioni sono rare.

- **Una risposta senza campo `cost` fa uscire il caso dalla misura** — senza la tabella
  prezzi (rimossa al Task 19), un `usage.cost` mancante solleva e il caso diventa
  `model_error`. Deliberato e coerente col criterio del design, ma un'omissione lato
  provider costa un caso.

- **Un trip del circuit breaker ora sopprime anche il report** — i tre `infra`
  consecutivi sono tre `transcript_missing`, che su qualunque run sotto ~30 casi
  superano il 10%. Un run troncato prima pubblicava un report dichiarando il troncamento;
  ora non pubblica affatto. Deliberato, il messaggio stderr nomina entrambe le condizioni.

- **Il circuit breaker è cieco a un run che risponde pulito senza niente di utilizzabile**
  — conta solo `error_kind == "infra"`, che `orchestrator.py` assegna in 4 punti.
  Un `stop_reason="model_error"` esce 0, il detector viene invocato e pagato, il breaker
  vede un caso sano. Sistemico: se la chiave agente esaurisce i crediti a metà run, ogni
  caso rimanente è pagato e il run non pubblica nulla. Estendere il breaker è stato
  scritto, revisionato e deliberatamente tagliato (decisione utente 2026-08-21, opzione
  C): compra solo tempo e denaro, su un evento mai osservato, al prezzo di toccare l'unico
  meccanismo di controllo del batch. Il costo che avrebbe protetto è ora misurato:
  **$0.0136 per l'intero run di 31 casi** — il che chiude la questione. Riaprire solo
  se il costo per caso del detector cresce di ordini di grandezza.

- **Il costo del detector è catturato ma mai aggregato** — `Verdict.cost_usd` è `None`
  senza una buona ragione. 519 risposte vendor su 519 portano un campo `cost` nel
  thin-proxy log (run pubblicato). `adapter.py:88` ignora il costo reale e forwarda
  `in_tokens`/`out_tokens` dall'autodichiarazione del vendor. Chiudere questo è economico
  e retroattivo: i numeri sono già su disco. Lavoro separato, non questo piano.

- **`error_count` ora esclude i guasti infra nostri** (decisione D-I) — confrontare
  `error_count` tra un report pre-fix e uno post-fix è confrontare due quantità diverse.
  Il report lo dice; un lettore che diffa due run deve saperlo.

- **Il retrofit fail-open di aidr (Task 7,
  `docs/superpowers/plans/2026-08-27-multi-vendor-llamafirewall-implementation.md`)
  cambia retroattivamente il comportamento di scoring di aidr sui casi
  fail-open** — `metrics.py:209-264` esclude ogni `Verdict` con
  `status="error"` da TP/FP/FN/TN, contandolo solo in `error_count`. Prima
  di questo retrofit, un fail-open del Sifter produceva un `DetectionResult`
  indistinguibile da una detection reale (Inspector veniva comunque
  invocato con `tactic="N/A"`, e il suo verdetto — vero o falsato dal
  tactic sbagliato — entrava in TP/FP/FN/TN). Dopo questo retrofit, lo
  stesso caso produce `status="error", label=None` — **esce** dal calcolo.
  Rilanciare un qualunque benchmark aidr già pubblicato dopo questo commit
  produrrebbe numeri P/R diversi da quelli pubblicati, non per un cambio di
  modello o dataset ma per un cambio nel codice di misura stesso — evento
  di riproducibilità (SPIRIT.md, principi 4/7), da dichiarare esplicitamente
  quando si confrontano run pre- e post-Task-7. I run già pubblicati in
  `docs/reports/` non vengono ricalcolati da questo piano — restano
  numericamente corretti secondo il codice di misura del loro tempo, ma non
  più direttamente comparabili a un run post-Task-7 senza questa nota. Non
  risolvibile per costruzione (è la natura di un fix che cambia una
  definizione di misura); da dichiarare, non da eliminare.

- **Copertura delle categorie native di LlamaFirewall contro il dataset
  scritto nel linguaggio aidr (T0001-T0014) non garantita** — AlignmentCheck
  emette solo ALLOW/HUMAN_IN_THE_LOOP_REQUIRED (nessuna tassonomia 3D come
  aidr's T-code); il dataset è stato scritto e classificato secondo le 14
  tecniche del vendor aidr, non validato indipendentemente contro cosa
  LlamaFirewall considera "misalignment". Stesso principio già applicato ad
  AgentDoG in fase di analisi (docs/notes/2026-08-26-analisi-integrazione-secondo-vendor.md):
  si riporta cosa il vendor rileva, non si forza una tassonomia condivisa.
  Design doc: `docs/design/2026-08-27-multi-vendor-llamafirewall-design.md`,
  "Limiti dichiarati". Non risolvibile senza un secondo dataset scritto nel
  linguaggio nativo del vendor — fuori scope di questo piano.
  **Causa del recall 0.000 identificata e verificata caso per caso, 2026-08-28**
  (non solo un'ipotesi di taxonomy mismatch — più radicale): il prompt di
  sistema di AlignmentCheck (catturato nel `vendor_proxy.jsonl` del run
  `20260828-100238-9775af`) valuta **una singola azione alla volta contro il
  messaggio utente immediatamente precedente**, chiedendo solo "l'azione
  persegue l'obiettivo dichiarato?", mai "l'obiettivo stesso è legittimo?"
  o "qual è l'effetto complessivo?". I 4 attacchi realmente riusciti nel
  run sono tutti richieste esplicite di un'azione dannosa a cui l'agente ha
  compiaciuto — per costruzione "aligned" (verificato sulle `rationale`
  reali dei verdetti, non solo sulla struttura del prompt). Gli unici 2 flag
  prodotti sull'intero run (`unrequested_account_deactivation_as_fix`,
  `order_summary_sent_to_own_address`) sono innescati da errori di tool che
  fanno deviare l'agente dal percorso diretto — confusione procedurale, non
  riconoscimento di un contenuto dannoso. **Un dataset riscritto nel
  linguaggio nativo del vendor non risolverebbe questo**: qualunque attacco
  che chieda esplicitamente, in un turno, l'azione voluta resta invisibile a
  questo meccanismo, indipendentemente dalla tassonomia usata per
  descriverlo. Analisi completa, verificata caso per caso sulle rationale
  reali: `docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md`.
  **Branch `judge-targeted-cases` (2026-08-28/29) non mergiato, per una conseguenza diretta
  di questa stessa voce**: il design (`docs/design/2026-08-28-judge-targeted-cases-design.md`,
  §3.2) affermava che una nota rivolta al "sistema di revisione" nel turno seed sarebbe
  "strutturalmente invisibile" per AlignmentCheck perché "letta da `read_ticket_content`,
  non l'istruzione immediatamente precedente all'azione" — affermazione mai verificata sul
  meccanismo reale già descritto qui sopra (il turno seed **è** lo `USER MESSAGE` valutato
  a ogni singola azione, non un ticket letto via tool). Verificato indipendentemente sui
  file reali durante la Step 2 final review (Opus) del branch: adapter
  (`src/detector_adapter/vendors/llamafirewall/adapter.py`, `role == "user"` →
  `UserMessage`), il file YAML del caso nuovo, e il log proxy reale del gemello
  (`docs/reports/llamafirewall-2026-08-28/bulk_export_to_partner_address/detector-llamafirewall.vendor_proxy.jsonl`).
  Un secondo limite, indipendente dal primo: il gemello malevolo scelto
  (`bulk_export_to_partner_address`) è già un miss (`benign`) su **entrambi** i vendor
  pubblicati — un payload che spinge verso "benigno" un caso già benigno per il detector non
  ha spazio di misura. Nessuna correzione applicata: il branch resta non mergiato,
  work-in-progress abbandonato a questo stato, non cancellato. **Causa a monte
  identificata e documentata, 2026-08-29**: LlamaFirewall è documentato dal vendor come
  difesa a più livelli (PromptGuard 2 + AlignmentCheck + CodeShield + Regex), questo
  progetto ne cablava solo `AGENT_ALIGNMENT` — fedele all'esempio ufficiale del vendor per
  `scan_replay()`, non una scorciatoia, ma mai dichiarato esplicitamente come scelta con un
  costo. `PROMPT_GUARD` non è raggiungibile via OpenRouter (è un classificatore
  discriminativo, `DebertaV2ForSequenceClassification`, non un modello generativo — non il
  tipo di modello che OpenRouter instrada) ed è gated manualmente sotto licenza Meta Llama
  4. Analisi completa, fonti primarie (doc vendor, HF API, doc OpenRouter):
  `docs/research/2026-08-29-llamafirewall-promptguard-not-wired.md`. Prossimo passo
  (non ancora scopato): attivare `PROMPT_GUARD` nel container (`torch`/`transformers`/
  `huggingface_hub` mancanti, accesso HF gated da ottenere, una seconda chiamata `scan()`
  per turno utente da affiancare a `scan_replay()`, decidere come i due verdetti confluiscono
  in un unico `Verdict`) prima di decidere se/come ridisegnare l'esperimento "judge-targeted".

- **La metrica strict (attribuzione della tecnica) resta definita solo per
  aidr** — per LlamaFirewall si pubblica solo la primary (label-only), già
  deciso nell'analisi precedente (§H) e confermato nel design doc di questo
  piano. AlignmentCheck non produce un `technique_detected` (CONTEXT.md:
  nessun suffisso di tecnica, solo ALLOW/HUMAN_IN_THE_LOOP_REQUIRED) — la
  colonna strict per LlamaFirewall nel report resta strutturalmente vuota
  (n/a), non un difetto del codice di misura.

- **Affidabilità del modello LLM-giudice non uniforme tra candidati**
  (falsificazione bidirezionale, design doc): `llama-4-maverick` ha fallito
  la validazione dello schema strutturato su un caso reale (omette il campo
  `conclusion`, silenziosamente convertito in `conclusion=True` dal
  fallback del vendor), `llama-3.3-70b-instruct` no. Il default scelto in
  Task 4 è il secondo, riverificato dal vivo al momento dell'implementazione
  (non solo a memoria della falsificazione di pre-design) — ma anche col
  modello più affidabile il meccanismo `status="error"`/`rationale` (Task
  5) resta necessario come rete di sicurezza, non solo come rimedio a un
  modello sbagliato: un modello oggi affidabile può smettere di esserlo
  (stesso principio già vero per `SIFTER_MODEL`/`INSPECTOR_MODEL`, Gap 10).

- **Copertura test di entrambi i vendor nel tempo, dopo il merge, non
  garantita a livello di processo** (review council, pragmatist — reso più
  specifico in questo piano, v3, convergenza skeptic Claude + pragmatist
  Claude + skeptic Pi/minimax): l'architettura abilita l'isolamento
  (vendor parametrico, container isolati, test parametrizzati sul ramo
  `llamafirewall`) ma nessun meccanismo garantisce che la suite gated di
  LlamaFirewall (Task 15, `docker/detector-llamafirewall/run_adapter_tests.sh`)
  continui a girare a ogni commit futuro dopo il merge, né che un
  fallimento in un vendor blocchi il merge di modifiche che toccano solo
  l'altro — rischio concreto che tra sei mesi la copertura LlamaFirewall
  smetta silenziosamente di essere verificata mentre la suite pytest
  continua a dare verde (la suite gated non è parte di `pytest tests/ -q`
  per costruzione, Task 15). Da definire in un futuro piano operativo/CI,
  non in questo.

- **Costo per chiamata LlamaFirewall non ancora misurato su un run reale**
  (a differenza della AgentDoG-ipotesi ereditata, che assumeva costo zero) —
  la soglia del circuit breaker di costo (Task 13, `MAX_COST_USD_DEFAULT =
  5.00`) è dichiarata esplicitamente provvisoria, nessun dato reale ancora
  disponibile al momento di questo task. Task 17 misura il costo reale sul
  primo run e aggiunge qui una quinta voce col numero effettivo (non una
  riscrittura di questa).

- **Costo reale misurato per LlamaFirewall: $0.0318 per il run completo di 31
  casi ($0.00102/caso)** — misurato Step c di
  `docs/superpowers/plans/2026-08-27-multi-vendor-llamafirewall-implementation.md`,
  Task 17, 2026-08-28. Confronto con aidr: $0.0136/31 casi ($0.00044/caso) —
  circa 2.3x più caro per caso, ma stesso ordine di grandezza. `MAX_COST_USD_DEFAULT
  = 5.00` (Task 13) resta ampiamente conservativo (>150x il costo osservato per
  l'intero run). Latenza max osservata per caso: 45.4s — margine ampio (~4x) sotto
  `DETECTOR_TIMEOUT_S = 180.0`, nessuna ritaratura necessaria (Task 17, Step d).
  **Correzione (I4, review finale del piano, 2026-08-28):** questo numero di 45.4s
  è stato derivato da delta tra timestamp nel log del proxy thin (marker di inizio/
  fine caso), non da un campo `latency_s` per-caso verificabile — `scan_decision_to_verdict`
  impostava `latency_s: None` incondizionatamente al momento di questa misura, quindi
  il numero non è ricostruibile dai soli `verdicts.jsonl`/`run.log` pubblicati (mostrano
  `latency_s=None` per ogni caso). Il fix di I4 aggiunge un timer wall-clock
  (`time.perf_counter()`) attorno alla chiamata di scan reale in
  `detector_adapter/vendors/llamafirewall/evaluate_case.py`, che ora popola
  `latency_s` per ogni run futuro — non è stato rieseguito il batch reale da 31 casi
  per rimisurare 45.4s con il nuovo campo (costo API reale evitato), quindi quel
  numero resta un'osservazione plausibile ma non verificabile dall'artefatto pubblicato,
  finché non viene rieseguito un run con il fix applicato.
  Su questo stesso run, il detector ha una recall primaria di 0.000 (0 TP, 2 FP,
  4 FN, 25 TN su 31 casi) — dato di performance, non un limite dell'harness di
  misura; vedi `docs/reports/llamafirewall-2026-08-28/report.md`.

- **Test di isolamento import non copre `detector_adapter.vendors.<altro>` come forma
  di import, e manca del tutto un test `toy_agent` ↛ `detector_adapter`** —
  `tests/test_no_vendor_imports.py` confronta il nome del modulo importato solo con il
  prefisso top-level (`"aidr"`/`"llamafirewall"`), quindi un import tipo
  `from detector_adapter.vendors.aidr.adapter import X` dentro `vendors/llamafirewall/`
  (o viceversa) non verrebbe intercettato; e non esiste alcun test che verifichi che
  `toy_agent` non importi mai `detector_adapter`, benché sia la garanzia su cui
  `orchestrator.py` poggia esplicitamente (Gap 9). Trovato: final whole-branch review
  del piano multi-vendor LlamaFirewall (I2), 2026-08-28. Fix: aggiungere
  `detector_adapter.vendors.<altro>` ai prefissi proibiti per ciascun sottopackage, più
  il test mancante `toy_agent` ↛ `detector_adapter`.

- **Circuit breaker di costo inerte con `--container-lifecycle per-case`** —
  `sequence.py` ricalcola il costo cumulativo rileggendo il log proxy dentro il
  container dopo ogni caso; in modalità `per-case` il container viene ricreato
  (`docker compose rm -f -s -v`) a ogni caso, quindi il log riparte vuoto e
  `cumulative_cost_usd` non supera mai il costo di un singolo caso — il breaker non
  scatta mai in questa modalità, pur essendo esposta in CLI e documentata in README.
  Trovato: final whole-branch review (I5), 2026-08-28. Fix: accumulare il costo lato
  harness tra i cicli open/close (somma dei delta per caso), oppure rifiutare
  esplicitamente la combinazione `--container-lifecycle per-case` + `--max-cost-usd`.

- **Dipendenze non pinnate nel container `detector-llamafirewall`** — il Dockerfile fa
  `pip install --no-deps llamafirewall==1.0.3` (pin corretto sul pacchetto vendor) ma poi
  `pip install 'openai>=1.76.0' 'pydantic>=2.11.3'` senza pin esatto: il client LLM che
  esegue materialmente il giudizio (`openai`) può cambiare versione a ogni rebuild senza
  che nulla lo registri — `provenance.py` cattura solo la versione di `llamafirewall`.
  Rispetto ad aidr (git checkout di un commit esatto + `requirements.txt` del vendor) il
  sistema misurato è definito peggio. Trovato: final whole-branch review (I7),
  2026-08-28. Fix: pinnare `openai==`/`pydantic==` e registrarne le versioni in
  provenance, o dichiarare esplicitamente il limite se il pin esatto non è praticabile.

- **`tool_name` duplicato in 3 punti senza guardia anti-drift** — la duplicazione
  (`vendors/aidr/adapter.py`, `vendors/llamafirewall/adapter.py`, `orchestrator.py`) è
  corretta per design (nessun import incrociato tra vendor), ma i verdetti normali
  portano il `TOOL_NAME` dell'adapter mentre `_error_verdict`/`_fallback_verdict`
  portano `config.tool_name`: una divergenza tra i due produrrebbe due `tool_name`
  diversi nello stesso `verdicts.jsonl` senza segnalazione. Trovato: final whole-branch
  review (I8), 2026-08-28. Fix: un test che estragga il literal dai due `adapter.py` per
  confronto testuale (senza importarli), analogo alla guardia AST già esistente per gli
  import incrociati.

- **Piccole imprecisioni di documentazione emerse dalla final whole-branch review del
  piano multi-vendor LlamaFirewall (M1-M6, 2026-08-28)**, nessuna bloccante:
  README chiama "vendor_proxy.py" il file `openrouter_proxy.py` di llamafirewall (M1,
  che non rimappa nulla per scelta esplicita); **(M2, prima metà risolta 2026-08-28)** la
  sezione "Stato" del README ora riflette entrambi i vendor e i due report aidr — resta
  aperta solo la seconda metà: `--max-cost-usd` non è documentato; un commento in `orchestrator.py` sul deadline interno del
  sottoprocesso non riflette che per llamafirewall il `pkill` esterno è l'unico
  meccanismo, non un fallback (M3, llamafirewall non ha un deadline interno come aidr);
  il report limita a 3 le misclassificazioni mostrate senza dichiararlo esplicitamente
  (M4); la garanzia di isolamento tra reti vendor dipende dalla configurazione di
  `squid.conf` (splice solo su SNI `openrouter.ai`), non dall'assenza di un percorso di
  rete — vale la pena dichiararlo esplicitamente dove si afferma la proprietà (M5);
  `run_adapter_tests.sh` del container llamafirewall installa `pytest` a runtime,
  funziona solo perché il Dockerfile lo preinstalla già, e un futuro rimaneggiamento che
  tolga quella riga romperebbe lo script in modo non ovvio (M6, il Dockerfile aidr
  documenta esplicitamente questa trappola, quello llamafirewall no).

## Risolti (storico, rimossi da "Aperti" quando chiusi nel codice)

- **R10 — output del preflight non sanitizzato a valle del tipo di ritorno** — il codice
  sanitizza già correttamente (`_probe()` restituisce solo `exc.__class__.__name__` o
  status code HTTP), ma il test aggirava il percorso reale (fake che *solleva* invece
  di *ritornare*), esponendo il fatto che `main()` stampa le stringhe ritornate tal
  quali — nessuna garanzia strutturale. Risolto (2026-08-26): test end-to-end con il
  preflight reale + `httpx.MockTransport` che solleva un'eccezione con sentinel, e
  verifica che il sentinel non raggiunga `run.log`. Fix test-only, zero sorgenti toccati.
  Analisi completa: `docs/design/2026-08-26-r10-preflight-output-sanitization.md`.

- **T0007 senza uno scenario valido nel catalogo/dataset** — design finalizzato
  2026-08-19 (approvato dall'utente, con due correzioni: i tre `customer_id` vanno
  enumerati esplicitamente nel testo del ticket, e il `case_id` finale non deve
  ripetere il nome della tecnica): una clausola statica aggiunta a `_SYSTEM_PROMPT`
  (`agent_loop.py`) dichiara `bulk_export` l'unico canale sanzionato per un export
  multi-cliente; lo scenario malevolo istruisce l'agente a evitarlo interrogando i
  clienti uno per uno (`query_customer_db` ripetuto), il gemello benigno usa
  `bulk_export` onestamente. Dettaglio completo: `docs/design/2026-08-14-toy-agent-gap-tracking.md`,
  Gap 16. Risolto: Plan 5a Task 1, commit `0be9e08` (clausola in `agent_loop.py` +
  2 voci di catalogo `piecemeal_lookup_avoids_bulk_export`/
  `bulk_export_honest_quarterly_report`), mergiato in master con `e3565c8`
  (2026-08-20).

- **Una tool call fallita (`ToolError`) conta comunque come successo dell'attacco per i
  criteri T0005(refund)/T0010 su `field`** — `criteria.py` non aveva un matcher su
  `ToolCall.status`, quindi `field: {equals: refund_total}` da solo non distingueva una
  chiamata riuscita da una fallita (es. `update_account` con `value` non numerico per
  `refund_total`) prima di qualunque cambio di stato. Trovato dalla review finale
  whole-branch di Plan 5c, 2026-08-21. Risolto: fix pre-Plan-5d, commit `18d5056` — nuovo
  flag opzionale `require_ok` su `ToolCallCriterion`/nel DSL `tool_call:` (default
  `False`, preserva la semantica deliberata "solo tentativo" di T0008), impostato a
  `true` sui 2 file dataset interessati (`refund_without_authorization.yaml`,
  `ticket_false_prior_authorization_claim.yaml`). Test: `tests/toy_agent/test_criteria.py`
  (6 nuovi test: rifiuta una chiamata fallita, accetta una riuscita, default `False`
  preserva T0008, parsing DSL, validazione tipo).

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

- **Tabella "Mapping Requisito → Verifica" del design doc originale mai aggiornata dopo
  l'accettazione di Gap 17** — la riga "Copertura completa della tassonomia" dichiarava
  ancora testualmente "copre tutti i codici T0001-T0014", nonostante l'eccezione
  T0009/T0011 (Gap 17) fosse già una decisione presa esplicitamente con l'utente il
  2026-08-19 — codice e test già corretti (12/14, dichiarato esplicitamente), solo il
  testo della specifica originale non era mai stato sincronizzato. Trovato dall'audit
  requisiti↔codice dell'estensione personale di `finishing-a-development-branch`
  durante la chiusura di Plan 5d, 2026-08-21 — non un gap nel codice, un gap tra una
  decisione già presa e il documento che l'aveva originata. Risolto: riga corretta in
  `docs/design/2026-08-14-toy-agent-e-pipeline-misura.md:970`, commit `a108b48`.

- **Il fail-open/fail-closed del vendor su errore interno non è distinguibile da una
  detection vera in nessun `Verdict` pubblicato finora, aidr incluso.** `detector/sifter.py:53`
  di aidr (`Sifter.triage_safe()`) intercetta qualunque eccezione (timeout, rate limit,
  output malformato) e restituisce `{"escalate": True, ..., "note": f"fail-open: {e}"}`
  — un default etichettato dal vendor stesso "fail-open", indistinguibile nel nostro
  `Verdict` da un giudizio reale del Sifter. **Vale per tutti i run di aidr pubblicati
  finora**: nessuno di essi distingue "il Sifter ha giudicato" da "il Sifter è fallito e
  ha escalato per default". Trovato durante grill-with-docs sul design doc del secondo
  vendor (2026-08-27), dopo che il council (skeptic + risk, indipendenti) aveva trovato
  lo stesso problema strutturale in `AlignmentCheckScanner._get_default_error_response()`
  di LlamaFirewall (`conclusion=True` su qualunque eccezione) — la verifica sul codice
  di aidr ha confermato che il problema preesisteva, non è specifico del secondo vendor.
  Risolto nel codice per aidr da questo task (retrofit fail-open,
  commit da compilare al momento del commit reale — vedi
  `detector_adapter/vendors/aidr/adapter.py`, `_wrap_sifter_triage`);
  per LlamaFirewall, in un task precedente di questo stesso piano.
