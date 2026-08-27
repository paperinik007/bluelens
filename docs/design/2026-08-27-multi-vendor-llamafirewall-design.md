# Design: architettura N-vendor + secondo vendor (LlamaFirewall)

Data: 2026-08-27. Copre due livelli distinti in un solo documento perché sono
sequenziali e dipendenti: (1) l'architettura generale per ospitare più di un
vendor sotto audit, applicata per la prima volta con (2) l'integrazione di
LlamaFirewall come secondo vendor. Non è un documento su AgentDoG: quella
scelta è stata riverificata e scartata (vedi
`docs/research/2026-08-27-agentdog-verification.md`); la parte generale
dell'analisi precedente (`docs/notes/2026-08-26-analisi-integrazione-secondo-vendor.md`,
sezioni C/E-parziale/F/H/I) resta valida e viene riusata qui, non riscritta
da zero.

## Perché

Il progetto è per natura un ente N-vendor (SPIRIT.md: "i vendor" al plurale,
principio 8: il vendor attivo è un parametro esplicito, mai implicito). Oggi
l'harness è accoppiato a un solo vendor (aidr) in modo non parametrico:
nome servizio, `tool_name` negli error verdict, campi di provenance sono
tutti hardcoded aidr. Questo documento decide come diventare N-vendor senza
introdurre debito (nessuna tassonomia neutra, nessun mapping forzato,
isolamento fisico reale tra vendor) e lo applica subito a LlamaFirewall.

## Scope

Dentro: layout a sottopackage con COPY selettivo, container dedicato per
LlamaFirewall, parametrizzazione dell'harness (`--vendor`), adapter
LlamaFirewall (AlignmentCheck via OpenRouter), proxy con logging, gestione
errori (riuso di `status="error"`/`error_count`/`rationale`, esteso ad
**entrambi** i vendor — retrofit di aidr incluso, non solo LlamaFirewall,
verificato che nessun meccanismo nuovo serva), piano di test.

Fuori: AgentDoG (scartato), un terzo vendor (l'architettura lo rende
un'aggiunta, non viene progettato ora), la metrica strict per vendor con
tassonomie diverse da quella T-code di aidr (resta primary-only per ora,
già deciso nell'analisi precedente, §H).

## Sequenza: due fasi, un gate di verifica in mezzo

**Fase 1 — refactor aidr, zero cambio di comportamento (blocking).**
Sposta `adapter.py`/`evaluate_case.py`/`vendor_proxy.py` in
`src/detector_adapter/vendors/aidr/`. Aggiorna il COPY selettivo nel
Dockerfile di `detector` e l'unico comando hardcoded in
`orchestrator.py:113` (`python -m detector_adapter.vendors.aidr.evaluate_case`).
Non introduce `--vendor`, non tocca C1/C4/C5/C6 (nessun comportamento nuovo
da parametrizzare finché esiste un solo vendor). Gate: la suite deve dare lo
stesso risultato di prima (oggi: 468 passed, 2 skipped) — se non è identico,
ci si ferma qui, prima di toccare LlamaFirewall.

**Fase 2 — LlamaFirewall come secondo vendor, solo dopo che la Fase 1 è verde.**
Nuovo sottopackage `vendors/llamafirewall/`, nuovo container
`detector-llamafirewall`, introduzione di `--vendor` come argomento CLI
esplicito a `run_batch` (mai persistente in `.env` — principio 8), e la
parametrizzazione reale di C1/C4/C5/C6/C7/D/E/F secondo l'inventario già
scritto nell'analisi precedente (touchpoint generali, non specifici di un
vendor). Include anche il rename di `DETECTOR_TOOL_NAME` (aidr) da
`"agentic_threat_detection"` a `"aidr"` (grill session, vedi `CONTEXT.md`):
non è uno spostamento di file, cambia il contenuto scritto in ogni futuro
`Verdict` — per questo appartiene qui, dove il comportamento cambia
comunque con l'introduzione di `--vendor`, e non alla Fase 1 (che deve
restare a zero cambio di comportamento).

## Falsificazione pre-design (prototipi reali, non letture di documentazione)

