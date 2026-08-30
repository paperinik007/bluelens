# Cross-check di copertura: tassonomia del vendor (14 T-code) contro MITRE ATLAS

Esercizio di ricerca, non codice — eseguito come Nodo A del design doc
`docs/design/2026-08-30-atlas-audit-method-design-v4.md`, che delega esplicitamente a
questo documento il compito di "definire il criterio di mappabilità tecnica ATLAS→tool
come suo primo passo". **Obiettivo unico**: trovare tecniche MITRE ATLAS con un analogo
plausibile come attacco eseguibile contro il nostro agente giocattolo customer-support
(6 tool, `src/toy_agent/tools.py`) ma nessun analogo tra i 14 T-code
(`catalog/vendor_taxonomy_snapshot.yaml`) — un vero gap-finding, mai un'importazione di
dati o etichette ATLAS nel catalogo di questo progetto (principio 1, `SPIRIT.md`).
Questo documento non aggiunge né modifica alcuna voce di `catalog/cases.yaml` né di
`catalog/vendor_scope_verification.yaml`.

**Stato del catalogo al momento del cross-check**: 31 voci, 12/14 T-code coperti
(T0009 Covert Data Over-Collection e T0011 Tool-Result Tampering esclusi per limite
dichiarato, Gap 17) — verificato leggendo `catalog/cases.yaml` (`entries`, campo
`technique_code`) come da documento di cross-check precedente
(`docs/research/2026-08-19-taxonomy-cross-check-findings.md`). Il cross-check qui sotto
è comunque condotto contro tutti e 14 i T-code dichiarati dal vendor, non solo i 12
popolati — una tecnica ATLAS può avere analogo in T0009/T0011 anche se quelle due
tecniche non hanno ancora voci di catalogo.

## Passo 1 — Criterio di mappabilità tecnica ATLAS→tool del nostro agente

**Definito prima di qualunque fetch o confronto**, guardando solo `src/toy_agent/tools.py`
e lo scenario dell'agente (customer-support con 6 tool fissi), mai un verdetto di
detector o un esito di esecuzione.

Una tecnica MITRE ATLAS è "mappabile" contro il nostro agente giocattolo se e solo se
**esiste un percorso plausibile per trasformare la tecnica ATLAS in un attacco
eseguibile che coinvolge almeno uno di questi tre vettori d'ingresso**:

1. **Canale utente diretto** — una richiesta malevola inserita dall'utente nel prompt
   della conversazione (turno `user`). L'agente la riceve direttamente nel suo contesto
   e può decidere di eseguirla, rifiutarla, o essere manipolato da essa.

