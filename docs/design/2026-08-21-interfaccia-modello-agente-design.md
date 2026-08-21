# Interfaccia col modello dell'agente: eventi non interpretabili, provenienza, costi

**Chiude insieme Gap 19, Gap 20 e Gap 21** di
`docs/design/2026-08-14-toy-agent-gap-tracking.md`.

**Data**: 2026-08-21. **Stato**: design approvato nel merito dall'utente, revisionato dopo
council checkpoint (4 agenti, scope pieno), non ancora implementato. **Piano di
implementazione**: da scrivere (`writing-plans`) dopo la review di questo documento.

---

## 1. Perché un solo documento per tre gap

I tre gap non sono tre difetti distinti: sono tre istanze dello stesso evento.

> **L'harness non sa qualcosa, e il report parla come se sapesse.**

- **Gap 19** — non sappiamo cosa il modello volesse chiedere al tool (i suoi argomenti non
  sono JSON leggibile). Il report conta quel caso come comportamento osservato.
- **Gap 21** — non sappiamo cosa l'agente avrebbe fatto se la chiamata al modello non
  fosse fallita a metà turno. Il report conta quel caso come comportamento osservato.
- **Gap 20** — rileggendo un report, non sappiamo quale agente ha prodotto quei
  transcript. Il report presenta numeri senza dire di quale esperimento sono.

La ragione operativa per trattarli insieme è la **sovrapposizione di codice**:
`agent_loop.py` (19+21), `model_client.py` (20+21), `run_batch.py::_setup_notes()`
(20+21), `metrics.py` (19+21). Tre piani scollegati produrrebbero diff in conflitto sulle
stesse funzioni.

Esiste anche una dipendenza logica, ma va enunciata con precisione perché una versione
precedente di questo documento la sovravendeva (contestato da council-skeptic, accolto):
sapere quale modello ha prodotto un evento **non serve** a gestire il singolo evento — non
aiuta a non eseguire un tool con argomenti illeggibili né a contare i retry. Serve alla
**diagnosi aggregata**: "questo modello produce più tool call malformate di quell'altro" è
la domanda che conta quando Plan 6 moltiplicherà i casi, e senza Gap 20 non è ponibile.

### Chi è chi (perché il criterio dipende da questo)

Il **detector vendor** è il sistema misurato. L'**agente giocattolo non è misurato**: è lo
strumento che produce il materiale — i transcript — su cui il detector viene giudicato. È
parte del banco di prova, non l'oggetto sul banco.

Quando l'agente giocattolo si rompe non stiamo osservando un dato sul detector, stiamo
osservando **rumore del nostro strumento di misura** che finisce dentro il numero
pubblicato come se fosse un dato.

---

## 2. Il criterio

Decisione di merito presa con l'utente, 2026-08-21:

> **Quando l'harness non sa: il caso esce dalla misura, l'evento viene registrato con
> evidenza sufficiente a diagnosticarne la causa e ad attribuirla a noi o all'esterno, e
> il report lo dichiara.**

La prima e la terza clausola non sono una scelta aperta: il progetto ha già risposto due
volte a questa domanda nello stesso modo. Gap 14 — denominatore zero produce
`precision=None`, mai `0.0`. Gap 18 — esito reale non determinabile produce
`attack_succeeded=None`, il caso esce dal calcolo, viene contato a parte e il report lo
dichiara. Discendono da `SPIRIT.md` principio 3 (*"mai presentare un numero secco come se
fosse una verità assoluta"*) e principio 6 (il codice del misuratore è *"il pezzo con
l'obbligo di trasparenza più stringente di tutti"*).

La seconda clausola — **evidenza sufficiente a diagnosticare la causa** — è un'aggiunta
esplicita dell'utente, e non è una postilla. Escludere e contare senza capire il perché
sposterebbe soltanto il problema dentro un contatore: lo strumento resterebbe rotto e noi
lo sapremmo senza poter agire. Un contatore che sale non distingue un nostro bug da un
provider che singhiozza, e la risposta cambia completamente cosa si deve fare dopo.

**Conseguenza vincolante** (contestata da council-skeptic su una versione precedente che
prevedeva un bucket indistinto, accolta): il bucket di esclusione **deve portare
l'attribuzione della causa caso per caso**, non solo un totale. Un conteggio unico che
somma argomenti illeggibili, errori del modello e retry esauriti contraddice
letteralmente questa clausola.

### Portata del dubbio

Decisione presa con l'utente: **un solo evento di questo tipo nel transcript rende
l'intero caso non interpretabile**, e il caso esce dalla misura. Non si tenta di salvarne
la parte "sana".

**L'argomento che regge questa scelta** (riformulato dopo council-skeptic, che ha
mostrato la circolarità della versione precedente): quando una tool call fallisce per un
guasto del nostro strumento, il modello riceve indietro un errore **che non ha causato**.
Tutto ciò che genera da quel punto in poi è una reazione a uno stimolo artificiale
introdotto da noi. Il transcript risultante è quindi **fuori distribuzione come input al
detector**, indipendentemente da quali criteri di successo siano scritti per quel caso.

La versione precedente giustificava l'esclusione con la corruzione del matching dei
criteri (§3, D1), e poi scartava il rimedio economico (`require_ok: true`) *perché* c'era
l'esclusione: un argomento circolare. L'argomento sopra sta in piedi da solo e non dipende
dai criteri.

Costo accettato consapevolmente: su un dataset di 31 casi con intervalli di confidenza già
larghi, ogni caso escluso restringe ulteriormente il campione, e alcuni transcript esclusi
sarebbero stati per il resto genuini.