| Assunzione | Esperimento | Risultato | Impatto sul design |
|---|---|---|---|
| Serve patchare il sorgente vendored di `LLMClient`/`AlignmentCheckScanner` per usare OpenRouter | Letto il sorgente reale in un clone locale di `meta-llama/PurpleLlama` (`base_llm.py`, `alignmentcheck_scanner.py`, `custom_check_scanner.py`) | **Falsa.** `CustomCheckScanner.__init__` accetta già `model_name`/`api_base_url`/`api_key_env_var`; una nostra sottoclasse chiama `CustomCheckScanner.__init__` direttamente, bypassando `AlignmentCheckScanner.__init__` (che li hardcoda su Together). Nessun fork/patch, a differenza di aidr. |
| Il verdetto di AlignmentCheck è ALLOW/BLOCK binario | Letto `llamafirewall_data_types.py` | **Parzialmente falsa.** `ScanDecision` ha tre valori; AlignmentCheck emette solo ALLOW o HUMAN_IN_THE_LOOP_REQUIRED (mai BLOCK, che è di altri scanner). Mapping: `label = "malicious" if decision == HUMAN_IN_THE_LOOP_REQUIRED else "benign"`. |
| AlignmentCheck è attivo di default su `scan_replay()` | Letto `llamafirewall.py` | **Falsa.** Nessuno scanner è configurato di default per nessun ruolo con AGENT_ALIGNMENT. Va registrato esplicitamente (`@register_llamafirewall_scanner`) e agganciato a `Role.ASSISTANT` in una `Configuration` custom. |
| `client.beta.chat.completions.parse()` (structured output) funziona attraverso OpenRouter | Chiamata reale con chiave dell'audit esistente, **due modelli × due casi** (misallineato/atteso True, allineato/atteso False — round bidirezionale, dopo che il council ha segnalato che il primo giro testava solo una direzione) | **Confermata con riserva concreta, non generica.** `llama-3.3-70b-instruct` risponde correttamente su entrambi i casi. `llama-4-maverick` **fallisce con `pydantic.ValidationError`** sul caso misallineato (il modello omette il campo `conclusion` dalla risposta) — un fallimento reale e riprodotto, non ipotetico. Questo fallimento, con `AlignmentCheckScanner` reale, verrebbe **silenziosamente convertito in `conclusion=True` (malicious)** dal fallback d'errore del vendor — prova diretta che il rischio "fail-closed contamina la metrica" segnalato dal council (skeptic + risk, convergenza indipendente) è concreto, non teorico. Conseguenza: il modello di default **non può essere `llama-4-maverick`** — va scelto `llama-3.3-70b-instruct` o altro modello verificato affidabile su questo schema, e comunque serve un meccanismo che distingua un fallback d'errore da una detection vera (vedi sezione "Gestione errori" corretta sotto). |
| I modelli `:free` citati nella ricerca di mercato sono ancora disponibili | Stesso prototipo, prima con slug `:free` | **Falsa.** 404 "unavailable for free" su entrambi i candidati testati — servono gli slug a pagamento. Conseguenza: il costo per chiamata **non è zero** (a differenza della AgentDoG-ipotesi ereditata), va letto dalla risposta OpenRouter come già avviene per l'agente — e serve un tetto di spesa/circuit breaker per un batch non presidiato (segnalato da risk). |

Nessuna assunzione critica è risultata falsa in modo bloccante, ma la
falsificazione bidirezionale ha cambiato una decisione concreta (modello di
default) e reso obbligatorio un meccanismo che nella prima stesura era solo
implicito (vedi "Gestione errori").

## Review del council (2026-08-27, non vincolante)

Council a scope pieno, roster completo (skeptic, risk, pragmatist,
advocate). Sintesi e verdetti nella conversazione di design; qui solo le
correzioni recepite dopo verifica diretta:

1. **Fail-open/fail-closed non distinguibile da detection vera** (skeptic +
   risk, convergenza indipendente, poi confermato con un fallimento reale
   riprodotto — vedi tabella sopra; grill session: confermato che vale
   anche per aidr, già oggi). Fix: riuso di `status="error"`/`rationale`
   (nessun bucket nuovo — vedi "Gestione errori").
2. **Topologia di rete non specificata** (risk, verificato su
   `docker-compose.yml`): `detector-llamafirewall` non aveva una rotta
   dichiarata verso `egress-proxy`. Fix: vedi "Architettura" corretta sotto.
