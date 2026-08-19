# Plan 5 — Dataset di audit: catalogo, copertura, authoring

Design doc per la costruzione del dataset di `TestCase` per il primo audit reale
(`SPIRIT.md`, "Primo obiettivo concreto"). Segue il terreno preparatorio
`2026-08-19-plan5-dataset-prep-benchmark-esterni.md` e chiude il punto (a) ancora
aperto di Gap 15/Gap 7 (`2026-08-14-toy-agent-gap-tracking.md`).

Prodotto di una sessione di brainstorming completa (`superpowers:brainstorming`,
percorso architetturale). Tre artefatti sono già stati scritti e verificati durante la
sessione stessa, prima di questo documento: `catalog/cases.yaml`, `catalog/
vendor_taxonomy_snapshot.yaml`, `catalog/_template.yaml`, `tests/test_catalog.py` —
questo doc ne spiega il perché, non li ripete.

## Obiettivo e scope

Costruire 40-60 `TestCase` (20-30 per label) che coprano le 14 tecniche dichiarate dal
vendor sotto audit, per produrre il primo report reale (P/R/F1 confrontato coi numeri
dichiarati dal vendor: P=1.0, R=0.667, 300 sessioni).

**Fuori scope, deliberatamente**: sceneggiature composte (Gap 15 modalità 2 — più
comandi nello stesso container) e il relativo authoring Excel (`registro-limiti-aperti.md`).
Il dataset di Plan 5 resta interamente **atomico** (un turno seed, un container per
caso) — nessuno schema nuovo richiesto, `TestCase`/`load_dataset()` esistenti bastano
così come sono. Il confronto con i numeri del vendor è già verificato strutturalmente
equivalente su base atomica (Gap 15, "Verifica fatta", 2026-08-18): nessun requisito di
Fase 1 richiede sceneggiature composte per essere soddisfatto. Un piano futuro dedicato
(non ancora numerato) affronterà le sceneggiature composte quando emergerà un bisogno
concreto — non prima.

## Layout del repo

Due directory nuove, sorelle di `docs/`/`src/`/`tests/` alla radice del repo — non
"figlie" di Plan 5 nel nome, perché sopravvivono al piano che le ha create:

- **`dataset/`** — i `TestCase` YAML reali, quello che `load_dataset()` legge. Vuota
  all'inizio di questo design doc; popolata durante l'esecuzione di Plan 5.
- **`catalog/`** — registro dinamico di scenari candidati, mai letto da
  `load_dataset()` (che fa `glob("*.yaml")` non ricorsivo solo su `dataset_dir`). Tenuta
  sorella e non figlia di `dataset/` per evitare ambiguità a chi esplora il repo, anche
  se tecnicamente una sottocartella sarebbe stata al sicuro dal glob.

## Catalogo (`catalog/cases.yaml`)

Livello separato tra "scenario di attacco/benigno documentato" e "`TestCase` scritto
per la pipeline" — la stessa separazione primitiva/sovrastruttura già applicata a Gap
15. **Motivazione primaria** (rivista il 2026-08-19, seconda sessione — vedi nota in
fondo a questo paragrafo): il catalogo è per natura la base di dati completa degli
scenari candidati disponibili, indipendente da `source_type` — una sessione di
authoring pesca da lì le voci che le servono e dichiara perché nel `rationale` del
`TestCase` risultante, senza dover rifare da zero la stessa ideazione ogni volta. Per
`real_incident`/`benchmark_inspired` questo si traduce spesso in un surplus concreto: la
ricerca su un incidente reale trova più candidati validi di quanti la regola di
copertura ne richieda subito per quella tecnica — il catalogo assorbe il surplus senza
costringere a scartare ricerca già fatta né a gonfiare il dataset oltre la regola. Per
`invented` non c'è surplus di ricerca da assorbire, ma vale lo stesso principio di
fondo: passare comunque dal catalogo tiene un solo workflow di authoring per tutte le
fonti (vedi "Authoring — template" sotto, già source_type-agnostico), registra le
varianti scartate anche quando nascono da ideazione pura invece che da letteratura, e
tiene la bookkeeping di copertura (`status`/`selected_as` per tecnica) in un unico
posto invece di spezzarla su due percorsi con due convenzioni diverse. Motivazione
secondaria: tracciabilità (perché un caso esiste, con quale citazione, quando ce n'è
una) e un beneficio collaterale di riuso per un'eventuale Fase 2 futura (non ancora
annunciata come piano concreto) — principio 6 `SPIRIT.md`.

