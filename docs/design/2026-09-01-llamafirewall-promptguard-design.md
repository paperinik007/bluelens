# Design: attivare PromptGuard in LlamaFirewall (secondo scanner, verdetto combinato)

## Perché

`docs/research/2026-08-29-llamafirewall-promptguard-not-wired.md` ha stabilito che
questo progetto cabla solo AlignmentCheck di LlamaFirewall, non i quattro componenti
che il vendor documenta come "layered defense" (PromptGuard 2, AlignmentCheck,
CodeShield, Regex). Non è una scorciatoia — l'integrazione replica fedelmente
l'esempio ufficiale del vendor per `scan_replay()` — ma nessun documento aveva
registrato *perché* PromptGuard fosse rimasto fuori, né cosa servisse per aggiungerlo.
Quel research doc ha chiuso le domande fattuali (modello 86M, non 22M — dataset
italiano, il 22M non ha pretraining multilingue; due chiamate `scan_replay()`
separate, non una `Configuration` combinata — il short-circuit del vendor
sopprimerebbe la seconda scansione) e lasciato aperta solo la domanda di design:
come si fondono due verdetti scanner indipendenti in un unico `Verdict` per lo schema
di questo progetto. Questo documento decide quella domanda, e a implementazione
avvenuta chiude (per rimozione, convenzione del registro) il paragrafo "Prossimo
passo (non ancora scopato): attivare PROMPT_GUARD nel container..." dentro la voce
"Copertura delle categorie native di LlamaFirewall..." di
`docs/design/registro-limiti-aperti.md`.

Obiettivo di questa fase, deciso con l'utente in brainstorming (2026-09-01): misura
ampia — PromptGuard misurato su tutti e 31 i casi del dataset esistente, accanto ad
AlignmentCheck, non un test mirato sui payload del branch abbandonato
`judge-targeted-cases`. La decisione se riaprire quel branch resta esplicitamente
fuori scope, da prendere solo dopo aver visto dati reali di PromptGuard.

## Scope

Dentro:
- Il container `detector-llamafirewall` esegue due scanner (AlignmentCheck +
  PromptGuard) sullo stesso transcript e pubblica **un solo** `Verdict` per caso,
  come già avviene per la pipeline interna multi-stadio di aidr (Dredge→Sifter→
  Inspector→Gauntlet → un solo `DetectionResult` → un solo `Verdict`,
  `detector_adapter/vendors/aidr/adapter.py:68`).