3. **Comunicazione al lettore del report sull'incomparabilità delle
   tassonomie** (advocate): assente. Fix: nuovo touchpoint report.
4. **Copertura test nel tempo per entrambi i vendor dopo il merge**
   (pragmatist): valido ma di livello CI/operativo, non architetturale —
   registrato come nota per il piano di implementazione, non risolto qui.

## Architettura

```
docker-compose.yml
├── agent                    (esistente, invariato)
├── egress-proxy               (esistente, invariato)
├── detector                    → vendor "aidr" (Fase 1: refactored in vendors/aidr/)
└── detector-llamafirewall       → vendor "llamafirewall" (Fase 2: nuovo)

src/detector_adapter/
├── vendors/
│   ├── aidr/              adapter.py, evaluate_case.py, vendor_proxy.py (migrati)
│   └── llamafirewall/     adapter.py, evaluate_case.py, openrouter_proxy.py (nuovi)
```

Ogni vendor: proprio package, proprio `pyproject.toml`, proprio Dockerfile
con COPY selettivo (il container aidr non contiene i byte di llamafirewall
e viceversa — è il COPY selettivo a rendere reale l'isolamento, non il solo
sottopackage). Stesso "entrypoint standardizzato" per entrambi: stessa forma
di invocazione (`python -m detector_adapter.vendors.<nome>.evaluate_case`),
stesso contratto wire (JSON stdin/stdout, forma `Verdict`). Nessuna
interfaccia Python condivisa tra i due adapter — non serve, non condividono
mai un processo (Gap 9), il contratto è solo il wire format.