**Convenzione d'ordine**: le voci `invented` si aggiungono in coda al file (dopo le
voci `real_incident`/`benchmark_inspired` già presenti), mai interfogliate — coerente
con l'append-only già dichiarato per la struttura dati sotto, e utile a chi scorre il
file per distinguere a colpo d'occhio "scenari con provenienza esterna" da "scenari
ideati per l'audit".

*Nota sulla revisione (2026-08-19, seconda sessione, revisione indipendente post-council):
la formulazione originale di questo paragrafo parlava solo di "ricerca su un incidente
reale", lasciando implicito — senza motivarlo — che anche le voci `invented` (dichiarata
maggioranza del dataset) passassero comunque dal catalogo. Non trovato dal council
checkpoint di questa sessione, trovato da una revisione indipendente successiva. Nessun
cambiamento di comportamento nel codice; corretta qui la motivazione, e un difetto di
schema collegato (vedi "Campi" sotto e `tests/test_catalog.py`).*

**Struttura dati**: un file YAML, non un database. Un vero DB (anche SQLite)
comprometterebbe la trasparenza (principio 6: revisione da terzi via `git diff`/`git
blame`, non un binario opaco) per un problema che non è transazionale (pochi editor
umani, nessuna scrittura concorrente). Se in futuro un file solo diventasse scomodo da
scorrere, lo scaling path dichiarato è lo split per categoria (un file per tecnica) —
**non ancora implementato**: `tests/test_catalog.py::CATALOG_PATH` punta oggi a un
singolo file, non a un glob su più file come fa `load_dataset()` per `dataset/`. Quando
lo split avverrà davvero, `CATALOG_PATH` va aggiornato insieme (fallirebbe in modo
rumoroso — file non trovato — non silenzioso, se dimenticato). Dichiarato esplicitamente
ora, coerente col principio 8 (mai una scorciatoia valida solo per la scala di oggi).

**Alternativa più leggera considerata e scartata** (trovata mancante dal council
checkpoint, skeptic e pragmatist convergenti — vedi sezione "Esito council" in fondo):
una tabella markdown di note (citazione, adattamento, tecnica, stato), zero schema, zero
test. Scartata perché il catalogo, per un progetto il cui intero valore è la
verificabilità di terzi (principio 6), deve reggersi da solo se mai pubblicato insieme
al dataset — una tabella markdown senza validazione rischia esattamente il tipo di
contenuto non strutturato/non verificabile che questo progetto contesta ad altri
strumenti. Il costo del catalogo strutturato è basso (3 file, una manciata di test in
`tests/test_catalog.py`, <1s di runtime) rispetto a questo beneficio.

