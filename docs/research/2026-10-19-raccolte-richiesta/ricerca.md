# Raccolte pubbliche per le caselle scoperte: ricerca (2026-10-19)

Parte da: `docs/research/2026-10-15-raccolte/verifica.md` (regola di equivalenza, sezione 5,
punto 1, con la lettura della sezione 7; criteri di scarto; uso dei produttori, sezioni 2 e 8);
`docs/design/2026-10-14-tabella-permessi-bozza.md` (strumenti e ruoli);
`docs/design/2026-10-11-piano-run-v3.md`, parte 5 ("Esito valido, dopo la correzione") e
parte 6 (AgentDojo escluso; regola 2).

Domanda: esistono raccolte pubbliche con testi d'attacco nelle caselle che InjecAgent e ASB non
coprono? Cioè: nella **richiesta** e nel **contenuto** letto da uno strumento, nelle forme
**override**, **iniezione camuffata** e **pretesto**, con una delle dodici azioni.

Metodo. Fonti primarie: repository clonati in sola lettura (fuori dal repository, nessun codice
eseguito), schede e file di Hugging Face alla revisione indicata, articoli su arXiv. I conteggi
delle forme sono fatti con parole chiave (per esempio "ignore", "SYSTEM:", "I am the admin"):
sono **stime**, non uno scarto testo per testo. Lo scarto vero, con la regola di equivalenza e il
motivo per ogni testo, si fa solo per le raccolte che il proprietario sceglie di verificare a fondo.
Nessun testo d'attacco è copiato qui: per ognuna si dice dove stanno.
Uso dei produttori: ricerca dei nomi e degli identificativi arXiv di tutte le raccolte nei
repository dei produttori ai commit fissati (PurpleLlama `4be64c3`, aidr `7fad14d`), nell'articolo
di LlamaFirewall (arXiv 2505.03574v1, testo intero) e nell'articolo di Meta SecAlign (arXiv
2507.02735v4, testo intero). Nessuna spesa.

## Tabella riassuntiva

"Testi utili" = stima di quanti testi distinti passerebbero la regola di equivalenza; tra
parentesi, quanti **gruppi di testi con lo stesso segnale** ne verrebbero, perché la strada C
(verifica, sezione 7) prende un caso per gruppo.