**Rete (fix da review council — risk, verificato su `docker-compose.yml`)**:
oggi `detector` è su `detector_net` (`internal: true`) e raggiunge
l'esterno solo passando per `egress-proxy`, che è l'unico container con
rotta reale a internet. Il documento non specificava come
`detector-llamafirewall` avrebbe raggiunto OpenRouter — senza questo, o non
ha nessuna rotta in uscita (si rompe al primo run reale), o va aggiunto a
`detector_net` esistente (condividendo la rete con aidr, il che vanifica
l'isolamento fisico che il resto del documento dichiara). Deciso: nuova rete
dedicata `detector_llamafirewall_net` (`internal: true`), con `egress-proxy`
aggiunto anche a questa rete — stesso pattern già in uso per `agent_net`/
`detector_net` (`egress-proxy` è già su tre reti in `docker-compose.yml`
attuale). Nessun vendor condivide mai una rete con un altro.

`--vendor` è un argomento CLI esplicito a ogni invocazione di `run_batch`
(mai una env var persistente — principio 8, e la stessa lezione
dell'editable-install trap su stato implicito). Scritto in provenance come
fonte di verità per la rigenerazione del report.

**Nota terminologica (grill session, vedi `CONTEXT.md`)**: `--vendor` /
`AUDIT_VENDOR` seleziona quale **pacchetto/container** instradare (nome
generico, es. `llamafirewall`), non necessariamente lo stesso valore del
`tool_name` preciso scritto nel `Verdict` (es. `llamafirewall-alignmentcheck`).
Oggi coincidono di fatto (un pacchetto = un tool attivo), ma non sono lo
stesso concetto — se in futuro un pacchetto ospitasse più tool
selezionabili, `--vendor` resterebbe il selettore di pacchetto/container,
mentre `tool_name` identificherebbe il tool preciso effettivamente
misurato in quella run.

## Componenti (Fase 2)

- **`vendors/llamafirewall/adapter.py`**: `OpenRouterAlignmentCheck(AlignmentCheckScanner)`
  che chiama `CustomCheckScanner.__init__` direttamente con `model_name`
  (da `LLAMAFIREWALL_MODEL` env var, default verificato dal vivo — mai uno
  slug `:free`, stessa disciplina di `SIFTER_MODEL`/`INSPECTOR_MODEL`/`EMBED_MODEL`),
  `api_base_url` puntato al proxy locale del container (non direttamente a
  OpenRouter). Registrata via `@register_llamafirewall_scanner`, agganciata
  a `Role.ASSISTANT` in una `Configuration` passata a `LlamaFirewall(scanners=...)`.
- **`vendors/llamafirewall/evaluate_case.py`**: entrypoint standardizzato —
  transcript JSON da stdin → `Message(role=Role.USER/ASSISTANT/TOOL, ...)` →
  `Trace` → `scan_replay()` → `Verdict` (mapping decisione sopra, `cost_usd`
  reale dalla risposta OpenRouter).
- **`vendors/llamafirewall/openrouter_proxy.py`**: forward+log+scrub verso
  OpenRouter reale (nessun remapping tier — a differenza di `vendor_proxy.py`,
  qui `LLMClient` manda già un vero model id). Stesso principio di
  osservabilità indipendente di aidr: vediamo il traffico reale, non solo
  quello che il nostro adapter dichiara di aver mandato. Legge
  `LLAMAFIREWALL_OPENROUTER_API_KEY` da `.env.llamafirewall` (dedicato — un
  container non vede mai la chiave di un altro vendor).
- **`docker/detector-llamafirewall/`**: Dockerfile (pip `llamafirewall`, no
  torch/transformers — non è un modello locale), `pyproject.toml` dedicato,
  `entrypoint.sh` avvia il proxy in background. `cap_drop: ALL`,
  `security_opt: no-new-privileges:true`, rete `internal: true` — stessa
  postura di `detector`.

## Data flow

```
orchestrator.py (vendor = "llamafirewall", da --vendor)
  → docker compose exec -T detector-llamafirewall
      python -m detector_adapter.vendors.llamafirewall.evaluate_case
  → stdin: transcript JSON (formato harness-side invariato per ogni vendor)
  → adapter: transcript → Trace → scan_replay() → ScanResult
      → LLMClient parla con http://127.0.0.1:<port>/v1 (proxy locale)
      → proxy: forward+log+scrub → OpenRouter reale
  → stdout: Verdict JSON (schema invariato per ogni vendor)
  → evidence.collect_case_evidence: legge il log del proxy llamafirewall
    (path diverso da vendor_proxy.jsonl, C7 generalizzato — non nuovo)
  → provenance: vendor="llamafirewall" (selettore pacchetto/container),
    tool_name="llamafirewall-alignmentcheck" (prodotto preciso misurato),
    modello+revisione OpenRouter (mai hash pesi — non pertinente a un
    vendor via API)
```

## Gestione errori

- **Fail-open/fail-closed del vendor non distinguibile da detection vera —
  non è specifico di LlamaFirewall, retrofit di aidr incluso in questa fase
  (grill session, 2026-08-27; limite registrato in `registro-limiti-aperti.md`).**
  `detector/sifter.py:53` di aidr (`Sifter.triage_safe()`) ha lo stesso
  problema di `_get_default_error_response()` di `CustomCheckScanner`
  (LlamaFirewall, `AlignmentCheckScanner`): qualunque eccezione (timeout,
  4xx/5xx, rate limit, o — dimostrato empiricamente per LlamaFirewall — un
  modello che non rispetta lo schema strutturato) viene intercettata
  **dentro** il codice del vendor e sostituita con un default
  (`escalate: True` per aidr, `conclusion=True` per LlamaFirewall) **prima**
  che il nostro adapter possa accorgersi che è successo un errore — in
  nessuno dei due casi il nostro codice vede un'eccezione sollevata. Senza
  intervento, un batch con rate limit o un modello inaffidabile produrrebbe
  verdetti "malicious" indistinguibili da detection reali — esattamente il
  rumore auto-inflitto che SPIRIT.md principio 3 esiste per evitare. Per
  aidr, questo vale **già oggi per tutti i run pubblicati finora** (limite
  registrato); per LlamaFirewall il rischio è nuovo ma dello stesso tipo.
  **Fix (verificato su `schema.py`/`metrics.py`/`report.py`, non solo
  proposto — nessun meccanismo nuovo, riuso di uno esistente)**: quando
  l'adapter rileva il fallback del vendor (per LlamaFirewall: sottoclasse
  che override `_evaluate_with_llm` per intercettare l'eccezione prima che
  venga sostituita dal default e imposta un flag d'istanza; per aidr:
  controllo della chiave `"note"` con prefisso `"fail-open:"` nel risultato
  del Sifter), produce un `Verdict` con **`status="error"`, `label=None`**
  (vincolo di schema già esistente, `schema.py:162-163`) e
  **`rationale`** che riporta la causa (es. `"vendor fail-open: <nota
  originale>"`). Questo riusa `error_count`/`metrics.py` (già escluso da
  TP/FP/FN/TN, zero modifiche a `metrics.py`) e la resa già esistente in
  `report.py:272` (`"Detector verdict: error ({verdict.rationale})"`) —
  nessun bucket nuovo, nessun campo schema nuovo, nessun touchpoint report
  aggiuntivo oltre alla generalizzazione già prevista (F1-F4). Il log del
  proxy (che cattura comunque il fallimento lato rete per LlamaFirewall)
  resta un canale di evidenza di supporto, non il meccanismo primario di
  rilevamento — il flag/controllo sull'adapter è affidabile anche quando il
  fallimento è nel parsing dello schema, non nella rete. Per aidr, questo è
  un vero cambio di comportamento — non entra in Fase 1 (zero cambio, vedi
  sopra), entra qui in Fase 2 insieme al resto della parametrizzazione
  degli error verdict (C4/C6).
- Errore che il nostro stesso adapter non riesce a intercettare (proxy
  irraggiungibile, eccezione fuori da `_evaluate_with_llm`): produce un
  `Verdict` con status d'errore — mai testo raw di eccezione (solo
  `__class__.__name__`, vincolo permanente).
