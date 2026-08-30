# Posizionamento strategico

Data: 2026-08-25. Documento di strategia, da rileggere quando il progetto prende decisioni
di direzione. Scritto in italiano per coerenza col repo; traduzione inglese prevista quando
il metodo sarà pronto per il pubblico esterno.

---

## 1. La tesi (in una frase)

**Non misuriamo il modello — misuriamo il detector.** Il red teaming classico verifica se
un LLM è vulnerabile. Noi verifichiamo se il prodotto che *promette di intercettare*
comportamenti malevoli nei sistemi ad agenti lo fa davvero.

---

## 2. Il vuoto di mercato

I detector di minacce agentiche sono valutati dai loro stessi creatori: il vendor costruisce
il detector e il benchmark che lo misura. Non esiste un ente indipendente che dica "questo
detector funziona come dichiara?" né un criterio condiviso per confrontare due vendor.

Chi compra un detector oggi non ha risposte a:
- Il 99% di recall dichiarato è reale?
- Come confronto due prodotti?
- Quali classi di attacco *non* vengono rilevate?

Questo vuoto è la ragione per cui il progetto esiste (SPIRIT.md).

---

## 3. Posizionamento: il metodo prima, l'ente dopo

La sequenza che regge è:

```
Metodo pubblico → Adozione (il mercato lo usa) → Ente (servizi professionali su di esso)
```

### Perché in questo ordine

- **Il metodo è difendibile, l'ente da solo non lo è.** Un ente senza metodo pubblico è
  opaco come il vendor che contesta. La reputazione nasce dal metodo, non dai report.
- **Il metodo crea la domanda.** OWASP non ha "venduto" nulla: ha creato un linguaggio. Le
  aziende hanno chiesto "voglio essere conforme al Top 10", e *poi* chi ha scritto lo
  standard è diventato naturalmente il verificatore più autorevole.
- **Il metodo è il moat.** Chiunque può aprire un'azienda di audit. Nessuno può ricostruire
  rapidamente dataset indipendenti, tassonomie, pipeline trasparente e storico di rigore
  (SPIRIT.md, principio 7).

### Il passaggio critico: adozione

