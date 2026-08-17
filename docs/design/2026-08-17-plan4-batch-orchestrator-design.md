# Design: Plan 4 — batch driver e orchestrazione del run (risoluzione Gap 6)

Status: brainstorming, council checkpoint e grill-with-docs completati (esiti in fondo
al documento). Prossimo passo: spec self-review, poi review finale dell'utente prima di
scrivere il piano di implementazione.

## Obiettivo

Costruire il componente che manca perché Gap 6 (`docs/design/2026-08-14-toy-agent-gap-tracking.md`)
sia davvero chiuso: nessun pezzo esistente oggi fa girare l'intero dataset di `TestCase`
attraverso la pipeline `agent`/`detector` già costruita da Gap 9, raccoglie le prove esterne,
persiste i dati grezzi e produce il report finale. `orchestrator.run_test_case()` (già
costruito ed eseguito, Gap 9) fa girare un solo `TestCase` alla volta; `metrics.compute_metrics()`
e `report.render_report()` (Plan 2, già mergiati) assumono `list[TestCase]`/`list[Verdict]`
già pronte. Questo design copre il pezzo di composizione tra i due — nessuna logica di
misura nuova, solo orchestrazione (stesso principio già dichiarato per Gap 6 nel design
doc principale).

**Spec/contesto vincolante**: `docs/design/2026-08-14-toy-agent-e-pipeline-misura.md`
(sezioni "Confine misuratore/misurato", "Meccanismo di handoff: orchestratore esterno",
"Orchestrazione del run (risoluzione Gap 6)", "Modulo metriche", "Report"),
`docs/design/2026-08-14-toy-agent-gap-tracking.md` (Gap 6, Gap 9), `SPIRIT.md` (principi 2,
3, 4, 6).

## Stato del codice verificato prima di questo design (2026-08-17)

- `src/toy_agent/orchestrator.py::run_test_case(test_case: dict, ...) -> dict` — fa girare
  UN `TestCase` end-to-end (`docker compose exec agent`/`detector`, JSON su stdin/stdout),
  ritorna `{"transcript": dict|None, "verdict": dict}`. Distingue già `error_kind`
  `"infra"`/`"application"`. **Importante**: `test_case` viene serializzato per intero e
  spedito sullo stdin di `agent` — `agent`'s `run_case.py::_extract_scenario()` legge solo
  `case_id` e `transcript.turns[0].content` (un solo seed turn, `role: "user"`), ignorando
  qualunque altro campo presente nel dict, ma non impedisce che altri campi vi transitino.
- `src/toy_agent/state.py::fresh_state()` — reset per invocazione (Gap 5), già usato
  internamente da `run_case.py` lato `agent`, nessuna azione richiesta da questo design.
- `src/toy_agent/evidence.py::collect_case_evidence(case_id, services, evidence_dir, ...)`
  e `collect_thin_proxy_log(case_id, evidence_dir, api_key, ...)` — canali di prova esterna
  già costruiti, operano per singolo `case_id`.
- `src/toy_agent/metrics.py::compute_metrics(cases: list[TestCase], verdicts: list[Verdict]) -> MetricsResult`
  e `src/toy_agent/report.py::render_report(cases, verdicts, metrics, tool_name, setup_notes) -> str`
  — già completi (Plan 2), operano su dataclass, non su dict.
- `src/toy_agent/schema.py` — `TestCase.transcript: Transcript` non è `Optional` (diventa
  `Optional[Transcript]` con questo piano, decisione 4 rivista dopo council checkpoint).
  `Verdict` non ha campi `in_tokens`/`out_tokens` (presenti solo nel dict prodotto da
  `detector_adapter.adapter.detection_result_to_verdict`, mai nello schema dataclass).
