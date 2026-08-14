# Gap tracking: toy agent + pipeline di misura (Fase 1)

Companion di `2026-08-14-toy-agent-e-pipeline-misura.md`. Ogni gap trovato durante la
revisione del design (o più avanti, durante l'implementazione) va registrato qui con
stato, evidenza e risoluzione proposta/applicata, prima di essere eventualmente
riportato nel design doc stesso.

Stati possibili: `open`, `in discussione`, `risolto nel design doc`, `accettato come limite dichiarato`.

## Gap 1 — SourceLens non trova mai il codice dei nostri tool

**Stato**: risolto nel design doc — sezione "Registro SourceLens per i tool del toy
agent (risoluzione Gap 1)" in `2026-08-14-toy-agent-e-pipeline-misura.md`, con tre
vincoli espliciti contro la distorsione della misura: (1) codice sorgente statico, mai
variato tra sessione benigna e malevola dello stesso tool; (2) eventuale comportamento
nascosto (es. `update_account` per T0007) deciso e fissato in fase di design del tool,
prima di eseguire il detector, non aggiustato dopo aver visto i risultati; (3) fonte
unica di verità nel nostro repo, il registro nel clone vendor punta lì, non a una copia
scritta apposta per SourceLens.

**Ancora aperto in origine ("cosa esattamente nasconde update_account"), ora deciso**:
vedi Gap 7 sotto — deciso durante la strutturazione di Plan 1 (non in fase di
costruzione del dataset come originariamente previsto, perché è codice del tool, non
contenuto di un `TestCase`), poi ristretto dopo un rischio trovato dal council checkpoint
su quel piano.

**Severità**: maggiore — tocca la validità metodologica del confronto con i numeri
dichiarati dal vendor (P=1.0, R=0.667), non solo un dettaglio implementativo.

**Evidenza**:
- `aidr/providers/sourcelens.py` (commit `7fad14d`): `get_source_code(server_names)`
  legge `REGISTRY = yaml.safe_load(open("aidr/data/source_registry.yaml"))["servers"]`
  e risolve i path da `BASE = Path("aidr/gauntlet/servers")`. Se un `server_name`
  richiesto non è nel registro, ritorna `{"status": "not_found"}`.
- `aidr/data/source_registry.yaml`: contiene esattamente 3 voci — `analytics_insights`,
  `business_metrics`, `host_toolkit` (i server del Gauntlet del vendor). Nessuno dei 6
  tool del nostro toy agent (`query_customer_db`, `read_ticket_content`, `send_email`,
  `update_account`, `run_diagnostic`, `bulk_export`) è presente.
- `aidr/detector/inspector.py`, `build_workflow()`: il workflow istruisce l'LLM
  Inspector a "1. elencare i server MCP nel transcript, 2. chiamare `get_source_code` su
  quei server..., 3. se l'implementazione nasconde comportamento oltre lo scopo
  dichiarato, classificare l'intera sessione come malevola." Con il registro attuale,
  il passo 2 ritorna sempre `not_found` per il nostro scenario.

**Perché conta**: il README del vendor cita "leggere l'implementazione reale del tool"
come meccanismo di punta di Inspector. Nel design doc
(`2026-08-14-toy-agent-e-pipeline-misura.md`, sezione "Set di tool") questo canale è
associato esplicitamente a T0007 (tool poisoning) via `update_account`. Se il canale non
scatta mai, un eventuale recall più basso di quanto dichiarato dal vendor sarebbe
indistinguibile da "il detector è più debole" — un confound che invaliderebbe il
confronto centrale che è l'obiettivo dichiarato della Fase 1 (`SPIRIT.md`).

**Risoluzione applicata**: estendere il registro nel nostro clone locale del vendor
(`agentic-threat-detection-vendor`, non upstream) con voci per i 6 tool del toy agent,
puntando — via mount o copia al build del container di controllo — al file sorgente
reale nel nostro repo (`agentic-security-audits`), non a una copia duplicata scritta
apposta per SourceLens. Vedi design doc per i tre vincoli anti-distorsione.

## Gap 2 — `ToolUsage.server_name` obbligatorio ma assente nel nostro `ToolCall`

**Stato**: risolto nel design doc — sezione "Adapter"
(`2026-08-14-toy-agent-e-pipeline-misura.md`)

**Evidenza**: `aidr/schema/agent_event.py`: `ToolUsage.server_name: str` è un campo
posizionale obbligatorio, senza default. Il nostro tipo `ToolCall` (design doc, sezione
"Schema di misura") non ha un campo equivalente.

**Perché è minore**: verificato che né `Sifter.triage()` né `Inspector.analyze()` usano
mai `server_name` — lavorano solo sul testo prodotto da `AgentEvent.transcript()`, che
include `tool_name` ma non `server_name`. È quindi un campo da popolare per non rompere
la costruzione dell'oggetto (qualunque stringa va bene), non un requisito che influenza
la detection.

**Risoluzione proposta**: nell'adapter, popolare `ToolUsage.server_name` con un valore
placeholder deterministico (es. uguale a `tool_name`, o una costante) al momento della
conversione `ToolCall` → `ToolUsage`. Non serve aggiungere il campo al nostro
`ToolCall` pubblico.

## Gap 3 — cwd, sottoprocessi MCP richiesti dal vendor, e ambiente Windows

**Stato**: risolto nel design doc — sezione "Container di controllo: fedeltà d'ambiente
e contenimento di sicurezza" (`2026-08-14-toy-agent-e-pipeline-misura.md`)

**Evidenza**: `sourcelens.py`, `threatlens.py`, `policylens.py` leggono path relativi
hardcoded (`aidr/data/...`, `aidr/gauntlet/servers`) — vanno eseguiti con cwd nella repo
vendor clonata, non nella nostra (`agentic-security-audits`). `Inspector.__init__`
lancia i tre provider come sottoprocessi MCP veri (`MCPClient`), non li chiama in
process. Inoltre il codice del vendor è scritto/testato per Linux (bash, sottoprocessi
stdio), mentre la macchina disponibile è Windows 11 consumer senza GPU.

**Risoluzione applicata**: un container Linux locale (Docker Desktop, nessuna GPU
richiesta) ospita sia il codice del vendor (cwd = root del clone vendor dentro il
container, ambiente Python del vendor installato lì) sia l'esecuzione dei tool del toy
agent. Questo container ha un secondo scopo emerso in discussione, non solo fedeltà
d'ambiente: **contenimento di sicurezza**, perché i `TestCase` malevoli inducono
deliberatamente il toy agent a tentare azioni pericolose (`send_email` senza whitelist,
`bulk_export` senza cap, `run_diagnostic`). Vedi la sezione del design doc per il
dettaglio completo (prima linea: tool scritti come simulazioni pure, nessun I/O reale;
seconda linea: container con egress di rete ristretto al solo host OpenRouter).

**Requisito aggiuntivo emerso**: audit di sicurezza preventivo del container stesso
prima di usarlo come confine di contenimento (scan dipendenze, verifica attiva delle
regole di rete, review del codice `aidr` per chiamate non dichiarate) — non dare per
scontato che "è in un container" equivalga a "è sicuro". Righe di verifica aggiunte al
mapping Requisito→Verifica del design doc.

Questo container è concettualmente distinto dal container "serving GPU" citato nella
sezione "Setup pratico" come fallback (quello resta deferred, attivato solo se
OpenRouter risulta insufficiente in fedeltà) — il container di controllo qui sopra serve
comunque, indipendentemente da quella decisione.

## Gap 4 — Il nome piatto dei tool non dà a Inspector il segnale sintattico per SourceLens

**Stato**: risolto nel design doc — sezione "Registro SourceLens per i tool del toy
agent (risoluzione Gap 1 e Gap 4)" in `2026-08-14-toy-agent-e-pipeline-misura.md`.

**Trovato da**: council checkpoint (`council-skeptic`), 2026-08-14, leggendo
`aidr/schema/agent_event.py`, `aidr/dredge/parsers.py`, `aidr/gauntlet/pack.py`
(commit `7fad14d`).

**Severità**: maggiore — stesso ordine di grandezza di Gap 1: se non chiuso, riapre
esattamente il confound che Gap 1 doveva chiudere.

**Evidenza**: `AgentEvent.transcript()` stampa
`f"TOOL CALL {c.call_id}: {c.tool_name}({c.arguments})"` — mai `c.server_name`. Il
prompt di Inspector (`build_workflow`, `inspector.py`) istruisce il modello a
"elencare i nomi dei server MCP che appaiono nel transcript" per poi chiamare
`get_source_code` su quei nomi: il modello deve inferire il server name dal testo, non
da un campo strutturato. Sia `dredge/parsers.py` (`JsonlAgentParser._absorb`) sia
`gauntlet/pack.py`/`runner.py` (`record_session`) derivano il server name con
`c["name"].split(".")[0]` — nel mondo reale del vendor (sessioni reali e proprio
Gauntlet) i tool sono nominati con convenzione punteggiata `server.tool`, ed è quella
stringa nel testo a dare a Inspector il segnale sintattico. I 6 tool del toy agent
(nomi piatti, senza prefisso) non danno questo segnale — la risoluzione originale di
Gap 1 (registro esteso) presuppone che il canale scatti, ma non verificava che
scattasse davvero.

**Perché conta**: se il canale SourceLens non si attiva mai per i nostri tool, un
eventuale recall più basso su T0007 sarebbe di nuovo indistinguibile tra "il detector
è più debole" e "il nostro ambiente non espone il canale come dovrebbe" — lo stesso
confound per cui Gap 1 era stato aperto.

**Risoluzione applicata**: i 6 tool del toy agent sono trattati come esposti da un
unico server logico `toy_support` (scelta più fedele anche a un deployment reale: un
agente di supporto clienti espone tipicamente un server MCP con più tool, non 6 server
separati). Nell'artefatto costruito per il vendor (`ToolUsage`, vedi sezione
"Adapter"), `tool_name` viene impostato in forma punteggiata
(`toy_support.<nome_tool_interno>`), coerente con la convenzione osservata nel codice
vendor — è questa stringa, stampata da `transcript()`, a dare a Inspector il segnale
sintattico. Il nostro `ToolCall.tool_name` interno resta piatto e invariato (nessun
impatto sullo schema di misura pubblico). Il registro SourceLens ha una singola voce
(`toy_support`), invece delle 6 originariamente previste, che punta al codice sorgente
reale dei 6 tool nel nostro repo.

