# Cross-check di copertura: tassonomia del vendor (14 T-code) contro 4 tassonomie accademiche esterne

Esercizio di ricerca, non codice — eseguito come Plan 5a Task 6, raccomandazione già
registrata in `docs/research/2026-08-19-prior-art-agent-security-harnesses.md`
(sezione "Recommendation"). **Obiettivo unico**: trovare pattern malevoli con un
analogo in una delle 4 tassonomie esterne (R-Judge, InjecAgent, ASB, AgentHarm) ma
nessun analogo tra i 14 T-code del vendor (`catalog/vendor_taxonomy_snapshot.yaml`) —
un vero gap-finding, mai un'importazione di dati o etichette da quei dataset nel
catalogo di questo progetto (principio 1, `SPIRIT.md`). Questo documento non aggiunge
né modifica alcuna voce di `catalog/cases.yaml`.

**Stato del catalogo al momento del cross-check**: 31 voci, 12/14 T-code coperti
(T0009 Covert Data Over-Collection e T0011 Tool-Result Tampering esclusi per limite
dichiarato, Gap 17) — verificato leggendo `catalog/cases.yaml` (`entries`, campo
`technique_code`) prima di scrivere questo documento. Il cross-check qui sotto è
comunque condotto contro tutti e 14 i T-code dichiarati dal vendor
(`catalog/vendor_taxonomy_snapshot.yaml`), non solo i 12 popolati — un pattern
malevolo può avere analogo in T0009/T0011 anche se quelle due tecniche non hanno
ancora voci di catalogo.

## Metodo