- Un **nuovo** vendor CLI (`--vendor llamafirewall-combined`, nuova voce in
  `VENDOR_DETECTOR_CONFIG`), `tool_name="llamafirewall-combined"` — il vendor
  esistente `llamafirewall-alignmentcheck` non viene toccato, rinominato né
  modificato. Decisione corretta durante `/grill-with-docs` (2026-09-01): il
  glossario del progetto (`CONTEXT.md`, "Nomi di tool risolti") dichiara già,
  scritto prima di questa sessione, che "un futuro audit di uno di quegli altri
  scanner avrebbe un `tool_name` diverso" — un audit combinato è anch'esso un
  "tool" a sé nel senso di `CONTEXT.md` ("il prodotto specifico misurato... che
  determina un set distinto di numeri nel report"), non una ridefinizione di
  quello che già esiste. Nessuna rottura di comparabilità da dichiarare:
  `docs/reports/llamafirewall-2026-08-28/` resta valido e comparabile per sempre
  come misura di solo AlignmentCheck.
- Build del container: dipendenze `torch`/`transformers`/`huggingface_hub`, modello
  scaricato una volta al build (non a runtime).
- Un secondo canale di evidenza per le decisioni di PromptGuard (non passa dal proxy
  OpenRouter, quindi non lascia traccia nel meccanismo di evidenza esistente).

Fuori scope: riaprire `judge-targeted-cases`; CodeShield/Regex (nessuna motivazione
per attivarli, non toccati da questo lavoro); un refactor del cablaggio agente↔
detector per riusare transcript tra run di vendor diversi (Approccio C scartato in
brainstorming — corretto ma non specifico di PromptGuard, voce a parte in
`registro-limiti-aperti.md`).

## Falsificazione pre-design

Il design regge su un'affermazione empirica su codice di terzi
(`huggingface_hub`/`promptguard_utils.py`, vendor): "il modello si scarica una volta
al build (con token HF come build secret) e da quel momento ogni container parte
senza rete né token, leggendo dalla cache locale dentro l'immagine". È la premessa
diretta della scelta "bake al build" richiesta esplicitamente dall'utente
("l'importante è che il tempo sia minimo e che non scarichiamo inutilmente le stesse
cose... riutilizziamo").

| Assunzione | Esperimento | Risultato | Impatto sul design |
|---|---|---|---|
| `huggingface_hub.get_token()` legge `HF_TOKEN` da env var (non solo da un file di login interattivo) | Eseguito contro il pacchetto reale installato localmente (`huggingface_hub==1.27.0`): `inspect.getsource` su `get_token()` e su `_get_token_from_environment()` | Confermato: `_get_token_from_environment()` ritorna `os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")`, controllato prima del file di login | Un token passato come build secret ed esportato come `HF_TOKEN` per il `RUN` che istanzia `PromptGuard()` viene trovato senza richiedere `login()` interattivo — la premessa del build secret regge |
| `promptguard_utils.PromptGuard._load_model_and_tokenizer` carica dalla cache locale senza rete se `model_path` esiste già | Lettura diretta del codice vendor (non eseguita: nessun download gated reale disponibile in questa sessione) — logica: `if not os.path.exists(model_path): download+save_pretrained else: load locale`, nessuna chiamata di rete nel ramo else | Verificato per lettura, non per esecuzione — la logica è un controllo locale su filesystem, non un comportamento opaco di libreria di terzi che potrebbe sorprendere | Il "bake" regge in linea di codice; resta non verificato con un download gated reale (nessun token disponibile in questa sessione) — verificarlo è il primo passo di implementazione (Task 0), non un'assunzione da cui il design possa ancora deviare |

Metà dell'assunzione (scoperta del token) è verificata per esecuzione contro il
pacchetto reale, non solo per lettura di documentazione. L'altra metà (comportamento
di cache del vendor) resta verificata solo per lettura — non richiede credenziali
reali per essere falsificata a fondo, quindi il Task 0 dell'implementazione deve farlo
con un vero `docker build` prima di considerare il resto del piano eseguibile.

## Review del council (2026-09-01, non vincolante)

Roster completo (skeptic, pragmatist, risk, advocate), scope pieno, dispatchato via
Pi — verificato di persona che tutti e 4 hanno letto il file reale (citano righe e
funzioni non presenti nel brief di dispatch), non solo il riepilogo dato in
contesto. File canonici: `temp/2026-09-01-council-{skeptic,pragmatist,risk,advocate}-llamafirewall-promptguard-design.md`.

**Difetto di correttezza reale, verificato riga per riga (risk, finding #2)**:
`scan_replay()` usato per PromptGuard avrebbe reso il punteggio non-bloccante
riportato quasi sempre 0.0 per un artefatto del meccanismo di aggregazione del
vendor, non per assenza di segnale — corretto (vedi sezione "Architettura / Data
flow" sotto), non solo annotato come limite.

**Accolto, corretto nel testo**: la scelta OR+max non eredita legittimità dal
precedente aidr (skeptic) — la forma sì, il contenuto no; `technique_detected`
resta `None` anche quando flagga PromptGuard, va dichiarato esplicitamente
(skeptic); distinzione testuale tra fail-open vendor e guasto di dipendenza locale
nel `rationale` di un Verdict d'errore (skeptic).

**Scartato con motivazione**: `previous_tool_name` nel Verdict (skeptic) — YAGNI,
concordo con pragmatist, la discontinuità resta tracciata da commit e
`registro-limiti-aperti.md`.

**Verificato e corretto/ridimensionato**: "tokenizer overflow = errore sistematico"
(risk, finding #3) è falso — il vendor tronca già silenziosamente
(`truncation=True, max_length=512`); il limite reale è il troncamento silenzioso
oltre 512 token, non un rischio di crash. "Disclosure risk" del nuovo log grezzo
(risk, finding #4) è sovrastimato — stesso testo già pubblicato oggi nei transcript
grezzi esistenti, nessuna nuova superficie. "Leak del token via `docker history`"
(risk, finding #5) descrive un meccanismo impreciso (BuildKit non registra
stdout/stderr dei `RUN` in `docker history`), ma la categoria di rischio
sottostante (il token stampato nel log di build stesso) è reale — aggiunta
verifica a Task 0.

**Non bloccante, da non perdere nel piano canonico** (advocate): una nota di
methodology nel report futuro che dichiari esplicitamente "questo Verdict fonde
AlignmentCheck+PromptGuard", e una convenzione di naming per la directory del
report che lo renda visibile senza leggere il codice.

## Architettura / Data flow

**Correzione post-council (2026-09-01, risk finding #2, verificato riga per riga su
`llamafirewall.py:108-211`)**: la versione iniziale di questo documento usava
`firewall.scan_replay({Role.USER: [PROMPT_GUARD]})` anche per PromptGuard, per
simmetria con AlignmentCheck. È sbagliato. `scan_replay()` sovrascrive il proprio
risultato a ogni messaggio della trace (`llamafirewall.py:202-210`); un messaggio il
cui ruolo non ha scanner configurato ritorna un `ScanResult(ALLOW, score=0.0)` di
default (`scan()`, righe 113-140, `decisions={}` → `ALLOW`/`0.0`) che **sovrascrive**
il punteggio reale di un turno precedente. Un vero BLOCK interrompe subito il loop ed
è preservato correttamente — la misura primaria (PromptGuard flagga o no) non è
compromessa — ma nel caso non bloccante lo `score` finale riflette solo l'ultimo
messaggio scansionato, che per costruzione è quasi sempre un turno assistente/tool
(l'ultimo turno di un transcript non è mai un turno utente, tranne casi degeneri),
non il vero punteggio massimo osservato sui turni utente. Con `confidence =
max(score_ac, score_pg)`, questo avrebbe reso `score_pg` quasi sempre 0.0 per
costruzione — l'opposto del "materiale per analizzare il perché" richiesto in
brainstorming.

**Correzione**: PromptGuard non passa da `scan_replay()`. L'adapter invoca lo
scanner direttamente e aggrega da solo:

```
orchestrator.py (vendor = "llamafirewall-combined", da --vendor)
  → docker compose exec -T detector-llamafirewall
      python -m detector_adapter.vendors.llamafirewall.evaluate_case_combined
  → stdin: transcript JSON (formato invariato)
  → adapter:
      trace = transcript_dict_to_trace(data)          # invariato
      t0 = perf_counter(); ac_result = LlamaFirewall({Role.ASSISTANT: [TOOL_NAME]})
                                          .scan_replay(trace); ac_latency = perf_counter()-t0

      # PromptGuard: invocazione diretta dello scanner, non scan_replay() (vedi
      # correzione sopra) — loop nostro sui turni Role.USER, aggregazione nostra
      t0 = perf_counter()
      pg_scanner = create_scanner(ScannerType.PROMPT_GUARD)
      pg_turn_results = []
      for ix, msg in enumerate(trace):
          if msg.role == Role.USER:
              past = trace[:ix] or None
              pg_turn_results.append(asyncio.run(pg_scanner.scan(msg, past)))
              # ogni pg_turn_results[-1] scritto anche nel log grezzo, sezione 5
      pg_decision = ScanDecision.BLOCK if any(r.decision == ScanDecision.BLOCK
                                               for r in pg_turn_results) else ScanDecision.ALLOW
      pg_score = max((r.score for r in pg_turn_results), default=0.0)
      pg_latency = perf_counter() - t0
      # entrambe sempre eseguite — nessun short-circuit tra le due (vedi "Perché
      # non copiamo l'arbitrato dal vivo del vendor" sotto)
      verdict = combine_scan_results_to_verdict(case_id, ac_result,
                                                 pg_decision, pg_score, pg_turn_results,
                                                 ac_latency, pg_latency)
  → stdout: un solo Verdict JSON (tool_name="llamafirewall-combined", schema invariato)
  → evidence.collect_thin_proxy_log × 2: proxy OpenRouter (AlignmentCheck) +
    nuovo log locale (PromptGuard, scritto dall'adapter da `pg_turn_results`,
    non dedotto da `scan_replay()`) — stessa funzione, due path diversi
```

**Limite pre-esistente scoperto in questa verifica, non introdotto da questo
design**: la stessa aggregazione "l'ultimo messaggio vince" di `scan_replay()`
si applica anche all'integrazione AlignmentCheck già pubblicata
(`Configuration={Role.ASSISTANT: [...]}`) — se l'ultimo turno di un transcript non
è una risposta naturale dell'agente ma un turno "tool" (es. il caso
`basic_login_diagnostic_check`, "max turns reached", già segnalato come anomalia in
`registro-limiti-aperti.md`), lo `score` di AlignmentCheck riportato potrebbe non
riflettere l'ultimo vero turno assistente scansionato. Non risolto qui (fuori scope
di questa attivazione di PromptGuard, tocca l'integrazione AlignmentCheck già
pubblicata) — registrato come nuovo limite in `registro-limiti-aperti.md`.

**Perché non copiamo l'arbitrato dal vivo del vendor**: in un deployment reale,
`scan_replay()` con una `Configuration` combinata fa short-circuit — se PromptGuard
blocca il primo turno utente, AlignmentCheck non viene mai invocato sui turni
successivi, perché l'interazione si fermerebbe lì. Questo progetto misura un
transcript già completo, generato da un agente che ha già finito di girare — non
c'è nessuna interazione da fermare in tempo reale. Eseguire sempre entrambe le
scansioni, indipendentemente, è la scelta corretta per uno strumento di misura
retrospettivo: il contrario introdurrebbe una dipendenza artificiale dall'ordine dei
turni nella trace, mai vista da nessun deployment reale di questo tipo (l'agente ha
già risposto per intero prima che qualunque detector venga invocato).

## Componenti

**Corretto durante `/grill-with-docs`**: nessun file esistente del percorso
`llamafirewall-alignmentcheck` viene modificato — `evaluate_case.py`/`adapter.py`
esistenti restano intatti, quel `tool_name` continua a pubblicare solo il verdetto
AlignmentCheck. La fusione vive in **nuovi** file, sotto lo stesso pacchetto
vendor (stesso container `detector-llamafirewall`, stessa immagine con PromptGuard
baked al build):

- `detector_adapter/vendors/llamafirewall/evaluate_case_combined.py` (nuovo file):
  orchestratrice delle due chiamate (AlignmentCheck via `scan_replay()`, PromptGuard
  via invocazione diretta dello scanner, vedi sezione "Architettura / Data flow"),
  stesso contratto esterno delle altre `evaluate_case*.py` (stdin transcript →
  stdout un Verdict).
- `detector_adapter/vendors/llamafirewall/adapter.py` (esteso, non riscritto): nuova
  funzione `combine_scan_results_to_verdict(case_id, ac_result, pg_decision,
  pg_score, pg_turn_results, ac_latency_s, pg_latency_s) -> dict`, aggiunta accanto
  a — non al posto di — `scan_decision_to_verdict` esistente, che resta in uso da
  `evaluate_case.py` invariato. `OpenRouterAlignmentCheck` invariata. `ScannerType.PROMPT_GUARD`
  è uno scanner off-the-shelf del vendor (`PromptGuardScanner`, `block_threshold=0.9`
  default, tenuto così — nessuna motivazione empirica per ritararlo, stesso
  trattamento già dato al default `gpt-4o-mini` non motivato in
  `registro-limiti-aperti.md`), nessun wrapper OpenRouter necessario perché non fa
  chiamate di rete.
- `toy_agent/orchestrator.py::VENDOR_DETECTOR_CONFIG`: **nuova voce**
  `"llamafirewall-combined"` (chiave CLI per `--vendor`), `service="detector-llamafirewall"`
  (stesso container, riusato), `module="detector_adapter.vendors.llamafirewall.evaluate_case_combined"`,
  `tool_name="llamafirewall-combined"`. La voce esistente `"llamafirewall"`
  (`tool_name="llamafirewall-alignmentcheck"`) resta identica, non toccata.
  Aggiunto un campo opzionale `secondary_log_path: str | None` al dataclass
  `VendorDetectorConfig`, valorizzato a `/var/log/llamafirewall_promptguard_raw.jsonl`
  per la nuova voce `"llamafirewall-combined"`, `None` per aidr e per la voce
  esistente `"llamafirewall"` (nessun cambiamento al comportamento di nessuna delle
  due).
- `toy_agent/sequence.py`: dopo la chiamata esistente a `collect_thin_proxy_log` per
  `config.proxy_log_path`, una seconda chiamata alla stessa funzione se
  `config.secondary_log_path` non è `None` — stessa funzione riusata, zero utility
  nuove.
- `docker/detector-llamafirewall/Dockerfile`: nuove dipendenze CPU-only
  (`torch`, `transformers`, `huggingface_hub`) e uno step di pre-download del
  modello.

Nessun cambiamento a `metrics.py`, `report.py`, `schema.py` — il contratto "un
detector, un Verdict per caso" resta identico a oggi.

## Combinazione del Verdict

Le due scale sono comparabili nel range e nella direzione, verificato leggendo il
codice vendor, non assunto: `AlignmentCheckScanner._convert_llm_response_to_score`
ritorna `1.0` se `conclusion` è vero, `0.0` altrimenti
(`experimental/alignmentcheck_scanner.py:120-125`); `PromptGuardScanner.scan`
ritorna un punteggio continuo `[0,1]` dalla softmax del classificatore
(`promptguard_utils.py::get_jailbreak_score`). Stessa direzione (più alto = più
sospetto), stesso range — un `max()` tra i due è ben definito, non un confronto tra
mele e pere.

**Precisazione post-council (skeptic, verificato)**: il precedente aidr
(`detector_adapter/vendors/aidr/adapter.py:68`) giustifica *che* un solo Verdict
per caso sia la forma giusta — aidr stesso è una pipeline interna a stati
(Dredge→Sifter→Inspector→Gauntlet, ogni stadio consuma l'output del precedente),
e questo progetto legge solo la decisione finale già presa dal vendor. Qui la
situazione è diversa: AlignmentCheck e PromptGuard sono due modelli indipendenti
che il vendor stesso non combina in un'unica decisione quando registrati su ruoli
diversi (nessun arbitrato cross-role, verificato in `docs/research/2026-08-29-
llamafirewall-promptguard-not-wired.md` §4b-4c) — l'OR sul `label` e il `max` sulla
`confidence` sono una policy di fusione **nostra**, senza precedente vendor da
cui ereditare legittimità. Resta la scelta giusta per le ragioni già discusse (
replica il fail-safe di un prodotto a più livelli, evita di scegliere
arbitrariamente tra le 3 policy meno giustificate proposte in fase di ricerca), ma
va giudicata sui propri meriti, non sul precedente aidr, che vale solo per la forma
("un Verdict"), non per il contenuto della fusione. Resta inoltre un limite di
granularità dichiarato: AlignmentCheck contribuisce un segnale binario (`0.0`/`1.0`),
PromptGuard un segnale continuo — il `max()` è ben definito ma i due addendi non
hanno la stessa risoluzione informativa.

- **`label`**: `"malicious"` se **almeno una** delle due decisioni è positiva
  (AlignmentCheck `HUMAN_IN_THE_LOOP_REQUIRED` o PromptGuard `BLOCK`, score
  `>= 0.9`), altrimenti `"benign"`. OR logico — replica il comportamento
  fail-safe reale di un prodotto con più livelli di difesa; policy nostra, non
  ereditata dal vendor né legittimata dal precedente aidr (vedi "Precisazione
  post-council" sopra — quel precedente vale solo per la forma "un Verdict",
  non per questo contenuto specifico).
- **`confidence`**: `max(score_alignmentcheck, score_promptguard)` — simmetrico con
  l'OR sul label, sempre ben definito anche nel caso benigno (nessuno dei due
  ambiguamente "decisivo").
- **`rationale`**: concatenazione testuale etichettata, sempre entrambe le metà
  anche quando una è il semplice esito "nessuna injection rilevata" — es.
  `"AlignmentCheck: <reason> | PromptGuard: <reason>"`. È il materiale per
  analizzare il *perché* di un verdetto, richiesto esplicitamente in
  brainstorming, dentro il Verdict pubblicato stesso, non solo nel log grezzo.
- **`cost_usd`**: resta `None` — invariato rispetto a oggi (nessuno dei due
  scanner popola un costo reale; PromptGuard è inferenza locale, nessun costo per
  chiamata).
- **`latency_s`**: somma delle due chiamate cronometrate separatamente — tempo
  reale wall-clock speso per produrre quel singolo Verdict.
- **`technique_detected`**: resta `None` per costruzione, invariato —
  `supports_technique_attribution=False` non cambia. Dichiarato esplicitamente
  (skeptic, difetto di completezza minore): resta `None` anche quando **PromptGuard**
  flagga, non solo quando flagga AlignmentCheck — PromptGuard è un classificatore
  binario injection/no-injection, non attribuisce nessuna tecnica per costruzione,
  indipendentemente da quale dei due scanner ha determinato il `label`.

## Gestione errori

Se una delle due `scan_replay()` solleva un'eccezione (es. `torch`/`transformers`
fallisce — OOM, tokenizer su input malformato), l'intero Verdict del caso diventa
`status="error"`, `label=None` — stesso trattamento già in uso per il fail-open di
AlignmentCheck (`fail_open_verdict`, `adapter.py:132-151`) e per il retrofit di aidr
(`registro-limiti-aperti.md`, "Il retrofit fail-open di aidr..."). Deliberatamente
**non** si pubblica un Verdict basato solo sullo scanner sopravvissuto: farlo
gonfierebbe silenziosamente la copertura misurata di LlamaFirewall su un caso in cui
solo metà del prodotto ha risposto — esattamente il difetto "self-reported" che
SPIRIT.md principio 6 chiede di evitare nel misuratore stesso ("un misuratore che
dichiara di essere imparziale ma non è verificabile da terzi ricade esattamente nel
difetto 'self-reported' che questo progetto contesta ai vendor"), corretta durante
`/grill-with-docs`: il documento originale citava "principio 3", che nel testo
reale di `SPIRIT.md` è "Onestà statistica" su campioni piccoli, non questo. Il
`rationale` del Verdict d'errore riporta
quale dei due scanner ha fallito (`__class__.__name__` dell'eccezione, mai testo raw,
vincolo permanente già in uso).

Un'eccezione non intercettata (proxy irraggiungibile per AlignmentCheck, crash del
processo Python) resta gestita dal meccanismo generico già esistente in
`orchestrator.py::run_test_case` (`_error_verdict`, "application"/"infra") — nessun
cambiamento lì.

**Precisazione post-council (skeptic)**: "stesso trattamento del fail-open vendor"
copre correttamente un fallimento del *modello remoto* di AlignmentCheck (rate
limit, 4xx/5xx, schema non rispettato — la stessa classe già gestita da
`fail_open_verdict`), ma un'eccezione di PromptGuard (OOM di `torch`, tokenizer su
input anomalo) è una categoria diversa: un guasto della **nostra dipendenza
locale**, non un fail-open del vendor remoto. Il trattamento del Verdict è
identico (`status="error"`, `label=None` — un errore di misura è un errore di
misura, la distinzione non cambia se il caso entra o meno in TP/FP/FN/TN), ma il
`rationale` deve dichiarare la distinzione in chiaro (`"vendor fail-open: ..."` per
AlignmentCheck, `"local dependency error: <ClassName>"` per PromptGuard) — così un
lettore che analizza `error_count` può distinguere un problema del vendor remoto da
un problema della nostra immagine, senza introdurre nessun campo di schema nuovo.

## Container e build

`docker/detector-llamafirewall/Dockerfile` aggiunge, dopo l'installazione esistente
di `llamafirewall`:

```dockerfile
# syntax=docker/dockerfile:1
...
RUN pip install --no-cache-dir torch transformers huggingface_hub  # CPU-only, +250-350MB immagine (stima Pi, da verificare col build reale)
ENV HF_HOME=/opt/hf-cache
RUN --mount=type=secret,id=hf_token \
    HF_TOKEN=$(cat /run/secrets/hf_token) python -c \
    "from llamafirewall.scanners.promptguard_utils import PromptGuard; PromptGuard()"
```

Il token non finisce mai in un layer permanente (BuildKit secret, montato solo
per la durata di quel `RUN`). `HF_HOME` è un `ENV` del Dockerfile (persiste nel
container finale, non solo nella shell del singolo `RUN`) cosi il codice vendor
(`promptguard_utils.py::_load_model_and_tokenizer`, che legge `os.environ["HF_HOME"]`)
trova la cache già popolata a ogni avvio futuro del container, senza rete né token.

Limite dichiarato: il loader del vendor non fissa una revisione HF esplicita
(`from_pretrained(model_name)`, nessun `revision=`) — il build di oggi fissa
qualunque revisione sia `main` in quel momento, non un hash pinnato nel commit. Una
volta baked nell'immagine resta fisso per tutta la vita di quell'immagine, ma un
rebuild futuro potrebbe silenziosamente prendere una revisione diversa — stesso
tipo di rischio già accettato per `SIFTER_MODEL`/`INSPECTOR_MODEL` (Gap 10).

## Logging/evidenza

`OpenRouterAlignmentCheck`/il proxy locale già scrivono `/var/log/llamafirewall_proxy.jsonl`,
raccolto oggi da `evidence.collect_thin_proxy_log`. PromptGuard non passa da lì (nessuna
chiamata di rete) — con l'invocazione diretta dello scanner (sezione "Architettura /
Data flow", corretta post-council), l'adapter ha già accesso a ogni `pg_turn_results[i]`
per turno utente scansionato, e scrive una riga JSONL per ciascuno in
`/var/log/llamafirewall_promptguard_raw.jsonl` (testo scansionato, score, soglia,
decisione) — non più dedotto dal `ScanResult` aggregato di `scan_replay()` (che non
lo permetterebbe comunque, essendo il bug appena corretto). `sequence.py` la
raccoglie con la stessa `collect_thin_proxy_log` già esistente, verso
`<run_dir>/<case_id>/detector-llamafirewall.promptguard_raw.jsonl` — nessuna nuova
funzione di raccolta.

**Valutato in council (risk, finding #4) e non accolto come rischio nuovo**: il
testo del turno scansionato finisce in questo nuovo log senza redazione (il
meccanismo di scrubbing di `collect_thin_proxy_log` sostituisce solo l'api key,
inapplicabile qui perché PromptGuard non ne usa una). Non è una nuova superficie di
esposizione: lo stesso testo, incluso quello dei casi malevoli, è già pubblicato
oggi per ogni caso nel transcript grezzo esistente (`raw/<case_id>.transcript.json`,
`sequence.py:226`) — questo è un dataset sintetico scritto dal progetto stesso per
testare i detector, non dati reali di terzi. La duplicazione è ridondante, non
rischiosa.

## Nuovo `tool_name`, non una rinomina (corretto durante `/grill-with-docs`)

Versione iniziale di questo documento: rinominare `llamafirewall-alignmentcheck` in
`llamafirewall`, dichiarando una rottura di comparabilità (stesso trattamento del
retrofit fail-open di aidr). **Scartata dopo aver controllato `CONTEXT.md`**, il
glossario del progetto, che dichiara già — scritto prima di questa sessione —
che "un futuro audit di uno di quegli altri scanner avrebbe un `tool_name`
diverso", proprio per non dover mai rompere la comparabilità di un tool già
pubblicato quando se ne aggiunge un altro dello stesso pacchetto vendor.

Il verdetto combinato diventa un **terzo tool**, `tool_name="llamafirewall-combined"`,
non una ridefinizione di `llamafirewall-alignmentcheck`. Nessuna rottura da
dichiarare: `docs/reports/llamafirewall-2026-08-28/` (misura solo AlignmentCheck)
resta valido e comparabile per sempre, esattamente come prima di questo lavoro. Un
futuro run di `--vendor llamafirewall-combined` produce un report a sé, sotto un
nome proprio, con la propria sezione "Methodology" che dichiara di misurare
AlignmentCheck+PromptGuard fusi (vedi "Limiti dichiarati" più sotto, nota advocate).

## Requisito → Verifica

| Requisito | Verifica eseguibile |
|---|---|
| `label` è `malicious` se almeno uno dei due scanner flagga (mai solo se entrambi) | test unitario su `combine_scan_results_to_verdict`: caso con solo AlignmentCheck positivo → malicious; solo PromptGuard positivo → malicious; nessuno dei due → benign |
| Il punteggio di PromptGuard riportato riflette il vero massimo sui turni utente, non l'ultimo messaggio della trace (bug `scan_replay()` corretto post-council) | test unitario: trace con un turno utente a score alto seguito da più turni assistente/tool → `pg_score` aggregato ancora alto, non azzerato dai turni successivi |
| `confidence` è il massimo dei due score, mai una scelta condizionale ambigua | test unitario: `max(0.3, 0.7) == 0.7` anche quando nessuno dei due supera la propria soglia di blocco (caso benigno con confidence non nulla) |
| `rationale` contiene sempre entrambe le metà, anche quando una è "nessuna injection rilevata" | test unitario: asserire che entrambe le sotto-stringhe etichettate compaiano nel `rationale` |
| Un'eccezione in una delle due scansioni produce `status="error"/label=None`, mai un Verdict basato su un solo scanner sopravvissuto | test unitario: forzare un'eccezione nella chiamata PromptGuard con AlignmentCheck che risponde normalmente, e viceversa; entrambi i casi verificano `Verdict(status="error", label=None)` |
| Il modello PromptGuard è caricabile senza rete/token dopo il build (bake, non runtime-download) | script gated (`run_adapter_tests.sh`), build reale dell'immagine seguito da un container senza `HF_TOKEN` in ambiente e senza rete esterna abilitata |
| `HF_TOKEN` passato come build secret non finisce in nessun layer permanente dell'immagine | `docker history <image>` ispezionato manualmente durante l'implementazione (Task 0), nessun test automatico permanente — verifica una tantum al momento del build, coerente con la natura del rischio (un secret leak si previene per costruzione BuildKit, non si testa a runtime) |
| Il routing harness (`--vendor llamafirewall-combined`) usa `tool_name="llamafirewall-combined"`; `--vendor llamafirewall` continua a usare `tool_name="llamafirewall-alignmentcheck"`, invariato | test parametrizzato su `test_orchestrator.py` per entrambe le voci |
| Il secondo canale di log (PromptGuard) viene raccolto per ogni caso quando configurato, non quando assente (aidr e `llamafirewall` esistente) | test su `test_sequence.py`: `secondary_log_path=None` non produce nessuna seconda chiamata a `collect_thin_proxy_log` |

## Test — cosa e perché

1. **`combine_scan_results_to_verdict`** (funzione pura, duck-typed su oggetti
   `ScanResult` fittizi): unica logica nuova nel punto più a rischio di errore
   silenzioso — è qui che un bug produrrebbe un `label`/`confidence` sbagliato senza
   che nessun test di integrazione lo scopra facilmente. Nessuna dipendenza da
   `llamafirewall`/`torch` installati, gira nella suite principale.
2. **Gestione errori combinata**: forzare un'eccezione in uno dei due rami,
   verificare che l'intero Verdict diventi errore — è il punto dove un bug
   produrrebbe silenziosamente una misura di copertura gonfiata.
3. **`VendorDetectorConfig.secondary_log_path`**: parametrizzato su
   `test_sequence.py`, garanzia che aidr resti invariato (nessuna seconda
   raccolta quando il campo è `None`).
4. **`run_adapter_tests.sh` gated**: unico punto che verifica contro il vero
   `PromptGuardScanner`/modello reale — dove la dipendenza pesante è installata.
   Stessa convenzione già in uso, stesso limite già registrato (non gira in CI,
   `registro-limiti-aperti.md`, "Copertura test di entrambi i vendor nel tempo").

Non serve un test su `report.py`/`metrics.py`: restano vendor-agnostici, invariati
da questo lavoro.

## Limiti dichiarati (da registrare in `registro-limiti-aperti.md` a integrazione
avvenuta)

- **`scan_replay()` chiama PromptGuard una volta per ogni turno utente nella
  trace, non una volta per caso** — su una sequenza composta con più turni utente
  il tempo totale si somma. Le stime di Pi (500-1500ms per chiamata su CPU, 86M)
  suggeriscono margine ampio sotto `DETECTOR_TIMEOUT_S=180s`, ma non è stato
  misurato su un run reale — verificare nel primo run (stesso trattamento già dato
  al costo/latenza di LlamaFirewall, Task 17 del piano precedente).
- **Revisione HF non pinnata esplicitamente** nel loader del vendor — vedi sezione
  "Container e build" sopra.
- **Metà della falsificazione pre-design non verificata per esecuzione** (il
  comportamento di cache di `promptguard_utils.py` con un vero download gated) —
  vedi sezione "Falsificazione pre-design"; da chiudere al Task 0
  dell'implementazione con un build reale, prima di considerare eseguibile il resto
  del piano.
- **Soglia di blocco di PromptGuard (`block_threshold=0.9`) è il default del
  vendor, non ritarata su questo dataset** — stesso trattamento già dato al
  default `gpt-4o-mini` non motivato (`registro-limiti-aperti.md`).
- **Bug pre-esistente in `scan_replay()` scoperto durante questa verifica,
  applicabile all'integrazione AlignmentCheck già pubblicata** — vedi sezione
  "Architettura / Data flow": se l'ultimo turno di un transcript non è una
  risposta naturale dell'agente (es. "max turns reached" su un turno tool), lo
  `score` di AlignmentCheck riportato può non riflettere l'ultimo vero turno
  assistente scansionato. Non risolto in questo lavoro (fuori scope, tocca
  un'integrazione già pubblicata) — da valutare separatamente.
- **PromptGuard tronca silenziosamente input oltre 512 token** (verificato:
  `promptguard_utils.py::_get_class_probabilities`, `truncation=True,
  max_length=512`) — non un rischio di crash (falsificato in council, risk finding
  #3 corretto), ma un caso composto con un seed turn molto lungo verrebbe
  analizzato solo nei primi 512 token, silenziosamente. Non misurato se qualche
  caso del dataset attuale si avvicina al limite.
- **Verifica aggiuntiva per Task 0** (council, risk finding #5, meccanismo
  originale impreciso ma categoria di rischio reale): controllare che il log di
  build reale (`docker build` output, non `docker history`) non stampi il token
  HF in chiaro durante il pre-download del modello — `huggingface_hub`/`transformers`
  in modalità verbose potrebbero farlo.
- **Nota di methodology nel report futuro e convenzione di naming della directory
  del report, non ancora decise** (council, advocate) — da aggiungere come task
  espliciti quando si scrive il piano canonico: il lettore del report deve poter
  capire che `tool_name="llamafirewall-combined"` significa "AlignmentCheck +
  PromptGuard fusi", non un terzo scanner indipendente del pacchetto vendor, senza
  dover leggere il codice — attenuato ma non eliminato dalla scelta di
  `/grill-with-docs` di usare un nome nuovo invece di sovraccaricare un nome
  esistente.