- **Difetto preesistente, trovato durante il council checkpoint (2026-08-17)**:
  `src/toy_agent/evidence.py::_container_id()` fa
  `output.decode().strip().splitlines()[0]` sull'output di `docker compose ps -q
  <service>` — solleva `IndexError` non gestito se l'output è vuoto (container/servizio
  irraggiungibile). Scenario plausibile proprio quando l'infrastruttura è instabile, cioè
  proprio quando il circuit breaker (decisione 8) sta per scattare: se questo crash arriva
  prima che il breaker conti il terzo fallimento, l'intero processo `run_batch.py` muore
  senza produrre `report.md`, contraddicendo la garanzia della decisione 8. Il bug è
  preesistente in `evidence.py`, non introdotto da questo piano, ma reso raggiungibile per
  la prima volta da un loop non presidiato — va corretto come parte del piano di
  implementazione di Plan 4.
- **Non esiste alcuna funzione dict→dataclass** per `Transcript`/`Verdict` in `toy_agent`
  oggi — solo la direzione opposta (`run_case.py::transcript_to_dict`).
- Nessuna directory `datasets/` esiste ancora (Plan 5 non iniziato). `pyproject.toml` non
  ha `pyyaml` tra le dipendenze.

## Decisioni prese in brainstorming (2026-08-17, con l'utente)

### 1. Formato ed entry del dataset

Un oggetto per `case_id` (non due file paralleli): `case_id`, `label`, `technique_target`,
`rationale`, più lo scenario da eseguire. Un file YAML per `case_id` (coerente col plurale
"i file YAML dei TestCase" già usato nel design doc principale, sezione "Report").

**Scoperta emersa durante il brainstorming, non richiede nuovo tipo**: lo schema
`TestCase` già esistente (case_id, transcript, label, technique_target, rationale) è
sufficiente a rappresentare l'entry pre-esecuzione senza modifiche — lo "scenario" è
semplicemente `transcript` popolato con un solo `Turn(role="user", ...)` di seed, la
stessa forma già attesa da `run_case.py::_extract_scenario()`. L'entry YAML su disco
(prodotta da Plan 5, non ancora costruito) è quindi un `TestCase` serializzato nella sua
forma "non ancora eseguita" (`transcript.turns` = `[seed]`). Il batch loop ne produce un
secondo, post-esecuzione, con lo stesso ground truth ma il transcript osservato reale al
posto del seed.

### 2. Isolamento del ground truth verso `agent`

Il batch loop non passa mai a `run_test_case()` l'intero `TestCase` caricato da disco.
Costruisce invece un dict ridotto — solo `case_id` e il contenuto del seed turn — prima
di ogni chiamata. `label`/`technique_target`/`rationale` restano esclusivamente in memoria
nel processo host, ricombinati con il transcript osservato solo dopo l'esecuzione.

**Perché** (decisione esplicita, non implicita nel codice esistente): `run_test_case()`
oggi serializza per intero qualunque dict gli venga passato sullo stdin di `agent`. Anche
se `run_case.py` ignora oggi i campi di ground truth, nulla lo garantisce in futuro (un
cambio a `run_case.py`, un debug log che stampa lo stdin ricevuto) — un agente che sa,
anche solo potenzialmente, di essere in un caso etichettato "malicious" invaliderebbe la
misura (SPIRIT.md principio 2, "metodologia dichiarata prima dei risultati": la rationale
è scritta prima di eseguire il detector, ma l'agente stesso non deve mai poter reagire a
un'etichetta che non dovrebbe conoscere). Difesa in profondità a costo marginale nullo:
non richiede toccare `run_test_case()` o `run_case.py`, solo cosa il batch loop costruisce
prima di chiamarli.

### 3. Conversione dict → dataclass (nuovo modulo)

`src/toy_agent/serialization.py` — `transcript_from_dict(d: dict) -> Transcript` e
`verdict_from_dict(d: dict) -> Verdict`, simmetriche a `run_case.py::transcript_to_dict`
già esistente. `verdict_from_dict` ignora silenziosamente le chiavi extra `in_tokens`/
`out_tokens` (non parte dello schema `Verdict` — restano comunque nei dati grezzi
persistiti su disco, punto 6 sotto, mai perse, solo assenti dalla dataclass in memoria).

### 4. Transcript mancante (`run_test_case()` ritorna `transcript: None`)

**Rivista dopo council checkpoint (2026-08-17)**. La versione originale usava un
placeholder a un solo turno per non toccare lo schema; il council (council-skeptic) ha
segnalato che questo è un "convention over structure" smell — l'invariante "questa
esecuzione non è reale" vive solo nella disciplina di chi consuma i dati (controllare
`Verdict.status == "error"` prima di leggere `case.transcript`), non nel type system.

Decisione rivista: `TestCase.transcript` diventa `Optional[Transcript] = None` in
`schema.py`. Quando l'invocazione di `agent` fallisce prima di produrre un transcript, il
`TestCase` finale per quel `case_id` viene costruito con `transcript=None`, nessun
placeholder fittizio.

Verificato prima di adottare la revisione che questo cambio non ha ripercussioni sul
codice già mergiato (Plan 2): `metrics.compute_metrics()` non accede mai a
`case.transcript`; `report.py` lo fa solo in `_format_transcript_excerpt`, dietro un
filtro che già esclude `status == "error"` (`_find_misclassified_cases`, riga 48) — quindi
`case.transcript` non è mai `None` nei punti in cui viene letto oggi. Il `Verdict`
associato ha già `status: "error"`, che esclude il caso da TP/FP/FN/TN e dalla sezione
"Casi concreti" del report.

### 5. Timing della raccolta prove esterne

`evidence.collect_case_evidence()` e `collect_thin_proxy_log()` vengono chiamate subito
dopo che `run_test_case()` ritorna per quel `case_id`, prima di passare al caso successivo
— non a fine batch. Non è una nuova decisione: è quanto il design doc principale già
richiede esplicitamente ("docker diff/stats devono... essere presi immediatamente dopo la
relativa invocazione e prima della successiva", mapping Requisito→Verifica, Gap 9). Viene
eseguita indipendentemente dall'esito di `run_test_case()` (successo o errore) — un caso
fallito è spesso il caso più interessante da poter diagnosticare con le prove esterne.

### 6. Persistenza dei dati grezzi

Scritta immediatamente dopo ogni caso, non accumulata in memoria e scritta un colpo solo
a fine batch — se il circuit breaker (punto 8) interrompe il batch a metà, i risultati dei
casi già eseguiti restano comunque salvati e ispezionabili.

- Il `verdict` dict grezzo (incluse `in_tokens`/`out_tokens`) viene appeso come una riga a
  `verdicts.jsonl` nella directory di output del run — corrisponde a "un file dei Verdict"
  già citato nel design doc principale, sezione "Report".
- Il `transcript` dict grezzo (quando non `None`) viene scritto in
  `raw/<case_id>.transcript.json`.

### 7. `cost_usd` fuori scope per questo piano

`Verdict.cost_usd` resta `None` anche dopo Plan 4 — nessuna tabella di pricing per
Sifter/Inspector/Embedding viene costruita qui. `in_tokens`/`out_tokens` restano comunque
nei dati grezzi persistiti (punto 6), quindi il calcolo resta possibile in un piano futuro
senza dover riaprire l'orchestratore o rieseguire il batch. **Limite dichiarato
esplicitamente** (SPIRIT.md principio 3): il report finale di Fase 1 non include un costo
in dollari per caso, solo il conteggio token grezzo nei dati pubblicati.

### 8. Circuit breaker su fallimenti infrastrutturali consecutivi

Il batch loop non salta mai silenziosamente un `case_id` per un singolo fallimento (Gap 6,
già richiesto dal design doc principale) — ma se `agent`/`detector` risultano del tutto
irraggiungibili (non un caso avversariale, un guasto strutturale, es. Docker daemon giù),
continuare a tentare tutti i 40-60 casi brucerebbe il timeout di ciascuno per un risultato
comunque inutilizzabile. Il loop conta i `Verdict` consecutivi con `error_kind: "infra"`;
al terzo consecutivo, il batch si ferma (nessun altro caso tentato). Un `Verdict` con
`error_kind: "application"` o un `Verdict` `ok` azzera il contatore. La soglia (3) è una
scelta pratica, non derivata da un vincolo del design doc principale — modificabile in
fase di piano se si rivela sbagliata.

**Report su circuit breaker trip**: il batch produce comunque `compute_metrics()` +
`render_report()` sui casi completati fino al trip (mai scartati, per il punto 6). Il
parametro `setup_notes` di `render_report()` porta una nota esplicita che include sia il
conteggio (`M/T casi eseguiti prima dell'interruzione`) sia il `rationale` diagnostico
degli ultimi fallimenti infra che hanno fatto scattare il breaker (già popolato da
`_error_verdict()` in `orchestrator.py`, es. "docker compose exec failed to start...",
"agent invocation exceeded 120.0s wall-clock timeout") — un lettore del report vede subito
sia che il batch è incompleto sia perché, senza dover scavare in `verdicts.jsonl`.