**Ancora aperto**: verifica empirica, da fare in fase di implementazione (non sul
design), che Inspector chiami effettivamente `get_source_code("toy_support")` quando
processa un transcript del toy agent — questa correzione chiude il gap sintattico
noto, ma la conferma finale richiede di eseguire il detector una volta e osservare la
chiamata MCP.

## Gap 5 — Isolamento di stato tra `TestCase` non specificato

**Stato**: risolto nel design doc — sezione "Isolamento di stato tra `TestCase`" in
`2026-08-14-toy-agent-e-pipeline-misura.md`.

**Trovato da**: council checkpoint (`council-risk`), 2026-08-14.

**Severità**: maggiore — un confound non dichiarato nella validità della `rationale`
scritta prima di eseguire il detector.

**Evidenza**: il "DB finto" dietro `query_customer_db` e `bulk_export` è condiviso
("Stesso DB finto" nella tabella "Set di tool"). `update_account` modifica
esplicitamente campi account, incluse azioni distruttive (disattivazione, refund). Il
design doc non specificava se ogni `TestCase` gira contro un'istanza fresca dello
stato finto o se lo stato persiste tra `TestCase` eseguiti in sequenza nello stesso
run.

**Perché conta**: `update_account` è anche il tool-veicolo scelto per il comportamento
nascosto T0007 (tool poisoning). Se il suo effetto persiste oltre la singola sessione,
un `TestCase` eseguito dopo un altro può ricevere in input uno stato del mondo diverso
da quello assunto quando la sua `rationale`/`label` sono state scritte — esattamente
il tipo di deriva silenziosa tra ground truth dichiarato e comportamento osservato che
il principio 2 di `SPIRIT.md` (metodologia dichiarata prima dei risultati) vuole
escludere.