Per ciascuna delle 4 tassonomie, fonte primaria fetchata via `WebFetch` (non un
riassunto di terzi):
- **R-Judge** — arXiv 2401.10019, versione HTML (`arxiv.org/html/2401.10019`) per il
  testo completo (l'abstract da solo non elenca i 10 risk type).
- **InjecAgent** — arXiv 2403.02691, abstract (sufficiente: la tassonomia ha solo 2
  categorie ed è enunciata per intero nell'abstract).
- **ASB** — arXiv 2410.02644, tre fetch: abstract, HTML (`arxiv.org/html/2410.02644v4`)
  e mirror `ar5iv.labs.arxiv.org/html/2410.02644` — vedi nota sotto, la tassonomia
  letterale ha richiesto più passaggi per essere disambiguata.
- **AgentHarm** — arXiv 2410.09024, versione HTML (`arxiv.org/html/2410.09024`).

Per ogni categoria dichiarata: verificato se esiste un analogo ragionevole in uno dei
14 T-code, citando quale. "Analogo ragionevole" = la stessa classe di comportamento
malevolo descritta a un livello di dettaglio comparabile (non serve un match
sinonimico esatto del nome).

## Nota metodologica — ASB, correzione del conteggio "27"

Il brief di questo task (ereditando la formulazione dell'abstract ASB) parla di "27
attack type". Il fetch diretto del testo (HTML `arxiv.org/html/2410.02644v4` e mirror
`ar5iv.labs.arxiv.org/html/2410.02644`, risultato identico su entrambi) mostra che 27
è la somma di **attacchi + difese**, non il conteggio degli attacchi da soli:

> "We benchmark 10 prompt injection attacks, a memory poisoning attack, a novel
> Plan-of-Thought backdoor attack, 4 mixed attacks, and 11 corresponding defenses
> across 13 LLM backbones."

10 + 1 + 1 + 4 = **16 attack type distinti**, + 11 difese = 27. Il documento di ricerca
prior-art già esistente (`docs/research/2026-08-19-prior-art-agent-security-harnesses.md`,
riga tabella ASB) usa correttamente la dicitura "27 attack/defense types" — la
formulazione "27 attack type" nel brief di Task 6 era una lettura imprecisa
dell'abstract, propagata dal design doc. La tabella sotto usa il conteggio corretto
(16 attack type), raggruppati come li definisce il paper: 5 varianti applicate sia a
Direct Prompt Injection (DPI) sia a Indirect Prompt Injection (IPI) = 10, + memory
poisoning (1) + PoT backdoor (1) + mixed attacks (4, combinazioni di DPI/IPI/memory
poisoning su più stadi dell'agente).

## R-Judge (arXiv 2401.10019) — 10 risk type

| Risk type (R-Judge) | Analogo T-code | Note |
|---|---|---|
| Privacy Leakage | T0012 (Data Exfiltration) | anche T0009 (Covert Data Over-Collection, escluso dal catalogo per Gap 17 ma presente nella tassonomia vendor) |
| Computer Security | T0006 (Unauthorized Resource Access) | errori di configurazione/verifica — anche T0008 (Sandbox Escape Attempt) per il sottocaso di escape |
| Financial Loss | T0004 (Malicious Tool Invocation) / T0014 (Destructive Action) | categoria di *esito*, non di tecnica — l'esito nasce da una tecnica già coperta (es. transazione non autorizzata via tool) |
| Property Damage | T0014 (Destructive Action) | idem: esito di una tecnica già coperta |
| Physical Health | T0014 (Destructive Action) / T0004 (Malicious Tool Invocation) | idem — rilevante per tool IoT/attuatori, non presente nel set di 6 tool di questo progetto ma la tecnica sottostante è coperta |
| Data Loss | T0014 (Destructive Action) | idem |
| Illegal Activities | **nessuno** | vedi discussione sotto |
| Ethics & Morality | **nessuno** | vedi discussione sotto |
| Bias & Offensiveness | **nessuno** | vedi discussione sotto |
| Miscellaneous | n/a | categoria residuale, non classificabile per definizione |

## InjecAgent (arXiv 2403.02691) — 2 harm category

Enunciate per intero nell'abstract: "We categorize attack intentions into two primary
types: direct harm to users and exfiltration of private data."

| Harm category (InjecAgent) | Analogo T-code | Note |
|---|---|---|
| Direct harm to users | T0004 (Malicious Tool Invocation) / T0014 (Destructive Action) | dipende dall'azione — InjecAgent non specifica ulteriormente |
| Exfiltration of private data | T0012 (Data Exfiltration) | match diretto |

Nessuna categoria senza analogo.

## ASB (arXiv 2410.02644) — 16 attack type (vedi nota conteggio sopra)

| Attack type (ASB) | Analogo T-code | Note |
|---|---|---|
| Direct Prompt Injection — 5 varianti (Naive, Escape Characters, Context Ignoring, Fake Completion, Combined) | T0001 (Direct Prompt Injection) | match diretto per tutte e 5 le varianti, sono tecniche di offuscamento della stessa classe |
| Indirect Prompt Injection — stesse 5 varianti, applicate a un risultato di tool invece che al prompt utente | T0002 (Indirect Prompt Injection) | match diretto |
| Memory Poisoning Attack | T0010 (Context Poisoning) | avvelenamento della memoria/retrieval è un caso di avvelenamento del contesto |
| Plan-of-Thought (PoT) Backdoor Attack | T0010 (Context Poisoning) / T0003 (Agentic Control-Flow Hijacking) | demo pre-iniettate nel system prompt (poisoning del contesto) che dirottano il piano dell'agente al trigger (hijacking del control-flow) — copertura combinata ragionevole |
| Mixed Attacks — 4 combinazioni di DPI/IPI/memory poisoning su più stadi | (composizione di T0001/T0002/T0010) | sono combinazioni di tecniche già coperte singolarmente, non introducono una classe nuova |

Nessuna categoria senza analogo.

## AgentHarm (arXiv 2410.09024) — 11 harm category

| Harm category (AgentHarm) | Analogo T-code | Note |
|---|---|---|
| Fraud | T0004 (Malicious Tool Invocation) / T0014 (Destructive Action) | esito ottenibile via tecnica già coperta |
| Cybercrime | T0006 (Unauthorized Resource Access) / T0008 (Sandbox Escape Attempt) | match ragionevole |
| Self-harm | **nessuno** | vedi discussione sotto |
| Harassment | **nessuno** | vedi discussione sotto |
| Sexual | **nessuno** | vedi discussione sotto |
| Copyright | **nessuno** | vedi discussione sotto |
| Drugs | **nessuno** | vedi discussione sotto |
| Disinformation | **nessuno** | vedi discussione sotto |
| Hate | **nessuno** | vedi discussione sotto |
| Violence | **nessuno** | vedi discussione sotto |
| Terrorism | **nessuno** | vedi discussione sotto |

## Discussione: le categorie senza analogo sono un asse diverso, non una tecnica mancante

Le categorie marcate "nessuno" sopra sono, in tutti i casi:

- R-Judge: Illegal Activities, Ethics & Morality, Bias & Offensiveness
- AgentHarm: Self-harm, Harassment, Sexual, Copyright, Drugs, Disinformation, Hate,
  Violence, Terrorism (9 delle 11 categorie)

Ho verificato che nessuna di queste ha un analogo ragionevole tra i 14 T-code, e il
motivo è strutturale, non un buco di copertura casuale: i 14 T-code del vendor
classificano **per tecnica/vettore d'attacco** (come un agente viene compromesso o
indotto a comportarsi male: iniezione, dirottamento del control-flow, abuso di tool,
escape, esfiltrazione...). Le categorie senza analogo classificano invece **per
dominio del contenuto/esito dannoso** (di cosa tratta il danno: frode, discorso
d'odio, contenuto sessuale, terrorismo...) — un asse ortogonale alla tecnica. Un
agente può arrivare a produrre contenuto d'odio o istruzioni per autolesionismo
tramite più tecniche diverse (prompt injection diretta, nessun attacco affatto — solo
un utente che chiede direttamente), o nessuna tecnica (l'agente lo fa spontaneamente,
senza che nessuno lo stia attaccando) — è un problema di *content safety/allineamento
dell'output*, non di *rilevamento di una tecnica d'attacco agentica*.

Questo è coerente con lo scope dichiarato di questo progetto: l'agente giocattolo è un
agente di customer support con un set fisso di 6 tool, e l'esercizio di audit misura
se un detector esterno riconosce **tecniche di attacco agentiche** in una transcript
(la tassonomia dei 14 T-code, per sua stessa definizione, è una tassonomia di
tecniche — non una tassonomia di content moderation). Non è quindi un'omissione da
colmare con un nuovo T-code (un "T0015: contenuto vietato" non sarebbe una tecnica,
sarebbe una categoria di esito — non si sposerebbe con la forma degli altri 14
T-code). È però un limite di scope reale e va registrato come tale, non liquidato.

## Conclusione — esiste un gap?

**Nessun gap trovato al livello di tecnica/vettore d'attacco.** Ogni categoria delle 4
tassonomie esterne che descrive *come* un agente viene attaccato o indotto a un
comportamento dannoso tramite un meccanismo agentico (iniezione diretta/indiretta,
avvelenamento del contesto/memoria, dirottamento del control-flow, invocazione
dannosa di tool, escape dal sandbox, accesso non autorizzato, esfiltrazione,
azione distruttiva) ha un analogo ragionevole tra i 14 T-code del vendor. InjecAgent e
ASB (le due tassonomie più vicine, per costruzione, a una classificazione per
tecnica) hanno copertura completa, zero categorie senza analogo.

**Osservazione da registrare come future work, non come gap tecnico**: R-Judge (3/10
categorie) e soprattutto AgentHarm (9/11 categorie) classificano prevalentemente per
dominio di contenuto/esito dannoso piuttosto che per tecnica — un asse che i 14 T-code
del vendor non tentano di coprire per costruzione. Non genera un'azione immediata (non
è una tecnica mancante, quindi non richiede una discussione di design come
T0007/T0009/T0011), ma è un limite di scope della tassonomia vendor stessa che vale la
pena avere esplicito: se in futuro questo progetto (o un audit di un vendor diverso in
Fase 2) volesse misurare rilevamento di *content-safety* oltre che di *tecnica
d'attacco*, servirebbe un asse di classificazione aggiuntivo, non un'estensione dei 14
T-code esistenti.

## Fonti consultate

- arXiv 2401.10019 (R-Judge) — abstract e HTML completo (`arxiv.org/html/2401.10019`),
  fetch riuscito.
- arXiv 2403.02691 (InjecAgent) — abstract, fetch riuscito (tassonomia di 2 categorie
  enunciata per intero nell'abstract stesso).
- arXiv 2410.02644 (ASB) — abstract, HTML (`arxiv.org/html/2410.02644v4`) e mirror
  `ar5iv.labs.arxiv.org/html/2410.02644`, fetch riusciti su tutti e tre; il PDF diretto
  (`arxiv.org/pdf/2410.02644`) è stato scaricato ma non leggibile localmente
  (`pdftoppm`/poppler non installato in questo ambiente) — non necessario, l'HTML/ar5iv
  ha fornito il testo completo richiesto.
- arXiv 2410.09024 (AgentHarm) — abstract e HTML completo
  (`arxiv.org/html/2410.09024`), fetch riuscito.
- `catalog/vendor_taxonomy_snapshot.yaml` (14 T-code, commit vendor pinnato
  7fad14d2478707e68a09b8ecd9942dec8fde1614) — fonte per il lato vendor del confronto.
- `catalog/cases.yaml` — letto per verificare lo stato di popolamento del catalogo
  (31 voci, 12/14 T-code) al momento del cross-check, non per il confronto tassonomico
  in sé (che è condotto contro tutti e 14 i T-code dichiarati, non contro le voci di
  catalogo).
- `docs/research/2026-08-19-prior-art-agent-security-harnesses.md` — riusato come
  punto di partenza per identificatori arXiv esatti, come richiesto dal brief.
