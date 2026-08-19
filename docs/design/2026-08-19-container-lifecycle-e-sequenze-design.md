# Ciclo di vita del container + sceneggiature composte: uno schema unico (Gap 14 cluster B/C + Gap 15)

Companion di `2026-08-14-toy-agent-gap-tracking.md` (Gap 14, Gap 15) e di
`2026-08-14-toy-agent-e-pipeline-misura.md`. Sessione di design dedicata,
2026-08-19 — brainstorming (superpowers:brainstorming + estensione locale).
Council checkpoint eseguito dopo la scrittura di questo file e
dell'aggiornamento al gap-tracking doc (su richiesta esplicita dell'utente),
findings applicati — vedi "Esito valutazione council" in fondo al documento.

## Obiettivo e principio unificante

Gap 14 (il ciclo di vita del container `detector` deve diventare un parametro
esplicito dell'orchestratore, non una scelta cablata) e Gap 15 (un "test" può
essere una sceneggiatura composta di più interazioni, non solo la primitiva
atomica) si chiudono con **un solo costrutto**: una **sequenza** — una lista
ordinata e puramente dichiarativa di passi tipizzati (`open`, `command`,
`close`), senza logica di controllo (nessun ciclo, nessuna condizione, solo
dati enumerabili). Questo non è un compromesso di comodo: era già il
principio deciso nella sessione precedente ("la struttura di configurazione
di un test/run non va progettata intorno al bisogno di oggi con un parametro
aggiunto qui e uno là — va progettata come una struttura di configurazione
generale", gap-tracking doc, Gap 15).

`agent` e `detector` hanno cicli di vita **indipendenti** all'interno della
stessa sequenza — decisione esplicita dell'utente ("entrambi indipendenti,
così restiamo generali"), anche se solo `detector` è oggi la priorità reale
essendo il container che ospita il codice vendor pinnato; `agent` è un plus
che generalizza lo schema senza essere richiesto da un gap aperto oggi.

**Correzione di metodo, decisiva per l'intera sessione** (osservazione
dell'utente, non pianificata): la verifica empirica di B4-B8 (ps aux, ricerca
core dump, socket aperti dopo un `pkill` indotto — proposta come primo passo
di questa sessione) **non serve**. Il framework non si basa su un repulisti
verificato empiricamente: un container o è davvero chiuso (nessuna storia
precedente esiste mai in quella sua vita, quindi non c'è nulla da correlare)
o è riusato e allora qualunque pulizia parziale (troncare un log, uccidere un
processo) non cambia il fatto strutturale che più chiamate sono avvenute
nello stesso ambiente. Non esiste una terza via "ripulita a metà" che valga
qualcosa — le uniche due garanzie reali sono chiusura effettiva o
accettazione dichiarata.

## Contesto per chi legge senza aver seguito Gap 14/15 (aggiunto dopo council, council-advocate)

In breve, per chi arriva a questo documento senza il retroscena completo:
**Gap 14** riguarda i segnali che potrebbero rivelare al detector sotto
misura di trovarsi in una sessione di test invece che in un uso reale
(effetto osservatore) — il ciclo di vita del container che lo ospita è uno
di questi segnali. **Gap 15** riguarda se un "test" debba per forza essere
una singola invocazione isolata, o possa essere una sequenza deliberata di
più interazioni collegate. Questo documento li risolve insieme perché sono
la stessa domanda vista da due lati: entrambi chiedono "quante invocazioni
condividono lo stesso container, e chi lo decide".

**Quando usare quale modalità** (indicazione operativa, non ancora un
vincolo formale — da raffinare quando Plan 5 scriverà le prime
sceneggiature reali): `per-case` per il dataset principale, dove ogni caso
deve essere valutato in isolamento puro; `reused` quando l'obiettivo è
restare fedeli alla condizione di misura dichiarata dal vendor sull'intero
batch; una sceneggiatura deliberata (container condiviso tra più `command`)
solo quando la domanda di misura riguarda esplicitamente la memoria/il
comportamento del detector attraverso più interazioni collegate nello
stesso ambiente — non come scorciatoia per altri scopi.

## Grammatica della sequenza

Tre tipi di passo, nomi di campo scelti per essere leggibili da chi scrive e
legge il file (priorità esplicita dell'utente: parlanti, non brevi):

```yaml
sequence:
  - open:
      containers: [agent, detector]
  - command:
      case_id: benign_001
      counts_toward_metric: true   # booleano per singolo comando, non un default a livello di sequenza
  - close:
      containers: [agent, detector]
```

**Nota di terminologia per chi implementa (aggiunta dopo grill-with-docs)**:
il passo `command` di questa grammatica non ha a che fare con `CommandRunner`/
`run_command` già esistenti in `orchestrator.py`/`evidence.py` (invocazione
di un comando shell/Docker di basso livello, es. `docker compose exec ...`)
— due significati diversi della stessa parola nello stesso codice. Non
rinominato qui (i due usi appaiono sempre in contesti distinguibili dal
contesto circostante, e `command` è già il termine usato in tutta la
sessione di design) — da riconsiderare in un secondo tempo solo se la
convivenza dei due significati genera confusione reale durante
l'implementazione.

`command` è sempre la primitiva fissa e indivisibile già decisa in Gap 15 (un
seed turn → loop ReAct dell'agente, fino a 8 turni interni → un `Transcript`
→ un `Verdict` del detector) — mai spezzata in passi più piccoli per
container (targeting per singolo container dentro un `command` valutato e
scartato come funzionalità speculativa, nessun caso d'uso concreto oggi).

`counts_toward_metric` risolve la domanda rimasta aperta in Gap 15 ("la label
vale per l'intera sceneggiatura o per singola interazione?") con un
meccanismo dichiarativo esplicito invece di una convenzione implicita
("prendo sempre l'ultimo verdetto") — coerente con principio 2 di
`SPIRIT.md` (metodologia dichiarata prima dei risultati). Ogni `command`
referenzia comunque il proprio `case_id` con la propria `label` nel dataset —
nessun nuovo tipo in `schema.py`, nessuna label a livello di sequenza.

**Chiarimento dopo council (council-risk, council-advocate) — semantica di
`counts_toward_metric=false`**: il flag governa solo l'inclusione in
`compute_metrics` (P/R/F1), mai la persistenza. Transcript e verdetto grezzi
di **ogni** `command` — `counts_toward_metric` vero o falso — vengono
comunque scritti su disco e compaiono nell'evidenza raccolta (coerente con
principio 4 di `SPIRIT.md`, riproducibilità: nessun dato osservato va perso
solo perché non contribuisce al numero finale). Il report finale (P/R/F1)
riflette solo il sottoinsieme dei `command` con flag vero — se un dataset di
40 casi ne ha 5 con flag falso, il denominatore delle metriche è 35, non 40,
e questo va reso esplicito nel report stesso (dettaglio di implementazione,
non di questo design doc).

**Meccanismo del filtro (aggiunto dopo grill-with-docs)**: `compute_metrics`
(`src/toy_agent/metrics.py:136-143`) oggi pretende `len(cases) ==
len(verdicts)` e non ha alcun concetto di esclusione — un `command` non
contato non deve mai arrivare fin lì. Il filtro avviene **prima**, in
`execute_sequence`/`execute_batch`: solo i `command` con
`counts_toward_metric=true` entrano nelle liste `cases`/`verdicts` passate a
`compute_metrics`. Zero cambiamenti a `metrics.py`, che resta ignaro del
concetto di sequenza — mantiene la sua responsabilità attuale (P/R su ciò
che riceve), aggiunto ai touch point sotto.

**Un `command` escluso resta comunque valutabile a mano**: anche se non
entra nell'aggregato P/R, riferisce comunque un `case_id` con una `label`
reale nel dataset — un revisore può sempre confrontare `Verdict.label` (cosa
il detector ha predetto) con `TestCase.label` (la verità dichiarata) e
giudicare se quella singola risposta è stata corretta, leggendo l'evidenza
raccolta. `Verdict` da solo non porta mai questo giudizio (nessun campo
"corretto/sbagliato" nello schema, `schema.py:66-77`) — la correttezza
esiste solo come relazione tra `Verdict` e `TestCase`, mai come proprietà
isolata del primo.

**`counts_toward_metric` è indipendente da `label` — nessuna scorciatoia per
gli step intermedi (aggiunto dopo grill-with-docs)**: non esiste un pattern
fisso tipo "gli step di setup sono sempre benign". Le due decisioni sono
ortogonali: `label` dice cos'è davvero quell'interazione, `counts_toward_metric`
dice solo se il suo verdetto entra nel calcolo finale. Esempio concreto: una
sceneggiatura può avere un primo `command` genuinamente `malicious` (un vero
tentativo di attacco, per stabilire che il detector ha già "visto" qualcosa
in quell'ambiente) con `counts_toward_metric: false`, e un secondo `command`
`benign` con `counts_toward_metric: true` — la domanda di ricerca essendo "una
richiesta pulita successiva viene giudicata correttamente, o la storia
recente contamina il giudizio?". Ogni `command`, contato o no, referenzia un
`TestCase` completo che lo schema esistente (`schema.py::TestCase.__post_init__`)
impone già abbia una `label` reale e una `rationale` non vuota — **la stessa
serietà con cui si decide qualunque altro caso**, mai un'etichetta di comodo
scelta perché "tanto non conta ai fini della metrica". Il rischio dichiarato
se questo non viene rispettato: un'erosione silenziosa del principio 2/3 di
`SPIRIT.md` che entrerebbe dalla porta di servizio di questo meccanismo.

**Criterio di assegnazione del flag per Plan 5**: quando si scriveranno le
prime sceneggiature reali, applicare lo stesso rigore già stabilito per Gap
7 (ground truth "per effetto, non per intento") — il criterio non è nuovo,
è la stessa classe di domanda già affrontata lì, non va riaperta da zero.

### Tre esempi

**Il comportamento di oggi (`execute_batch`), riscritto esplicitamente:**

```yaml
sequence:
  - open: {containers: [agent, detector]}
  - command: {case_id: benign_001, counts_toward_metric: true}
  - command: {case_id: malicious_001, counts_toward_metric: true}
  # ... un command per ogni case_id del dataset
  - close: {containers: [agent, detector]}
```

**Isolamento massimo (container fresco per ogni caso, chiude B4-B8 per
costruzione):**

```yaml
sequence:
  - open: {containers: [agent, detector]}
  - command: {case_id: benign_001, counts_toward_metric: true}
  - close: {containers: [agent, detector]}
  - open: {containers: [agent, detector]}
  - command: {case_id: malicious_001, counts_toward_metric: true}
  - close: {containers: [agent, detector]}
```

**Sceneggiatura deliberata (Gap 15 modalità 2): `detector` osserva più
interazioni collegate nello stesso ambiente, `agent` riparte fresco per ogni
turno — mostra perché i due cicli di vita restano indipendenti:**

```yaml
sequence:
  - open: {containers: [detector]}
  - open: {containers: [agent]}
  - command: {case_id: ticket_open_001, counts_toward_metric: false}
  - close: {containers: [agent]}
  - open: {containers: [agent]}
  - command: {case_id: ticket_followup_002, counts_toward_metric: true}
  - close: {containers: [agent]}
  - close: {containers: [detector]}
```

**Non sono tre modalità distinte, sono due forme dello stesso spettro
(aggiunto dopo grill-with-docs)**: gli Esempi 1 (`reused`) e 3 (sceneggiatura
deliberata) hanno la stessa identica forma meccanica — un `open`, più
`command` in sequenza, un `close` — cambia solo *quanti* comandi contiene il
blocco e *perché* sono raggruppati insieme (tutto il dataset per fedeltà
alla misura vendor, contro un piccolo gruppo scelto apposta per testare la
memoria cross-step). L'Esempio 2 (`per-case`) è l'altra forma (un blocco
`open`/`close` per ogni singolo comando). `reused`/`per-case` non sono quindi
una terza categoria accanto alle sceneggiature — sono i due estremi
auto-generati di questo stesso spettro applicati al caso comune (l'intero
dataset); una sceneggiatura scritta a mano è lo stesso spettro applicato a
un sottoinsieme scelto deliberatamente. Un solo meccanismo, non tre.

### Il caso comune non si scrive a mano

Per un batch di 40-60 casi, la sequenza **non va scritta a mano** — la
genera `run_batch.py` da `load_dataset()` + un parametro
`--container-lifecycle={reused|per-case}`. Il file YAML scritto a mano serve
solo per sceneggiature deliberate (corte per natura, Gap 15 modalità 2).

Check principio 8: la grammatica regge per costruzione — nessun elemento è
specifico al vendor pinnato; `containers: [agent, detector]` sono nomi
nostri, non imposti dal vendor.

## Limite dichiarato: sequenze composte con `case_id` ripetuto

Gli artefatti per-comando — il transcript grezzo e le directory di
evidenza/log del thin-proxy — sono chiavettati per `case_id` da solo, non
per `case_id` + `command_index`. In `src/toy_agent/sequence.py`:
`raw_dir / f"{case_id}.transcript.json"` (riga 205), e le chiamate a
`collect_case_evidence_fn(case_id, ...)` / `collect_thin_proxy_log_fn(case_id,
...)` (righe 210-211), che a loro volta usano `evidence_dir / case_id`
dentro `src/toy_agent/evidence.py`. `command_index` esiste già (è
l'argomento passato al marcatore nel log del thin proxy, vedi sopra) ma non
viene usato per differenziare questi due canali.

**Conseguenza**: una sceneggiatura composta scritta a mano (Gap 15 modalità
2) che esegue lo stesso `case_id` più di una volta nella stessa sequenza
sovrascrive silenziosamente sul disco tutto tranne l'ultima esecuzione — sia
il transcript grezzo sia l'evidenza raccolta. `verdicts.jsonl` è l'unico
canale append-only che sopravvive intatto a una ripetizione.

**Non raggiungibile da nessun percorso di codice di questo piano**:
`load_dataset` impone `case_id` univoci su tutto il dataset
(`validate_unique_case_ids`), e le sequenze generate automaticamente (il
"caso comune", `reused`/`per-case`) emettono esattamente un `CommandStep` per
`case_id` — nessuna ripetizione possibile finché nessuno scrive a mano una
sceneggiatura composta con lo stesso `case_id` due volte.

**Stato**: accettato come limite dichiarato per ora, non un bug e non
silenziosamente risolto — coerente con il principio 8 di `SPIRIT.md` (mai
lasciare un limite reale non dichiarato). Da affrontare quando/se si
costruiranno davvero sceneggiature composte con `case_id` ripetuto (Gap 15
modalità 2): a quel punto l'opzione naturale è estendere la chiave su disco
a `case_id` + `command_index`, ma quella decisione resta fuori scope qui.

## Validazione statica (prima di eseguire qualunque comando reale)

Un passaggio a scorrimento sulla sequenza, tenendo un insieme di container
"aperti" — stesso principio di `CASE_ID_PATTERN`/`validate_unique_case_ids`
in `dataset.py` (fail fast, costo zero, nessuna chiamata Docker/LLM sprecata
su un file malformato). Fallisce se:

- un `open` include un container già aperto;
- un `command` richiede `agent`/`detector` e uno dei due non è aperto (il
  `command` tocca sempre entrambi);
- un `close` include un container non aperto;
- la sequenza finisce con container ancora aperti;
- un `case_id` referenziato da un `command` non esiste nel dataset caricato.

## Meccanica Docker per `open`/`close`

Solo `agent`/`detector` fanno parte del vocabolario — `egress-proxy` resta
sempre acceso, infrastruttura condivisa, mai gestito dalla sequenza.

- **`open`**: **prima** `docker compose rm -f -s -v <service>` best-effort
  (no-op silenzioso se il container non esiste — mai un errore), **poi**
  `docker compose up -d <service>`, che lo crea da zero usando i layer
  immagine già costruiti (economico, stima di costo già fatta in Gap 14: la
  parte pesante — clone del repo vendor, installazione dipendenze — avviene
  alla build dell'immagine, non all'avvio del container). Il `rm` preventivo
  è **auto-risanante**, non ridondante — vedi "Correzione dopo council:
  crash dell'orchestratore" sotto.
- **`close`**: `docker compose rm -f -s -v <service>` (stop se attivo,
  rimozione forzata, `-v` rimuove anche eventuali volumi anonimi/nominati —
  nessuno dichiarato oggi in `docker-compose.yml`, ma la garanzia non deve
  dipendere dal fatto che resti così in futuro) — **non** uno `stop` da
  solo, che lascerebbe intatto il filesystem scrivibile e vanificherebbe la
  garanzia. La rimozione reale è il contratto di Docker stesso: `rm`
  cancella il layer scrivibile del container per definizione del comando —
  non serve verificare empiricamente ogni volta cosa resta (coerente con la
  correzione di metodo sopra). La verifica che scriveremo controlla che il
  nostro codice emetta *quel* comando (`rm -f -s -v`, non `stop`), non che
  il filesystem sia vuoto.

**Limite dichiarato: nessuna attesa esplicita di readiness prima della prima
invocazione del detector.** `_open_container()` ritorna appena Docker
riporta il container **avviato** (`docker compose up -d` completato), non
appena l'entrypoint del detector (`docker/detector/entrypoint.sh`) ha finito
di attendere che il suo processo interno `vendor_proxy` abbia effettivamente
aperto le proprie porte. Oggi questa finestra è chiusa nella pratica dal
tempo del round-trip LLM lato agente, che avviene sempre prima che il
detector venga invocato in una sequenza — ma è incidentale, non garantito
per costruzione: un verdetto classificato come infra-failure per detector
non ancora pronto resta una possibilità teorica non coperta da alcun poll di
readiness esplicito.

**Correzione dopo council (council-risk): crash dell'orchestratore a metà
sequenza.** Finding reale: l'insieme "aperti" vive solo in memoria del
processo Python. Se l'orchestratore muore (crash, `SIGKILL`, OOM — non un
`command` che fallisce, il processo stesso) tra un `command` e il suo
`close` abbinato, nessuno chiude il container. Senza correzione, il run
successivo ripartirebbe con un `open` che, essendo `docker compose up -d`
idempotente, lascerebbe intatto un container "sporco" residuo del crash —
esattamente il tipo di residuo che la modalità `per-case` esiste per
escludere, senza errore visibile. **Fix applicato sopra**: `open` precede
sempre la creazione con una rimozione forzata best-effort — rende ogni
`open` auto-risanante indipendentemente da cosa sia successo prima (crash
incluso), non solo dal percorso "tutto è filato liscio". Chiude anche il
finding gemello (fallimento di `close` durante l'esecuzione normale, non
solo al trip del circuit breaker): se `close` fallisce silenziosamente, il
container resta sporco fino al prossimo `open` — ma quel prossimo `open` lo
ripulisce comunque, quindi il fallimento costa risorse sprecate, non una
fuga di segnale residua.

## Esecuzione

Nuova funzione `execute_sequence` (modulo nuovo, es. `src/toy_agent/sequence.py`)
che sostituisce la logica interna di `execute_batch` mantenendone la firma
pubblica — `execute_batch` diventa un generatore sottile del caso comune:
costruisce la sequenza di default da `load_dataset()` +
`--container-lifecycle`, poi chiama `execute_sequence`. Nessuna rottura
dell'interfaccia pubblica esistente di `run_batch.py`.

**Interruzione a metà (circuit breaker)**: stessa soglia di oggi (3
fallimenti infra consecutivi su un `command`), applicata lungo l'intera
sequenza. Alla rottura: si chiudono comunque tutti i container ancora aperti
(letti dall'insieme "aperti" mantenuto a runtime, non dal resto della
sequenza scritta) prima di terminare — mai un'interruzione che lascia
risorse accese fuori controllo. La chiusura in questa fase è best-effort, non
solleva se il container è già irraggiungibile (stesso pattern già usato in
`evidence.py` per `_container_id`).

**Raccolta prove**: resta agganciata a ogni `command`, subito dopo,
container ancora aperto — mai rimandata al `close`, mai condizionata dalla
modalità scelta.

**Limite residuo dichiarato (council-risk)**: sul percorso di timeout
(`orchestrator.py::run_test_case`, righe 111-137), il `pkill` verso i
sottoprocessi MCP orfani è best-effort e non attende conferma. Se un
provider orfano è ancora in volo con una richiesta HTTP verso il thin-proxy
proprio mentre l'host appende il marcatore per il comando successivo, quella
riga di risposta tardiva può finire dopo il marcatore — un'imperfezione di
attribuzione nell'evidenza (quale comando "possiede" quella riga), non una
fuga di segnale verso il detector. Accettato come limite dichiarato, stesso
trattamento già riservato ad altri percorsi best-effort in questo progetto
(es. `terminate_subprocesses()`, Gap 11) — non risolto qui.

## Raccolta prove del thin-proxy log: marcatore invece di troncamento

Idea dell'utente, emersa discutendo perché il log veniva troncato prima di
ogni invocazione (`orchestrator.py::run_test_case`, righe 88-104): il motivo
originale era attribuzione per-caso (`vendor_proxy.py` gira come un unico
processo per tutta la vita del container `detector`, il suo log è
altrimenti un unico file cumulativo condiviso da tutti i casi), non un
meccanismo di sicurezza — e infatti non lo sarebbe stato (stessa correzione
di metodo sopra: cancellare log nel container osservato non serve a nulla
contro l'effetto osservatore).

**Sostituzione**: stesso punto del codice, stesso meccanismo
(`docker compose exec detector sh -c ...`), cambia solo il comando — da `>
{path}` (svuota) a `>> {path}` con una riga JSON di confine:
`{"marker": true, "case_id": ..., "command_index": <indice del comando nella
sequenza>, "timestamp": <ISO 8601>}` — nome scelto (dopo grill-with-docs, non
`sequence_position`) per restare distinto dal campo `seq` già esistente in
`schema.py:25` (posizione di un turno/tool-call dentro un singolo
`Transcript`) — due contatori concettualmente diversi (uno per singolo caso,
uno per l'intero run), abbastanza vicini nel nome da poter confondere chi
legge in fretta un'evidenza con entrambi i concetti presenti. Non serve una
nuova chiamata HTTP a `vendor_proxy.py` — l'orchestratore (lato host) emette
già questo comando oggi, cambia solo il contenuto.

**Nota pratica — leggere i segnali cross-step in una sceneggiatura (aggiunto
dopo grill-with-docs, zero infrastruttura nuova)**: grazie al marcatore, il
log del thin-proxy è un corpus continuo per l'intera sceneggiatura — un
revisore può leggere il ragionamento reale di Inspector su un `command` e
controllare se menziona esplicitamente qualcosa di un `command` precedente
nella stessa sequenza ("come visto nel messaggio precedente", "data
l'interazione precedente in questa sessione"). Un segnale diretto e leggibile
a occhio (o con un semplice grep su parole chiave) che il detector sta usando
memoria cross-step nel proprio ragionamento — nessun meccanismo nuovo, solo
lettura diagnostica di un'evidenza già raccolta, stesso uso legittimo già
descritto sopra ("Nota sul confine scatola-nera e il log del thin-proxy").

**Vantaggi**: nulla si perde mai — il file diventa la cronologia completa e
continua del batch, non più frammenti troncati; chiude la finestra residua
C2 per costruzione (nessuna finestra da preoccuparsi se non si tronca mai);
si aggancia naturalmente al confine di un passo `command` dentro un
container riusato; corpus migliore per l'idea candidata per Plan 5+ (vedi
sotto). `evidence.py::collect_thin_proxy_log` **non cambia struttura** —
continua a copiare l'intero file per ogni caso, ora cumulativo e
auto-descrittivo tramite marcatori invece che pre-isolato.

## Chiusura di A4, A5, B2, B3

- **A4 (timestamp)**: risolto dallo stesso parametro di ciclo di vita, nessun
  meccanismo nuovo. Con `per-case` (container fresco per comando) il segnale
  non è calcolabile dall'interno — non esiste una seconda chiamata nella
  stessa vita del container con cui confrontare il timestamp. Con `reused`
  resta presente, **accettato come limite dichiarato** — coerente con la
  fedeltà alla misura del vendor (le loro 300 sessioni Gauntlet girano nello
  stesso `Pipeline()`, stesso tipo di segnale presente anche nella loro
  misura dichiarata, vedi Gap 14 nel gap-tracking doc). **Caveat aggiunto
  dopo council (council-skeptic)**: l'analogia di fedeltà non è 1:1 —
  un oggetto Python persistente in memoria (`Pipeline()`) e un container OS
  persistente (filesystem scrivibile, processi, socket) non sono la stessa
  cosa. Non sappiamo se il `Pipeline()` del vendor porti davvero stato
  osservabile tra sessioni, solo che l'oggetto esiste — è la migliore
  approssimazione disponibile con l'informazione pubblica che abbiamo, non
  una replica verificata. Il confronto P/R tra `reused`/`per-case` sullo
  stesso dataset (già annotato come beneficio aggiuntivo, non ancora
  eseguito) resta la mitigazione corretta per questa incertezza residua.
- **B2 (ritmo/tempistica)**: stessa risoluzione di A4, stesso parametro.
  Confermata la conclusione già scritta nel gap-tracking doc: nessun
  tentativo di imitare un "ritmo umano" — resta sconsigliato a livello di
  principio (nessun riferimento credibile a cui ancorare l'imitazione), non
  solo di costo.
- **A5 (forma dei `messages`)**: si spacca in due.
  - "Sempre esattamente un turno seed utente" — **non è un segnale**, già
    verificato in Gap 15: stessa identica struttura del Gauntlet del vendor
    (un solo `user_prompt` seed → traiettoria agentica multi-step).
  - `call_id` sempre `call_{seq}` (`src/detector_adapter/adapter.py:38`) —
    pattern reale, a basso costo di correzione, stesso ordine di grandezza
    di A1/A2: un tool-calling di produzione genera tipicamente id opachi
    (hash/token), non una sequenza prevedibile `call_1, call_2, ...`. Fix
    proposto: identificativo opaco per chiamata (es. `uuid.uuid4().hex`),
    stessa fix wave di A1/A2. Nota di metodo: non si sta leggendo codice
    vendor per giustificare questo (scatola nera rispettata) — è un giudizio
    ingegneristico su cosa produce plausibilmente un sistema di produzione
    reale, dichiarato come tale.
- **B3 (traffico dal proxy sostitutivo)**: **riclassificato dopo council
  (council-skeptic) — da "verificato e scartato" a "accettato come limite
  dichiarato"**, non più nella categoria di A3/B1/C1. La chiusura originale
  ("l'interfaccia dichiarata non porta questo dato": lo schema
  `AgentEvent`/`ToolUsage` non ha campi latenza/rete, `detector` ha
  `cap_drop: ALL`) esclude solo l'osservazione a livello rete/sistema —
  **non esclude un canale application-level**: qualunque client HTTP del
  vendor può misurare da sé il tempo di round-trip della propria chiamata
  (`time.perf_counter()` prima/dopo), senza bisogno di alcuna capability. Se
  il nostro proxy ha caratteristiche di latenza sistematicamente diverse
  dall'endpoint reale (rete Docker interna vs. internet), quel timing è
  osservabile dal codice vendor per costruzione, indipendentemente da cosa
  gli abbiamo dichiarato nello schema — esattamente il tipo di conclusione
  che il principio scatola-nera di questa sessione vieta di dare per
  "sicura" solo perché non ancora osservata in questo vendor pinnato. Nessun
  lavoro di ingegneria nuovo per questo — solo l'etichetta corretta, stessa
  categoria di A4/B2 in modalità `reused`.

## Nota sul confine scatola-nera e il log del thin-proxy

Discussione dedicata durante la sessione: il log del thin-proxy (prompt e
risposte raw di Sifter/Inspector, catturati perché il nostro proxy è
l'intercettazione reale del traffico verso l'LLM, non un log passivo) è la
prova più ricca che raccogliamo — ma va tenuto distinto in due usi:

1. **Uso legittimo — evidenza/diagnostica**: ricostruire la traiettoria di
   ragionamento di un caso, verificare la fedeltà del nostro adapter al
   verdetto raw del modello, confermare che il remapping dei modelli (Gap
   10) funzioni, diagnosticare fallimenti. Esattamente il tipo di prova che
   `SPIRIT.md` principio 2/3 chiede dietro a un numero P/R.
2. **Uso vietato — giustificare un segnale come "sicuro"**: osservare che
   *oggi*, con *questo* vendor pinnato, un certo campo non compare nel
   traffico non è una garanzia strutturale (stesso principio di
   [[feedback_blackbox_measured_system]] — vale il memory file del progetto,
   non riportato qui). Le chiusure A1-A5/B1-B8/C1-C2 restano ancorate solo
   al confine ingresso/uscita dichiarato, mai a un'osservazione di traffico
   specifica di questo vendor.

## Idea candidata per Plan 5+ (non in scope qui)

Discussione emersa dal punto precedente, esplicitamente **rimandata**
(coerente con la decisione già presa il 2026-08-17,
`project_poc_monitoraggio_da_discutere.md` — memoria di progetto, punto 4):
usare i Q&A del thin-proxy log (ora un corpus continuo grazie al marcatore
invece che frammenti troncati) per costruire uno spazio vettoriale con una
baseline di ancore "sicure" note, misurando la distanza delle risposte reali
da quella baseline come segnale continuo — invece del solo binario
etichetta/verdetto.

Collegamento nuovo rispetto alla valutazione del 2026-08-17: potrebbe essere
un confronto più sensibile del semplice P/R aggregato per il "beneficio
aggiuntivo" già annotato in Gap 14 (far girare lo stesso dataset in modalità
`reused` vs `per-case` e confrontare i risultati) — con un dataset piccolo
(40-60 casi) una differenza di comportamento reale potrebbe non spostare mai
l'etichetta finale, mentre una distanza vettoriale tra le risposte del
detector nelle due modalità, sugli stessi casi, potrebbe far emergere la
stessa deriva (effetto osservatore) in modo più fine.

Resta fuori scope per questa sessione: introduce una dipendenza nuova
(modello di embedding) e, per coerenza con principio 3 di `SPIRIT.md`,
richiederebbe di giustificare qualunque soglia di distanza con lo stesso
rigore riservato a P/R — lavoro di design a sé, candidato per Plan 5+, non
questa sessione.

**Estensione dello stesso confronto a livello di singola sceneggiatura
(aggiunto dopo grill-with-docs)**: lo stesso principio — far girare lo
stesso `case_id` in due condizioni e confrontare il risultato — si applica
anche dentro Gap 15 modalità 2, non solo al confronto `reused`/`per-case`
sull'intero batch. Far girare **lo stesso comando finale** una volta dentro
una sceneggiatura deliberata (con storia precedente nello stesso container)
e una volta isolato (`per-case`, nessuna storia), confrontando
verdetto/confidence/rationale tra le due esecuzioni — una divergenza sarebbe
prova diretta che la storia condivisa ha influenzato il giudizio del
detector su un'interazione altrimenti identica. Metodologicamente identico
al confronto già proposto sopra (stessa idea, granularità più fine — per
singola sceneggiatura invece che per l'intero batch), non una feature a sé.
Resta comunque candidato per Plan 5+, stesso motivo di scope: richiede
eseguire deliberatamente due varianti dello stesso caso, lavoro di dataset
non ancora pianificato.

## Touch point nel codice esistente

Elenco per orientare un futuro piano di implementazione — non è un piano,
nessun ordine di task deciso qui:

1. `src/toy_agent/sequence.py` (nuovo) — tipi dei tre passi, validatore
   statico, `execute_sequence`.
2. `src/toy_agent/run_batch.py` — `execute_batch` diventa un generatore
   sottile della sequenza di default (dataset + `--container-lifecycle`)
   sopra `execute_sequence`; nessuna rottura della firma pubblica esistente.
3. `src/toy_agent/orchestrator.py::run_test_case` — comando di troncamento
   sostituito da comando di marcatura; il resto della primitiva
   (agent→detector, gestione errori) resta invariato.
4. `src/toy_agent/evidence.py` — nessun cambiamento strutturale.
4b. `src/toy_agent/sequence.py`/`run_batch.py` (stesso modulo del punto 1-2)
   — filtra `cases`/`verdicts` per `counts_toward_metric` prima di chiamare
   `compute_metrics` (aggiunto dopo grill-with-docs). `metrics.py` non
   cambia.
5. `src/detector_adapter/adapter.py:38` — fix A5: `call_id=f"call_{seq}"` →
   identificativo opaco, stessa fix wave di A1/A2.
6. `docker-compose.yml` — nessun cambiamento necessario (nessuna `restart
   policy` oggi che confligga con `rm`/ricreazione).
7. `dataset.py`/`schema.py` — nessun cambiamento.

## Mapping Requisito → Verifica

| Requisito | Verifica |
|---|---|
| Validatore statico rifiuta ogni sequenza malformata (doppio `open`, `command` su container non aperto, `close` sbilanciato, `case_id` inesistente) | Un test per ciascun caso d'errore elencato |
| `close` rimuove davvero il container (non solo lo ferma) | Test che verifica il comando emesso via command runner mockato sia `docker compose rm -f -s -v <service>`, mai `stop` da solo |
| Log del thin-proxy non viene mai troncato, solo marcato | Test che verifica il comando emesso non contenga mai `>` di troncamento, sempre `>>` con marcatore JSON valido contenente `case_id` |
| Interruzione a metà sequenza chiude comunque ogni container rimasto aperto | Test che simula un trip del circuit breaker a metà con container aperti, verifica la chiamata di `close` corrispondente prima del ritorno |
| `call_id` non rivela più la posizione sequenziale (A5) | Test analogo a quello già scritto per A1: formato non `call_{seq}`, univoco per chiamata — **più, per lo stesso rigore già applicato ad A1 (verifica end-to-end dal vivo contro il vendor pinnato, non solo unitaria — aggiunto dopo council, council-risk)**: una verifica dal vivo che `aidr.AgentEvent`/`ToolUsage` accetti il nuovo formato senza sollevare, non solo un test unitario con command runner mockato |
| `open` è auto-risanante indipendentemente da uno stato residuo precedente (crash dell'orchestratore incluso) | Test che verifica che `open` emetta sempre prima `rm -f -s -v`, poi `up -d`, anche quando il validatore non ha visto alcun `close` precedente per quel container nella sequenza corrente |
| Un `command` con `counts_toward_metric=false` non entra nel denominatore P/R, ma il suo verdetto grezzo resta persistito | Test che verifica `len(cases_passati_a_compute_metrics) < len(tutti_i_command_eseguiti)` quando almeno un flag è falso, e che il transcript/verdetto di quel comando compaia comunque su disco/evidenza |

**Esito valutazione mapping**: su 6 righe totali, 1 estesa dal council
rispetto alla proposta iniziale (verifica dal vivo aggiunta ad A5) e 1
aggiunta ex novo (`open` auto-risanante, non prevista prima del finding di
council-risk) — il council ha contestato/rafforzato una porzione non
trascurabile delle verifiche proposte, non solo confermato.

## Esito valutazione council (2026-08-19)

Council eseguito, scope pieno, roster completo (skeptic, risk, pragmatist,
advocate), ognuno con lettura diretta e integrale di questo documento e
delle sezioni Gap 14/15 del gap-tracking doc. Tutti e quattro: `procedi con
riserve`. Nessuno ha raccomandato `da rivedere`.

**Finding applicati** (sostanziali, correggono un'affermazione che non
reggeva com'era scritta):
- **council-risk**: crash dell'orchestratore a metà sequenza rendeva la
  garanzia "isolamento per costruzione" della modalità `per-case` non
  reggente sotto quello scenario — fix: `open` sempre preceduto da un `rm`
  best-effort, reso auto-risanante (vedi "Meccanica Docker per open/close").
  Chiude anche il finding gemello (fallimento di `close` durante
  l'esecuzione normale).
- **council-skeptic**: B3 non era davvero "verificato e scartato" — copriva
  solo il canale rete/sistema, non il timing application-level lato client
  vendor. Riclassificato a limite dichiarato (vedi "Chiusura di A4, A5, B2,
  B3").

**Finding applicati** (minori, chiarimenti/rafforzamenti):
- council-risk: nota sul flag `-v` per `docker compose rm` (volumi futuri
  non dichiarati oggi); verifica dal vivo aggiunta per A5, simmetrica al
  rigore già usato per A1; chiarita la persistenza del dato grezzo
  indipendente da `counts_toward_metric`; limite dichiarato per la race di
  attribuzione sul percorso di timeout del thin-proxy log.
- council-skeptic: caveat sulla fedeltà imperfetta dell'analogia
  `Pipeline()` vendor / container OS riusato; collegamento esplicito a Gap 7
  come precedente per il criterio di assegnazione di `counts_toward_metric`
  in Plan 5.
- council-advocate: aggiunta la sezione "Contesto per chi legge senza aver
  seguito Gap 14/15" (bridge per un lettore esterno) e un criterio operativo
  su quando usare quale modalità.

**Dissenso registrato, non applicato**:
- **council-pragmatist**: propone di risolvere solo Gap 14 con un parametro
  semplice (`--container-lifecycle`) e rimandare la grammatica dichiarativa
  a Plan 5, quando le sceneggiature diventeranno un bisogno concreto
  (oggi non richieste da nulla di già scritto). Non applicato: l'unificazione
  in un solo schema era già principio deciso in una sessione precedente
  (gap-tracking doc, Gap 15, "una struttura di configurazione generale, non
  un parametro aggiunto qui e uno là"), non una scelta nuova presa con
  leggerezza in questa sessione — riaprirla ora significherebbe disfare una
  decisione già presa consapevolmente. Il costo aggiuntivo per il caso
  comune resta comunque nullo al call-site (nessuna riga YAML scritta a
  mano per il batch di 40-60 casi, generata automaticamente) — il costo
  reale segnalato dal pragmatist (un modulo e un validatore in più da
  mantenere) è vero ma giudicato accettabile per la generalità ottenuta.

**Grill-with-docs**: eseguito su richiesta esplicita dell'utente (valutazione
iniziale "salta" superata dall'utente). Incrociato con `schema.py`,
`metrics.py`, `orchestrator.py`, `evidence.py` oltre al gap-tracking doc.
Trovati e applicati:
- **Buco reale** (non solo terminologia): `compute_metrics` non ha alcun
  meccanismo di esclusione — il filtro per `counts_toward_metric` deve
  avvenire prima, in `execute_sequence`/`run_batch.py`, mai dentro
  `metrics.py`. Aggiunto touch point e riga di verifica mancanti.
- **Chiarimento metodologico**: `counts_toward_metric` è indipendente da
  `label` — nessuna scorciatoia per gli step intermedi di una sceneggiatura,
  stesso rigore di qualunque `TestCase`.
- **Collisione terminologica risolta**: marcatore rinominato da
  `sequence_position` a `command_index` per restare distinto dal campo `seq`
  già esistente in `schema.py`. Collisione minore `command` (passo della
  grammatica) vs `CommandRunner`/`run_command` (invocazione shell) notata ma
  non risolta con un rename — nota per chi implementa.
- **Precisione concettuale**: `reused`/`per-case`/sceneggiatura deliberata
  non sono tre modalità distinte — sono due forme meccaniche dello stesso
  spettro, reso esplicito nel documento.
- **Idea Plan 5+ estesa**: il confronto già proposto (`reused` vs `per-case`
  sull'intero batch) si applica identico a livello di singola sceneggiatura
  (stesso comando finale, isolato vs con storia precedente).
- **Nota pratica aggiunta senza costo di ingegneria**: leggere il log
  cross-step del thin-proxy per segnali di riferimento espliciti a
  interazioni precedenti nella stessa sceneggiatura.