- **Tetto di spesa (review council, risk)**: nessun budget cap o circuit
  breaker era previsto per chiamate reali a pagamento durante un batch non
  presidiato. Da aggiungere: un limite di chiamate/costo per run,
  configurabile, che interrompe il batch (non il singolo case) se superato
  — stesso principio del circuit breaker già esistente per aidr, esteso a
  un vendor con costo reale non nullo.
- Timeout esterno (`detector_timeout_s`): da ritarare sulla latenza reale
  di una chiamata LLM-giudice via OpenRouter (collo di bottiglia è la rete/
  il modello remoto, non il caricamento pesi locale) — misurato nel primo
  run, non assunto.
- `_error_verdict`/`_fallback_verdict` (C4/C6): `tool_name` deve dichiararsi
  `"llamafirewall-alignmentcheck"`, mai ereditare `"aidr"` (post-rename,
  vedi Fase 2 sopra) né il vecchio `"agentic_threat_detection"`.

## Requisito → Verifica

| Requisito | Verifica eseguibile |
|---|---|
| Nessun import incrociato tra vendor, nessuno importa `toy_agent` | `tests/test_no_vendor_imports.py` esteso (scan AST) |
| Il verdetto llamafirewall usa il mapping corretto (HUMAN_IN_THE_LOOP_REQUIRED → malicious, mai BLOCK atteso) | test unitario su `detection_result_to_verdict`-equivalente, duck-typed, nessuna dipendenza da `llamafirewall` installato |
| Serializzazione transcript → `Trace`/`Message` corretta (ruoli, tool_calls) | test unitario puro sulla funzione di serializzazione |
| La chiave API non finisce mai in chiaro nel log del proxy | test del proxy con transport iniettato (no rete reale), stesso pattern di `vendor_proxy.py` |
| Il routing harness (`--vendor`) seleziona il container/tool_name corretto | test parametrizzati su `test_orchestrator.py`/`test_evidence.py`/`test_sequence.py`/`test_run_batch.py` per il ramo `llamafirewall` |
| La sottoclasse si costruisce davvero contro le classi reali di `llamafirewall` (non solo contro un duck-type) | script gated (`run_adapter_tests.sh`), eseguito dove la dipendenza reale è installata |
| Fase 1 non cambia comportamento | suite piena, stesso conteggio pass/skip di prima del refactor |
| Un fallback d'errore del vendor non viene mai contato come detection (**entrambi i vendor**) | test unitario per llamafirewall: forzare un'eccezione in `_evaluate_with_llm`; test unitario per aidr: risultato Sifter con `note` prefissata `"fail-open:"`; entrambi verificano che il case produca `Verdict(status="error", label=None, rationale=...)`, mai un `Verdict` con label |
| Il report dichiara esplicitamente l'incomparabilità delle tassonomie per un run multi-vendor | test su `report.py`: il caveat compare nell'output quando il run include un vendor diverso da aidr |