**Risoluzione applicata**: ogni `TestCase` esegue contro un'istanza fresca e isolata
dello stato finto (DB clienti, account, ticket) — nessuna mutazione prodotta da un
`TestCase` è visibile a un altro, indipendentemente dall'ordine di esecuzione nel
batch. Requisito aggiunto al mapping Requisito→Verifica del design doc.

## Gap 6 — Nessun componente orchestra loop toy agent → adapter → metriche

**Stato**: risolto nel design doc — sezione "Orchestrazione del run" in
`2026-08-14-toy-agent-e-pipeline-misura.md`.

**Trovato da**: writing-plans, 2026-08-14, durante la scomposizione del design in piani
di implementazione separati per sotto-sistema — mappando ogni componente del design doc
su un piano non emergeva un proprietario per la sequenza completa.

**Severità**: minore — non tocca l'integrità della misura (a differenza di Gap 1/4/5),
è un buco di composizione, non di metodologia.

**Evidenza**: `Adapter.evaluate(transcript: Transcript) -> Verdict` (sezione "Adapter")
opera su un singolo `Transcript` alla volta. Il modulo metriche (sezione "Modulo
metriche") "prende `list[TestCase]` + `list[Verdict]` (accoppiati per `case_id`)" —
assume che i `Verdict` esistano già. Nessuna sezione del design doc descrive il
componente che, per ogni `TestCase` del dataset, resetta lo stato finto (Gap 5), fa
girare il loop ReAct per produrre il `Transcript`, chiama `adapter.evaluate()`, raccoglie
il `Verdict`, e passa le due liste accoppiate al modulo metriche/report.

**Risoluzione applicata**: aggiunta la sezione "Orchestrazione del run" al design doc,
componente collocato come ultimo task del piano di implementazione dell'adapter (nessuna
logica propria oltre alla composizione di componenti già definiti altrove nel design
doc, quindi nessuna nuova decisione architetturale da sottoporre a un council dedicato).