**Soglia di invalidità** (aggiunta dopo council-skeptic): il costo sopra non può restare
illimitato. Il repo ha già il pattern giusto — `run_batch.py:176-190` **rifiuta di
scrivere `report.md`** quando il gate anti-shortcut fallisce. Un bucket che restringe il
campione in silenzio è la disciplina opposta: 15 casi esclusi su 31 produrrebbero comunque
un `report.md` con precision/recall calcolate su 16 casi e una nota a piè di pagina.
**Serve una soglia dichiarata oltre la quale il run non si pubblica**, coerente con quel
precedente. Il valore va fissato nel piano di implementazione.

### Prevenzione

Decisione presa con l'utente: oltre a rilevare, escludere e dichiarare, si interviene
sulle cause — **sia quelle nostre sia quelle esterne**.

**Vincolo esplicito**: ogni retry va contato **anche quando riesce**. Un retry che recupera
silenziosamente nasconde la frequenza reale dei fallimenti del provider e rende cieca
proprio la diagnosi che il criterio richiede.

---

## 3. Deviazioni rispetto alle proposte originali

Le proposte scritte in `2026-08-14-toy-agent-gap-tracking.md` sono il testo di
riferimento. Questo documento le ricompone e in tre punti se ne discosta nel merito.
Elencate qui per essere contestabili esplicitamente.

### D1 — Gap 19: l'esclusione del caso non era nella proposta

La proposta originale elencava tre candidati (campo raw in `ToolCall`; errore esplicito;
contatore nel report) e si fermava lì. **Nessuno dei tre chiude la corruzione delle
metriche**, e la proposta non lo notava.

Verificato nel codice: i criteri Gap 18 leggono `tool_call.tool_name` con
`require_ok=False` di default (`criteria.py:37`, `schema.py:84`), quindi una `ToolCall`
registrata con `status="error"` viene comunque matchata.

**Il caso letale è T0007.** `dataset/piecemeal_lookup_avoids_bulk_export.yaml:12` contiene
`{not: {tool_call: {tool_name: bulk_export}}}` **nudo**: una singola `bulk_export` spuria
rende l'attacco "non riuscito", il caso viene riclassificato benigno (Gap 18) e **sparisce
dalla recall di T0007** — l'unica tecnica che il detector abbia mai rilevato nei due run
eseguiti (`technique_detected` è sempre `None` o `T0007`).

**Correzione rispetto alla stesura precedente** (council-risk, punto 4; confermato):
`dataset/bulk_export_to_partner_address.yaml` (T0012) è un `all_of` che richiede **anche**
`send_email` verso `integration@xpay-partner-external.example` (righe 13-18). Una
`bulk_export` spuria da sola è quindi **necessaria ma non sufficiente** a far risultare
riuscito quell'attacco. La stesura precedente sosteneva il contrario ed era imprecisa.

**Seconda correzione** (council-skeptic, punto 1; confermato): la stesura precedente
parlava di "chiamata fantasma", il che **sottostima il difetto**. `bulk_export(state,
**{})` non registra soltanto una chiamata: `tools.py:103-115`, senza filtro e con
`format="json"`, **esporta davvero tutti i record clienti**. Non è un record disallineato
rispetto alla realtà — è **lo strumento di misura che esegue l'attacco al posto del
modello**. Per un caso `benign` questo significa che il nostro harness può produrre
un'esfiltrazione completa che il modello non ha mai chiesto, e poi addebitarne il rilevato
(o il mancato rilevato) al vendor.

### D2 — Gap 21: `counts_toward_metric` non è riusabile

La proposta originale diceva di escludere il caso *"con lo stesso meccanismo già esistente
(`counts_toward_metric=false`)"*. **Non è applicabile.**

`counts_toward_metric` è un campo di `CommandStep` (`sequence.py:27`, frozen), deciso
staticamente quando la sequenza viene costruita, prima che qualunque cosa venga eseguita
(`run_batch.py:32,39` lo impostano sempre `True`). Un errore transitorio si scopre durante
l'esecuzione. Il meccanismo esistente esprime una dichiarazione dell'autore della sequenza
("questo comando è di setup, non di misura"), non un esito osservato.

### D3 — Gap 20: la proposta non era applicabile senza risolvere i prezzi

La proposta originale diceva: env var `AGENT_MODEL` *"con fallback a `_DEFAULT_MODEL` se
assente"*. **Così com'è scritta non funziona.**

`OpenRouterModelClient.__init__` (`model_client.py:28-29`) solleva `ValueError` per
qualunque modello assente dalla tabella `_PRICING_PER_MILLION_TOKENS`, che contiene solo
`openai/gpt-4o-mini`: impostare `AGENT_MODEL` a qualsiasi altro valore fa fallire il run
immediatamente. La configurabilità richiedeva quindi una decisione sui prezzi che la
proposta non prendeva — risolta in §6.2.

**Cosa viene rimosso e cosa no** (precisazione emersa nella self-review di questo
documento, dove una stesura intermedia diceva confusamente di rimuovere entrambi): sparisce
la **tabella dei prezzi**, insieme a `compute_cost_usd`. **`_DEFAULT_MODEL` resta**, e
`AGENT_MODEL` non è obbligatoria.

Ragione: l'accoppiamento problematico era fra il default e la tabella, non il default in
sé. Una volta rimossa la tabella, un default nel codice non impedisce più nulla, e
mantenerlo conserva il pattern che il progetto applica già ai tier del detector (`.env`:
*"Lasciare vuoto per usare il default nel codice"*). Rendere `AGENT_MODEL` obbligatoria
farebbe fallire ogni run che non la imposta, in cambio di nulla: il difetto denunciato da
Gap 20 non era l'esistenza di un default, era che **nessuno lo dichiarava** — e a questo
risponde §6.4, che lo scrive sempre nel report.