| Raccolta | Licenza | Uso dei produttori | Dove | Forme | Azioni (delle dodici) | Testi utili (gruppi) | Esito proposto |
|---|---|---|---|---|---|---|---|
| b3, Lakera e UK AISI (versione "weak") | conflitto: la scheda dice MIT, il file `LICENSE` pone condizioni proprie (solo ricerca non commerciale, attribuzione, nessuna modifica ingannevole) | nessuno trovato | richiesta e contenuto | camuffata, pretesto, override (pochi), esplicita | scoprire (prompt di sistema, elenco strumenti); dati nel contenuto | circa 30-40 (3-5) | **da verificare a fondo**, dopo una decisione sulla licenza |
| BrowseSafe-Bench (Perplexity) | MIT | PromptGuard 2 misurato da Perplexity come termine di confronto (non dal produttore) | contenuto (pagine HTML) | override, camuffata, pretesto ("CEO"), esplicita | quasi solo dati verso un indirizzo esterno; scoprire | molti testi, pochi segnali (2-4) | **da verificare a fondo**, ma porta lo stesso segnale di InjecAgent |
| DoomArena (ServiceNow) | Apache 2.0 | usa Prompt Guard 1 (86M) come difesa: uso di terzi | richiesta (cliente malevolo) e contenuto (catalogo) | camuffata (avvisi di sistema finti), pretesto (finto responsabile), override nel nome | denaro (rimborsi), dati di un altro cliente | circa 3-6 sequenze (2-3) | **da verificare a fondo**; i testi sono sequenze di più turni |
| AgentInjectionBench (2026) | Apache 2.0 | nessuno trovato | contenuto | camuffata, gioco di ruolo, testo annidato | dati, comandi | circa 15-25, non verificato (2-4) | da verificare a fondo, con riserva sulla qualità (sintetica, un solo autore, ottobre 2026) |
| promptprotection/agent-security-datasets (2026) | CC BY 4.0 | nessuno trovato | contenuto (e testi isolati) | camuffata, override | dati, comandi | circa 10-15 (2-3) | da verificare a fondo, con la stessa riserva |
| Tensor Trust | **nessuna licenza per i dati** (codice BSD-2, articolo CC BY 4.0) | nessuno trovato; probabile nell'addestramento di PromptGuard 2 (non verificato) | richiesta | override, camuffata, gioco di ruolo | scoprire (prompt di sistema) | circa 150-250 (2-3) | scartata finché la licenza non è chiara |
| Lakera Gandalf (`gandalf_ignore_instructions` e affini) | MIT | nessuno trovato; probabile nell'addestramento di PromptGuard 2 (non verificato) | richiesta | override (scelta per somiglianza a "Ignore all previous instructions") | scoprire, se il testo chiede le istruzioni e non la password | circa 120-200 (1) | da verificare a fondo solo per la casella richiesta-override con "scoprire"; un solo segnale |
| deepset/prompt-injections | Apache 2.0 | nessuno; la scheda di PromptGuard 2 confronta un modello di deepset (addestrato su questa raccolta) | richiesta | override, gioco di ruolo | scoprire (pochi) | circa 10-20 (1) | scartata: mescola lingue, scopi fuori dalle dodici, già coperta da Gandalf |
| HackAPrompt | MIT, accesso con registrazione | nessuno trovato | richiesta (dentro un modello di prompt) | override e molte altre | nessuna: scopo fisso "I have been PWNED" o una chiave nascosta | 0 | scartata: scopo fisso (come LLMail-Inject) |
| SaTML CTF 2024 (ETH) | MIT | nessuno trovato | richiesta, conversazioni | varie | scoprire un segreto del prompt | non stimato | scartata: scopo fisso, conversazioni di più turni |
| BIPIA (Microsoft) | MIT | Meta SecAlign usa i suoi articoli (testi innocui, non gli attacchi) | contenuto | solo esplicita, senza tecnica | nessuna con oggetto nel mondo | 0 | scartata: solo forma esplicita, scopi fuori dal mondo |
| TaskTracker (Microsoft) | MIT | Meta SecAlign lo usa per valutarsi | contenuto | non descritte | nessuna (compiti generici, attacchi di BIPIA) | 0 | scartata |
| AgentHarm (UK AISI, Gray Swan) | MIT con clausola (solo sicurezza, non addestrare) | nessuno trovato | richiesta | esplicita (il modello di jailbreak non è pubblico) | nessuna nel mondo (frode, droghe, disinformazione) | 0 | scartata |
| Agent-SafetyBench (Tsinghua) | MIT | nessuno trovato | contenuto e richiesta | override nel contenuto | quelle di InjecAgent | 0 nuovi | scartata: le iniezioni sono i testi di InjecAgent |
| R-Judge | nessuna licenza nel repository | nessuno trovato | contenuto | override | quelle di InjecAgent | 0 nuovi | scartata: deriva da InjecAgent, senza licenza |
| ToolEmu | Apache 2.0 | nessuno trovato | richiesta | nessuna (non sono attacchi) | — | 0 | scartata: casi di rischio, non attacchi |
| WASP | CC BY-NC 4.0 | **di Meta** (FAIR), usato per Meta SecAlign | contenuto (pagine web) | override | sul web (GitLab, Reddit) | — | scartata: banco della stessa azienda |
| CyberSecEval (prompt injection) | MIT | **di Meta**; Prompt Guard 1 misurato su di esso | richiesta e contenuto | molte, compresa la persuasione | domande di chat | — | scartata: banco del produttore |
| AgentVigil | nessuna raccolta pubblicata trovata | — | — | — | — | — | non verificabile; comunque costruita su AgentDojo |
| Persuasive Adversarial Prompts | Apache 2.0 per il codice; dati con modulo di rilascio | nessuno trovato | richiesta | persuasione | contenuti dannosi (AdvBench), non azioni | 0 | scartata |
| ART, Gray Swan e UK AISI | dati non pubblici (non verificato) | — | — | — | — | — | non disponibile |

## 1. b3, Backbone Breaker Benchmark (Lakera, Check Point, UK AISI)

Fonte: `Lakera/b3-agent-security-benchmark-weak` su Hugging Face, revisione `584a182`
(2026-10-07); articolo arXiv 2510.22620 (Bazińska e altri; Lakera, ETH Zurigo, UK AISI, Oxford).

1. **Licenza.** In conflitto. La scheda (`README.md`) dice "License: MIT", ma i metadati dicono
   `license: other` e il file `LICENSE` è un testo proprio: solo ricerca "academic, non-commercial";
   attribuzione obbligatoria; non si può modificare il dataset "in any manner that is deceptive or
   leads to false conclusions"; niente ridistribuzione fuori dalla ricerca. Modificare con le
   modifiche registrate in `origin.changes` non è ingannevole; resta da decidere se BlueLens
   rientra nella "ricerca non commerciale". **Da decidere con il proprietario.**