**Precondizione aggiunta dopo council checkpoint (2026-08-17)**: la raccolta prove
chiamata subito dopo ogni caso (decisione 5) deve essere resa a prova del difetto
preesistente in `evidence.py::_container_id()` (vedi «Stato del codice verificato»)
prima che questo piano sia dichiarato concluso — altrimenti la garanzia "il batch produce
comunque un report sui casi completati fino al trip" non è affidabile proprio nello
scenario (infrastruttura instabile) per cui il circuit breaker esiste. Discusso
esplicitamente con l'utente il taglio dell'intero circuit breaker (proposto dal
council-pragmatist) — confermato invariato: soglia 3 fallimenti `infra` consecutivi. Un
tetto sui fallimenti infra non-consecutivi (gap segnalato da council-risk: un pattern
intermittente non fa mai scattare il breaker) resta un limite dichiarato ma non
implementato in questo piano, stessa categoria della soglia 3 — "scelta pratica,
modificabile in futuro se si rivela sbagliata".

### 9. Punto di ingresso

Un unico comando end-to-end: `python -m toy_agent.run_batch <dataset_dir> <run_output_dir>`.
Esegue in sequenza: caricamento dataset YAML → loop per-caso (punti 2-8) → `compute_metrics()`
→ `render_report()` → scrittura di `report.md` in `run_output_dir`. Non ci sono comandi
separati "esegui" / "genera report" in questo piano — dato che i dati grezzi sono comunque
persistiti per-caso (punto 6), rigenerare un report dagli stessi dati grezzi resta possibile
in futuro come funzione richiamabile separatamente, anche se oggi non esposta come comando
CLI a sé.

