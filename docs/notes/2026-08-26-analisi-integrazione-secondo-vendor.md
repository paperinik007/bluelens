# Analisi integrazione secondo vendor (AgentDoG) — dove e perché intervenire

> **Fonte viva delle decisioni (supersede il handoff `handoff-prossimo-pi-2026-08-26.md`).**
> Se leggi quel handoff, le sue sezioni su modello e architettura sono superate: il modello
> corretto è la variante **Base 0.8B** (`AgentDoG1.5-Qwen3.5-0.8B`), non "Unified-0.8B" (che
> non esiste — Unified è solo 4B), e l'architettura è **generativa** (non `pipeline("text-classification")`).

> **⚠️ VENDOR CAMBIATO (2026-08-27, deciso con l'utente): secondo vendor = LlamaFirewall, non
> AgentDoG.** `docs/research/2026-08-27-agentdog-verification.md` ha riverificato la scelta di
> AgentDoG e l'ha trovata non sostenuta (repo GitHub fermo da ~3 mesi, nessun veicolo commerciale,
> nessuna valutazione indipendente, 3 citazioni sul paper 1.5) — confermando invece la classifica
> originaria del documento di ricerca vendor del 20 agosto (LlamaFirewall più forte su rilevanza di
> mercato, Meta-backed, mai acquisito). **Questo intero documento resta come riferimento storico per
> il livello generale "gestione N vendor" (§1.0 invarianti, §1.2 sezioni C/E-parziale/F/H/I —
> parametrizzazione harness, provenance, report, tassonomia, test), che vale per qualsiasi secondo
> vendor.** Le decisioni architetturali specifiche in §4 (Strada A container dedicato, modello
> co-locato, sottopackage+COPY selettivo, modello baked, daemon residente, hash pesi, costo=0) sono
> **specifiche di AgentDoG come modello locale embedded e non si applicano a LlamaFirewall**, che
> passa per API (OpenRouter, come sifter/inspector/embed di aidr oggi) — verosimilmente Strada B
> (adapter parametrizzato, riuso del pattern `vendor_proxy` esistente), nessun container nuovo, nessun
> modello da bakare, costo reale non nullo. **Serve un nuovo documento di analisi/design per
> LlamaFirewall prima di scrivere codice** — questo non va riusato come se fosse già quel documento.

Data: 2026-08-26. Scritto da pi (sessione corrente) come follow-up del handoff
`handoff-prossimo-pi-2026-08-26.md`. Scopo: registrare **dove** (file:riga) e
**perché** va toccato il codice per integrare AgentDoG come secondo vendor, poi
sottoporre l'analisi a una review critica.