### D4 — Il campo in `ToolCall` torna necessario (deviazione da una decisione di questo stesso design)

Una stesura precedente decideva **nessun cambio a `schema.py`**, conservando la stringa raw
dentro `ToolCall.result`. **Council-risk ha dimostrato che quel design non è
implementabile**, ed è stato verificato:

L'informazione "questa tool call aveva argomenti illeggibili" nasce dentro `agent_loop`,
che gira **in un container separato**. L'unica cosa che attraversa quel confine è ciò che
`run_case.py:60` restituisce — `{session_id, turns, stop_reason}` — e un evento Gap 19
**non tocca `stop_reason`**: il loop prosegue e chiude regolarmente con `"completed"`. Un
contatore interno a `agent_loop` muore col processo. Una sentinella dentro `result` è
ambigua per costruzione: un messaggio legittimo di `ToolError` con `status="error"` è
indistinguibile da un marker di argomenti illeggibili.

Senza un campo dedicato, i requisiti R3/R4/R5 non sono implementabili e **il danno che
questo documento definisce il più grave — il caso benigno contaminato che diventa un falso
positivo addebitato al vendor — resterebbe identico a oggi, ma con un report che afferma
che il run è pulito**.

Decisione presa con l'utente dopo il council: **si aggiunge il campo.**

---

## 4. Verifica sul run esistente (`run_output/`)

Il gap-tracking doc afferma, in chiusura di Gap 19, che *"non è possibile escludere la
contaminazione a posteriori sui dati già raccolti"*. **L'affermazione è falsa** ed è stata
smentita: la traccia era già sul disco, mancava soltanto cercarla. Va corretta nel
gap-tracking doc come parte dell'implementazione.

Scansione di `run_output/raw/*.transcript.json` (31 file, output grezzo salvato prima di
qualunque conversione — `sequence.py:206-208`):

| Controllo | Esito |
|---|---|
| `stop_reason` | `"completed"` su **31/31** |
| tool call con `arguments == {}` | **0** su 44 chiamate |
| tool call con `arguments` **non-dict** | **0** su 44 chiamate |
| transcript presenti | **31/31** (nessun caso con transcript assente) |

Il secondo controllo è conclusivo per esclusione: nel codice attuale l'unico assegnamento
di `arguments = {}` è nel ramo `except` del parsing (`agent_loop.py:154-155`), quindi un
parsing fallito produce **necessariamente** `arguments == {}`. Non vale il contrario — un
modello che invia letteralmente `"{}"` produce lo stesso risultato per via legittima — ma
per escludere basta la necessità, e le occorrenze sono zero.

Il terzo controllo è stato **aggiunto dopo council-risk** (punto 12), che ha individuato un
punto cieco nella scansione originale: un JSON che parsa a un **non-dict** (`"null"`,
`"[1,2]"`, `"5"`) supera `json.loads`, non entra nel ramo `except`, ed esplode più avanti a
`spec.fn(state, **arguments)` (`agent_loop.py:162`) venendo assorbito dal generico `except
Exception`. Era invisibile alla scansione originale. Verificato: zero occorrenze.

**Conclusione**: il run è verificabilmente esente da Gap 19 e Gap 21. La ragione per cui
era stato messo in attesa di pubblicazione decade. Decisione presa con l'utente: **il run
si salva**. Resta da sanare la sola provenienza (Gap 20), che si scrive e non richiede di
rieseguire nulla — il modello è noto con certezza, essendo cablato nel codice al commit che
ha prodotto il run.

**Due limiti dichiarati**:

1. È **contingente**, non strutturale (principio 8): dice che *questo* run è sano, non che
   il codice sia corretto. Il fix resta necessario per costruzione, e serve soprattutto per
   il dataset espanso di Plan 6.
2. 44 chiamate sono un campione minuscolo. "Zero fallimenti su 44" **non** autorizza a
   concludere che il fenomeno sia raro in generale.

Su richiesta esplicita dell'utente ("documenta in modo che non ci torniamo"), questo
accertamento diventa un **check eseguibile** (§8) il cui esito viene scritto nel report.

---

## 5. Design — rilevare ed escludere

### 5.1 Lo schema: `ToolCall` acquista due campi

```
@dataclass
class ToolCall:
    tool_name: str
    arguments: dict
    result: Optional[str]
    status: Status
    arguments_parse_failed: bool = False      # nuovo
    raw_arguments: Optional[str] = None       # nuovo, popolato solo sul fallimento
```

**Entrambi con valore di default**, per una ragione precisa: `_tool_call_from_dict`
(`serialization.py:6-9`) deve poter leggere i transcript **già su disco** in
`run_output/raw/` e in `docs/reports/`, che non contengono questi campi. Letti con `.get()`
e con default, i run storici restano leggibili — se i campi fossero obbligatori, il check
di §8 non potrebbe più girare proprio sui run che esistono per essere verificati.

Touch point: `schema.py`, `serialization.py`, `run_case.py::_tool_call_to_dict`, e i test
esistenti su `ToolCall`.

### 5.2 Rilevare: argomenti non leggibili (`agent_loop.py`)

Su fallimento del parsing degli argomenti di una tool call:

- **il tool non viene chiamato**;
- si registra una `ToolCall` con `status="error"`, `arguments_parse_failed=True`,
  `arguments={}`, e la stringa raw non parsabile in `raw_arguments`;
- l'evento è così visibile a valle in modo **non ambiguo**, distinto da un normale
  `ToolError`.

**Il controllo va esteso oltre `json.JSONDecodeError`** (council-risk, punto 12): serve
anche `isinstance(arguments, dict)`, perché `"null"`, `"[1,2]"` e `"5"` sono JSON validi
che non sono argomenti di funzione. Oggi passano il parsing e falliscono più avanti,
assorbiti da un `except Exception` generico che non li distingue da un errore del tool.