### 10. Layout di output

- `dataset_dir` (input, Plan 5 — es. `datasets/fase1/`) **non viene mai scritto** da
  `run_batch.py`. I file YAML del ground truth restano stabili tra un run e l'altro; il
  transcript osservato varia da run a run (chiamata a un LLM live) e non deve mai
  sovrascrivere il file di ground truth che lo ha generato.
- `run_output_dir` (es. `docs/reports/2026-XX-XX-aidr-audit/`, coerente con la convenzione
  di percorso del report già dichiarata nel design doc principale) contiene:
  `verdicts.jsonl`, `raw/<case_id>.transcript.json`, l'albero di prove esterne già prodotto
  da `evidence.collect_case_evidence`/`collect_thin_proxy_log` (una sottodirectory per
  `case_id`, struttura già definita da `evidence.py`), e `report.md`.

### 11. Nuova dipendenza

`pyyaml` — non presente oggi in `pyproject.toml`. Necessaria per leggere le entry del
dataset (punto 1). **Uso esplicito, aggiunto dopo council checkpoint (2026-08-17)**:
`yaml.safe_load`, mai `yaml.load` — i file YAML del dataset contengono per costruzione
payload avversariali (seed turn di prompt injection nel campo `transcript`), quindi vanno
trattati come dati semi-esterni anche se scritti dal team (council-risk).

### 12. Validazione `case_id` (aggiunta dopo council checkpoint, 2026-08-17)