Scope già deciso con l'utente (sessione corrente):
- **Un vendor per run, selezionabile** (no contemporaneità — coerente con SPIRIT.md: si audita un vendor alla volta, la comparabilità è nel tempo, non nel batch).
- **Strada A**: container `detector-b` separato.
- **Modello co-locato in `detector-b`** (non container dedicato): il modello è il *misurato*, non strumentazione nostra; l'interfaccia è in-process (`guardrail()`), quindi un container dedicato obbligherebbe a inventare un layer di serving inutile. Il "processo residente" è un daemon interno a `detector-b` (stesso pattern di `vendor_proxy`), non un quarto container.
- **Decisione metodologica centrale (tassonomia)**: si misura **solo sul label** (malicious/benign contro il nostro ground truth per-effetto); la tassonomia di ciascun vendor si **riporta, non si misura** (stampata nel report così com'è); **nessun mapping, nessuna tassonomia neutra**. Motivo: il confronto legittimo è vendor ↔ ground truth, mai vendor ↔ vendor; tradurre una tassonomia nell'altra imporrebbe la griglia di un vendor all'altro (il bias self-reported che SPIRIT.md contesta, in versione certificatore). La differenza di ontologia è un *risultato* pubblicato, non un rumore da eliminare.
- **Layout del pacchetto (decisa)**: sottopackage `src/detector_adapter/vendors/{aidr,agentdog}/` **con COPY selettivo nel Dockerfile** — i due ambienti devono essere **fisicamente distinti** (il container aidr non contiene i byte di agentdog e viceversa). Il sottopackage da solo non isola nulla: è il COPY selettivo che rende la separazione reale. Esecuzione in due passi: (1) refactor di aidr sul nuovo pattern con suite verde a ogni passo (rete di sicurezza: 468 test), (2) solo poi AgentDoG come aggiunta al pattern consolidato. Motivazione: il progetto è per natura un ente N-vendor (SPIRIT.md: "i vendor" al plurale), quindi "un vendor = un package con entrypoint standardizzato" è architettura di destinazione, non speculazione.
- **Configurazione (decisa)**: stesso principio della separazione fisica, applicato ai file di config. `.env` = **condiviso**, del misuratore (serve sempre: `AGENT_OPENROUTER_API_KEY`, `AGENT_MODEL`); `.env.aidr` / `.env.agentdog` = **dedicato**, visto **solo** dal container di quel vendor via `env_file:` (un container non vede mai le chiavi/config dell'altro). `.env.example` diventa l'unica fonte di verità: una sezione per file, ogni variabile con due righe obbligatorie — *dove vive* e *chi la legge*. Regola da scrivere nel README: "una variabile vive in un solo file, e ogni file dichiara chi lo legge".
- **Modello baked (decisa)**: il file dei pesi di AgentDoG (~1.8 GB) viene copiato dentro l'immagine Docker alla build (come già avviene per il codice aidr con `git clone`), non scaricato al primo avvio. Coerente con l'offline di `detector-b`, riproducibile (revisione + hash fissati al build); il costo è spazio su disco, non correttezza.
- **Selezione vendor via CLI (decisa)**: `AUDIT_VENDOR` passato **esplicitamente a ogni invocazione** di `run_batch` (argomento CLI / env var in shell), **non** lasciato a persistere nel `.env`. Motivo: massima chiarezza, nessuno stato implicito che sopravvive tra sessioni — coerente con la lezione sull'editable-install che fece sprecare due batch per uno stato implicito. Il vendor va poi scritto in provenance come fonte di verità per la rigenerazione del report (che legge dalla provenance, mai dall'ambiente).

---

## Parte 1 — Analisi (dove e perché)

### 1.0 Invarianti che ogni intervento deve preservare

1. **Gap 9 (confine)**: `toy_agent` non importa mai `detector_adapter`/`aidr`; `detector_adapter` non importa mai `toy_agent`. Enforced da `tests/test_no_vendor_imports.py` (scan AST). Il solo contratto è JSON su stdin/stdout via `docker compose exec -T <service> python -m ...`.
2. **Verdict.tool_name** (`schema.py:142`) distingue il vendor senza schema change. Esiste già per questo.
3. Suite verde prima di ogni commit (`python -m pytest tests/ -q`, oggi 468 pass).
4. Nessuna nuova dipendenza nel `pyproject.toml` root (resta `toy_agent`-only).
5. Nessun messaggio raw di eccezione raggiunge output (solo `__class__.__name__`).
6. Principio 8 (SPIRIT.md): il vendor attivo deve essere un **parametro esplicito** dichiarato per ogni audit e registrato in provenance — mai implicito.

### 1.1 Tre fatti strutturali che cambiano il lavoro (rispetto a un "secondo aidr")

**(A) Modello locale vs modello via API — risolto dal pattern esistente, non una decisione aperta.**
`aidr` chiama modelli su OpenRouter (client per invocazione, costo di costruzione = solo handshake MCP). AgentDoG è un modello 0.8B **locale CPU** (~1.8 GB): il costo reale non è per-invocazione, è il **caricamento dei pesi da disco a RAM**, che va pagato una volta sola. Il container è già la risposta: il lifecycle `--container-lifecycle reused` tiene il container su per l'intero batch, e dentro il container un **daemon residente** (processo long-lived avviato da `entrypoint.sh`, esattamente il pattern di `vendor_proxy` che oggi gira in background nel container `detector`) carica il modello una volta e risponde alle N chiamate. Quindi: `reused` = daemon che carica una volta, N `exec` leggeri che gli parlano; `per-case` = daemon nuovo per caso = ricarica a ogni caso, che per un vendor locale è **anti-economico** e va **dichiarato come limite** (non corretto: è il costo intrinseco di quel lifecycle). Non si inventa nessun layer di comunicazione: se il vendor prevede un server (vllm/sglang), il nostro adapter è un client HTTP; se prevede una funzione (`guardrail()`), il daemon è un wrapper nostro — in entrambi i casi un pattern già presente nel repo. Resta solo la **verifica empirica** (formato d'interfaccia, da model card) e la **misura delle latenze reali** per ritarare i timeout (180s/150s) sul profilo CPU.