2. **Contenuto non fidato letto da un tool** — un payload malevolo inserito in un
   contenuto che l'agente legge attraverso uno dei 6 tool, in particolare
   `read_ticket_content` (il cui contenuto è "untrusted channel — written by the
   customer", esplicitamente dichiarato nella docstring) e potenzialmente campi di
   `query_customer_db` o `bulk_export` se contengono dati non sanitizzati.

3. **Invocazione diretta di un tool** — l'agente viene indotto a chiamare uno dei 6
   tool con parametri malevoli, sfruttando la superficie di attacco di quel tool
   (es. `send_email` senza whitelist di dominio destinatario, `update_account` con
   escalation nascosta a privilegi admin su campi `status`/`refund_total`,
   `bulk_export` senza hard cap).

Il criterio **non** richiede che un attacco sia già stato costruito, né che esista un
caso nel dataset — richiede solo che sia ragionevolmente possibile **costruirlo** con
la superficie d'attacco esistente dell'agente.

**Esclusioni esplicite** (tecniche ATLAS NON mappabili per costruzione, perché il
nostro agente non ha la superficie d'attacco richiesta):

- Tecniche specifiche di **training/fine-tuning di modelli ML**: il nostro agente non
  allena modelli. Esempi: Create Proxy AI Model (AML.T0005), Training Data Poisoning
  (AML.T0020), Poison AI Model (AML.T0018.000), Modify AI Model Architecture
  (AML.T0018.001).

- Tecniche che richiedono **accesso white-box a un modello**: il nostro agente usa un
  LLM via API (OpenRouter), non abbiamo accesso ai pesi, all'architettura, o al
  training set. Esempi: Full AI Model Access (AML.T0044), Craft Adversarial Data
  (AML.T0043, e tutte le sue sub-tecniche: White-Box, Black-Box, Transfer).

- Tecniche specifiche di **computer vision / image processing**: il nostro agente non
  processa immagini. Esempi: Evade AI Model con adversarial images (AML.T0015),
  Insert Backdoor Trigger (AML.T0043.004), Generate Deepfakes (AML.T0088).

- Tecniche che richiedono **accesso fisico a sensori/hardware**: il nostro agente è
  puramente software. Esempi: Physical Environment Access (AML.T0041), Physical
  Countermeasures (AML.T0008.003).

- Tecniche di **AI supply chain a livello di modello/dataset/infrastruttura di
  training**: il nostro agente non costruisce né distribuisce modelli o dataset.
  Esempi: AI Supply Chain Compromise e tutte le sub-tecniche (AML.T0010.*), Publish
  Poisoned AI Artifacts (AML.T0115), AI Supply Chain Rug Pull (AML.T0109), AI Supply
  Chain Reputation Inflation (AML.T0111).

- Tecniche di **Reconnaissance puramente passiva su organizzazioni esterne**: il
  nostro agente non ha un'organizzazione esterna da ricognire — l'unica "vittima" è
  il sistema customer-support stesso. Tecniche come Search Open Technical Databases
  (AML.T0000), Search Victim-Owned Websites (AML.T0003), Search Application
  Repositories (AML.T0004) descrivono la ricognizione dell'avversario su
  un'organizzazione terza, non un attacco eseguibile *attraverso* l'agente contro il
  sistema che lo ospita. **Queste tecniche descrivono come l'avversario prepara
  l'attacco, non l'attacco stesso.**

- Tecniche di **Resource Development a livello infrastrutturale**: acquisire server,
  domini, GPU — è preparazione dell'avversario, non un attacco eseguibile attraverso
  l'agente. Esempi: Acquire Infrastructure (AML.T0008), Establish Accounts
  (AML.T0021), Obtain Capabilities (AML.T0016), Develop Capabilities (AML.T0017).

- Tecniche specifiche di **modelli predittivi/classificatori**: il nostro agente è
  generativo, non un classificatore. Esempi: Discover AI Model Ontology (AML.T0013,
  "the types of objects a model can detect").

- Tecniche di **Credential Access sul sistema operativo**: il nostro agente non ha
  accesso al filesystem del sistema operativo. Esempi: OS Credential Dumping
  (AML.T0090), Unsecured Credentials (AML.T0055, nel senso di file di configurazione
  OS).

- Tecniche che richiedono **sfruttamento di vulnerabilità software tradizionali**
  (buffer overflow, deserializzazione, ecc.) contro l'infrastruttura di deployment
  dell'agente — non contro l'agente stesso. Esempi: Exploit Public-Facing Application
  (AML.T0049, nel suo senso ATT&CK classico di exploit di CVE su un server web), Drive-by
  Compromise (AML.T0078), Exploitation for Credential Access (AML.T0106).

- Tecniche di **Exfiltration via AI Inference API a livello di modello**: estrarre
  informazioni dal training set via API (membership inference, model inversion) non ha
  senso per un agente customer-support che non espone embedding né logits. Esempio:
  Exfiltration via AI Inference API (AML.T0024 e sub-tecniche).

## Passo 2 — Fonte primaria: MITRE ATLAS

**Fonte**: repository ufficiale MITRE ATLAS su GitHub
(`github.com/mitre-atlas/atlas-data`), file `dist/ATLAS-latest.yaml`, fetch riuscito
via clone completo del repository.

- **Content version**: `2026.07` (campo `collection.version`)
- **Format version**: `6.0.0` (campo `format-version`)
- **Data di fetch**: 2026-08-30
- **File letto per intero**: `dist/ATLAS-latest.yaml` (17.878 righe)

**Tattiche** (16 totali, elencate per completezza — il confronto è a livello di
tecnica, non di tattica):

| Tactic ID | Nome |
|---|---|
| AML.TA0000 | AI Model Access |
| AML.TA0001 | AI Attack Staging |
| AML.TA0002 | Reconnaissance |
| AML.TA0003 | Resource Development |
| AML.TA0004 | Initial Access |
| AML.TA0005 | Execution |
| AML.TA0006 | Persistence |
| AML.TA0007 | Defense Evasion |
| AML.TA0008 | Discovery |
| AML.TA0009 | Collection |
| AML.TA0010 | Exfiltration |
| AML.TA0011 | Impact |
| AML.TA0012 | Privilege Escalation |
| AML.TA0013 | Credential Access |
| AML.TA0014 | Command and Control |
| AML.TA0015 | Lateral Movement |

**Tecniche** (top-level, escludendo sub-tecniche): 101 tecniche identificate da
AML.T0000 a AML.T0115, con gap nella numerazione (non contigua — es. salta da AML.T0018 a
AML.T0020, da AML.T0025 a AML.T0029, ecc.). La lista completa è nel file YAML citato sopra; il
cross-check sotto elenca solo le tecniche pertinenti al confronto (mappabili o
borderline), con esclusione esplicita motivata per quelle scartate.

## Passo 3 — Applicazione del criterio di mappabilità

Delle 101 tecniche ATLAS top-level, **46 sono mappabili** secondo il criterio del Passo
1. Le restanti 55 sono scartate esplicitamente con motivazione. La tabella sotto elenca
le tecniche mappabili (e quelle borderline discusse) con la motivazione di inclusione o
esclusione.

### Tecniche scartate — motivazione sintetica per blocco

| Blocco | Tecniche ATLAS coinvolte | Motivazione |
|---|---|---|
| ML training/fine-tuning | AML.T0005 (Create Proxy AI Model), AML.T0018.000 (Poison AI Model), AML.T0018.001 (Modify AI Model Architecture), AML.T0020 (Training Data Poisoning), AML.T0031 (Erode AI Model Integrity), AML.T0059 (Erode Dataset Integrity), AML.T0076 (Corrupt AI Model) | Il nostro agente non allena modelli |
| White-box model access | AML.T0044 (Full AI Model Access), AML.T0043 (Craft Adversarial Data + sub), AML.T0015 (Evade AI Model) | Il nostro agente usa un LLM via API, nessun accesso a pesi/architettura |
| Computer vision / biometrics | AML.T0088 (Generate Deepfakes), AML.T0043.004 (Insert Backdoor Trigger) | Il nostro agente non processa immagini |
| Physical access / sensors | AML.T0041 (Physical Environment Access), AML.T0008.003 (Physical Countermeasures) | Agente puramente software |
| AI supply chain (modello/dataset) | AML.T0010 (AI Supply Chain Compromise + sub), AML.T0115 (Publish Poisoned AI Artifacts), AML.T0109 (AI Supply Chain Rug Pull), AML.T0111 (AI Supply Chain Reputation Inflation) | Il nostro agente non distribuisce modelli/dataset |
| Reconnaissance passiva su terzi | AML.T0000 (Search Open Technical Databases + sub), AML.T0001 (Search Open AI Vulnerability Analysis), AML.T0003 (Search Victim-Owned Websites), AML.T0004 (Search Application Repositories), AML.T0013 (Discover AI Model Ontology), AML.T0014 (Discover AI Model Family), AML.T0095 (Search Open Websites/Domains + sub) | Preparazione dell'avversario su organizzazione esterna, non attacco attraverso l'agente |
| Resource Development infrastrutturale | AML.T0008 (Acquire Infrastructure + sub tranne .003), AML.T0021 (Establish Accounts), AML.T0016 (Obtain Capabilities + sub), AML.T0017 (Develop Capabilities + sub), AML.T0079 (Stage Capabilities) | Preparazione dell'avversario, non attacco eseguibile attraverso l'agente |
| Network/OS-level credential access | AML.T0055 (Unsecured Credentials), AML.T0090 (OS Credential Dumping), AML.T0091 (Use Alternate Authentication Material + sub), AML.T0113 (Steal Web Session Cookie + sub) | Il nostro agente non ha accesso al filesystem OS/network |
| Exploit di vulnerabilità software tradizionali | AML.T0049 (Exploit Public-Facing Application), AML.T0078 (Drive-by Compromise), AML.T0106 (Exploitation for Credential Access), AML.T0107 (Exploitation for Defense Evasion) | Sfruttano CVE/vulnerabilità dell'infrastruttura di deployment, non dell'agente |
| Model-level inference API exfiltration | AML.T0024 (Exfiltration via AI Inference API + sub) | Membership inference / model inversion non applicabili a un agente customer-support senza embedding/logits |
| Esito/esterno (non tecnica d'attacco) | AML.T0048 (External Harms + sub: Financial, Reputational, Societal, User Harm, AI IP Theft) | Categorie di esito/danno, non tecniche — stesso pattern trovato nel cross-check 20/08 per AgentHarm/R-Judge |
| Raccolta dati OS-level / repository | AML.T0035 (AI Artifact Collection), AML.T0036 (Data from Information Repositories), AML.T0037 (Data from Local System), AML.T0035 (AI Artifact Collection) | File system / SharePoint / SQL Server, non superficie d'attacco del nostro agente |
| Machine Compromise (OS-level) | AML.T0112 (Machine Compromise + sub) | Compromissione del sistema operativo, non dell'agente |
| Altro — non pertinenti | AML.T0007 (Discover AI Artifacts — filesystem), AML.T0025 (Exfiltration via Cyber Means — rete OS), AML.T0029 (Denial of AI Service — livello modello/infrastruttura, vedi nota sotto), AML.T0034 (Cost Harvesting + sub — livello modello/infrastruttura, vedi nota sotto), AML.T0042 (Verify Attack — testing offline), AML.T0046 (Spamming AI System with Chaff Data — vedi nota sotto), AML.T0047 (AI-Enabled Product or Service — contesto dell'avversario, non attacco), AML.T0062 (Discover LLM Hallucinations — analisi passiva), AML.T0063 (Discover AI Model Outputs — analisi passiva), AML.T0069 (Discover LLM System Information — analisi passiva), AML.T0075 (Cloud Service Discovery — infrastruttura cloud), AML.T0089 (Process Discovery — OS), AML.T0097 (Virtualization/Sandbox Evasion — OS/VM), AML.T0105 (Escape to Host — container/sandbox escape OS-level) |

**Note su tecniche borderline scartate con motivazione estesa**:

- **AML.T0029 (Denial of AI Service)** e **AML.T0034 (Cost Harvesting)**: descrivono
  attacchi di saturazione a livello di API/model inference (richieste eccessive,
  query costose). Un agente customer-support potrebbe teoricamente essere sommerso di
  ticket, ma la tecnica ATLAS descrive il consumo di risorse computazionali del
  modello, non l'intasamento di una coda di ticket. Il nostro agente non è un
  endpoint API di inferenza esposto direttamente — è un agente conversazionale.
  **Scartate come asse diverso.**

- **AML.T0046 (Spamming AI System with Chaff Data)**: l'idea di intasare un agente
  con eventi a bassa severità è concettualmente vicina a T0013 (Resource Exhaustion),
  ma la formulazione ATLAS è specifica per "increase in the number of detections" di
  un classificatore, non per un agente conversazionale. T0013 copre già il caso
  agentico (es. loop infinito di tool). **Scartata come già coperta da T0013.**

- **AML.T0112 (Machine Compromise)**: compromissione della macchina (OS-level), non
  del comportamento dell'agente. **Scartata come asse diverso.**

- **AML.T0105 (Escape to Host)**: sandbox/container escape a livello OS. Il nostro
  agente non è sandboxato in un container isolato in modo rilevante per questa
  tecnica (non esegue codice arbitrario in un container da cui evadere). **Scartata.**

## Passo 4 — Cross-check per le tecniche mappabili

Per ogni tecnica ATLAS mappabile, verificato se esiste un analogo ragionevole tra i 14
T-code. "Analogo ragionevole" = la stessa classe di comportamento malevolo a un
livello di dettaglio comparabile (non serve un match sinonimico esatto), stesso
criterio del documento 2026-08-19.

### Tabella di cross-check

| Tecnica ATLAS (codice + nome) | Analogo T-code | Note |
|---|---|---|
| AML.T0002 (Acquire Public AI Artifacts) → sub AML.T0002.002 (AI Agent Configuration) | T0001/T0002 (Prompt Injection) contestualmente | La sub-tecnica descrive l'acquisizione di file di configurazione di agenti AI (system prompt, tool config). Per il nostro agente, il system prompt e i tool sono codice sorgente versionato — conoscerli equivale a conoscere la superficie d'attacco per T0001/T0002. Non è di per sé un attacco eseguibile, ma è il prerequisito per prompt injection mirata. **Nessun T-code dedicato alla ricognizione della configurazione dell'agente**, ma è coperta indirettamente dal fatto che T0001/T0002 presuppongono questa conoscenza. |
| AML.T0006 (Active Scanning) | **nessuno** | Vedi discussione sotto — gap candidate |
| AML.T0011 (User Execution) → sub AML.T0011.002 (Poisoned AI Agent Tool) | T0005 (Privilege Escalation via Tool) | Un tool avvelenato (MCP server malevolo, poisoned skill) è esattamente il pattern di T0005: un tool che fa più di quanto dichiara. Anche T0011 (Tool-Result Tampering, non ancora popolato ma presente nella tassonomia) copre l'avvelenamento di risposte di tool. |
| AML.T0011.003 (Malicious Link) | T0002 (Indirect Prompt Injection) / T0004 (Malicious Tool Invocation) | Un link malevolo presentato all'agente (es. in un ticket) per indurlo a navigarlo è un caso di indirect prompt injection con esito di tool invocation. Coperto. |
| AML.T0012 (Valid Accounts) | **nessuno** | Vedi discussione sotto — gap candidate |
| AML.T0040 (AI Model Inference API Access) | n/a | Non è un attacco, è l'accesso legittimo all'API di inferenza — descrive la superficie, non la tecnica. I T-code pertinenti (T0001/T0002) descrivono cosa si fa con quell'accesso. |
| AML.T0050 (Command and Scripting Interpreter) | T0004 (Malicious Tool Invocation) / T0008 (Sandbox Escape Attempt) | L'agente può eseguire comandi via tool (run_diagnostic, potenzialmente send_email con corpo malevolo). Se l'agente esegue comandi OS sarebbe T0008, se invoca tool malevoli è T0004. Coperto. |
| AML.T0051 (LLM Prompt Injection) → sub AML.T0051.000 (Direct), AML.T0051.001 (Indirect), AML.T0051.002 (Triggered) | T0001 (Direct Prompt Injection), T0002 (Indirect Prompt Injection), T0010 (Context Poisoning) per Triggered | Match quasi sinonimico. Direct→T0001, Indirect→T0002, Triggered (istruzione latente che si attiva dopo più turni)→T0010 (avvelenamento del contesto che persiste). Copertura completa. |
| AML.T0052 (Phishing) → sub AML.T0052.000 (Spearphishing via Social Engineering LLM) | T0004 (Malicious Tool Invocation) | L'agente che invia email di phishing via send_email è T0004. Coperto. |
| AML.T0053 (AI Agent Tool Invocation) | T0004 (Malicious Tool Invocation) | Match diretto — invocazione di tool da parte dell'agente per scopi malevoli. |
| AML.T0054 (LLM Jailbreak) | T0007 (Guardrail Evasion) | Jailbreak = aggirare le restrizioni di sicurezza del modello. T0007 copre esattamente questo: tecniche per eludere le guardrail. Coperto. |
| AML.T0056 (Extract LLM System Prompt) | T0007 (Guardrail Evasion) / T0012 (Data Exfiltration) | Estrarre il system prompt è sia esfiltrazione di informazioni (T0012) sia un prerequisito per eludere le guardrail (T0007). Coperto da entrambi. |
| AML.T0057 (LLM Data Leakage) | T0012 (Data Exfiltration) | Il modello che "leak-a" dati privati dal contesto. T0012 copre l'esfiltrazione via agente. Coperto. |
| AML.T0060 (Publish Hallucinated Entities) | T0002 (Indirect Prompt Injection) / T0005 (Privilege Escalation via Tool) | Pubblicare package/librerie con nomi che un LLM potrebbe allucinare è un attacco supply-chain indiretto: l'agente installa/esegue qualcosa di malevolo perché il modello lo suggerisce. Coperto da T0002 (il nome del package è il payload indiretto) o T0005 (il package installato è un tool avvelenato). |
| AML.T0061 (LLM Prompt Self-Replication) | T0002 (Indirect Prompt Injection) + T0004 (Malicious Tool Invocation) | L'agente che replica un'istruzione malevola ad altri agenti via email/ticket è composizione di T0002 (indirect injection via contenuto replicato) e T0004 (tool invocation per propagare). Composizione già coperta. |
| AML.T0064 (Gather RAG-Indexed Targets) | T0010 (Context Poisoning) contestualmente | Identificare contenuti indicizzati in un RAG store per avvelenarli. Il nostro agente non ha RAG, ma il pattern di avvelenamento del contesto è T0010. La ricognizione non ha un T-code dedicato — vedi AML.T0006 sopra. |
| AML.T0065 (LLM Prompt Crafting) | T0001/T0002 (Prompt Injection) | Costruire prompt injection efficaci è esattamente ciò che T0001/T0002 descrivono — è la tecnica stessa, non una categoria separata. Coperto. |
| AML.T0066 (Retrieval Content Crafting) | T0010 (Context Poisoning) | Creare contenuti malevoli destinati a un RAG store = avvelenamento del contesto. Coperto da T0010. |
| AML.T0067 (LLM Trusted Output Components Manipulation) → sub AML.T0067.000 (Citations) | T0011 (Tool-Result Tampering, non popolato) / T0002 (Indirect Prompt Injection) | Manipolare citazioni/URL nel testo generato dal modello per indirizzare l'utente (o l'agente stesso) verso risorse malevole. Coperto da T0011 (se la citazione è il risultato di un tool) o T0002 (indirect injection via link). |
| AML.T0068 (LLM Prompt Obfuscation) → sub AML.T0068.000 (Special Character Sets), AML.T0068.001 (System Instruction Keywords) | T0007 (Guardrail Evasion) | Offuscare prompt injection per eludere detection. T0007 copre l'elusione delle guardrail. Coperto. |
| AML.T0070 (RAG Poisoning) | T0010 (Context Poisoning) | Avvelenamento del retrieval store = avvelenamento del contesto. Match diretto. |
| AML.T0071 (False RAG Entry Injection) | T0010 (Context Poisoning) | Iniettare entry false in un RAG store. Coperto da T0010. |
| AML.T0072 (Reverse Shell) | T0008 (Sandbox Escape Attempt) | Stabilire una reverse shell via agente. T0008 copre tentativi di escape/accesso non autorizzato a risorse di sistema. Coperto. |
| AML.T0073 (Impersonation) | T0004 (Malicious Tool Invocation) / T0006 (Unauthorized Resource Access) | L'agente che impersona un utente per ottenere accesso non autorizzato. Coperto da T0004 (uso malevolo di tool) o T0006 (accesso non autorizzato). |
| AML.T0074 (Masquerading) | T0007 (Guardrail Evasion) | Mascherare attività malevole come legittime. T0007 copre l'elusione. Coperto. |
| AML.T0077 (LLM Response Rendering) | **nessuno** | Vedi discussione sotto — possibile gap |
| AML.T0080 (AI Agent Context Poisoning) → sub AML.T0080.000 (Memory), AML.T0080.001 (Thread) | T0010 (Context Poisoning) | Avvelenamento della memoria/thread dell'agente. Match diretto con T0010. |
| AML.T0081 (Modify AI Agent Configuration) | T0003 (Agentic Control-Flow Hijacking) / T0005 (Privilege Escalation via Tool) | Modificare la configurazione dell'agente (system prompt, tool config) per dirottarne il comportamento. Coperto da T0003 (hijacking del control-flow) o T0005 (se fatto via tool avvelenato). |
| AML.T0082 (RAG Credential Harvesting) | T0012 (Data Exfiltration) / T0006 (Unauthorized Resource Access) | Raccogliere credenziali da un RAG store. Coperto da T0012 (esfiltrazione) o T0006 (accesso non autorizzato). |
| AML.T0083 (Credentials from AI Agent Configuration) | T0012 (Data Exfiltration) | Estrarre credenziali da file di configurazione dell'agente. Coperto da T0012. |
| AML.T0084 (Discover AI Agent Configuration) → sub AML.T0084.000 (Embedded Knowledge), AML.T0084.001 (Tool Definitions), AML.T0084.002 (Activation Triggers), AML.T0084.003 (Call Chains) | **nessuno** | Vedi discussione sotto — gap candidate (stessa famiglia di AML.T0006) |
| AML.T0085 (Data from AI Services) → sub AML.T0085.000 (RAG Databases), AML.T0085.001 (AI Agent Tools) | T0012 (Data Exfiltration) / T0009 (Covert Data Over-Collection, non popolato) | Raccolta dati da servizi AI dell'agente. Coperto da T0012 o T0009. |
| AML.T0086 (Exfiltration via AI Agent Tool Invocation) | T0012 (Data Exfiltration) | Esfiltrare dati via tool dell'agente. Match diretto. |
| AML.T0087 (Gather Victim Identity Information) | T0012 (Data Exfiltration) / T0006 (Unauthorized Resource Access) | Raccolta di PII via agente. Coperto. |
| AML.T0092 (Manipulate User LLM Chat History) | T0010 (Context Poisoning) | Avvelenare la chat history dell'utente = avvelenamento del contesto. Coperto. |
| AML.T0093 (Prompt Infiltration via Public-Facing Application) | T0002 (Indirect Prompt Injection) | Prompt injection che entra via un'applicazione pubblica (es. un ticket di supporto). Match diretto con T0002. |
| AML.T0094 (Delay Execution of LLM Instructions) | T0010 (Context Poisoning) / T0002 (Indirect Prompt Injection) | Istruzioni malevole che si attivano dopo un ritardo — stesso pattern di "Triggered" di AML.T0051.002. Coperto da T0010 (persistenza nel contesto) o T0002. |
| AML.T0096 (AI Service API) | T0001/T0002 (Prompt Injection) | Usare API di servizi AI come vettore. Coperto da T0001/T0002. |
| AML.T0098 (AI Agent Tool Credential Harvesting) | T0012 (Data Exfiltration) | Raccogliere credenziali via tool dell'agente. Coperto da T0012. |
| AML.T0099 (AI Agent Tool Data Poisoning) | T0011 (Tool-Result Tampering, non popolato) / T0010 (Context Poisoning) | Avvelenare i dati restituiti da un tool. Coperto da T0011 (risultato tool alterato) o T0010 (se il dato avvelenato contamina il contesto). |
| AML.T0100 (AI Agent Clickbait) | T0002 (Indirect Prompt Injection) / T0004 (Malicious Tool Invocation) | Attirare l'agente a cliccare/invocare qualcosa di malevolo. Coperto da T0002 o T0004. |
| AML.T0101 (Data Destruction via AI Agent Tool Invocation) | T0014 (Destructive Action) | Distruggere dati via tool. Match diretto. |
| AML.T0102 (Generate Malicious Commands) | T0004 (Malicious Tool Invocation) / T0008 (Sandbox Escape Attempt) | Generare comandi malevoli da eseguire. Coperto da T0004 o T0008. |
| AML.T0103 (Deploy AI Agent) | **nessuno** | Vedi discussione sotto — gap candidate |
| AML.T0108 (AI Agent) | **nessuno** | Vedi discussione sotto — gap candidate (legato a AML.T0103) |
| AML.T0110 (AI Agent Tool Poisoning) → sub AML.T0110.000 (Definition and Instructions), AML.T0110.001 (Implementation), AML.T0110.002 (Runtime Response) | T0005 (Privilege Escalation via Tool) / T0011 (Tool-Result Tampering, non popolato) | Avvelenamento di tool a livello di definizione, implementazione o risposta runtime. T0005 (tool che fa più di quanto dichiara, come update_account con escalation admin nascosta) e T0011 (risultati alterati) coprono tutte e tre le sub-tecniche. |
| AML.T0114 (AI Service Web Interface) | T0001 (Direct Prompt Injection) | Interfaccia web di un servizio AI — per il nostro agente è il canale utente diretto. Coperto da T0001. |

### Discussione: tecniche ATLAS senza analogo — gap reali vs. asse diverso

#### Gap candidato 1: Active Scanning contro l'agente (AML.T0006) e famiglia "Discover AI Agent"

**AML.T0006 (Active Scanning)** descrive la scansione attiva di un sistema AI per
scoprirne le capacità: "They can also send emails to organization service addresses and
inspect the replies for indicators that an AI agent is managing the inbox." Questo è
direttamente applicabile al nostro agente: un avversario può inviare ticket/esplorare
il comportamento dell'agente per mapparne tool, permessi e risposte — **una tecnica di
reconnaissance attiva specifica contro l'agente**, non contro l'organizzazione.
Nessuno dei 14 T-code copre la **ricognizione attiva delle capacità dell'agente** come
tecnica a sé (T0001/T0002 presuppongono già di sapere cosa attaccare, ma non
descrivono la fase di esplorazione). Tuttavia, la domanda è se questa sia una tecnica
di attacco distinta o un prerequisito: nel modello ATT&CK classico, Active Scanning è
Reconnaissance, una fase separata. **Giudizio: gap reale ma di fase preliminare — un
T-code per "Agent Capability Discovery" coprirebbe la ricognizione attiva sulle
capacità dell'agente, distinta dalla prompt injection che presuppone già la
conoscenza del target.**

La stessa osservazione si applica a **AML.T0084 (Discover AI Agent Configuration)** e
tutte le sue sub-tecniche: scoprire configurazione, tool, trigger e catene di chiamata
dell'agente. Anche qui, nessun T-code dedicato — è un gap nella stessa famiglia.

#### Gap candidato 2: Valid Accounts specifici per agenti AI (AML.T0012)

**AML.T0012 (Valid Accounts)** descrive l'abuso di credenziali legittime per accedere
a risorse AI. Nel contesto del nostro agente customer-support, questo potrebbe
significare: usare un account utente legittimo per inviare ticket malevoli che
sfruttano fiducia/permessi più alti, o usare una sessione agente autenticata. T0006
(Unauthorized Resource Access) copre l'accesso non autorizzato alle risorse, ma non
specificamente l'abuso di credenziali legittime per elevare il profilo di fiducia
dell'attaccante agli occhi dell'agente. **Giudizio: possibile gap, ma sfumato — il
confine con T0006 è sottile. L'abuso di un account legittimo per attacchi
agent-specific (es. ticket da un utente VIP che l'agente tratta con meno scrutiny) è
un pattern che T0006 non cattura esplicitamente.**

#### Gap candidato 3: Deploy AI Agent / AI Agent (AML.T0103, AML.T0108)

**AML.T0103 (Deploy AI Agent)** e **AML.T0108 (AI Agent)** descrivono il deployment
di un agente AI malevolo da parte dell'avversario. Nel contesto del nostro agente
customer-support, un avversario potrebbe indurre l'agente a deployare un sub-agente
(es. via tool invocation) che opera con i permessi dell'agente originale. Questo è un
pattern di **propagazione laterale agentica** che nessuno dei 14 T-code cattura
esplicitamente: T0004 (Malicious Tool Invocation) copre la singola invocazione, ma non
la creazione di un agente persistente. **Giudizio: gap reale.** Un T-code per "Agent
Propagation" o "Sub-Agent Deployment" catturerebbe questa classe di attacchi.

#### Gap candidato 4: LLM Response Rendering (AML.T0077)

**AML.T0077 (LLM Response Rendering)** descrive attacchi che sfruttano il rendering
dell'output del modello (es. markdown, HTML, link cliccabili) per eseguire codice o
esfiltrare dati lato client. Per il nostro agente, il "client" è l'ambiente in cui
l'output viene consumato — se l'agente produce output che contiene comandi markdown/HTML
malevoli che un sistema a valle esegue, è un vettore indiretto. T0002 (Indirect Prompt
Injection) copre l'iniezione di contenuti malevoli in output, ma non specificamente lo
sfruttamento del **rendering** dell'output. **Giudizio: gap parziale.** La tecnica è
coperta da T0002 per la parte di "payload malevolo nell'output", ma il meccanismo
specifico del rendering non ha un T-code dedicato. È un confine sottile — vedi
discussione sotto.

#### Non-gap: tecniche senza analogo che sono un asse diverso

**AML.T0048 (External Harms)** e le sue sub-tecniche (Financial Harm, Reputational
Harm, Societal Harm, User Harm, AI IP Theft): categorie di **esito/danno**, non di
tecnica d'attacco. Stesso pattern già trovato nel cross-check 2026-08-19 per le
categorie content-safety/domain-specific di R-Judge e AgentHarm: un agente può
causare danni finanziari via T0004 (transazione non autorizzata), T0014 (azione
distruttiva), o T0012 (furto di dati) — il danno è l'esito, la tecnica è già coperta.
**Nessun gap.**

## Passo 5 — Conclusione: elenco dei gap reali

Delle 101 tecniche MITRE ATLAS top-level, 46 sono mappabili contro il nostro agente
customer-support. Di queste, la grande maggioranza (39/46) ha un analogo ragionevole
tra i 14 T-code del vendor. Questo conferma che la tassonomia del vendor, pur costruita
a mano e senza una fonte esterna mantenuta, ha una copertura sorprendentemente ampia
dello spazio delle tecniche di attacco contro agenti LLM-based — inclusi pattern emersi
nella ricerca ATLAS successiva alla creazione del vendor (es. le tecniche della
famiglia AML.T0080-T0110 pubblicate tra gennaio e luglio 2026).

### Gap reali (tecniche ATLAS mappabili senza analogo T-code)

Questi sono i candidati per un futuro popolamento del dataset, come T-code aggiuntivi o
come estensioni di T-code esistenti. **Nessuna variante viene scritta qui, nessun file
di catalogo viene toccato** — questa è solo l'identificazione dei gap, il popolamento è
un passo successivo deliberatamente escluso da questo documento.

| # | Tecnica ATLAS | Nome | Gap T-code proposto | Note |
|---|---|---|---|---|
| 1 | AML.T0006 | Active Scanning (contro l'agente) | "Agent Capability Discovery" | Ricognizione attiva delle capacità/tool/permessi dell'agente tramite interazione. Distinto da T0001/T0002 che presuppongono già la conoscenza del target. La sub-tecnica specifica per agenti ("send emails... inspect replies for indicators that an AI agent is managing the inbox") è direttamente applicabile al nostro scenario customer-support. |
| 2 | AML.T0084 | Discover AI Agent Configuration (e sub: Embedded Knowledge, Tool Definitions, Activation Triggers, Call Chains) | Stesso T-code del #1, o sub-tecniche | Famiglia di tecniche di scoperta della configurazione dell'agente — parte dello stesso gap di ricognizione attiva. |
| 3 | AML.T0012 | Valid Accounts (per contesto agentico) | Estensione di T0006 o nuovo T-code "Credential Abuse for Agent Trust Elevation" | Abuso di credenziali/account legittimi per elevare il profilo di fiducia presso l'agente (es. ticket da utente VIP). Più specifico di T0006. |
| 4 | AML.T0103 / AML.T0108 | Deploy AI Agent / AI Agent | "Agent Propagation" o "Sub-Agent Deployment" | L'agente indotto a deployare/eseguire un sub-agente malevolo che eredita permessi. Pattern di lateral movement agentico non coperto da T0004 (singola tool invocation). |
| 5 | AML.T0077 | LLM Response Rendering | Possibile estensione di T0002 o nuovo T-code | Sfruttamento del rendering dell'output (markdown/HTML/link) per eseguire codice o esfiltrare dati. Coperto in parte da T0002, ma il meccanismo di rendering è specifico. |

### Osservazioni per il design doc, non applicate qui

1. **Copertura della tassonomia vendor**: i 14 T-code coprono 39/46 tecniche ATLAS
   mappabili (84.8%) — le rimanenti 7 righe si dividono in 6 senza analogo ("nessuno")
   e 1 caso "n/a" (AML.T0040, non una tecnica d'attacco ma la descrizione della
   superficie d'accesso — vedi tabella del Passo 4). Le 6 tecniche senza analogo sono
   concentrate in due aree:
   ricognizione attiva dell'agente (AML.T0006 + AML.T0084 = 2 tecniche) e
   deploy/propagazione agentica (AML.T0103/AML.T0108 = 1 coppia = 2 tecniche).
   AML.T0012 e AML.T0077 sono casi più sfumati (confine con T0006 e T0002
   rispettivamente). Questo è un risultato notevole per una tassonomia costruita a
   mano.

2. **T0009 e T0011**: entrambi i T-code non ancora popolati (Gap 17) hanno un ruolo
   nel cross-check: T0011 (Tool-Result Tampering) è l'analogo per almeno 4 tecniche
   ATLAS (AML.T0067, AML.T0099, AML.T0110.002, AML.T0011.002) e la sua assenza dal
   dataset è ora documentata come gap di **popolamento**, non di **tassonomia** — la
   tecnica esiste nella tassonomia, ma non ha casi di test. Lo stesso vale per T0009
   (Covert Data Over-Collection) rispetto a AML.T0085.

3. **AML.T0006 come gap strutturale**: la presenza di tecniche di ricognizione attiva
   in ATLAS (e la loro assenza dai 14 T-code) è coerente con l'impianto originale del
   vendor, che classifica per tecnica d'attacco, non per fase della kill chain. Se il
   progetto vuole allinearsi al modello a fasi di ATLAS/ATT&CK, la ricognizione è la
   lacuna più evidente.

## Fonti consultate

- Repository MITRE ATLAS su GitHub (`github.com/mitre-atlas/atlas-data`), clone
  completo del repository. File `dist/ATLAS-latest.yaml` (17.878 righe), content
  version `2026.07`, format version `6.0.0`. Fetch riuscito 2026-08-30.
- `dist/manifest.yaml` (nello stesso repository) — verificato il versioning (content
  version YYYY.MM, format version semver).
- `catalog/vendor_taxonomy_snapshot.yaml` (14 T-code, commit vendor pinnato
  7fad14d2478707e68a09b8ecd9942dec8fde1614) — fonte per il lato vendor del confronto.
- `catalog/cases.yaml` — letto per verificare lo stato di popolamento del catalogo
  (31 voci, 12/14 T-code) al momento del cross-check, non per il confronto tassonomico
  in sé.
- `src/toy_agent/tools.py` — letto per costruire il criterio di mappabilità del Passo
  1 e per verificare la superficie d'attacco di ciascun tool.
- `docs/design/2026-08-30-atlas-audit-method-design-v4.md` — contesto del metodo a 5
  passi; questo documento è il Nodo A delegato da quel design.
- `docs/research/2026-08-19-taxonomy-cross-check-findings.md` — pattern di
  formato/metodo replicato in questo documento.