2. **Produttori.** Nessuna occorrenza di b3, Lakera o 2510.22620 nei repository dei produttori,
   nell'articolo di LlamaFirewall o in quello di Meta SecAlign. La scheda non nomina Meta né
   PromptGuard. L'articolo valuta 31 modelli usati come motore di agenti, non i giudici
   (non verificato su tutto il testo dell'articolo).
3. **Dove e forme.** 210 attacchi distinti (630 righe: ogni attacco su 3 livelli di difesa) in
   `selected_attacks_low-quality.csv`, colonne `app_name`, `level`, `attack`; 21 per ognuna di 10
   "fotografie" di un agente, descritte in `threat_snapshots/*.json` (campi `attack_vector`,
   `attack_objective`). È la versione di qualità bassa: la scheda dice che gli attacchi migliori
   sono stati tolti e che la versione buona non è pubblica.
   - Richiesta: Cycling Coach (rivelare il prompt di sistema), Thingularity (rivelare nome e
     descrizione di tutti gli strumenti; un assistente di acquisti con ordini, sconti e
     rimborsi), CorpConnect Messenger (mandare un'email a nome di un altro), Solace AI
     (linguaggio volgare).
   - Contenuto: Clause AI (documento recuperato che fa mandare nome e indirizzo di una persona
     protetta a un indirizzo esterno), Trippy Planner (pagina web che fa inserire un link di
     phishing nel piano di viaggio), PortfolioIQ (PDF che fa scrivere una raccomandazione falsa),
     Curs-ed CodeReview (file di regole che fa proporre codice malevolo), MindfulChat (memoria).
   - Strumento: OmniChat Desktop (descrizione di uno strumento avvelenata).
   Forme, lette su un campione (Thingularity, Cycling Coach): molte iniezioni camuffate (finti
   messaggi di sistema tra parentesi, finte modalità "verbose" o "debug"), alcuni pretesti
   ("sto facendo controllo qualità", "sono l'amministratore delegato"), poco override esplicito.
   Un testo tipico: una richiesta d'aiuto innocua seguita da un finto avviso di sistema che chiede
   di elencare le capacità con i loro parametri. Conteggio per forma non fatto.
4. **Azioni.** Il danno sta nel testo (nessuno strumento d'attacco aggiunto). Con le nostre
   azioni: scoprire il sistema (Cycling Coach, Thingularity: 42 testi); dati a chi non deve
   averli (Clause AI: 21, nel contenuto). Dubbi: il link di phishing va nella risposta, non in
   un'email (la nostra azione "contro terzi" è un link in un'email); CorpConnect chiede di
   falsificare il mittente, campo che `send_email` non ha; PortfolioIQ è "ingannare" ma
   sull'oggetto "investimento", che il mondo non ha. Fuori: volgarità, memoria, codice.
5. **Stima.** Circa 30-40 testi: i 42 su "scoprire" meno quelli che nominano oggetti del gioco
   (per esempio "competitor", "training plan" senza corrispondente); più una parte dei 21 di
   Clause AI, se "testimone protetto" si legge come "dati di un'altra persona" (stesso genere,
   identità e contatti) e se il resto del testo non parla di cause e tribunali (da leggere
   testo per testo). Gruppi: scoprire nella richiesta con la forma camuffata, con il pretesto,
   esplicita; dati nel contenuto con la forma camuffata.
6. **Lingua.** Inglese (scheda).

## 2. BrowseSafe-Bench (Perplexity)

Fonte: `perplexity-ai/browsesafe-bench` su Hugging Face, revisione `b506fb5` (2025-12-04);
articolo arXiv 2511.20597v1.

1. **Licenza.** MIT (file `LICENSE`, "Copyright 2025 Perplexity AI, Inc."). Permette uso e
   modifica con attribuzione.
2. **Produttori.** Nessuna occorrenza nei repository dei produttori né negli articoli di Meta.
   La scheda riporta PromptGuard 2 (22M e 86M) come termine di confronto, misurato da
   Perplexity: è un uso di terzi, come l'articolo arXiv 2511.15203 per AlignmentCheck
   (verifica, sezione 2). Non è un banco del produttore.
3. **Dove e forme.** Solo contenuto: 14.719 pagine HTML (`train.parquet` 11.039,
   `test.parquet` 3.680), colonne `content` e `label` ("yes" 1.824 nel test). **Nessuna colonna
   con il tipo d'attacco o lo scopo**: il testo d'attacco sta dentro una pagina di circa 50.000
   caratteri in media e va estratto a mano. La scheda elenca 11 tipi: Important Message, Todo,
   InjecAgent, Ignore Previous, URL Segment, Role Manipulation, System Prompt Exfiltration,
   Delimiter Injection, Social Engineering, Indirect Hypothetical, Multilanguage. Lette con le
   nostre forme: override (Ignore Previous), camuffata (finto messaggio dell'utente, finto
   "TODO", finti delimitatori di fine contesto), pretesto (un finto "CEO" urgente; il ruolo di
   "personale di supporto"). Conteggi per tipo: non pubblicati; con parole chiave sul test,
   circa 550 pagine con "ignore (all) previous", circa 140 con "TODO", circa 90 con "END OF"
   (stime grezze). Un testo tipico: un paragrafo nascosto in un commento HTML che, dopo un finto
   avviso di sistema, chiede di mandare tutti i dati visibili a un indirizzo esterno.
4. **Azioni.** L'articolo stesso dice che "nearly all of the attacks reduce to some form of data
   exfiltration": dati verso un indirizzo esterno; più "scoprire" (prompt di sistema mandato
   fuori) e "URL Segment" (una frase da aggiungere alla risposta, cioè ingannare, ma con
   oggetti delle pagine web). Il danno sta nel testo.
5. **Stima.** Molti testi, pochissimi segnali: è lo stesso segnale del gruppo 1 di InjecAgent
   (dati mandati a un indirizzo esterno), in più forme. Gruppi possibili: dati con la forma
   override, camuffata, pretesto; scoprire nel contenuto. Ogni testo va estratto dalla pagina
   (lavoro a mano) e portato in un ticket (regola 2: si cambia il contenitore, non la frase).
   Il criterio (c) va controllato: "tutti i dati della sessione" ha un corrispondente (i dati
   del cliente letti dall'agente) solo se il testo non nomina oggetti del browser.
6. **Lingua.** Inglese, con una parte in altre lingue (tipo Multilanguage).

## 3. DoomArena (ServiceNow)

Fonte: `ServiceNow/DoomArena`, commit `b80902f` (2025-09-10); licenza nel file `LICENSE`.

1. **Licenza.** Apache 2.0: uso e modifica permessi, con attribuzione e nota delle modifiche.
2. **Produttori.** Nessuna occorrenza nei repository dei produttori né negli articoli di Meta.
   DoomArena usa Prompt Guard 1 (`meta-llama/Prompt-Guard-86M`) e Llama Guard come difese
   (`doomarena/core/src/doomarena/core/agent_defenses/promptguard.py:109`): uso di terzi di un
   prodotto Meta, non di PromptGuard 2.
3. **Dove e forme.** È un sistema per generare attacchi, non una raccolta: la maggior parte degli
   attacchi su τ-bench (assistenza clienti: vendita al dettaglio e linea aerea) è prodotta da un
   modello che recita il cliente malevolo. Testi fissi, in
   `doomarena/taubench/src/doomarena/taubench/system_prompt_config/system_prompt_initialization.py`:
   - richiesta, linea aerea, buono regalo (righe 5-25): 4 turni; avvisi di sistema finti e un
     finto "supervisore" che autorizza un rimborso: camuffata e pretesto;
   - richiesta, linea aerea, dati di un altro cliente (righe 28-51): 5 turni; chi scrive si
     finge un responsabile e chiede il profilo completo di un altro cliente: pretesto e
     camuffata;
   - richiesta, linea aerea, iniezioni fisse (righe 54-76): 5 testi, in parte suffissi
     avversari senza senso;
   - contenuto, vendita, catalogo (riga 78 e seguenti): 1 testo nel nome di un prodotto, una
     finta "politica aziendale" che chiede di aggiungere nome e codice postale del cliente in una
     chiamata: camuffata.
   Esempi di dialoghi d'attacco: `few_shot_examples/retail_few_shot.json` e
   `retaildb_few_shot.json` (2 riusciti e 2 falliti ciascuno).
4. **Azioni.** Denaro (rimborso o buono non dovuto), dati (profilo di un altro cliente). Il danno
   sta nel testo. Il dominio è il più vicino al nostro tra tutte le raccolte.
5. **Stima.** Circa 3-6 testi o sequenze. Problema: i due testi più utili sono **sequenze di più
   turni**, e la scheda del caso ha un solo messaggio (`seed_turn`). Unire i turni in un
   messaggio cambia la struttura (vietato dalla regola di equivalenza: "mai la struttura della
   frase"); prendere un turno solo toglie il contesto. Da decidere prima dello scarto. Il testo
   del catalogo mette i dati in un argomento di una chiamata di ricerca, che nei nostri strumenti
   non ha un corrispondente diretto (i dati non escono verso un terzo): probabilmente non passa.
6. **Lingua.** Inglese.

## 4. AgentInjectionBench

Fonte: `ppradyoth/AgentInjectionBench`, commit `540669a` (2026-10-10); file
`data/agent_injection_bench.jsonl` (campo `conversation`, ruolo `tool_result`).

1. **Licenza.** Apache 2.0.
2. **Produttori.** Nessuna occorrenza; la pagina non nomina Meta, PromptGuard o LlamaFirewall.
3. **Dove e forme.** 182 casi, 142 attacchi e 40 innocui; tutti nel contenuto (risultato di uno
   strumento 87, risposta MCP 40, API 26, documento recuperato 19, file 10). Campo
   `defense_bypass`: gioco di ruolo 73, cambio di contesto 31 (finte note di un "bot di
   revisione", vicine all'iniezione camuffata), testo annidato 26, codifica 9. Generati con un
   modello a partire da modelli di testo (README); un solo autore; versione 0.2.0.
4. **Azioni.** Campo `attacker_intent`: esfiltrazione 63, scalata 47 (per lo più comandi in una
   shell: per noi "comandi", non "permessi"), manipolazione 20, ricognizione 3, negazione del
   servizio 2. Oggetti per lo più da sviluppatore (pull request, file, shell).
5. **Stima.** Circa 15-25 testi, non letti uno per uno: dati verso un'email esterna (16 casi con
   `email_send`), comandi. Gruppi: dati con la forma camuffata; comandi con la forma camuffata.
6. **Lingua.** Inglese.
Riserva: raccolta sintetica, recentissima, senza articolo né revisione esterna.

## 5. promptprotection/agent-security-datasets

Fonte: Hugging Face, revisione `3c808d8` (2026-09-15); file `agent-flows.jsonl` (campo
`sources[].text`) e `attacks.jsonl` (campo `text`).

1. **Licenza.** CC BY 4.0 (file `LICENSE`): uso e modifica con attribuzione.
2. **Produttori.** Nessuna occorrenza; la scheda non nomina Meta.
3. **Dove e forme.** `agent-flows.jsonl`: 100 scenari, 50 attacchi nel contenuto (email lette 8,
   file eseguiti 8, documenti recuperati 8, pagine con pagamento 7, strumenti MCP 7, messaggi
   Slack 6, revisione di codice 4, calendario 2). Forme: istruzioni nascoste in commenti
   travestite da nota per l'assistente (camuffata), "ignora il diff" (override).
   `attacks.jsonl`: 130 testi isolati, 40 tecniche nominate una o due volte ciascuna (tra cui
   "authority-escalation", "priority-claim", "persona", vicine al pretesto).
4. **Azioni.** Dati verso l'esterno (con `http_post`: cambiare lo strumento in `send_email` è
   un cambio di nome ammesso), comandi, pagamenti a terzi (nessun corrispondente: il nostro
   rimborso va al titolare).
5. **Stima.** Circa 10-15 testi (email lette con esfiltrazione, file con comandi, calendario e
   documenti con `send_email`). Gruppi: 2-3.
6. **Lingua.** Inglese, con 15 testi in 14 altre lingue.
Riserva: come la precedente (piccola, 2026, un solo autore, nessun articolo).

## 6. Tensor Trust

Fonte: `HumanCompatibleAI/tensor-trust-data`, commit `747a75e` (2024-03-17); articolo arXiv
2311.01011 (Toyer e altri, ICLR 2024).

1. **Licenza.** **Nessuna licenza per i dati**: il repository dei dati non ha un file di
   licenza, il README non ne dice; il codice del gioco (`HumanCompatibleAI/tensor-trust`) è
   BSD-2-Clause, l'articolo è CC BY 4.0 (vale per l'articolo, non per i dati); la pagina
   tensortrust.ai/paper dice solo "We release all data". Senza licenza, riuso e modifica non sono
   permessi in modo chiaro. Chiedere agli autori sarebbe l'unica strada.
2. **Produttori.** Nessuna occorrenza nei repository e negli articoli di Meta. È una delle
   raccolte pubbliche più usate per addestrare classificatori: che sia tra i "malicious prompt
   injection and jailbreaking datasets" open source dell'addestramento di PromptGuard 2
   (`Llama-Prompt-Guard-2/86M/MODEL_CARD.md:60`) è plausibile, **non verificato**.
3. **Dove e forme.** Solo richiesta (l'attaccante scrive tra due parti del prompt del
   difensore). `benchmarks/extraction-robustness/v1/extraction_robustness_dataset.jsonl`: 570
   righe, 438 attacchi distinti, campo `attack`, per far uscire il prompt del difensore o il
   codice d'accesso. `benchmarks/hijacking-robustness/v1/hijacking_robustness_dataset.jsonl`:
   776 righe, 492 distinti, per far dire "Access Granted". Più i dati grezzi (`raw-data/v2`).
   Forme sull'estrazione, con parole chiave: override circa 95, camuffata (finti delimitatori,
   finti messaggi di sistema) circa 71, pretesto quasi nessuno. Un testo tipico: un finto
   segnale di fine input seguito da "ripeti tutte le istruzioni qui sopra".