Prima di caricare il dataset, ogni `case_id` viene validato contro un allowlist esplicito
(es. `^[a-zA-Z0-9_-]+$`) — nessun carattere di path (`/`, `\`, `..`) né spazi. **Perché**:
`evidence.collect_case_evidence()` costruisce `case_dir = evidence_dir / case_id` senza
alcuna validazione oggi; un `case_id` malformato potrebbe causare scritture fuori
`run_output_dir` (path traversal) o, sulla macchina di sviluppo Windows (filesystem
case-insensitive di default), una collisione silenziosa tra due `case_id` che differiscono
solo per maiuscole/minuscole, corrompendo l'attribuzione per-caso delle prove esterne
(council-risk). Costo marginale: una regex al caricamento del dataset.

### 13. Parametri operazionali nel report (aggiunta dopo council checkpoint, 2026-08-17)

`render_report()` viene chiamato con un `setup_notes` che include, oltre al conteggio M/T
e al rationale diagnostico già previsti dalla decisione 8, i parametri operazionali
effettivi usati per il run: `agent_timeout_s`, `detector_timeout_s`, soglia del circuit
breaker. **Perché**: senza questi valori nel report, chi lo legge non ha modo di giudicare
se un run è riproducibile o di distinguere risultati ottenuti con parametri diversi tra un
run e l'altro (council-advocate). Collocazione: parte 3 della struttura report già definita
nel design doc principale ("Metodologia e limiti dichiarati") — non una nuova sezione.

## Testing

- `run_batch.py`: test dell'orchestrazione del loop con un `run_test_case` finto e un
  collector di prove finto (stesso stile di `tests/toy_agent/test_orchestrator.py`, che già
  finge `run_command`) — nessun Docker reale richiesto per testare la logica del loop
  (circuit breaker, isolamento ground truth, persistenza per-caso, fallback transcript).
- `serialization.py`: round-trip `dict → dataclass → dict` testato direttamente.
- Verifica end-to-end contro lo stack reale: fuori scope per i test automatici (stessa
  scelta già fatta per `verify_sourcelens.py`, Gap 4 — verificato manualmente una volta),
  ma il piano di implementazione deve includere un passo di verifica manuale con un
  dataset minimo (2-3 casi reali) contro `agent`/`detector` reali prima di dichiarare
  Plan 4 concluso.

## Mapping Requisito → Verifica

| Requisito | Verifica |
|---|---|
| Il ground truth (`label`/`technique_target`/`rationale`) non deve mai transitare nel JSON inviato ad `agent` | Test: ispezionare il dict passato a `run_test_case()` dal batch loop per un caso con ground truth noto, verificare che contenga solo `case_id` e il seed turn, nessuna chiave `label`/`technique_target`/`rationale` |
| Nessun `case_id` del dataset deve mai essere assente dall'output finale (`list[TestCase]`/`list[Verdict]` passate a `compute_metrics`), anche su fallimento (Gap 6) | Test: eseguire un batch con un caso che fa fallire `run_test_case()` e verificare che il `case_id` compaia comunque in entrambe le liste finali |
| `run_batch.py` deve interrompersi dopo 3 fallimenti `error_kind: "infra"` consecutivi, senza tentare i casi residui | Test: simulare 3 `Verdict` infra consecutivi e verificare che il loop non chiami `run_test_case()` per il caso successivo |
| Un `Verdict` non-infra (application o ok) deve azzerare il contatore del circuit breaker | Test: sequenza infra, infra, ok, infra, infra — verificare che il batch non si interrompa (il contatore è tornato a 2, non 4) |
| I dati grezzi (`verdict`, `transcript`) di un caso devono essere persistiti su disco subito dopo la sua esecuzione, non solo a fine batch | Test: interrompere l'esecuzione a metà batch (es. eccezione forzata dopo il caso N) e verificare che `verdicts.jsonl`/`raw/` contengano comunque le entry dei primi N casi |
| Un report generato dopo un trip del circuit breaker deve dichiarare esplicitamente quanti casi sono stati eseguiti e perché si è interrotto | Test: forzare un trip e verificare che il `report.md` prodotto contenga sia il conteggio M/T sia il testo del `rationale` diagnostico dell'ultimo fallimento infra |
| `dataset_dir` non deve mai essere modificato da un'esecuzione di `run_batch.py` | Test: calcolare un hash dei file in `dataset_dir` prima e dopo un run completo, verificare che siano identici |
| `Verdict.cost_usd` resta `None` in ogni `Verdict` prodotto da questo piano, `in_tokens`/`out_tokens` restano nei dati grezzi persistiti | Test: ispezionare `verdicts.jsonl` dopo un run, verificare che ogni riga abbia `cost_usd: null` e `in_tokens`/`out_tokens` non nulli quando lo status è `ok` |
| Un `case_id` che non rispetta l'allowlist non deve mai arrivare a costruire un percorso su disco (decisione 12) | Test: caricare un dataset con un `case_id` contenente `/` o `..` e verificare che il caricamento fallisca esplicitamente, prima di qualunque scrittura |
| Il codice che legge i file YAML del dataset deve usare `yaml.safe_load`, mai `yaml.load` (decisione 11) | Check statico: `rg "yaml\.load\("` su `src/toy_agent` non deve trovare occorrenze prive di `Loader=yaml.SafeLoader` esplicito |
| La raccolta prove non deve far crashare l'intero batch se `docker compose ps -q` ritorna output vuoto | Test: forzare `_container_id()` a ricevere output vuoto e verificare che il batch continui (o registri un fallimento per il singolo caso) invece di sollevare un'eccezione non gestita che interrompe `run_batch.py` |
| Il report finale deve dichiarare i parametri operazionali (timeout agent/detector, soglia circuit breaker) usati per il run (decisione 13) | Test: ispezionare `report.md` prodotto e verificare che `setup_notes` contenga i tre valori |
| Un `TestCase` con `transcript=None` (fallimento agent, decisione 4 rivista) non deve mai causare un errore nella generazione del report | Test: eseguire `render_report()` con un caso `transcript=None`/`Verdict.status="error"` tra gli input e verificare che non sollevi eccezioni e non compaia nella sezione "Casi concreti" |

## Esito council checkpoint (2026-08-17)

Roster completo (`council-skeptic`, `council-risk`, `council-pragmatist`,
`council-advocate`), scope pieno (documento intero + `docs/design/2026-08-14-toy-agent-e-pipeline-misura.md`
+ `docs/design/2026-08-14-toy-agent-gap-tracking.md` + `SPIRIT.md` + codice reale citato
nella sezione "Stato del codice verificato", letti per intero da ogni agente).

- **Nessuna** delle 8 verifiche originariamente proposte nel mapping Requisito→Verifica è
  stata contestata dal council — tutte confermate invariate.
- Il council ha trovato 4 gap non coperti da alcuna riga del mapping esistente, ora tutti
  aggiunti (decisioni 12, 13, e le due nuove righe di verifica su `evidence.py`/
  `yaml.safe_load` in questa tabella).
- La decisione 4 (transcript mancante) è stata **rivista in modo sostanziale** — da
  placeholder a `Optional[Transcript]` — in seguito al finding di council-skeptic.
- La decisione 8 (circuit breaker) è stata **discussa esplicitamente** con l'utente dopo
  un disaccordo tra council-pragmatist (proponeva di tagliarla come robustezza
  speculativa non richiesta da Gap 6) e gli altri tre membri — confermata invariata, con
  l'aggiunta obbligatoria del fix di `evidence.py::_container_id()` come precondizione.
- Council-pragmatist ha proposto di tagliare anche le decisioni 2 (isolamento ground
  truth) e 6 (persistenza granulare per-caso), giudicandole robustezza speculativa.
  Entrambe **mantenute invariate**, in disaccordo esplicito con quel parere: lo split
  container di Gap 9 protegge un confine diverso (detector/infra) da quello che la
  decisione 2 indirizza (l'agente sotto misura che vede la propria etichetta via stdin);
  la decisione 6 è indipendentemente giustificata dal difetto trovato in `evidence.py`
  (un crash a metà batch, non solo un trip del circuit breaker, perderebbe tutti i
  risultati se la persistenza fosse spostata a fine batch).

**`grill-with-docs`**: eseguito il 2026-08-17, incrociando questo design (dopo i findings
del council) con `docs/design/2026-08-14-toy-agent-gap-tracking.md` e la sezione
"Orchestrazione del run" del design doc principale. Un punto di peso trovato: la
sezione "Gap 6" del gap-tracking doc dichiarava la risoluzione originaria "pura
composizione, nessuna decisione architetturale da sottoporre a un council dedicato" —
smentito nei fatti da questo stesso design (13 decisioni, council dedicato completo,
un bug reale trovato, una decisione rivista in modo sostanziale). Corretto con una nota
datata in `gap-tracking.md` (Gap 6) e un rimando esplicito nella sezione "Orchestrazione
del run" del design doc principale, che descriveva ancora l'orchestratore come un
componente unico invece dello split `orchestrator.py`/`run_batch.py` effettivo. Due
rifiniture minori aggiunte insieme: il vincolo `case_id` (decisione 12) reso esplicito
come eredità per Plan 5; la collocazione dei parametri operazionali nel report
(decisione 13) agganciata alla parte 3 della struttura report già definita nel design
doc principale. Nessun altro branch di peso trovato.

## Fuori scope per questo piano (dichiarato esplicitamente)

- Calcolo di `cost_usd` da `in_tokens`/`out_tokens` (punto 7) — rimandato a un piano futuro.
- Comando CLI separato per rigenerare solo il report da dati grezzi già persistiti (punto 9)
  — la funzione resta chiamabile separatamente, solo non esposta come comando oggi.
- Costruzione del dataset reale di `TestCase` (Plan 5) — questo piano deve funzionare anche
  con un dataset minimo/stub, non dipende dal contenuto reale dei casi. **Vincolo che Plan 5
  eredita da questo design** (decisione 12): ogni `case_id` scritto nel dataset deve
  rispettare l'allowlist `^[a-zA-Z0-9_-]+$` — non una scelta libera per chi scriverà i file
  YAML del dataset.