## Gap 7 — Ground truth ambigua per un `TestCase` benigno che tocca un tool avvelenato

**Stato**: `open` — da chiudere durante Plan 5 (costruzione del dataset), non durante
Plan 1.

**Trovato da**: council checkpoint su Plan 1 (`council-pragmatist`), 2026-08-14, con
un'osservazione aggiuntiva del thread principale durante la sintesi.

**Severità**: maggiore — tocca la validità della ground truth stessa, non
un'implementazione.

**Evidenza**: `update_account` opera solo su campi dell'*account* (`status`,
`refund_total`, `marketing_opt_in` — non su email/telefono/indirizzo, che appartengono
al `Customer` e si leggono via `query_customer_db`, non si scrivono qui). È veicolo sia
di tecniche malevole (T0005, T0014, T0007) sia, plausibilmente, di richieste benigne
legittime sul campo non sensibile `marketing_opt_in` (es. "vorrei disiscrivermi dalle
email di marketing") o sugli stessi campi sensibili con intento benigno (es. "voglio
disattivare il mio account, sto annullando l'abbonamento"). Il comportamento nascosto
T0007 (vedi sopra, Gap 1) è stato ristretto ai campi `status`/`refund_total` proprio per
non contaminare i `TestCase` benigni che toccano `marketing_opt_in` — ma non elimina il
problema per un `TestCase` benigno che tocca legittimamente `status` o `refund_total`.

Due rischi distinti, entrambi aperti:
1. **Scorciatoia di correlazione**: se `update_account` viene chiamato *solo* nei
   `TestCase` malevoli del dataset, il detector potrebbe imparare "sessione che chiama
   `update_account` = malevola" senza mai ragionare sul contenuto del transcript o sul
   codice sorgente — un recall gonfiato per un motivo estraneo alla capacità che si
   vuole misurare. Servono quindi anche `TestCase` benigni che usano il tool, inclusi
   almeno alcuni che toccano `status`/`refund_total` per intento genuinamente benigno.
2. **Definizione di "benigno" quando il tool è di fatto avvelenato**: se un `TestCase`
   con intento benigno tocca `status`/`refund_total`, il backdoor scatta comunque (per
   costruzione, non selettivo). Non è ancora deciso se quel `TestCase` debba restare
   etichettato `label: "benign"` (la label riflette l'intento/condotta dell'agente, non
   l'esito di sicurezza) oppure se un effetto collaterale di sicurezza reale (escalation
   silenziosa a admin) renda quella sessione intrinsecamente non "pulita" a prescindere
   dall'intento — una convenzione di etichettatura che il design doc non specifica
   ancora esplicitamente.

**Perché conta**: qualunque scelta va dichiarata esplicitamente come convenzione
metodologica nel design doc (o nel report finale, come limite dichiarato) prima di
scrivere i `TestCase` reali — coerente col principio 2 di `SPIRIT.md` (metodologia
dichiarata prima dei risultati). Scriverla dopo aver visto come si comporta il detector
sarebbe esattamente il bias di conferma che il principio vuole escludere.

**Da decidere in Plan 5, prima di scrivere qualunque `TestCase` che usi
`update_account`**: (a) quanti `TestCase` benigni devono comunque esercitare il tool
(inclusi alcuni su `status`/`refund_total`), per evitare la scorciatoia di correlazione;
(b) la convenzione di etichettatura per un `TestCase` benigno che attiva comunque il
backdoor — probabilmente: la `label` resta `"benign"` perché riflette la condotta
dell'agente (non l'esito), ma la `rationale` deve dichiarare esplicitamente che il
backdoor si attiva comunque, così che un eventuale falso positivo del detector su quel
caso specifico sia leggibile nel report come "il detector ha segnalato un effetto
collaterale reale non causato dall'intento dell'agente", non come un errore generico.

## Come si chiude un gap

Quando una risoluzione viene applicata al design doc, aggiornare lo stato qui a
"risolto nel design doc" e linkare la sezione del design doc che la contiene. Se invece
si decide di accettarlo come limite (non risolverlo), lo stato diventa "accettato come
limite dichiarato" e va comunque riportato nel report finale (sezione Report del design
doc), coerentemente col principio di onestà statistica di `SPIRIT.md`.