Tra metodo ed ente c'è il passaggio dove si vince o si perde. L'adozione si guadagna con:
1. Essere citato come riferimento (il framework compare quando un buyer cerca "come valuto
   un detector per agenti").
2. Essere riusabile da terzi (non solo da noi: principio 4, riproducibilità).
3. Accumulare report che dimostrano il metodo in azione (ogni audit è una prova, non un
   prodotto fine a sé stesso).

---

## 4. Chi paga, e per cosa

Tre destinatari, tre modelli di ricavo potenziali:

| Destinatario | Bisogno | Modello di ricavo |
|---|---|---|
| **Buyer** (chi valuta l'acquisto) | Un criterio per decidere tra vendor | Audit commissionato (one-off, non scala) |
| **Vendor** (chi vende il detector) | Differenziarsi da concorrenti con claim verificati | Certificazione indipendente (pagata dal vendor ma con firewall organizzativo) |
| **Regolatore** (EU AI Act, NIST) | Un riferimento tecnico per la conformità | Framework pubblico, servizi di advisory |

Il modello più pulito (SPIRIT principio 5) è il primo: pagato da chi compra, non da chi
vende. Ma da solo non scala. La combinazione sostenibile è: framework pubblico (regolatore)
come gancio reputazionale + audit (buyer/vendor) come ricavo.

---

## 5. Il moat (perché non è replicabile in fretta)

- **Dataset indipendenti.** Costruiti a mano su tecniche reali, non il benchmark del vendor.
- **Metodologia dichiarata prima dei risultati.** Ogni caso di test è definito *prima* di
  eseguire il tool (principio 2), evitando bias di conferma.
- **Risultati grezzi pubblicati per intero.** Non solo le conclusioni: chiunque può
  riprodurre i numeri (principio 4). È l'opposto del benchmark self-reported.
- **Storico di rigore.** Ogni report porta il commit esatto del misuratore (provenance).
  Chi copia il codice e lo richiude diventa visibilmente il vendor opaco che questo progetto
  contesta (principio 7).

La domanda da porsi non è "qualcuno può copiare il codice?" (sì, è pubblico). È "qualcuno
può copiare la reputazione?" (no, è accumulata).

---

## 6. Le debolezze (da dire, non da nascondere)

Un posizionamento onesto nomina i rischi. Nasconderli è il difetto dei benchmark
self-reported che questo progetto contesta — non lo commettiamo anche noi.

- **Il mercato è piccolo e giovane.** I detector di minacce agentiche sono una nicchia.
  Se il mercato non decolla, l'ente indipendente non ha nulla da misurare.
- **Il gap di generalizzabilità.** Il metodo misura il detector su un toy agent specifico,
  con tool e prompt specifici. Il buyer ha il *suo* agente, diverso. La domanda "protegge
  il mio agente?" non trova risposta in "recall 0.667 sul toy agent di qualcun altro". Il
  principio 8 (strutturale prima di contingente) è la risposta interna corretta, ma non
  colma il gap percepito dal compratore.
- **Il modello di ricavo è definito nei principi ma non testato.** Pagato dal buyer, mai
  dal vendor — il principio è giusto, ma non si sa ancora se regge economicamente.
- **Manca un nome citabile.** "agentic-security-audits" è il repo, non il metodo. Servirà
  un nome che identifichi il metodo come entità — OWASP ha il "Top 10", MITRE ha "ATT&CK".

---

## 7. Naming — deciso: BlueLens

Il progetto ha un nome tecnico (`agentic-security-audits`, il repo). Il metodo ora ha
anche un nome citabile: **BlueLens**.

**Deciso il 2026-08-28**, dopo che il trigger di maturità dichiarato al punto 8.2
("il secondo vendor è il vero test") si è verificato: LlamaFirewall integrato senza
modifiche al metodo, con un finding verificato strutturalmente diverso da quello di
aidr con lo stesso impianto (vedi `docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md`).

**Perché "BlueLens" e non altro** (sessione di brainstorming completa, non ripetuta
qui — solo l'esito): il progetto non è un ente (una persona sola, non un consorzio —
scartato per questo il registro "acronimo istituzionale" tipo OWASP/MITRE ATT&CK, che
si guadagna *dopo* l'adozione, non si dichiara prima). "Blue" nomina correttamente il
soggetto misurato — non l'agente sotto test, non l'attaccante simulato, ma il
*detector*, lo strato difensivo (blue team) che dovrebbe accorgersi dell'attacco.
"Lens" nomina lo strumento — osserviamo, non costruiamo un prodotto di difesa (scartato
"Firewall", collide con LlamaFirewall stesso e implica che *siamo* un prodotto),
non monitoriamo in tempo reale (scartato "Sensor", è il registro del prodotto di
monitoraggio operativo già scartato per questo progetto, sezione 4 di
`docs/notes/valutazione-argomenti-poc-monitoraggio.md`), non certifichiamo con
un'autorità che non abbiamo ancora guadagnato (scartati "Cert" e "Stamp" — quest'ultimo
rischia pure l'idioma inglese "rubber stamp", approvazione acritica, l'opposto di un
audit rigoroso). Radice dell'immagine: "La finestra sul cortile" di Hitchcock — un
osservatore immobile, esterno, che scopre la verità guardando i comportamenti reali
invece di ascoltare le dichiarazioni — la stessa distinzione intento/effetto che regge
ogni finding pubblicato finora.

**Cosa resta aperto**: se e quando rinominare anche il repo GitHub (`agentic-security-audits`
→ qualcosa con "bluelens"), o tenere il nome tecnico del repo separato dal nome
pubblico del metodo (come OWASP Foundation e "OWASP Top 10" non condividono
necessariamente un unico nome di repo). Non deciso in questa sessione — vedi la
conversazione che ha portato a questa decisione per il contesto completo, se serve
riaprirla.

---

## 7bis. Piano editoriale — tre pezzi, non uno

Deciso il 2026-08-28, durante la stessa sessione del naming: la pubblicazione non è
un articolo unico, sono **tre pezzi separati**, pubblico e scopo diversi:

1. **BlueLens** — introduzione/posizionamento: cos'è, perché esiste, come misura
   (include qui la metodologia — le due metriche primary/strict, il DSL
   `attack_success_criteria`, provenance/riproducibilità — come parte
   dell'"ecco come funziona", non un pezzo a sé stante).
2. **Il caso di studio** — i finding concreti sui due vendor auditati: aidr giudica
   l'intento del prompt, non l'effetto (`docs/research/2026-08-26-analisi-metriche-intento-vs-effetto.md`);
   LlamaFirewall/AlignmentCheck giudica la coerenza locale azione-istruzione, mai la
   legittimità dell'obiettivo (`docs/research/2026-08-28-analisi-llamafirewall-alignmentcheck-azione-per-azione.md`).
3. **Il metodo di lavoro** — il processo uomo+agente con cui questo progetto è stato
   costruito (disciplina di verifica, council multi-agente, delega a Pi con review
   indipendente). Pubblico diverso dagli altri due (chi lavora con agenti di coding,
   non chi valuta detector di sicurezza). Tensione dichiarata da affrontare prima di
   scriverlo: il meccanismo di review citato come prova (`council`) vive in un repo
   privato dell'utente, non ispezionabile da chi legge — stesso limite già registrato
   per BlueLens stesso riguardo al proprio tooling di revisione (sezione "Risolti" più
   sotto in questa nota non si applica; vedi `docs/design/registro-limiti-aperti.md`,
   ultima voce prima di "Risolti"). Dettaglio completo salvato in memoria
   (`project_second_article_idea_workflow`), non ancora un documento in questo repo.

Nessuno dei tre è scritto. Nessun ordine di scrittura deciso ancora — solo la
scomposizione in tre, per non fonderli e diluirli a vicenda.

## 8. Prossimi passi strategici

1. **Rendere il metodo il prodotto.** Oggi la narrazione è "audit di FareedKhan-dev".
   Deve diventare: "un metodo per auditare detector agentici, dimostrato su un caso
   concreto". I report sono dimostrazioni del metodo, non fine a sé stessi.
2. **Accumulare report su vendor diversi.** Un solo vendor non fa un metodo: il secondo
   vendor è il vero test. Se il metodo funziona senza modifiche su un detector diverso,
   è generale. Se richiede adattamenti, è fragile.
3. **Targetizzare i buyer giusti.** Non il singolo compratore con un audit one-off, ma il
   mercato: vendor che vogliono differenziarsi, buyer che cercano criteri, regolatori
   che cercano riferimenti.
4. **Scegliere il nome quando il metodo è stabile.** Non è urgente, ma è una decisione
   da prendere una volta sola — sbagliare nome costa un rebrand.

---

## 9. Il metodo generalizza oltre l'agentic security (osservazione, non decisione)

Emerso il 2026-08-29 durante una pausa forzata (il lavoro sul secondo scanner di
LlamaFirewall, PromptGuard, è bloccato in attesa dell'approvazione gated di Meta — vedi
`docs/design/registro-limiti-aperti.md`, voce LlamaFirewall). **Non è un'idea nuova
inventata in questa sessione**: il principio — non fidarsi del numero che un tool
pubblica su sé stesso, verificare indipendentemente sul confine ingresso/uscita
dichiarato — questo stesso progetto lo ha già trovato due volte sui propri soggetti,
non solo teorizzato:
- `aidr` (il tool sotto audit) pubblica P/R/F1 contro il proprio benchmark, il
  **Gauntlet**, costruito da chi lo pubblica.
- **AgentDoG** (candidato scartato come secondo vendor, `docs/research/2026-08-27-agentdog-verification.md`)
  pubblica P/R/F1 contro il proprio **ATBench** — stessa struttura di conflitto
  d'interesse, registrata esplicitamente nel doc di mercato come "same conflict-of-interest
  structure this project already refuses to trust for aidr's Gauntlet".

Il punto 1 di questo stesso documento ("Non misuriamo il modello — misuriamo il
detector") è quindi un caso specifico di un principio più largo: **non fidarsi
dell'autocertificazione di nessun tool AI che promette un risultato misurabile**, non
solo dei detector di minacce agentiche.

### Il parallelo più forte trovato finora: i laboratori di test antivirus (non-AI, ma lo stesso identico schema)

Trovato più tardi nella stessa sessione del 2026-08-29, discutendo CodeShield+OWASP
Benchmark: **AV-TEST, AV-Comparatives, SE Labs** fanno da decenni, per gli antivirus,
esattamente quello che questo progetto fa per i detector agentici — campioni noti
(malware reale + file puliti noti) lanciati contro il prodotto, tasso di rilevamento e
falsi positivi misurati indipendentemente dal claim del vendor. Non è nell'ambito AI, ma
è lo schema di misura più vicino di tutti quelli trovati in questa sezione, per tre
motivi:
1. Testa specificamente **prodotti di sicurezza** (non classificatori AI generici come
   negli altri esempi sotto) — stesso dominio concettuale di questo progetto.
2. **Ha un modello di ricavo già rodato e verificato**, non solo un ente pubblico che
   testa gratis: [VERIFICATO, 2026-08-29, `av-comparatives.org/funding/`] i test del
   "Public Test Series" sono gratuiti, ma i vendor pagano per certificazione, report
   dettagliati, uso del logo — dichiarano esplicitamente che il pagamento non influenza
   il risultato. **Questo è un precedente reale, funzionante da decenni, del modello di
   ricavo "Vendor... Certificazione indipendente (pagata dal vendor ma con firewall
   organizzativo)" già scritto al punto 4 di questo documento** — non più solo un'ipotesi
   sulla carta.
3. È il più citabile: "facciamo per i detector agentici quello che AV-TEST fa per gli
   antivirus" si spiega in una frase, senza bisogno di contesto aggiuntivo.

**Caveat (dichiarato dall'utente subito dopo, poi corretto una volta ciascuno con
verifica reale, stessa sessione)**: il metodo è lo stesso, la scala no — da dire
esplicitamente, coerente col punto 6 ("le debolezze si dicono, non si nascondono"). Ma
i due problemi sono di natura diversa, vanno tenuti separati:

1. **Tecniche da iniettare — meno grave di quanto sembrasse.**
   [VERIFICATO, 2026-08-29] **MITRE ATLAS** è una tassonomia di attacchi AI reale,
   attivamente mantenuta, in espansione proprio sull'agentic AI (v5.1.0 nov. 2025, 16
   tattiche/84 tecniche; aggiornamenti fino a v5.4.0 feb. 2026 con tecniche
   agent-specifiche come "Publish Poisoned AI Agent Tool"). Non è un catalogo statico
   isolato — è un flusso esterno codificato e mantenuto da terzi, a differenza di come
   presentato nella prima stesura di questo caveat. **Ma va distinto cosa è codificato
   da cosa no**: la tassonomia sì; un **corpus di campioni-attacco etichettati** legato
   a quella tassonomia, della scala dei feed di malware usati da AV-TEST, non è stato
   trovato — il nostro stesso `docs/research/2026-08-19-prior-art-agent-security-harnesses.md`
   aveva già verificato che nessun benchmark accademico esistente usa i codici ATLAS.
   Il catalogo T0001-T0014 di questo progetto resta un artefatto da costruire a mano,
   ma può appoggiarsi a una tassonomia esterna che matura da sola, invece di essere
   isolato.
2. **Accesso ai prodotti — non verificato, non risolvibile a tavolino.** La prima
   stesura di questo caveat trattava "solo contact-sales, nessun self-serve" (dato
   verificato nella Tabella 1) come equivalente a "inaccessibile" — non lo è. "Solo
   contact-sales" significa che nel materiale fetched non è stata trovata
   un'iscrizione self-serve, non che una richiesta di demo/POC verrebbe rifiutata.
   **Non è stata testata nessuna richiesta reale a nessuno dei 10 vendor** — resta una
   domanda aperta e verificabile (scrivere e vedere cosa risponde), non una barriera
   strutturale accertata. Un'asimmetria plausibile ma non verificata: un ricercatore
   indipendente senza azienda/budget dietro potrebbe ricevere un trattamento diverso da
   un buyer enterprise.

La frase corretta resta **"BlueLens applica il metodo di un certificatore AV-style, su
una fornitura ancora da verificare su entrambi i lati"** — ma il lato tecniche è meglio
di quanto sembrasse (una tassonomia esterna matura esiste), il lato accesso-prodotti è
semplicemente non testato, non necessariamente peggiore.

### Altri ambiti AI con lo stesso problema (livello di certezza dichiarato per ciascuno)

- **Rilevatori di testo generato da AI** (GPTZero, Turnitin AI detection,
  Originality.ai) — i vendor dichiarano accuratezza molto alta; uno studio indipendente
  di Stanford (Liang et al., 2023) ha trovato tassi di falsi positivi più alti sui testi
  di non-madrelingua inglesi rispetto a quanto dichiarato. Confidenza alta
  sull'esistenza dello studio, numeri esatti non citati qui perché non verificati in
  questa sessione.
- **Riconoscimento facciale/biometria** — il caso più forte trovato: il NIST gestisce da
  anni il **FRVT** (Face Recognition Vendor Test), un programma di test indipendente
  nato perché le autocertificazioni dei vendor non erano affidabili. Unico caso qui dove
  esiste già un'istituzione dedicata proprio per questo motivo — il parallelo
  istituzionale più diretto con l'ambizione dichiarata al punto 3 di questo documento
  ("l'ente dopo il metodo"). Confidenza alta, programma pubblico documentato da anni.
- **Scanner di vulnerabilità nel codice generato da AI** (incluso CodeShield di
  LlamaFirewall, mai testato in questo progetto) — esiste l'**OWASP Benchmark
  Project**, suite di test indipendente nata perché i claim dei vendor SAST non erano
  comparabili tra loro. Stesso schema del punto precedente. Confidenza alta.
- **Rilevatori di deepfake/media sintetici** — la Deepfake Detection Challenge di Meta
  (2019-2020) ha mostrato un divario netto tra prestazioni dichiarate in laboratorio e
  quelle su un test set indipendente "a scatola nera". Confidenza alta sull'esistenza
  della challenge, numeri non citati per lo stesso motivo di cui sopra.
- **Strumenti "LLM-as-judge"** (TruLens, Ragas — verificati come reali il 2026-08-29,
  vedi addendum in `docs/research/2026-08-20-vendor-market-agentic-threat-detection.md`)
  — problema **ricorsivo**: sono AI che giudicano altre AI (allucinazioni, pertinenza
  RAG), e la loro accuratezza da giudice è raramente verificata da terzi. Già osservato
  internamente a questo progetto: `llama-4-maverick` come giudice ha fallito la
  validazione dello schema strutturato su un caso reale, `llama-3.3-70b-instruct` no
  (`docs/design/registro-limiti-aperti.md`) — l'affidabilità del giudice va verificata,
  non assunta, anche dentro questo stesso progetto.

### Cosa NON è questa sezione

Non è una decisione di allargare lo scope di BlueLens oggi. Il progetto resta
un'audit di detector agentici, con due vendor misurati e un metodo dimostrato su quel
caso concreto (punto 8.2). Questa sezione è una nota di posizionamento: risponde in
anticipo alla debolezza dichiarata al punto 6 ("il mercato è piccolo e giovane") con
un argomento — il metodo, non il mercato specifico, è la cosa riusabile, e ha già
precedenti istituzionali riconosciuti (NIST FRVT, OWASP Benchmark) in ambiti AI
adiacenti. Se e quando allargare lo scope reale del progetto resta una decisione
separata, non presa qui.

---

## 10. Gate pre-pubblicazione — contenuto da purgare prima che il repo diventi pubblico

Deciso il 2026-08-30, discutendo dove deve vivere fisicamente la famiglia di note
spin-off del `toy_agent` (contesto delle idee stesse al punto 9 sopra). Il fix già fatto
sulle note (`docs/notes/2026-08-29-famiglia-spinoff-toy-agent.md`, sezione "Dove si
decide") protegge solo da un lettore interno a questo progetto — futura sessione, mia o
dell'utente — che potrebbe leggere il tono descrittivo delle note come un piano in attesa
di approvazione **dentro** questo repo. Non protegge da un lettore diverso: chi, dal di
fuori, trova esplicitamente descritta un'idea in tensione diretta con la tesi del punto 1
("non misuriamo il modello") nel momento in cui questo repo (oggi privato,
`paperinik007/bluelens`) o il suo contenuto diventa pubblico.

**Decisione**: non rimuovere ora — il repo è privato, il rischio non è attivo oggi. Un
unico passaggio di pulizia della storia git, eseguito prima di qualunque cambio di
visibilità del repo o di qualunque estrazione di contenuto per il terzo pezzo editoriale
(§7bis, "il metodo di lavoro"), è più efficiente che rincorrere ogni singolo file mano a
mano che nasce — nel frattempo è probabile che si accumuli altro materiale simile.

**Cosa purgare — elenco preciso, da eseguire come controllo meccanico, non da
ricostruire a memoria**:
- `docs/notes/2026-08-29-atlas-antivirus-metodo-note.md`
- `docs/notes/2026-08-29-famiglia-spinoff-toy-agent.md`
- `docs/notes/2026-08-29-idea-harness-bersaglio-pubblico.md`
- `docs/notes/2026-08-29-idea-sottoprodotto-benchmark-modelli.md`
- La sezione "Estensione futura dichiarata (Nodo D)" in tutte e 4 le versioni del design
  doc del metodo ATLAS — descrive la stessa idea in prosa, anche se per escluderla dalla
  tesi: `docs/design/2026-08-29-atlas-audit-method-design.md` (v1),
  `docs/design/2026-08-30-atlas-audit-method-design-v2.md` (v2),
  `docs/design/2026-08-30-atlas-audit-method-design-v3.md` (v3),
  `docs/design/2026-08-30-atlas-audit-method-design-v4.md` (v4).
- Commit da purgare dalla storia: `c7ec3d6` (introduce le note),
  `29410e6` (aggiorna le note, introduce i design doc v1-v4).
- Prima di eseguire, ricontrollare se sessioni successive a questa (2026-08-30) hanno
  aggiunto altro materiale collegato alla stessa famiglia di idee — questo elenco è
  accurato alla data della decisione, non garantito completo per sempre.

**Come**: riscrittura della storia (`git filter-repo` o equivalente) sui path sopra,
poi force-push su `origin` — operazione distruttiva sul remoto, da confermare
esplicitamente con l'utente al momento dell'esecuzione, non solo qui.

**Perché non risolto ora**: coerente con come il progetto tratta altri rischi reali ma
non attivi (`docs/design/registro-limiti-aperti.md`) — dichiarato esplicitamente come
debito, non rinviato per omissione.