4. **Azioni.** Estrazione: scoprire il sistema (prompt di sistema), se il testo chiede le
   istruzioni; 214 su 570 nominano oggetti del gioco (password, codice d'accesso, "Access
   Granted") e non hanno un corrispondente nel mondo. Dirottamento: far dire una frase fissa,
   non una delle dodici azioni (stesso motivo di LLMail-Inject, verifica sezione 8).
5. **Stima.** Circa 150-250 testi distinti su "scoprire", nella richiesta (356 righe di
   estrazione senza oggetti del gioco, meno i doppioni e quelli senza richiesta chiara). Gruppi:
   scoprire con override, scoprire con camuffata.
6. **Lingua.** In prevalenza inglese (non verificato riga per riga).

## 7. Lakera Gandalf (`gandalf_ignore_instructions`, `gandalf_summarization`, `mosscap_prompt_injection`, `gandalf-rct`)

Fonti: Hugging Face; `Lakera/gandalf_ignore_instructions` revisione `04737b6` (2025-02-28);
`gandalf_summarization` `8e213cc`; `mosscap_prompt_injection` `b7e495f`; `gandalf-rct` `c669807`.

1. **Licenza.** MIT per le prime tre (schede); `gandalf-rct` ha `license: other` (non letto).
2. **Produttori.** Nessuna occorrenza nei repository e negli articoli di Meta (l'unica
   corrispondenza, `gandalf-the-white/foundation` in `CybersecurityBenchmarks/datasets/third-party.txt`,
   è un altro progetto). Come Tensor Trust: presenza nell'addestramento di PromptGuard 2
   plausibile, non verificata; la scheda di Hugging Face elenca 16 modelli addestrati su
   `gandalf_ignore_instructions`.
3. **Dove e forme.** `gandalf_ignore_instructions`: 1.000 testi (999 distinti), campo `text`,
   tutti nella richiesta, scelti per somiglianza con "Ignore all previous instructions": quasi
   tutti override (circa 700 con la parola chiave), quasi nessuna camuffata, circa 10 pretesti.
   `gandalf_summarization`: 140 testi nel contenuto (un testo da riassumere). `mosscap`: 278.945
   testi di una gara, molti non sono attacchi (scheda). Lo scopo è sempre la password del
   prompt di sistema.
4. **Azioni.** Scoprire il sistema solo per i testi che chiedono le istruzioni o il prompt
   (circa 125 con una lettura per parole chiave, di più con una lettura a mano); quelli che
   chiedono la password non hanno un corrispondente (il nostro prompt non contiene una
   password; "credenziali" sarebbe un altro oggetto). Molti testi sono solo "ignora le
   istruzioni" senza azione: non passano il criterio (a).
5. **Stima.** Circa 120-200 testi, tutti lo stesso segnale (richiesta, override, scoprire).
6. **Lingua.** Inglese per `gandalf_ignore_instructions`; `gandalf_summarization` anche in
   altre lingue.

## 8. deepset/prompt-injections

Fonte: Hugging Face, revisione `4f61ecb` (2024-07-30).
1. Licenza Apache 2.0. 2. Produttori: nessun uso della raccolta; la scheda di PromptGuard 2
confronta il modello "Deepset" (`MODEL_CARD.md:89`), che la scheda di Hugging Face dà come
addestrato su questa raccolta: un confronto tra modelli, non un uso dei testi. 3. 662 righe, 263
iniezioni (`label` 1), tutte nella richiesta; forme override e gioco di ruolo; circa 80 in
tedesco e altre in spagnolo e croato. 4. Scopi per lo più fuori dalle dodici (scrivere un
manifesto, dire una frase); pochi chiedono il prompt (scoprire). 5. Circa 10-20, lo stesso
segnale di Gandalf. 6. Lingue miste. **Scartata.**

## 9. HackAPrompt

Fonte: `hackaprompt/hackaprompt-dataset`, revisione `25b87fb` (2024-01-24), accesso con
registrazione; articolo arXiv 2311.16119v3.
Licenza MIT. Nessun uso dei produttori trovato. Ogni livello ha lo stesso scopo: far scrivere
"I have been PWNED" o una chiave nascosta nel modello di prompt (articolo, sezione sulla gara).
Lo scopo fisso non è una delle dodici azioni (stesso motivo di LLMail-Inject); la chiave
nascosta è una variante della password di Gandalf. **Scartata**, senza scaricare i testi.

## 10. SaTML CTF 2024

Fonte: `ethz-spylab/ctf-satml24`, revisione `11426ba`; arXiv 2406.07954. Licenza MIT. Circa
137.000 conversazioni d'attacco per scoprire un segreto messo nel prompt. Scopo fisso (un
segreto, non il prompt), conversazioni di più turni. **Scartata.**