**(B) La tassonomia del dataset è accoppiata ad aidr (T0001–T0014) — ma questo NON è un problema da risolvere, è un dato da dichiarare.**
`TestCase.technique_target` (`schema.py`) porta i codici T di aidr. AgentDoG produce una tassonomia 3D diversa (Risk Source / Failure Mode / Real-world Harm, detta anche Risk Consequence — conteggi esatti da verificare). La risoluzione adottata (vedi scope sopra) è che questo disallineamento **non si risolve con un mapping**: il metro resta il label (taxonomy-free), e la tassonomia di ciascun vendor è riportata, non misurata. Quindi l'accoppiamento aidr nel dataset non è un debito da ripagare ora: è una caratteristica dichiarata — il dataset è scritto nel linguaggio aidr perché aidr è stato il primo vendor, e per AgentDoG la copertura delle sue categorie 3D **non è garantita** (limite di copertura, non bias da correggere). Non si introduce una tassonomia neutra, perché sarebbe una terza ontologia nostra imposta a entrambi.

**Fatti assodati sul modello (verificati direttamente su HF: API catalogo + `config.json`, 2026-08-26).** A 0.8B esistono **due** varianti: `AgentDoG1.5-Qwen3.5-0.8B` (Base, solo binario `safe`/`unsafe`) e `AgentDoG1.5-FG-Qwen3.5-0.8B` (fine-grained, sola tassonomia 3D). La variante **Unified esiste solo a 4B** (`AgentDoG1.5-Unified-Qwen3.5-4B`) e richiede GPU. L'architettura è **generativa** (`Qwen3_5ForConditionalGeneration`, senza `id2label`/`num_labels`): il `pipeline_tag: text-classification` è solo metadata — il modello NON va caricato con `pipeline("text-classification")`, va caricato come generativo e l'output estratto con regex. Il modello scelto per il container è la variante **Base 0.8B** (basta per la metrica primary, l'unica pubblicata); la 3D è un passaggio FG separato, opzionale e descrittivo. Restano da confermare dalla model card: il template esatto del prompt di input e l'elenco dei valori ammessi nella tassonomia 3D (conteggi divergenti tra le fonti: 7/12/6 vs 8/14/10).

**(C) `vendor_proxy` / thin-proxy log sono aidr-specifici, e sono cablati in due punti dell'harness.**
`orchestrator.py:108` (scrittura marker nel log) e `evidence.py:74` (`collect_thin_proxy_log`) presuppongono che il detector abbia `/var/log/vendor_proxy.jsonl`. AgentDoG non ha proxy né log: entrambi i punti devono diventare condizionali sul vendor, non solo "cambiare nome servizio".

**(D) Il modello locale è un problema e un'opportunità di verifica — più forte che con aidr.**
Con aidr metà del detector vive fuori dal nostro controllo (modelli su OpenRouter): vediamo solo il traffico al proxy. Con AgentDoG locale il container è il perimetro completo del detector, quindi dall'esterno si può verificare ciò che per aidr è impossibile: (1) **nessun egress — per costruzione**, se `detector-b` è su rete internal-only non ha fisicamente una rotta esterna (garanzia strutturale, non per osservazione); (2) **identità esatta dei pesi** — `docker exec sha256sum` sul file del modello confrontato con l'hash in provenance (con aidr i pesi non li tocchiamo); (3) i canali `evidence.py` già esistenti (`logs`/`diff`/`stats`) valgono identici. Inoltre lo "scambio di informazioni" non esce mai dal processo: l'intero I/O del detection (traiettoria serializzata in input, verdetto/3D in output) è **completamente osservabile e loggabile** dal nostro stesso adapter — il canale di evidenza non è perso rispetto a `vendor_proxy.jsonl`, è **sostituito da uno migliore** (log completo input/output della chiamata, senza hop di rete). Tre caveat onesti: (a) osservare I/O ≠ capire il calcolo interno (i pesi restano black-box, come ogni detector, ma senza il gap di rete di aidr); (b) il log I/O è auto-prodotto dall'adapter — fiducia coperta dal principio 6 (codice del misuratore pubblicato e verificabile), stesso tipo già richiesto per l'adapter aidr; (c) va verificato il **determinismo** (stesso input → stesso output, o varianza di sampling) — con un modello locale verificabile direttamente ripetendo la chiamata. Questa osservazione indirizza tre punti aperti: preflight (presenza + hash pesi + "ready" del daemon), provenance HF (hash come dato di riproducibilità), evidenza (nuovo canale I/O per vendor offline).

### 1.2 Inventario dei touchpoint

Legenda: **dove** (file:riga) → **perché** si interviene.

#### A. Nuovo adapter (`src/detector_adapter/vendors/`)

Con il layout sottopackage, aidr migra in `vendors/aidr/` e AgentDoG nasce in `vendors/agentdog/`. Ogni vendor ha il proprio entrypoint standardizzato e il proprio pyproject dedicato.

| # | Dove | Perché |
|---|---|---|
| A1 | nuovo `vendors/agentdog/agentdog_adapter.py` | Serve un adapter che non importa `aidr`: carica il modello (lazy import `transformers`), serializza il transcript nel formato testuale atteso, chiama `guardrail()`, normalizza il verdetto in `Verdict`-shape. |
| A2 | nuovo entrypoint `vendors/agentdog/evaluate_case_agentdog.py` (nome distinto) | I `pkill -f detector_adapter.evaluate_case` in `orchestrator.py` (righe 135/140/161/166) sono scoped per-container via `exec`, ma un entrypoint con lo stesso nome renderebbe ambiguo il pattern; nome distinto = pulizia e attribuzione inequivocabili. |
| A3 | nuovo `docker/detector-b/detector_adapter.pyproject.toml` (transformers+torch CPU) | La root non può avere nuove dipendenze; `docker/detector/detector_adapter.pyproject.toml` attuale ha solo `httpx`. Il container detector-b installa il proprio. |
| A4 | serializzazione traiettoria → testo | Il formato testuale esatto atteso da AgentDoG va verificato su model card/paper (Passo 2 del handoff). È un "unknown" da chiudere col prototipo offline. |
| A5 | migrare `adapter.py`/`evaluate_case.py`/`vendor_proxy.py` in `vendors/aidr/` | Refactor del layout attuale (passo 1). Aggiornare: comando `python -m detector_adapter.vendors.aidr.evaluate_case` in `orchestrator.py:113`, COPY nel Dockerfile detector, import nei test. |
| A6 | COPY selettivo nei Dockerfile | Il container aidr COPY-a solo `vendors/aidr/` + la parte condivisa (se esiste); il container agentdog solo `vendors/agentdog/`. **È questo che rende la separazione fisica reale** — il sottopackage da solo non isola nulla. |

Disciplina obbligatoria (con COPY selettivo diventa meno critica ma resta buona pratica): `agentdog_adapter.py` importa `transformers` **solo lazy dentro il costruttore**, mai a module scope — lo stesso pattern di `adapter.py` che importa `aidr` lazy. Con la separazione fisica l'import cross-vendor è già impossibile per costruzione (i file non coesistono), ma il lazy import protegge anche da import accidentale di dipendenze pesanti a livello di package discovery condiviso.

#### B. Docker

| # | Dove | Perché |
|---|---|---|
| B1 | `docker-compose.yml`: nuovo servizio `detector-b` | Secondo container, nessun conflitto di porte/nomi (nessun servizio espone porte host). |
| B2 | `docker/detector-b/Dockerfile`: python + transformers + torch CPU, niente chiavi, niente proxy | Vendor offline; nessuna `OPENROUTER_API_KEY`, nessuna `HTTPS_PROXY`. |
| B3 | rete di `detector-b`: internal-only o nessuna | È offline: non deve stare su `detector_net` né passare da egress-proxy. |
| B4 | `entrypoint.sh` detector-b: avvia il processo residente che carica il modello | Vedi §1.1(A). Replica `cap_drop: ALL` + `no-new-privileges:true` (parità col container detector). |

#### C. Harness — parametrizzazione del vendor attivo

| # | Dove | Perché |
|---|---|---|
| C1 | `orchestrator.py:113` (`detector_cmd`): nome servizio → parametro | `run_test_case` deve parlare con `detector-b` quando il vendor attivo è agentdog. |
| C2 | `orchestrator.py:108` (marker thin-proxy log): condizionale sul vendor | Il marker scrive in `/var/log/vendor_proxy.jsonl`, che AgentDoG non ha. Va saltato per vendor offline. |
| C3 | `orchestrator.py:135,140,161,166` (4× pkill fallback): pattern + servizio → vendor-aware | Il fallback `pkill -f aidr/providers` non ha equivalente AgentDoG; va reso condizionale o generalizzato. |
| C4 | `orchestrator.py:47` `_error_verdict`: `tool_name="agentic_threat_detection"` → parametro | Un verdict d'errore durante un run agentdog non deve dichiararsi aidr. |
| C5 | `sequence.py:16` `KNOWN_CONTAINERS = ("agent", "detector")` → derivato dal vendor attivo | Open/close e la validazione (`validate_sequence`) devono aprire `detector-b`. È il punto singolo da cui seguono open/close **e** `evidence.collect_case_evidence` (già parametrizzato via argomento, `sequence.py:227`). |
| C6 | `sequence.py` `_fallback_verdict`: `tool_name` hardcoded → parametro | Come C4. |
| C7 | `evidence.py:74` `collect_thin_proxy_log`: condizionale sul vendor | `cat /var/log/vendor_proxy.jsonl` è aidr-specifico; per agentdog è no-op, **sostituito** dal canale I/O del detection loggato dall'adapter (vedi §1.1-D: log completo input/output della chiamata, migliore del proxy log). |

#### D. Preflight

| # | Dove | Perché |
|---|---|---|
| D1 | `preflight.py` + `run_batch.py:302-307` | I probe dei 3 tier aidr (sifter/inspector/embed, `TIER_ENV_VARS`) non si applicano ad agentdog. Nota: il loop già skippa tier senza env var, quindi con `SIFTER_MODEL` ecc. assenti il probe detector diventa no-op — ma restano da sistemare: la riga `checking 4 models... OK` (`run_batch.py:307`) e la riga progress `detector: sifter/inspector/embed` (`run_batch.py:296`), entrambe aidr-specifiche. Il probe dell'agent model resta sempre (il toy agent chiama ancora OpenRouter). |
| D2 | nuovo preflight per vendor offline (§1.1-D) | Per agentdog sostituisce i probe OpenRouter: verificare **presenza del modello su disco** nel container + **hash dei pesi** (`sha256sum` confrontato con la provenance) + **daemon "ready"** prima di aprire il batch. Sfrutta il fatto che il modello è verificabile dall'esterno per costruzione. |

#### E. Provenance

| # | Dove | Perché |
|---|---|---|
| E1 | `provenance.py:12,27-28` `vendor_commit()`: regex su `docker/detector/Dockerfile` `git checkout` | Per agentdog il vendor identifier è la **revisione del modello HF**, non un commit git. Serve un modo per registrare l'identità del vendor attivo. |
| E2 | `provenance.py` campi `sifter_model`/`inspector_model`/`embed_model` | aidr-specifici. Per agentdog servono campi diversi (modello HF + revisione) o un campo generico `vendor_config`. |
| E3 | nuovo campo `vendor`/`tool_name` in provenance → report | Principio 8: il vendor attivo deve essere dichiarato per audit. |
| E4 | hash dei pesi del modello nella provenance (§1.1-D) | La riproducibilità di un modello HF non è garantita dal solo nome repo: serve revisione + **hash del file dei pesi**, verificabile dall'esterno con `sha256sum` (principio 4). "Stesso nome, pesi diversi" vanificherebbe la riproducibilità. |

#### F. Report

| # | Dove | Perché |
|---|---|---|
| F1 | `report.py:92` `render_report(tool_name="agentic-threat-detection")` | Il titolo del report deve dire chi è stato auditato. Il parametro esiste già; va valorizzato dal chiamante col vendor attivo. |
| F2 | `report.py` riga "Vendor-declared numbers" hardcoded (`P=1.0, R=0.667`, 300 sessioni, 42 malicious) | aidr-specifico. Per agentdog: parametrizzare o omettere. |
| F3 | `run_batch.py` `_setup_notes`: "dataset technique coverage: 12/14 vendor techniques" e riga progress `detector: sifter/inspector/embed` | aidr-specifiche. |
| F4 | `regenerate_report.py` | Ricostruisce il report dai raw data + provenance: deve leggere il vendor dalla provenance per renderizzare `tool_name`/vendor-numbers corretti. |

#### G. Metriche — nessun intervento (conferma positiva)

`metrics.py` non referenzia `tool_name` né campi vendor-specifici: fa scoring solo su `label`. Un verdetto agentdog (con `tool_name="agentdog"`) scorre identico. `serialization.verdict_from_dict` (`serialization.py:34-39`) legge `tool_name` genericamente. Questi due moduli sono già vendor-agnostici per costruzione.

#### H. Tassonomia (RISOLTA — vedi scope)

Decisione presa: **nessun mapping, nessuna tassonomia neutra**. Il metro è il label (taxonomy-free). La tassonomia di ciascun vendor si riporta, non si misura. Conseguenze sul codice:

| # | Dove | Perché |
|---|---|---|
| H1 | `Verdict.technique_detected` per agentdog | Resta valorizzato **con la tassonomia nativa di AgentDoG** (es. la diagnosi 3D serializzata), ma la metrica strict e il breakdown per-tecnica **non** la confrontano col ground truth (non c'è griglia comune). La metrica strict diventa intra-vendor: per aidr continua a confrontare `technique_detected == technique_target` (T-code); per agentdog la metrica strict non è definita (o è definita solo sulle sue categorie, da decidere nel design doc se serve davvero). |
| H2 | report: dove finisce la tassonomia | La tassonomia nativa (T-code per aidr, 3D per agentdog) va **stampata nel report come descrizione** di come il vendor vede la sessione, non come cosa misurata. Serve un posto nel report per "tassonomia del vendor" distinto dalla metrica strict. |
| H3 | `TestCase.technique_target` resta aidr-coupled | Non si tocca (nessuna tassonomia neutra). Si dichiara nel report/setup-notes che il dataset è scritto nel linguaggio aidr e che per AgentDoG la copertura delle sue categorie 3D non è garantita (limite di copertura, non bias). |

#### I. Test

| # | Dove | Perché |
|---|---|---|
| I1 | estendere `tests/test_no_vendor_imports.py` per il layout sottopackage: nessun modulo di `vendors/aidr/` importa `transformers`; nessun modulo di `vendors/agentdog/` importa `aidr`; nessuno importa `toy_agent` | Con la separazione fisica l'import cross-vendor è già impossibile per costruzione, ma il test resta come rete di sicurezza contro regressioni future (e copre il caso di package discovery condiviso). |
| I2 | nuovi test per `agentdog_adapter` (serializzazione, normalizzazione verdict) con pattern `importorskip`/fake-pipeline | La suite host non ha transformers; stesso pattern di `test_adapter_agent_event.py` che usa `pytest.importorskip("aidr")`. Niente test di "mapping tassonomia": la tassonomia si riporta, non si misura (vedi scope). |
| I3 | test harness che hardcodano `detector` (`test_orchestrator.py`, `test_evidence.py`, `test_sequence.py`, `test_run_batch.py`) → parametrizzare | Seguono la parametrizzazione C. |
| I4 | eventuale `run_adapter_tests.sh` per detector-b | Per i test gated da transformers, come `docker/detector/run_adapter_tests.sh` per aidr. |

#### J. Documentazione

`README.md`, `docs/notes/pi-onboarding-reference.md` (dice "3 container"), `docs/design/registro-limiti-aperti.md` (nuovi limiti: copertura tassonomia non garantita per agentdog; costo per vendor offline = 0 con CPU-time non misurato; eventuale non-determinismo del modello locale) vanno aggiornati quando il servizio `detector-b` è stabile.

---

### 1.3 Sequenza di esecuzione proposta

1. **Design doc** per le decisioni aperte (§1.4) + council (tier Light: skeptic+pragmatist+griller).
2. **Prototipo offline** (A4 + guardrail): serializzazione + chiamata modello, verifica output parsabile.
3. **Adapter + entrypoint + pyproject detector-b** (A1–A3).
4. **Container + processo residente** (B1–B4).
5. **Parametrizzazione harness** (C–F).
6. **Test** (I) + suite verde.
7. **Run di verifica** + report + aggiornamento registro limiti.

### 1.4 Domande aperte (da chiudere nel design doc)

1. **Formato esatto di serializzazione** della traiettoria per AgentDoG (da verificare su model card/paper).
2. ~~Processo residente vs per-invocazione~~ **RISOLTA** (vedi §1.1-A): il pattern è già `vendor_proxy` + `reused`; daemon residente nel container, N `exec` leggeri. Resta solo la verifica empirica del formato d'interfaccia (server vs funzione, da model card) e la misura delle latenze per ritarare `detector_timeout_s`/deadline interna. `per-case` su vendor locale = anti-economico, dichiarato come limite.
3. ~~Mapping tassonomia~~ **RISOLTA** (vedi scope e §H): nessun mapping, nessuna tassonomia neutra. Resta solo da decidere **se la metrica strict ha senso per agentdog** (diagnostica intra-vendor) o se per agentdog si pubblica solo la primary.
4. ~~Forma del parametro "vendor attivo"~~ **RISOLTA** (vedi scope): `AUDIT_VENDOR` passato **via CLI esplicita** a ogni `run_batch` (non persistente in `.env`); propagato a orchestrator/sequence/evidence/provenance/report/preflight; scritto in provenance come fonte di verità per la rigenerazione. Resta da definire nel design doc solo il *meccanismo interno di propagazione* (firma di `run_test_case`/`execute_sequence`), non il principio.
5. ~~Caricamento modello a build-time vs runtime~~ **RISOLTA** (vedi scope): **baked** nel layer Docker, coerente con l'offline; revisione + hash fissati al build e registrati in provenance (E4).
6. **Layout del pacchetto (RISOLTA — sottopackage + COPY selettivo)**: `src/detector_adapter/vendors/{aidr,agentdog}/`, con COPY selettivo nel Dockerfile così che i due container restino fisicamente distinti. Esecuzione in due passi: (1) refactor aidr sul nuovo pattern (suite verde a ogni passo), (2) AgentDoG come aggiunta. Il refactor non è lungo né rischioso: ~4 file da spostare + punti di aggancio (comando `python -m detector_adapter.vendors.aidr.evaluate_case` in orchestrator, COPY nei 2 Dockerfile, `run_adapter_tests.sh`, import nei test), e la suite 468 fa da rete di sicurezza. Il beneficio è strutturale e duraturo (terzo vendor = pura aggiunta), coerente col principio 8.
7. **Cost/cost_usd per vendor offline (RISOLTA)**: costo marginale per chiamata = **0** (modello locale, nessuna API). `in_tokens`/`out_tokens`/`cost_usd` restano `None` per agentdog. Non è una decisione da prendere: è una riga nel registro limiti ("per vendor offline il costo variabile è zero; la risorsa consumata è CPU-time, non misurata").

---

## Parte 2 — Review critica dell'analisi

Rilettura con occhio critico, alla ricerca di ciò che manca, di ciò che è sovra-specificato e di ciò che è sotto-specificato.

### 2.1 Cosa l'analisi copre bene

- L'inventario dei punti hardcoded è **completo e verificato sul codice reale** (non a memoria): i riferimenti file:riga di C1–C7, D1, E1–E3, F1–F4 sono corretti e riconducibili.
- Ha colto la conferma positiva più importante: **`metrics.py` e `serialization.py` sono già vendor-agnostici**, quindi lo scoring non è il collo di bottiglia (contraddice l'impressione iniziale che servisse toccare la metrica).
- Ha separato correttamente i tre fatti strutturali (§1.1) dai touchpoint meccanici (§1.2): questo è il valore reale dell'analisi, perché dice *dove sta la difficoltà*, non solo *dove sta il codice*.

### 2.2 Lacune trovate rileggendo (ordinate per gravità)

1. **La tassonomia accoppiata ad aidr: RISOLTA in sessione — non è un debito da ripagare con una tassonomia neutra, è un dato da dichiarare.** La prima stesura di questa review suggeriva "tassonomia neutra nel dataset + mapping per-vendor". La discussione con l'utente l'ha corretto: una tassonomia neutra sarebbe una *terza ontologia nostra imposta a entrambi*, cioè il bias self-reported in versione certificatore. Il confronto legittimo è vendor ↔ ground truth (label, per-effetto), mai vendor ↔ vendor. Quindi: si misura solo sul label; la tassonomia di ciascun vendor si riporta, non si misura; nessun mapping. Il dataset resta aidr-coupled e lo si **dichiara** come limite di copertura per AgentDoG.

2. **Voce "costo/pricing" per vendor offline: RISOLTA — costo marginale zero.** Il costo per chiamata è 0 (modello locale). `cost_usd` resta `None` per agentdog. Non è una decisione strutturale: è una riga nel registro limiti. La review originaria l'aveva sopravvalutata.

3. **Layout del pacchetto: RISOLTA in sessione — sottopackage + COPY selettivo, in due passi.** La stesura originaria di questa review aveva due posizioni successive, entrambe superate dalla discussione: prima "sottopackage" per pura purezza, poi "flat + YAGNI" per economia. L'errore di framing era applicare lo YAGNI a un requisito che è nel DNA del progetto (ente N-vendor, SPIRIT.md al plurale). Il punto decisivo emerso dalla discussione è che **il sottopackage da solo non isola nulla**: finché il Dockerfile fa `COPY src/detector_adapter` intero, spostare i file cambia solo l'estetica. La separazione fisica richiede sottopackage **+ COPY selettivo** (container aidr senza i byte di agentdog, e viceversa). Esecuzione in due passi (prima aidr sul nuovo pattern, poi AgentDoG), col refactor a basso rischio perché la suite 468 fa da rete di sicurezza.

4. **Preflight per vendor offline: direzione stabilita da §1.1-D — da scrivere nel design doc, non più aperta.** Il preflight attuale verifica modelli OpenRouter con probe live. Per agentdog il controllo equivalente sfrutta il fatto che il modello è verificabile dall'esterno: **presenza del modello su disco + hash dei pesi (`sha256sum`) + daemon "ready"** prima di aprire il batch. Vedi nuovo touchpoint D2.

5. **Timeout/deadline: ritarare e misurare, non decidere.** Con il daemon residente (reused) il load è una tantum e l'inference 0.8B CPU sta comodamente dentro `detector_timeout_s=180`; le latenze reali vanno **misurate sul primo run**, non assunte. Il punto serio era il caso per-invocazione (31 ricariche), ora escluso dal pattern `reused` + daemon. Il falso positivo del circuit breaker resta un rischio solo per il lifecycle `per-case` (che per vendor locale è anti-economico e dichiarato come limite), non per il default `reused`.

6. **`analyze_run.py`/`inspect_run.py`: l'analisi li cita solo di sfuggita.** Da verifica: `analyze_run.py` mostra `detector_label`/`detector_technique` (colonne "detector") leggendo il verdetto genericamente — probabilmente funziona già con un `tool_name="agentdog"`, ma va confermato con un test sul dato reale. Non è elencato come touchpoint, e dovrebbe esserlo almeno come "verifica".

7. **Provenienza del modello HF come artefatto: direzione stabilita da §1.1-D — da scrivere nel design doc, non più aperta.** La provenance oggi registra `vendor_commit` (git). Per agentdog serve **revisione del modello HF + hash del file dei pesi**, verificabile dall'esterno con `sha256sum` (principio 4): "stesso nome, pesi diversi" vanificherebbe la riproducibilità. Vedi nuovo touchpoint E4.

### 2.3 Cosa resta da fare prima di toccare codice

1. **Design doc** che chiuda l'unica decisione metodologica ancora aperta: "la metrica strict ha senso per agentdog?" (domanda #3 post-risoluzione). Tutto il resto è risolto in sessione (tassonomia, costo, layout, processo residente, configurazione, modello baked, selezione vendor via CLI) o con direzione già fissata (preflight offline D2, provenance HF E4, §1.1-D). Restano da chiudere col prototipo offline: formato serializzazione + formato d'interfaccia (server vs funzione) + misura latenze + verifica determinismo — il prototipo è **il primo esperimento**.
2. Il council va invocato sul design doc, **non** su questa analisi (che è una mappa, non una proposta risolutiva).
3. Aggiornare `registro-limiti-aperti.md` con: copertura tassonomia non garantita per agentdog (dataset aidr-coupled), costo per vendor offline = 0 (CPU-time non misurato), eventuale non-determinismo del modello locale. Sono limiti *dichiarati*, non difetti nascosti.

### 2.4 Verdetto sulla completezza

Dopo la risoluzione in sessione di tassonomia, costo, layout, processo residente, configurazione, modello baked, selezione vendor via CLI, e la direzione su preflight offline e provenance HF (§1.1-D), l'analisi è **completa sia sul piano meccanico che metodologico**. Resta da chiudere nel design doc **una** decisione metodologica (metrica strict per agentdog); il resto è verifica empirica col prototipo (formato serializzazione, formato d'interfaccia server-vs-funzione, latenze, determinismo). La Parte 1 resta la checklist di implementazione; la Parte 2 ora riflette lo stato decisionale reale.