## Test — cosa e perché

1. **`tests/test_no_vendor_imports.py` esteso**: garanzia strutturale
   dell'isolamento fisico (Gap 9 esteso a N vendor).
2. **Normalizzazione verdetto** (funzione pura, duck-typed): unica logica
   nostra nel punto più a rischio di errore silenzioso (es. trattare
   HUMAN_IN_THE_LOOP_REQUIRED come se ci fosse BLOCK).
3. **Serializzazione transcript → Trace**: rende permanente la garanzia
   appena stabilita col prototipo, non solo verifica una tantum.
4. **Proxy con logging** (transport iniettato): codice nuovo che tocca una
   chiave API — la scrubbing prima di disco è security-relevant.
5. **Parametrizzazione test harness esistenti** sul ramo `llamafirewall`:
   copre i touchpoint C1-C7 che diventano codice vero in Fase 2 — senza,
   una regressione nel routing si scoprirebbe solo in un run reale costoso.
6. **`run_adapter_tests.sh` gated**: verifica contro le classi vere di
   `llamafirewall`, non contro un mock, dove la dipendenza è installata.

Non serve nessun test di "mapping tassonomia": `metrics.py`/`serialization.py`
sono già vendor-agnostici per costruzione (conferma positiva già verificata
per aidr), e la decisione "nessun mapping, si misura solo il label" non
introduce logica nuova da testare.

## Comunicazione al lettore del report (fix da review council — advocate)

Il documento copriva l'infrastruttura ma non la comunicazione: un lettore
del report che confronta P/R di aidr e P/R di LlamaFirewall senza sapere
che misurano tassonomie diverse su scale diverse rischia di trarre
conclusioni sbagliate — esattamente il tipo di confusione tra segnale e
rumore che questo progetto esiste per evitare, ora a rischio di
auto-infliggersi nel proprio report. Nuovo touchpoint per Fase 2
(estende F1-F4 dell'inventario generale): `report.py` deve includere, per
ogni run multi-vendor pubblicato, un caveat esplicito e non rimovibile —
"i vendor auditati misurano tassonomie diverse (T-code aidr vs
ALLOW/HUMAN_IN_THE_LOOP_REQUIRED LlamaFirewall); i numeri primary sono
comparabili solo sul label malicious/benign contro il ground truth, mai
vendor-contro-vendor sulla tecnica" — più la motivazione della scelta del
vendor (perché LlamaFirewall, non solo "come funziona"), leggibile da chi
deve decidere se fidarsi di uno di questi prodotti, non solo da chi
mantiene il repo.

## Limiti dichiarati (da registrare in `registro-limiti-aperti.md` a
integrazione avvenuta)

- Costo per chiamata LlamaFirewall non è zero (a differenza della
  AgentDoG-ipotesi): va misurato sul primo run reale, non stimato.
- La copertura delle categorie native di LlamaFirewall (ALLOW/HUMAN_IN_THE_LOOP_REQUIRED,
  nessuna tassonomia 3D) contro il dataset scritto nel linguaggio aidr
  (T0001-T0014) non è garantita — stesso principio già applicato ad
  AgentDoG: si riporta, non si misura.
- La metrica strict resta definita solo per aidr (T-code); per llamafirewall
  si pubblica solo la primary, salvo decisione futura esplicita.
- **Affidabilità del modello LLM-giudice non uniforme tra candidati**
  (falsificazione bidirezionale): `llama-4-maverick` ha fallito la
  validazione dello schema strutturato su un caso reale, `llama-3.3-70b-instruct`
  no. Il default va scelto sul secondo (o altro modello verificato
  affidabile), ma anche col modello più affidabile il meccanismo
  `status="error"`/`rationale` resta necessario come rete di sicurezza, non
  solo come rimedio a un modello sbagliato.
- **Copertura test di entrambi i vendor nel tempo, dopo il merge** (review
  council, pragmatist): l'architettura la abilita (vendor parametrico,
  container isolati, test parametrizzati) ma non specifica l'enforcement
  di processo (se entrambe le suite vendor girano a ogni commit, come CI
  monta entrambi i container, se un fallimento in un vendor blocca il
  merge di modifiche all'altro) — da definire nel piano di implementazione,
  non in questo design.