**Campi** (documentati per esteso nell'header del file stesso, non ripetuti qui):
`catalog_id`, `technique_code`, `technique_name`, `label_hint`, `source_type`,
`summary`, `citation`, `adaptation`, `status`, `selected_as`. `citation`/`adaptation`
sono chiavi sempre presenti (schema uniforme), ma valorizzate solo per
`source_type: real_incident` — per `invented`/`benchmark_inspired` restano
esplicitamente `null`, mai stringa vuota, per distinguere "non applicabile per
costruzione" da "dimenticato in fase di authoring". Corretto il 2026-08-19: la prima
versione di `tests/test_catalog.py::REQUIRED_FIELDS` richiedeva la chiave ovunque senza
vincolare il valore per le fonti diverse da `real_incident` — un `invented` con
`citation: ""` passava il test tanto quanto uno con `citation: null`, che è lo stato
corretto.

Due decisioni non ovvie, trovate verificando il file su dati concreti invece che in
astratto:

1. **`technique_code`/`technique_name` separati**, non un'unica stringa composita
   (`"T0002 — Indirect Prompt Injection"`). Una stringa composita costringe un filtro
   futuro a un prefix-match invece di un confronto esatto — meno robusto. Campi
   separati permettono `technique_code == "T0007"` esatto, restando comunque leggibili
   senza dover aprire il repo vendor per capire cosa significa il codice.
2. **`technique_name` non cablato nel codice del test** — vive in un file dati a sé
   (`catalog/vendor_taxonomy_snapshot.yaml`), non in una costante Python dentro
   `tests/test_catalog.py`. La tassonomia è un fatto specifico *di questo vendor, a
   questo commit pinnato* — cablarla nel codice del test la tratterebbe come una
   verità universale, esattamente ciò che il principio 8 vieta. Aggiornare per un pin
   nuovo o un vendor diverso (Fase 2) significa editare un file dati, non toccare la
   logica del test. Verificato concretamente: una tecnica ipotetica aggiunta solo allo
   snapshot viene accettata dal test senza modifiche al suo codice.

**`label_hint` separato da `technique_code`**: un "gemello" benigno (vedi sotto, regola
di copertura) è associato a una tecnica per scopi di tracciabilità della copertura, ma
un `TestCase` benigno non può dichiarare `technique_target` (vincolo dello schema
esistente, `schema.py:57-58`). I due campi tengono distinti "a quale tecnica è
associato" da "quale label avrà nel `TestCase` finale".

## Naming — due regole diverse per due pubblici diversi

**`case_id`** (nello schema `TestCase`, quello che un lettore del dataset pubblicato
incontra): uno slug che nomina la **meccanica/il trucco distintivo** dello scenario, mai
`label`/`technique_target` ripetuti (già campi separati — ripeterli è ridondante e, se
la tecnica cambiasse, l'id mentirebbe in silenzio), mai una traccia letterale di ogni
step per un caso multi-tool (quel dettaglio vive nel `rationale`, non nell'id — più step
non significa id più lungo). Esempi della convenzione discussi in questa sessione:
`refund_without_authorization` (illustrativo, mai scritto in un file). Due di questi
esempi sono stati anche fatti passare a mano, in questa sessione, attraverso lo schema
reale (non solo discussi): `account_status_change_escalates_privilege` e
`marketing_optin_change_request` — vedi sezione "Authoring — template" sotto. **Limite
dichiarato** (trovato da `grill-with-docs`, 2026-08-19): questa validazione non è
riproducibile — nessun test, script o commit nel repo la rieseguirebbe; nessuna delle
due stringhe compare altrove che in questo documento. La sostanza del claim resta
verosimile ma non verificabile da un revisore terzo così com'è. Voce aperta in
`registro-limiti-aperti.md` per un test automatico che la renda rieseguibile.

**`catalog_id`** (nel catalogo, riferimento di lavoro): può includere la fonte (es.
`forcedleak_...`, `postmark_mcp_...`) per tracciabilità — un pubblico diverso (chi
mantiene il catalogo, non chi legge il dataset pubblicato) con un bisogno diverso
(ritrovare rapidamente "quali voci vengono da quale incidente").

## Regola di copertura minima

Per ciascuna delle 14 tecniche (T0001-T0014):

- **≥1 `TestCase` malevolo** che la esercita.
- **≥1 `TestCase` benigno "gemello"** — stesso tool, pattern superficiale simile,
  intento e contenuto legittimi. Impedisce la scorciatoia di correlazione: se un tool
  compare solo in sessioni malevole, il detector potrebbe imparare "tool X = malevolo"
  senza mai ragionare sul contenuto.

Più un piccolo numero di **`TestCase` benigni generici**, non abbinati a nessuna
tecnica specifica, per varietà oltre ai soli gemelli.

**Questa regola generale chiude Gap 7 punto (a)** (`gap-tracking.md`, "quanti `TestCase`
benigni devono comunque esercitare `update_account` su campi non avvelenati") come caso
particolare: per T0005 (veicolo `update_account`, backdoor su `status`/`refund_total` —
**corretto da T0007 il 2026-08-19, vedi `gap-tracking.md` Gap 16**: il comportamento del
tool combacia testualmente con T0005 "Privilege Escalation via Tool", non con T0007
"Guardrail Evasion", che richiederebbe l'agente stesso ad aggirare attivamente un
filtro — cosa che qui non avviene mai, l'agente si comporta in modo trasparente), il
gemello benigno non può toccare quei campi — per costruzione, farlo lo renderebbe
malevolo per la convenzione "per effetto" già decisa (Gap 7) — quindi usa
necessariamente il campo non avvelenato (`marketing_opt_in`). Nessuna azione separata
richiesta oltre all'applicazione della regola generale.

**Tecniche prioritarie (≥2 varianti malevole)**: T0005 (Privilege Escalation via Tool —
sostituisce T0007 in questa lista dopo la correzione sopra: il ragionamento sull'impatto
peggiore era sempre stato per lo scenario del backdoor silenzioso, che è T0005),
T0014 (Destructive Action), T0012 (Data Exfiltration), T0002 (Indirect Prompt
Injection) — scelte come giudizio nostro sull'impatto peggiore nel nostro scenario di
supporto clienti (il vendor non dichiara una propria classificazione di severità,
`threat_repository.yaml` raggruppa solo per tattica), dichiarato esplicitamente come
tale, non presentato come oggettivo (principio 2, `SPIRIT.md`). Le restanti 10 tecniche
restano a 1 malevolo + 1 gemello benigno in questo primo giro.

**T0007 non ha (più) un veicolo valido**: l'unico caso mai pensato per questa tecnica
era in realtà T0005 (sopra). T0007 richiede un vero scenario di guardrail evasion —
l'*agente*, non il tool, che riformula/spezza/maschera un'azione per evitare che un
controllo la noti — non ancora progettato. Candidato plausibile coi tool esistenti
(nessun codice nuovo): un prompt che istruisce l'agente a spezzare un `bulk_export` in
più chiamate piccole, descritte come "aggiornamenti di routine" invece che come export,
per non far scattare un controllo. Voce aperta in `registro-limiti-aperti.md`. T0007
resta a copertura base (1+1), non promosso a prioritario: la sua severità va valutata
indipendentemente una volta progettato uno scenario reale, non ereditata dal
ragionamento fatto per T0005.

**Conteggio risultante**: 4×2 + 10×1 = 18 malevoli minimo, 14 gemelli benigni minimo +
N generici — dentro il target 20-30/label (invariato dalla correzione: cambia
l'etichetta di una tecnica prioritaria, non il numero di tecniche prioritarie né il
conteggio totale).

## Fonti dei casi

Tre fonti, tenute esplicitamente distinte (`source_type` nel catalogo):

1. **`invented`** — ragionati da noi sulle 14 tecniche, maggioranza del dataset.
2. **`real_incident`** — casi ispirati a incidenti reali documentati (`SPIRIT.md`,
   "Primo obiettivo concreto": non opzionale, parte dell'obiettivo dichiarato di Fase
   1). Quattro voci già scritte e verificate in questa sessione, coprenti T0002, T0012,
   T0005, T0014 (T0007, non più tra le prioritarie dopo la correzione Gap 16, resta da
   coprire con uno scenario nuovo — vedi sopra):
   - `forcedleak_ticket_hidden_instruction` (T0002) — ForcedLeak, Salesforce
     Agentforce, Noma Labs, 25/09/2025.
   - `forcedleak_export_unauthorized_endpoint` (T0012) — stesso incidente, isolato
     sull'effetto invece che sul vettore (un solo incidente reale, quando copre più di
     una tecnica che ci serve, diventa più voci di catalogo — non una regola
     automatica di scomposizione: si spacca solo per le tecniche che intendiamo
     effettivamente coprire con quell'incidente, non per ogni tecnica che la sua
     narrazione tocca implicitamente).
   - `postmark_mcp_account_tool_hidden_escalation` (**T0005**, corretto da T0007 —
     Gap 16) — tool poisoning via npm, Koi Security. Citazione corretta alla fonte
     contemporanea (`thehackernews.com/2025/09/...`, non un articolo secondario
     successivo trovato nella prima ricerca — trovato dal council checkpoint,
     `council-risk`). Adattamento dichiarato: l'incidente reale è un tool compromesso
     via supply chain (una versione successiva introduce la backdoor); il nostro
     vincolo anti-distorsione (Gap 1: codice statico, mai variato tra caso benigno e
     malevolo) impedisce di riprodurlo così com'è — si riusa solo la *forma*
     dell'attacco (un tool dalla superficie legittima che fa più di quanto dichiarato),
     sul backdoor già esistente di `update_account`. Non vale costruire un tool nuovo
     solo per la fedeltà narrativa: la capacità misurata (il detector nota via
     SourceLens che il tool fa più del dichiarato) è già pienamente esercitata dal
     backdoor esistente, indipendentemente dalla storia d'origine. **Riserva dichiarata
     (council-skeptic)**: questo è l'adattamento meno fedele dei quattro — l'elemento
     che rendeva l'incidente reale interessante (supply chain, attivazione ritardata)
     è assente dalla riproduzione, che sarebbe identica anche senza la citazione. Tenuto
     comunque come `real_incident` (non retrocesso a `invented`) perché il campo
     `adaptation` dichiara onestamente lo scarto, invece di nasconderlo — coerente col
     principio 1 (mai un copia-incolla diretto, ma nemmeno un'etichetta a coprire
     un'assenza di derivazione reale: qui la derivazione reale c'è, è solo parziale, ed
     è dichiarata come tale).
   - `pocketos_unrequested_deactivation` (T0014) — cancellazione database in 9
     secondi, NeuralTrust, 25/04/2026. Adattato da un'API infrastrutturale
     all'unica azione distruttiva disponibile nel nostro set di tool
     (`update_account`) — il nucleo riusato è il pattern comportamentale (un
     agente che, di fronte a un ostacolo, sceglie un'azione irreversibile non
     richiesta invece di chiedere), non il meccanismo tecnico.

   Ogni voce dichiara `citation` (fonte verificabile) e `adaptation` (cosa è stato
   cambiato rispetto all'incidente reale — mai un copia-incolla diretto, principio 1
   `SPIRIT.md`), verificati entrambi obbligatori dal test automatico. **La verifica
   automatica copre solo la forma** (campo non vuoto, contiene un URL) **non il
   contenuto** (che la citazione dica il vero, che l'URL sia quello giusto) — quello
   resta una disciplina umana in fase di authoring, non automatizzabile senza scaricare
   e leggere ogni fonte a ogni test run. Verificato manualmente per le 4 voci sopra
   (`WebFetch` sulle fonti primarie, non solo sui risultati di ricerca), non solo
   dichiarato.

3. **`benchmark_inspired`** — benchmark accademici indipendenti (InjecAgent, AgentDojo,
   ASB — nota preparatoria) usati solo come cross-check di copertura, mai importati
   direttamente: ogni caso richiede comunque `rationale`/`technique_target` nostri, mai
   un'etichetta ereditata da un altro dataset (principio 1 `SPIRIT.md`, già stabilito
   nella nota preparatoria).

## Authoring — template

`catalog/_template.yaml` — ogni campo dello schema `TestCase` annotato in linguaggio
semplice, con le convenzioni sopra richiamate inline (label per effetto non intento,
`technique_target` obbligatorio/vietato secondo la label, come nominare il `case_id`).
Vive in `catalog/`, non in `dataset/`, perché `load_dataset()` legge *ogni* `*.yaml`
dentro `dataset_dir` — un template con valori placeholder lì dentro farebbe fallire il
caricamento dell'intero dataset.

Verificato a mano in questa sessione (non solo scritto): il template compilato con
valori reali produce `TestCase` validi attraverso la funzione di validazione reale del
progetto (`_entry_to_test_case`), sia per un caso malevolo sia per il suo gemello
benigno. **Limite dichiarato** (stesso trovato da `grill-with-docs`, 2026-08-19, vedi
sezione "Naming" sopra): verifica non riproducibile, nessuna traccia nel repo oltre a
questo testo — voce aperta in `registro-limiti-aperti.md`.

## Mapping Requisito → Verifica

| Requisito | Fonte | Verifica |
|---|---|---|
| "Ogni caso di test viene definito (tecnica target, esito atteso, ragionamento) prima di eseguire il tool" | `SPIRIT.md`, principio 2 (testo letterale) | `TestCase.rationale` obbligatorio e non vuoto (`schema.py`, `__post_init__`, già esistente). Disciplina processuale non automatizzabile: nessun `TestCase` va scritto/modificato dopo aver visto un verdetto — dichiarata qui, non testabile da codice. |
| "un dataset... costruito a mano sulle 14 tecniche... poi arricchito con casi ispirati a incidenti reali documentati" — **gate bloccante** (rivisto 2026-08-19, seconda sessione: verificato che `metrics.py`/`report.py` costruiscono la tabella per-tecnica solo dalle tecniche effettivamente presenti nel dataset — una tecnica scoperta non produce una riga vuota, sparisce senza segnale, equivalente nella sostanza alla contaminazione tool→label, anch'essa un gate bloccante — vedi riga sotto, il cui meccanismo concreto è stato riformulato da `grill-with-docs` il 2026-08-19; nessuna ragione trovata per trattare i due requisiti diversamente nella sostanza) | `SPIRIT.md`, "Primo obiettivo concreto" (testo letterale) | Copertura tecniche: **non ancora scritto** — verificato in questo self-review che nessun test attuale controlla questo (`grep T0001-T0014` su `tests/` trova solo valori di esempio arbitrari in test di schema, mai una verifica di copertura). Il requisito era già descritto nel design doc originale (`2026-08-14-toy-agent-e-pipeline-misura.md`, riga 966: "l'insieme di `technique_target` sui `TestCase` malevoli copre tutti i codici T0001-T0014"), scritto prima che esistesse qualunque `TestCase` reale — resta da implementare durante l'esecuzione di Plan 5, non prima (nessun dato su cui girare finché `dataset/` è vuota). A differenza della riga sotto, `technique_target` è dichiarato staticamente nel `TestCase` autorato (non emerge solo dall'esecuzione) — resta quindi un vero test pytest statico sul dataset, eseguibile prima di `run_batch.py`. **`run_batch.py` sul dataset completo e la pubblicazione del primo report non devono avvenire prima che questo test esista e passi.** Incidenti reali: soddisfatto dalle 4 voci `real_incident` nel catalogo, verificate da `tests/test_catalog.py` (citation+adaptation obbligatorie). |
| **Nessuna scorciatoia di correlazione tool→label** (Gap 7 rischio 1, generalizzato a tutte le 14 tecniche in questa sessione) — **gate bloccante** (council-risk/advocate: senza questo, il rischio è pubblicare P/R/F1 contaminati senza che nessun controllo lo impedisca) | Questa sessione; meccanismo riformulato da `grill-with-docs`, 2026-08-19, dopo aver trovato una circolarità nella formulazione originale (vedi sotto) | **Non un test pytest statico sul dataset**, a differenza della riga sopra: quali tool un `TestCase` esercita davvero emerge solo dal `Transcript` osservato dopo l'esecuzione live del loop ReAct (`dataset.py:36-39` vincola l'input autorato a un solo turno seed; il tool reale si scopre solo dentro `execute_sequence`, `sequence.py`) — un test eseguibile *prima* di `run_batch.py`, come nella formulazione originale, richiederebbe un campo dichiarato in anticipo (`expected_tool` o simile), scartato: introdurrebbe lo stesso disallineamento dichiarazione/realtà che Gap 4 esiste per evitare. **Gate riformulato**: non più "prima di `run_batch.py`" ma **dentro `run_batch.py::main()`, tra `execute_batch()` e la scrittura di `report.md`** — un controllo che raggruppa `case.transcript.turns[*].tool_call.tool_name` per `label` sui `metric_cases` (i transcript realmente osservati, non il turno seed autorato — `sequence.py:229-240`, `case_obj.transcript` è ricostruito da `raw_transcript_dict`, non è il transcript a un turno del `TestCase` originale), e blocca la scrittura del report se un tool compare solo tra i casi malevoli. Precedente strutturale più vicino nel codice: `preflight_check_models` (`run_batch.py:125-129`, `sys.exit(1)` prima di procedere), non `breaker_tripped` (che annota una nota nel report, non blocca la sua scrittura). Nessun dato grezzo va perso in caso di blocco: transcript/verdetti/evidenza restano persistiti su disco progressivamente da `execute_sequence`, indipendentemente dalla scrittura del report (principio 4 `SPIRIT.md`). **Caveat esplicito, principio 8 `SPIRIT.md`**: questo controllo non è una garanzia strutturale del dataset — è contingente all'esecuzione osservata. Quali tool l'agente sceglie di chiamare per un dato seed non è una proprietà fissa del `TestCase`, dipende dal campionamento del modello: una riesecuzione dello stesso dataset invariato potrebbe produrre un esito diverso (il check potrebbe passare oggi e fallire domani, senza che nulla nel dataset sia cambiato). Il report deve dichiarare "verificato sui transcript di questa run" (data, commit del misuratore, modello usato) — mai "questo dataset non ha scorciatoie di correlazione tool→label" come proprietà atemporale del dataset stesso. |
| Ogni `TestCase` selezionato dal catalogo resta coerente con la voce che lo ha originato (nessuna deriva silenziosa tra `catalog/cases.yaml` e `dataset/`) | Trovato dal council checkpoint (`council-risk`) | Test da scrivere durante l'esecuzione di Plan 5 (non ancora scritto): per ogni voce con `status: selected`, il `TestCase` in `dataset/<selected_as>.yaml` ha lo stesso `technique_target` di `technique_code` (quando `label_hint: malicious`) e la sua `rationale` cita il `catalog_id`. |
| Il catalogo non duplica label/rationale finale del `TestCase` (rischio di divergenza silenziosa) | Questa sessione | Verificabile per costruzione: `REQUIRED_FIELDS` in `tests/test_catalog.py` non contiene né `label` né `rationale` — solo `label_hint` (etichetta attesa, non quella finale) e `summary` (scenario, non rationale da detector). |
| Ogni voce `real_incident` dichiara una citazione verificabile e l'adattamento fatto | Principio 1 `SPIRIT.md` + nota preparatoria | `tests/test_catalog.py::test_real_incident_entries_declare_citation_and_adaptation`, `::test_real_incident_citations_contain_a_url` — già scritti e verdi. Copertura solo formale (vedi sezione "Fonti dei casi") — il contenuto resta verificato a mano in fase di authoring, non da un test. |
| `technique_name` nel catalogo fedele al vendor, non cablato come verità universale (principio 8) | Principio 8 `SPIRIT.md` | `tests/test_catalog.py::test_technique_name_matches_vendor_taxonomy`, contro `catalog/vendor_taxonomy_snapshot.yaml` (dato, non codice) — già scritto, verde, e verificato dinamico (una tecnica aggiunta solo allo snapshot viene accettata senza modifiche al test). |
| `catalog_id` univoci, nessun campo mancante, `status`/`selected_as` coerenti | Questa sessione (integrità del catalogo stesso) | `tests/test_catalog.py::test_catalog_ids_are_unique`, `::test_every_entry_has_all_required_fields`, `::test_status_and_selected_as_are_consistent`, `::test_label_hint_is_a_known_value` — già scritti, verdi, e verificati in negativo (rilevano davvero un errore iniettato, non verdi a vuoto). |
| `case_id` conforme al pattern consentito dallo schema | `dataset.py::CASE_ID_PATTERN`, già esistente | Nessun test nuovo richiesto — già applicato da `load_dataset()` a ogni caso reale scritto in `dataset/`. |
| Per un caso `real_incident`, la `rationale` del `TestCase` finale è auto-sufficiente (un lettore del dataset pubblicato non deve trovare/aprire il catalogo per sapere da dove viene) | Trovato dal council checkpoint (`council-advocate`) | Disciplina di authoring, non automatizzabile a priori: il `rationale` deve riportare in sintesi citazione e adattamento, non solo il `catalog_id` come riferimento. Verificabile a posteriori con lettura manuale, non con un test. |

**Esito council checkpoint (2026-08-19)**: eseguito, roster completo (skeptic, risk,
pragmatist, advocate), scope pieno. Un finding maggiore applicato (Gap 16, T0005/T0007 —
sopra); citazione `postmark_mcp_...` corretta alla fonte contemporanea; test
anti-scorciatoia elevato da passo narrativo a gate esplicito; verifica catalogo↔dataset
aggiunta al mapping; formulazione dello scaling path del catalogo corretta (era
presentata come "già pronta", non lo è); alternativa più leggera al catalogo (tabella
markdown) ora dichiarata e argomentata invece di assente dal documento; requisito di
auto-sufficienza del `rationale` per casi `real_incident` aggiunto. Dissenso di
`council-pragmatist` ("over-scoped" sul catalogo come livello intermedio) registrato,
non applicato nella sostanza — vedi paragrafo "Alternativa più leggera considerata e
scartata" sopra per il ragionamento. `grill-with-docs`: valutato non necessario — questo
documento incrocia già `SPIRIT.md` e il gap-tracking doc riga per riga nel mapping
sopra e nella sezione Gap 16; non c'è altra documentazione pregressa sostanziale da
incrociare che il mapping non copra già.

**Esito `grill-with-docs` (2026-08-19, terza sessione)**: l'auto-valutazione appena
sopra ("valutato non necessario") era sbagliata — stesso pattern già visto per Gap 16
(un problema reale non trovato dal council checkpoint, trovato da una revisione
indipendente successiva). Quattro correttivi applicati: (1) due riferimenti a un campo
`category` mai esistito nello schema del catalogo, residui di una revisione precedente,
corretti in `catalog/_template.yaml` e `catalog/vendor_taxonomy_snapshot.yaml`; (2) il
claim di validazione dei due esempi di `case_id` (sezione "Naming") e del template
compilato (sezione "Authoring — template") ammorbidito da "verificato" a "verificato a
mano, non riproducibile" — nessuna traccia nel repo oltre al testo del design doc, voce
aperta in `registro-limiti-aperti.md`; (3) il conteggio "10 test" (sezione "Struttura
dati") corretto — non allineato a `pytest tests/test_catalog.py --collect-only` (11
nodi), riformulato per non richiedere manutenzione a ogni test aggiunto; (4) la
formulazione del gate anti-scorciatoia tool→label (mapping Requisito→Verifica) conteneva
una circolarità logica — imponeva che il test passasse prima di `run_batch.py`, ma quali
tool un `TestCase` esercita davvero emerge solo dall'esecuzione stessa — riformulato come
controllo in-process tra `execute_batch()` e la scrittura di `report.md`, con caveat
esplicito di non-strutturalità (principio 8 `SPIRIT.md`). Il punto (4) non è un refuso di
forma come gli altri tre: è un errore di design che, non corretto, avrebbe reso il
requisito irrealizzabile come scritto.

## Scostamenti dal testo originale (confronto esplicito)

Nessuno scostamento nascosto da segnalare: i due requisiti citati da `SPIRIT.md` nella
tabella sopra sono riportati testualmente, non parafrasati né ristretti. La decisione
iniziale di questa sessione di rimandare gli incidenti reali ("per ora saltiamoli") è
stata rivista nella sessione stessa dopo aver segnalato lo scostamento dal testo
originale — non richiede più una voce in `registro-limiti-aperti.md`, il requisito è
soddisfatto.

## Cosa resta fuori da questo design doc (prossimi passi di implementazione)

- Progettare da zero un vero scenario T0007 (guardrail evasion) — nessuno dei casi
  pensati finora era in realtà T0007 (Gap 16). Candidato in "Regola di copertura
  minima" sopra, non ancora scritto.
- Popolare il resto del catalogo: le 9 tecniche restanti non prioritarie (1 malevolo + 1
  gemello ciascuna, T0007 escluso perché trattato sopra), i benigni generici, eventuali
  seconde varianti per le tecniche prioritarie non ancora coperte da un incidente reale
  specifico.
- Scrivere i 40-60 `TestCase` reali in `dataset/`, selezionando dal catalogo — ogni
  `rationale` di un caso `real_incident` deve riportare citazione+adattamento in
  sintesi, non solo il `catalog_id` (mapping sopra, requisito auto-sufficienza).
- Scrivere le verifiche ancora assenti (tutte in tabella sopra, nessuna esiste oggi —
  verificato con una ricerca in `tests/`, non solo dichiarato): copertura completa
  delle 14 tecniche sui `TestCase` malevoli (**gate bloccante**, un vero test pytest
  statico sul dataset, eseguibile prima di `run_batch.py`), anti-scorciatoia
  tool→label (**gate bloccante**, ma non un test pytest — un controllo in-process
  dentro `run_batch.py::main()`, tra `execute_batch()` e la scrittura di `report.md`;
  meccanismo riformulato da `grill-with-docs` il 2026-08-19, vedi mapping sopra),
  coerenza catalogo↔dataset dopo la selezione (test pytest, non bloccante).
- Aggiornare `README.md` per menzionare `dataset/`/`catalog/` e come sono legati
  (trovato assente dal council checkpoint, `council-advocate`) — rimandato a quando
  `dataset/` avrà contenuto reale, per non descrivere una struttura ancora vuota.
- Eseguire `run_batch.py` sul dataset completo, primo report reale.

Questi non sono decisioni di design — sono esecuzione della regola di copertura e del
formato già fissati qui.