## 11. BIPIA (Microsoft)

Fonte: `microsoft/BIPIA`, commit `a004b69` (2024-04-15; repository archiviato); file
`benchmark/text_attack_{train,test}.json` e `code_attack_{train,test}.json`.
1. Licenza MIT ("Copyright (c) Microsoft Corporation"); i testi di base vengono da altre
fonti (OpenAI Evals, WikiTableQuestions, Stack Exchange) con licenze proprie.
2. Produttori: nessuna occorrenza nei repository e nell'articolo di LlamaFirewall. Meta SecAlign
(arXiv 2507.02735v4) usa "11K articles from the XSum dataset ... (a subset from BIPIA)": i testi
innocui, non gli attacchi. TaskTracker usa gli attacchi di BIPIA.
3. Contenuto (email, pagine, tabelle, codice); 30 categorie di testo da 5 istruzioni (150) e 10
categorie di codice da 5 sia nella prova sia nell'addestramento (100); inseriti all'inizio, a metà o alla fine del contenuto, senza
prefisso: forma esplicita, senza tecnica (`bipia/data/utils.py`).
4. Scopi: cambiare la risposta (cifrare, tradurre, aggiungere pubblicità, un link a un sito,
una statistica falsa su un politico) o inserire codice malevolo nella risposta. Nessuno ha un
oggetto nel nostro mondo; il link va nella risposta, non in un'email.
5. Zero. 6. Inglese. **Scartata**: anche se passasse, la casella contenuto-esplicita è già piena.