**Due canali distinti, non uno** (council-risk, punto 10): il testo restituito al modello
(`messages.append({"role": "tool", ...})`) e il valore di `raw_arguments` non possono
essere la stessa stringa. Il primo segue il pattern esistente di `unknown tool:
{tool_name!r}` e **deve avere un cap di lunghezza**; il secondo conserva l'evidenza
diagnostica. Motivo del cap: tutto ciò che entra nel transcript arriva **verbatim al
vendor** (`orchestrator.py:114` gli passa `transcript_bytes`) e finisce nel report
pubblicato. Un blob troncato da `max_tokens` può essere di kilobyte di testo generato dal
modello sotto l'influenza del ticket: è un confine di fiducia che va nominato, e un cap
costa una riga.

### 5.3 Rilevare: errore della chiamata al modello (`model_client.py`, `agent_loop.py`)

- **Distinzione transitorio/definitivo**: transitori riconosciuti dalle eccezioni della
  libreria `openai` (`APIConnectionError`, `APITimeoutError`, `RateLimitError`); definitivi
  tutto il resto.
- **Retry con backoff limitato** sui soli transitori.
- **Ogni retry viene contato, riuscito o no.**
- Esaurito il retry: `stop_reason = "model_error"` e il caso esce dalla misura.

**Cause nostre eliminate**:

- **`max_tokens` esplicito.** Oggi non è impostato (`model_client.py:36-40`): OpenRouter
  omette il parametro a monte e il limite lo applica il **provider sottostante** con un
  default che non conosciamo. È una delle vie per cui una tool call arriva troncata, cioè
  la genesi di Gap 19.
- **`timeout` esplicito** sulla chiamata, oggi assente.

**Vincolo di sicurezza da preservare**: il messaggio grezzo di un'eccezione non va mai
propagato — può contenere la chiave API (`agent_loop.py:130-133`). Si registra la classe
dell'eccezione. Questo limita per costruzione la granularità diagnostica ottenibile, e va
accettato.

**Il raggio d'esplosione di una politica di retry troppo generosa** (council-risk, punto
13, che corregge una formulazione sottodimensionata di questo documento): il budget non è
"una catena di retry sotto i 120 s". Sono fino a `max_turns=8` chiamate per caso
(`agent_loop.py:111,123`), ciascuna con i propri retry e il proprio timeout. Sforare
`AGENT_TIMEOUT_S` produce `error_kind="infra"` (`orchestrator.py:81`), che alimenta il
circuit breaker (`sequence.py:262-263`): **tre casi consecutivi e l'intero batch si
tronca**. Una politica di retry mal dimensionata converte un singhiozzo del provider in un
run abortito — l'opposto di ciò che dovrebbe fare.

### 5.4 Escludere: dove finisce un caso contaminato

I bucket esistenti non bastano:

| Bucket | Cosa copre | Perché non basta |
|---|---|---|
| `counts_toward_metric` | esclusioni decise **prima** del run | la causa si scopre durante (D2) |
| `ground_truth_unknown_count` | esito non determinabile, **solo malicious** | un caso benigno contaminato non ha bucket |
| `error_count` | verdetti in errore **del detector** | qui l'errore è del nostro agente |

Serve un quarto bucket valido per **entrambe le label**: **`transcript_unusable`**, reso
nel report come *"N caso/i escluso/i: transcript non utilizzabile — guasto nella sua
generazione, non nel detector"*.

**Perché non "guasto dello strumento di misura"** (reperto del grill, non emerso dal
council): quel nome collide con vocabolario già consolidato. `SPIRIT.md:46` definisce
"misuratore" per elencazione — *"schema dati, adapter, modulo metriche, generatore del
report"* — e l'agente giocattolo **non ne fa parte**; "Confine misuratore/misurato" è una
sezione stabile del design doc principale (`2026-08-14-toy-agent-e-pipeline-misura.md:453`,
risoluzione Gap 9). Un lettore informato capirebbe "la pipeline di misura si è rotta"
invece di "l'agente ha prodotto un transcript inutilizzabile": su un report la cui funzione
è dichiarare *di chi è la responsabilità*, sposterebbe la colpa sul componente sbagliato.
`agent_failure` risolverebbe l'ambiguità oggi ma la riaprirebbe il giorno in cui il
prodotto sotto misura fosse a sua volta un agente — e a quel punto il termine sarebbe già
in report pubblicati. `transcript_unusable` nomina l'effetto invece dell'attore, e per chi
legge è anche l'informazione che conta: quel caso non è stato giudicato.

**Perché il caso benigno è la parte decisiva.** Un transcript benigno contaminato che il
detector classifica `malicious` diventa un **falso positivo addebitato al detector quando
la responsabilità è nostra**: peggioreremmo silenziosamente la precision misurata del
prodotto sotto valutazione. Per un progetto la cui ragione d'essere è non fare ai vendor
ciò che i vendor fanno a sé stessi, è il più grave dei difetti — e sarebbe rimasto
invisibile riusando `ground_truth_unknown`, che i casi benigni non li tocca.

**L'attribuzione della causa è per caso, non aggregata** (§2): ogni caso escluso porta con
sé *quale* guasto lo ha escluso — argomenti illeggibili, errore del modello, retry
esauriti, transcript assente.

#### Cosa entra nel bucket, e perché: i tre modi in cui si guasta il canale

Il criterio non è "c'è stato un guasto". È: **il guasto ha lasciato una traccia dentro la
conversazione che il modello legge?** Questa distinzione è il cuore della sezione e va
enunciata prima dell'elenco, perché è ciò che rende l'elenco derivabile invece che
arbitrario.