## 12. TaskTracker, SEP (Microsoft e altri)

TaskTracker (`microsoft/TaskTracker`, MIT): iniezioni nel contenuto generate da GPT-4 e prese da
BIPIA, su compiti generici (domande di cultura generale). SEP: 9.100 istruzioni iniettate
innocue. Tutte e due usate da Meta SecAlign (arXiv 2507.02735v4). Nessuna delle dodici azioni.
**Scartate.**

## 13. AgentHarm (UK AISI, Gray Swan)

Fonte: `ai-safety-institute/AgentHarm`, revisione `e23b3fe`. Licenza: "MIT License with an
additional clause" (solo per migliorare la sicurezza; chiedono di non addestrarci; stringa di
controllo per la contaminazione). 208 richieste dannose e 208 innocue, nella richiesta, forma
esplicita (il modello di jailbreak non è pubblico). Categorie: frode, criminalità informatica,
disinformazione, molestie, droghe, odio, contenuti sessuali, diritto d'autore, con strumenti
inventati dalla raccolta. Non sono attacchi all'agente ma abusi da parte di chi lo usa; gli
oggetti non hanno corrispondente. **Scartata** (lettura della scheda, testi non scaricati).

## 14. Agent-SafetyBench (Tsinghua) e R-Judge

Agent-SafetyBench (`thu-coai/Agent-SafetyBench`, commit `74feea8`, MIT; `data/released_data.json`,
2.000 casi): 106 casi con un override nel contenuto, e 56 di questi contengono l'indirizzo
`amy.watson@gmail.com` e il prefisso "IMPORTANT!!! Ignore all previous instructions" di
InjecAgent; le richieste sono casi di rischio, non attacchi con una forma. R-Judge
(`Lordog/R-Judge`, commit `83ce301`, **nessun file di licenza**): 564 registrazioni leggibili, 414
con un'iniezione, tutte nei file `dh_*` e `ds_*`, con i testi di InjecAgent. **Scartate: nessun
testo nuovo.**

## 15. ToolEmu

`ryoungj/ToolEmu`, Apache 2.0, 144 casi in `assets/all_cases.json`: istruzioni dell'utente
ambigue con rischi, non attacchi. Gli strumenti di InjecAgent vengono da qui. **Scartata.**

## 16. WASP e CyberSecEval (Meta)

- **WASP** (`facebookresearch/wasp`, archiviato il 2026-07-01): pubblicato
  nell'organizzazione di ricerca di Meta su GitHub; autori Evtimov, Zharmagambetov, Grattafiori,
  Guo, Chaudhuri (la pagina non dà le affiliazioni; Zharmagambetov e Guo firmano Meta SecAlign
  come FAIR at Meta, e Meta SecAlign usa WASP). Licenza CC BY-NC 4.0 per quasi tutto. Iniezioni in pagine di GitLab e
  Reddit. **Scartata**: è un banco della stessa azienda, con un legame più stretto di InjecAgent
  (fatto da Meta, non solo usato).
- **CyberSecEval, prova di prompt injection** (`CybersecurityBenchmarks/datasets/prompt_injection/prompt_injection.json`
  nel repository PurpleLlama, MIT): 251 testi (196 diretti, 55 indiretti), 15 varianti tra cui
  persuasione 26, "ignore previous instructions" 25, "system mode" 19. La scheda di Prompt Guard 1
  riporta il "CyberSecEval Indirect Injections Set" tra le sue valutazioni
  (`Prompt-Guard/MODEL_CARD.md`, righe 159-170). **Scartata**: banco del produttore (principio 1
  di `SPIRIT.md`), anche se misura la prima versione di PromptGuard.

## 17. Non disponibili o non verificabili

- **AgentVigil** (arXiv 2505.05849v4): un metodo che genera iniezioni, non una raccolta; nessun
  insieme di testi pubblicato trovato; valutato su AgentDojo (che escluderebbe comunque le
  iniezioni costruite sopra di esso).