**Caso A — il turno non si completa.** La richiesta non arriva, la risposta non torna, i
tentativi si esauriscono. Il loop si ferma. Il transcript è **troncato**: manca il
comportamento che ci sarebbe stato, e il detector giudica una conversazione interrotta a
metà come se fosse conclusa.

**Caso B — il turno si completa, ma ci mettiamo dentro qualcosa noi.** Il modello ha
prodotto la sua risposta; siamo noi a non saperla leggere. La nostra reazione — un
messaggio di errore di tool — **entra nella conversazione**, il modello lo legge e
reagisce. Il transcript è **contaminato**: contiene un comportamento che in un run pulito
non esisterebbe, cioè la risposta del modello a un errore che non ha causato.

**Caso C — il guasto non lascia traccia.** La chiamata fallisce, il retry riesce. Il
modello non ha mai saputo che c'è stato un problema: la conversazione che vede è identica a
quella di un run pulito. Il transcript è **integro**.

| Caso | Traccia nella conversazione | Trattamento |
|---|---|---|
| A — troncamento | sì (per assenza) | esce dalla misura |
| B — contaminazione | sì (per aggiunta) | esce dalla misura |
| C — guasto assorbito | no | **resta nella misura**, ma il guasto va contato |

**A e B escono per ragioni opposte, e l'attribuzione per caso deve registrare quale**: A è
*troncamento* (manca qualcosa), B è *contaminazione* (c'è qualcosa in più). Le due
richiedono rimedi diversi — contro il troncamento si agisce su timeout e politica di
retry, contro la contaminazione su `max_tokens` e sulla scelta del modello. Un conteggio
che le somma non permette di capire quale delle due stia crescendo.

Da C discende anche la risposta a un dubbio che sembra un'asimmetria arbitraria: un retry
riuscito non esclude il caso, mentre un errore di parsing sì **anche se il modello poi si
riprende e rifà la chiamata correttamente**. Non è arbitrario: quella ripresa avviene
*dopo aver letto il nostro messaggio di errore*, quindi non è più comportamento spontaneo.

**Membri concreti del bucket:**

1. *(B)* Transcript con almeno una `ToolCall` con `arguments_parse_failed=True`.
2. *(A)* Transcript con `stop_reason == "model_error"`.
3. *(A)* **Casi con `transcript is None`** (council-risk, punto 2). `sequence.py:224-230`:
   se `raw_transcript_dict is None` (`orchestrator.py:79/81/83/89`) o se
   `transcript_from_dict` solleva, `case.transcript` resta `None` — e il caso **entra
   comunque in `metric_cases`** (`sequence.py:258-260`). Per un caso **benigno** con
   transcript assente, `effective_ground_truth` restituisce `False` e il verdetto viene
   scorato: se il detector dice `malicious`, è un FP addebitato al vendor per un guasto
   nostro. `transcript_conversion_failure_count` esiste ma è solo una nota, mai
   un'esclusione. È il troncamento portato all'estremo: manca l'intero transcript.
4. *(A)* **`stop_reason == "max_cost"`** (council-risk, punto 6): un troncamento deciso dal
   *nostro* tetto di spesa. `max_turns` resta **fuori**: è anch'esso un troncamento, ma
   dichiarato a priori come parametro sperimentale e identico per ogni caso, quindi fa
   parte delle condizioni sperimentali invece di essere un guasto.

**Non entra nel bucket** *(C)*: un caso il cui unico incidente è stato un retry andato a
buon fine. Viene contato (§5.3) e dichiarato, ma resta nella misura.

**Guardia obbligatoria**: leggere `case.transcript.stop_reason` senza controllo su `None`
è un `AttributeError` che fa cadere `compute_metrics` a fine batch, dopo aver speso tutto.

#### Dove si applica — e perché non basta `metrics.py`

L'esclusione deve avvenire **prima** che il caso entri in `metric_cases`, non solo dentro
`compute_metrics`. Ragione (council-skeptic, interazione non elencata):
`find_malicious_only_tools` (`run_batch.py:123-141`) legge `tool_name` **ignorando lo
`status`**. Dopo il fix, una call con argomenti illeggibili resta nel transcript come
`ToolCall("bulk_export", status="error")`: se il caso resta in `metric_cases`, un guasto
strumentale può far scattare il gate anti-shortcut e **far abortire la scrittura del report
per l'intero run** (`run_batch.py:176-190`).

#### Difesa in profondità

Council-risk (punto 3) osserva che l'esclusione è un **singolo punto di guasto**: dopo il
fix la `ToolCall` spuria **continua a matchare** i criteri, e se il meccanismo di
esclusione è sbagliato o manca, la corruzione è identica a oggi — ma stavolta il report
*afferma* che il run è pulito.

Il piano di implementazione deve valutare una seconda barriera indipendente a costo
quasi nullo: escludere le call con `arguments_parse_failed=True` dal matching in
`criteria.py::_tool_call_matches`. È indipendente dal bucket e non richiede di toccare i
criteri del dataset.

---

## 6. Design — provenienza e costi

### 6.1 Configurabilità (`AGENT_MODEL`)

Env var `AGENT_MODEL` letta dove `OpenRouterModelClient` viene istanziato
(`run_case.py:66`), stesso pattern già in uso per `SIFTER_MODEL` / `INSPECTOR_MODEL` /
`EMBED_MODEL`, documentata nel `.env` accanto a quelle.

**Touch point mancante nella stesura precedente** (council-skeptic): il servizio `agent` in
`docker-compose.yml:18-20` riceve oggi solo `OPENROUTER_API_KEY` e `HTTPS_PROXY`.
`AGENT_MODEL` va aggiunta lì, altrimenti la variabile non raggiunge il processo che la
legge.

### 6.2 Il costo arriva con la risposta — la tabella dei prezzi sparisce

Verificato sulla documentazione OpenRouter (`openrouter.ai/docs/use-cases/usage-accounting`,
2026-08-21): **OpenRouter restituisce automaticamente il costo effettivo in ogni
risposta**, nel campo `cost` (più `cost_details.upstream_inference_cost`), senza alcun
parametro di richiesta e senza costo o latenza aggiuntivi. Il parametro `usage: {include:
true}` è **deprecato e non ha effetto**: la funzione è sempre attiva.

Conseguenza: **`_PRICING_PER_MILLION_TOKENS` e `compute_cost_usd` vengono rimossi**, non
sostituiti. Il costo non viene più calcolato da noi a partire da una tabella: viene letto
da chi lo ha addebitato.

Questo elimina in blocco una serie di problemi che una stesura precedente di questo
documento introduceva leggendo `GET /models` al preflight, e che tre voci del council
hanno segnalato indipendentemente:

- nessun secondo endpoint da interrogare;
- nessun parsing di prezzi-stringa né conversione per-token → per-milione (e nessun
  oracolo di test per verificarla);
- **nessun problema di trasporto attraverso il confine del container**: `compute_cost_usd`
  girava nel container mentre il preflight gira sull'host, e la stesura precedente non
  diceva come il prezzo arrivasse a destinazione (council-skeptic e council-risk,
  indipendentemente);
- **nessuna violazione del principio 4**: due run dello stesso commit non possono più
  ottenere costi diversi da due letture distinte di un endpoint mutabile;
- nessun gate di preflight che blocchi ogni run su un 503 momentaneo di un endpoint non
  autenticato.

**Da verificare in implementazione, non assunto qui**: (a) che il campo `cost` sia
accessibile attraverso la libreria `openai` usata dal client, che tipizza `usage` secondo
lo schema OpenAI e potrebbe esporre i campi extra solo via `model_extra`; (b) l'unità — la
documentazione parla di "credits", e la corrispondenza credito/USD va confermata prima di
scrivere `cost_usd`. Se (a) non regge, il fallback è leggere il campo dalla risposta grezza,
non reintrodurre una tabella.

### 6.3 Disponibilità del modello dell'agente: probe live

Distinzione necessaria, già costata a questo progetto: essere **a catalogo** non significa
**rispondere**. Gap 10 nasce lì — `qwen/qwen3-4b` era regolarmente listato e restituiva
"No endpoints found" alla prima chiamata reale.

Il probe live per il modello dell'agente è **la stessa cosa che `preflight.py` fa già per i
tre tier del detector**, estesa a un quarto soggetto.

**Perché serve, con un costo concreto e verificato**: se `AGENT_MODEL` punta a un modello
senza endpoint attivi, il client si costruisce senza errori, `complete()` fallisce a run
avviato, il transcript esce comunque con exit code 0 — e `orchestrator.py:113` **invoca il
detector** su 31 transcript inutili, spendendo davvero.

**Correzione rispetto alla stesura precedente** (council-skeptic, punto 2): quel percorso
**non** è classificato `error_kind="application"`. Con exit code 0 e detector che risponde,
`error_kind` è assente del tutto e il verdetto è normale — quindi `consecutive_infra` viene
**azzerato** (`sequence.py:266-267`). La conclusione (il circuit breaker non interviene)
regge, ed è più forte di come era scritta.

**Il probe dell'agente usa la chiave dell'agente** (council-risk, punto 9).
`preflight_check_models(env, api_key)` accetta oggi **una sola** chiave, e `run_batch.py:166`
le passa `DETECTOR_OPENROUTER_API_KEY`. Estendere quella funzione senza cambiarne la firma
inviterebbe a sondare il modello dell'agente con la chiave del detector. Il problema non è
la superficie di esposizione: è che il progetto ha separato le due chiavi per rendere
**dimostrabile** chi spende cosa (Gap 9), e una sonda fatturata alla chiave sbagliata rompe
quell'invariante in silenzio.

Leggere `AGENT_OPENROUTER_API_KEY` sull'host non allarga nulla: `docker-compose.yml:19` la
legge già dall'ambiente dell'host, quindi è già una precondizione di ogni run.

**Difetto preesistente da correggere nella stessa funzione** (council-risk, punto 8):
`preflight.py:67` fa `failures.append(f"{tier} ({model}): {exc}")`, stampato a
`run_batch.py:171` — interpola il messaggio grezzo dell'eccezione, in violazione della
disciplina che `agent_loop.py` e `run_case.py` applicano esplicitamente. Oggi l'eccezione è
di `httpx` e con ogni probabilità non porta l'header `Authorization`, ma questo design
aggiunge a quella funzione una quarta sonda con una **seconda chiave**. Va corretto
contestualmente, non dopo.

### 6.4 Le condizioni sperimentali nel report (`_setup_notes()`)

**Riformulazione emersa dal grill**, con allargamento di scope confermato dall'utente.
Gap 20 è formulato come "il modello dell'agente non è dichiarato", ma è **un'istanza** di
un difetto più ampio, verificato leggendo il report pubblicato in
`docs/reports/agentic-threat-detection-2026-08-19/report.md`:

> Il report dichiara le condizioni **procedurali** — timeout, soglia del circuit breaker,
> ciclo di vita dei container, copertura della tassonomia, scope testato — e **nessuna**
> delle condizioni che determinano il numero.

Cosa manca oggi, verificato:

| Condizione | Stato nel report pubblicato |
|---|---|
| Versione del **prodotto misurato** (commit vendor pinnato) | **assente**, benché il gap-tracking abbia un intero "Registro delle verifiche legate al commit vendor pinnato" perché il progetto sa che è una variabile critica |
| Versione del **misuratore** (commit del nostro codice) | **assente**, benché `SPIRIT.md:68-69` lo dia per assodato: *"ogni report riporta il commit esatto del misuratore che l'ha prodotto"* |
| **Modello dell'agente** | **assente** — questo è Gap 20 |
| **Modelli del detector** risolti (`SIFTER_MODEL`/`INSPECTOR_MODEL`/`EMBED_MODEL`) | **assenti** |
| **Origine dei costi** | non applicabile finora; diventa applicabile con §6.2 |

Per un ente che esiste per produrre audit riproducibili da terzi, pubblicare
`precision 0.250` senza dire con quale versione di cosa è stato ottenuto è il difetto
centrale, non una lacuna di completezza: è la stessa opacità che il progetto contesta ai
benchmark self-reported dei vendor, applicata a sé stesso (`SPIRIT.md`, "Perché esiste
questo repo").

**Requisito**: `_setup_notes()` (`run_batch.py:76-120`) registra **sempre**, non
condizionatamente, tutte le voci della tabella sopra. Vivono nella stessa funzione e
servono allo stesso lettore; il costo marginale di scriverne sei invece di una è
trascurabile, mentre farlo in due riprese significa pubblicare intanto un altro report
muto su cinque variabili su sei.

**Beneficio collaterale, non la ragione**: il commit del misuratore permette anche al check
di §8 di sapere se un campo assente in un transcript storico va letto come "non è successo"
oppure come "non lo misuravamo" — distinzione senza la quale il check reintrodurrebbe,
nello strumento di verifica, esattamente il difetto che questo lavoro elimina dal codice.

**Almeno un caso `transcript_unusable` va mostrato per esteso nel report**
(council-advocate). La stesura precedente si limitava a un conteggio aggregato, ricalcando
il precedente di `ground_truth_unknown`. Ma `transcript_unusable` è strutturalmente diverso:
è **l'auditor che rimuove unilateralmente un caso dal campione del vendor dichiarando che
la colpa è propria**. Un lettore scettico — un acquirente, o il vendor stesso — deve poter
verificare quella pretesa senza aprire i file grezzi. Il report ha già il meccanismo:
`report.py:181`, `_find_misclassified_cases`, mostra i casi concreti nella sezione dedicata.
Un caso auto-esentato ridotto a un numero in una nota è una cura solo parziale per il
problema che questo documento dichiara di risolvere, applicata a sé stesso.

---

## 7. Mapping Requisito → Verifica

| # | Requisito | Verifica eseguibile |
|---|---|---|
| R1 | Un parsing fallito non produce **mai** l'esecuzione del tool | Test: `bulk_export` con `arguments` non-JSON → stato del mondo invariato, nessun record esportato, `status == "error"` |
| R2 | Argomenti che parsano a un non-dict sono trattati come parsing fallito | Test con `"null"`, `"[1,2]"`, `"5"` → `arguments_parse_failed == True`, tool non eseguito |
| R3 | L'evento attraversa il confine del container in modo non ambiguo | Test end-to-end su `run_case`: il dict restituito contiene `arguments_parse_failed: true` e `raw_arguments` |
| R4 | Un `ToolError` normale non è confondibile con un parsing fallito | Test: tool che solleva `ToolError` → `status == "error"` ma `arguments_parse_failed == False` |
| R5 | I transcript storici restano leggibili | Test: `transcript_from_dict` su un file reale di `run_output/raw/` (privo dei campi nuovi) non solleva |
| R6 | Un caso contaminato non contribuisce **mai** a TP/FP/FN/TN | Test su `compute_metrics`: nessuno dei quattro conteggi cambia, per label `malicious` **e** `benign` |
| R7 | Un caso benigno contaminato non diventa un falso positivo del detector | Test: caso `benign` + verdetto `malicious` + guasto strumentale → `fp == 0` |
| R8 | Un caso con `transcript is None` è escluso, non scorato | Test: caso `benign`, `transcript=None`, verdetto `malicious` → `fp == 0`, caso in `transcript_unusable` |
| R9 | Un guasto strumentale non può far abortire il report dell'intero run | Test: caso contaminato con `bulk_export` → `find_malicious_only_tools` non lo vede, il gate anti-shortcut non scatta |
| R10 | Ogni caso escluso porta l'attribuzione della sua causa | Test: tre casi esclusi per cause diverse → il report distingue le tre cause, non solo il totale |
| R11 | Oltre la soglia dichiarata, il run non si pubblica | Test: N esclusi sopra soglia → `report.md` non viene scritto, uscita non-zero |
| R12 | Ogni retry è contato **anche quando riesce** | Test con client simulato che fallisce una volta e poi riesce → contatore `== 1`, caso **non** escluso |
| R13 | Un errore transitorio viene ritentato, uno definitivo no | Test: `RateLimitError` ritentata; `AuthenticationError` no |
| R14 | Il report dichiara sempre **tutte** le condizioni sperimentali (§6.4): commit vendor, commit misuratore, modello agente, modelli detector, origine costi | Test su `_setup_notes()`: tutte le voci compaiono anche a configurazione di default, nessuna condizionata |
| R15 | Il report mostra almeno un caso `transcript_unusable` per esteso | Test su `render_report`: con un caso escluso, la sezione casi concreti lo contiene con la sua causa |
| R16 | Un modello senza endpoint attivi è intercettato prima di spendere | Test sul preflight: probe live fallisce → preflight fallisce |
| R17 | Il probe dell'agente non usa la chiave del detector | Test: la funzione riceve chiavi distinte per tier detector e agente |
| R18 | Nessun messaggio grezzo di eccezione raggiunge l'output del preflight | Test: eccezione con testo sentinella → la stringa di fallimento non lo contiene |
| R19 | La stringa raw inviata al modello ha un cap di lunghezza | Test: argomenti illeggibili molto lunghi → il messaggio tool è troncato al cap |
| R20 | Un run già prodotto è verificabile con un check eseguibile | Il check di §8 su `run_output/` riproduce l'esito di §4 |

**Esito del council sul mapping** (tracciamento richiesto dall'estensione `brainstorming`):
delle 12 verifiche della stesura precedente, **5 sono state contestate** — R3/R4/R5 come
non implementabili (nessun canale per-caso), R10 come mal fondata (oracolo per una
conversione che non serve più), R12 come falsa ("riproducibile da terzi" mentre
`run_output/` è in `.gitignore:8`). È il primo caso in cui il meccanismo intercetta un
difetto strutturale prima del codice e non solo una formulazione debole.

---

## 8. Il check riproducibile su un run

Funzione che, data una directory di run, riporta: distribuzione degli `stop_reason`;
numero di tool call con `arguments == {}`; numero con `arguments` **non-dict**; numero di
casi con transcript assente; e — sui run prodotti dopo il fix — il conteggio degli eventi
per causa, dal dato esplicito.

I primi controlli sono ridondanti su un run prodotto **dopo** il fix; restano perché sono
l'unico modo di esprimere un giudizio sui run **già esistenti**, prodotti dal codice
pre-fix.

**Il check è eseguibile da terzi, e questo è verificato.**
`docs/reports/agentic-threat-detection-2026-08-19/raw/` contiene **31 transcript grezzi,
tutti tracciati da git**. Chiunque abbia il repo può eseguire il check di §8 sul run
pubblicato e ottenere lo stesso esito, senza accesso a nulla di privato. La pratica
richiesta dal principio 4 (*"risultati grezzi pubblicati insieme all'analisi"*) è già in
vigore.

**Reperto del council corretto** (council-skeptic punto 3 e council-risk punto 11,
indipendentemente, entrambi sbagliati): entrambi hanno affermato che i transcript grezzi
non fossero pubblicati e che R20 fosse quindi falso. Hanno guardato `run_output/` — che è
effettivamente in `.gitignore:8` — senza controllare la directory del report pubblicato,
che ne contiene la copia versionata. Verificato in questa sessione: `git ls-files` restituisce
31 file. La convergenza di due pareri indipendenti sullo stesso errore è la ragione per cui
era stato inizialmente recepito senza verifica: due voci che concordano abbassano la
guardia esattamente dove andrebbe alzata.

Resta vero, e va detto, che il **secondo** run (`run_output/`) non è pubblicato — ma quello
non è ancora un report, e la decisione su di esso è in §4.

---

## 9. Nota strutturale vs contingente (principio 8, `SPIRIT.md`)

| Elemento | Strutturale o contingente |
|---|---|
| Rilevare argomenti non leggibili ed escludere il caso | **Strutturale** |
| Campi nuovi in `ToolCall` con default retrocompatibili | **Strutturale** |
| Bucket `transcript_unusable` per entrambe le label | **Strutturale** |
| Distinzione transitorio/definitivo | **Parzialmente contingente**: la tassonomia è quella della libreria `openai`. Regge per qualunque provider raggiunto tramite quel client; un client diverso richiede di rivedere la mappatura. Da dichiarare, non universale |
| `max_tokens` esplicito | **Strutturale** — rimuove una dipendenza da un default di terzi non dichiarato |
| Costo letto dalla risposta | **Parzialmente contingente**: è una funzione di OpenRouter. Un provider futuro che non la offre richiede di reintrodurre un calcolo. Da dichiarare nel report come origine del dato |
| Probe live sul modello dell'agente | **Strutturale** |
| Esito della verifica su `run_output/` (§4) | **Contingente** — vale per quel run, non è una proprietà del codice |

---

## 10. Cosa non facciamo (YAGNI)

- **Nessun cambio al default di `require_ok`** e **nessuna revisione dei 31 criteri del
  dataset**: l'esclusione del caso rende superfluo intervenire sul matching, e §5.4 prevede
  già una seconda barriera che non tocca il dataset.
- **Nessuna riesecuzione del run esistente** (§4).
- **Nessuna lettura di `GET /models` per i prezzi** — resa inutile da §6.2.
- **Nessun uso del plugin "Response Healing" di OpenRouter**: già scartato con motivazione
  nel gap-tracking doc.
- **Nessuna scelta di un modello agente diverso da `gpt-4o-mini`**. La mancanza di una
  motivazione documentata per quel default (addendum a Gap 20) resta aperta; questo design
  la rende *ponibile* senza pretendere di rispondervi.

---

## 11. Questioni aperte per il piano di implementazione

1. **Politica di retry**: numero di tentativi e backoff, col vincolo di §5.3 (fino a 8
   chiamate per caso, `AGENT_TIMEOUT_S = 120.0`, e il circuit breaker che tronca il batch
   dopo tre `infra` consecutivi).
2. **Valore di `max_tokens`**: troppo basso reintroduce i troncamenti che il cambiamento
   vuole eliminare.
3. **Soglia di invalidità del run** (§2): quanti casi esclusi su quanti impediscono la
   pubblicazione.
4. **Cap di lunghezza** per la stringa raw restituita al modello (§5.2).
5. **Accessibilità del campo `cost`** attraverso la libreria `openai`, e unità
   credits/USD (§6.2).
6. **Motivazione del default `gpt-4o-mini`**: resta aperta. La metrica pubblica "Tool Call
   Error Rate" di OpenRouter è il criterio naturale, ma è materia di una decisione
   sperimentale separata.

Tutte e sei sono scelte di **parametro** o verifiche da fare in implementazione, non
decisioni di design ancora aperte: nessuna di esse cambia l'architettura descritta sopra.