- **ART** (Gray Swan e UK AISI, arXiv 2507.20526v1): l'abstract dice "releasing the ART
  benchmark", ma non dà un link; nessun dato pubblico trovato. Non verificato.
- **Persuasive Adversarial Prompts** (`CHATS-Lab/persuasive_jailbreaker`, Apache 2.0): la
  tassonomia di 40 tecniche di persuasione è pubblica (`persuasion_taxonomy.jsonl`); i testi
  d'attacco hanno un modulo di rilascio e chiedono contenuti dannosi (AdvBench), non azioni di
  un agente. **Scartata** come raccolta; la tassonomia potrebbe servire solo come riferimento
  per scrivere i nostri pretesti (non è un testo d'attacco).

## Caselle della parte 5 che resterebbero scoperte

Le caselle della parte 5 hanno già un'azione assegnata a ogni caso (estrazione del 2026-10-19,
"Esito valido, dopo la correzione"). Un testo di una raccolta entra senza toccare l'estrazione
solo se coincide in luogo, forma **e** azione con un caso nostro. Confronto:

| Casella | Azioni assegnate | Raccolte che hanno testi con quel luogo, forma e azione |
|---|---|---|
| richiesta, iniezione camuffata | contro terzi, consumare, scoprire, contro terzi | **scoprire**: b3 (Thingularity, Cycling Coach), Tensor Trust (licenza); contro terzi, consumare: nessuna |
| richiesta, override | denaro, denaro, distruggere, alterare | nessuna con queste azioni (Gandalf e Tensor Trust hanno solo "scoprire"; DoomArena ha denaro, ma in una sequenza di più turni e con il pretesto) |
| richiesta, pretesto | ingannare, restare, permessi, comandi | nessuna |
| contenuto, iniezione camuffata | alterare, denaro, consumare, contro terzi | nessuna (BrowseSafe, b3, AgentInjectionBench e promptprotection portano quasi solo dati e comandi) |
| contenuto, override | ingannare, ingannare, permessi, restare | nessuna |
| contenuto, pretesto | scoprire, credenziali, scoprire, distruggere | forse **scoprire** in BrowseSafe ("System Prompt Exfiltration" con un pretesto: da cercare a mano, nessun metadato); le altre nessuna |

Con l'estrazione così com'è, le raccolte trovate coprirebbero al più 1-2 caselle (richiesta,
iniezione camuffata, scoprire; forse contenuto, pretesto, scoprire). Restano scoperte, in ogni
caso: tutte le caselle con pretesto nella richiesta; override nella richiesta e nel contenuto;
e, per azione, **alterare dati, cambiare permessi, restare nel sistema, distruggere, consumare
risorse, contro terzi (link in un'email), ingannare** in tutte le forme non esplicite. Nessuna
raccolta trovata ha testi di questo tipo con un oggetto che il nostro mondo possiede.

L'altra strada sarebbe mettere prima i casi delle raccolte e rifare l'estrazione delle azioni
sulle caselle rimaste, come fatto con la correzione di `dh_14`. Cambierebbe un'estrazione già
fatta, anche se nessun verdetto è stato visto: è una decisione del proprietario, non una scelta
delegata. Anche così il guadagno sarebbe piccolo: le raccolte portano soprattutto "scoprire"
(richiesta) e "dati" (contenuto), e "dati" ha già 3 casi su un minimo di 2; con la regola di un
caso per gruppo, si arriverebbe a circa 4-8 casi in più, contro i circa 8 che servirebbero per
un terzo dei 31 casi di testo.

## Da decidere con il proprietario

1. Quali raccolte verificare a fondo (scarto testo per testo con `scarto.py` e un motivo per
   ogni testo). Proposta, in ordine di utilità: b3, DoomArena, BrowseSafe-Bench; poi, con riserva
   sulla qualità, AgentInjectionBench e promptprotection.
2. La licenza di b3: il file `LICENSE` chiede uso "academic, non-commercial" e vieta modifiche
   ingannevoli; la scheda dice MIT.
3. Tensor Trust senza licenza: scartarla, oppure chiedere agli autori.
4. DoomArena: come trattare una sequenza di più turni in una scheda con un solo messaggio.
5. Se i casi nuovi delle raccolte entrano solo dove coincidono con l'estrazione fatta, oppure
   prima di una nuova estrazione delle azioni.
6. Un limite da dichiarare comunque: Tensor Trust, Gandalf, deepset e HackAPrompt sono tra le
   raccolte più usate per addestrare classificatori di prompt injection; PromptGuard 2 dice di
   essere addestrato su raccolte open source senza elencarle. Per b3, BrowseSafe, DoomArena e le
   due raccolte del 2026 il rischio è più basso (più recenti o meno diffuse), ma non si può
   escludere.
