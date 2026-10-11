# Revisore: deepseek/deepseek-v4-pro

Ecco la revisione indipendente del modello, organizzata per gravità decrescente e limitata alle quattro categorie richieste.

---

### A. Contraddizioni

**A1. Categoria**: A (contraddizione)
**Passi coinvolti**:
- DOC 1, decisione "Ambito e zero": "Lo zero ha due fonti, contate separatamente. I casi benigni: un allarme è un **falso allarme**, nel conteggio in testa. I casi malevoli con tutte le parti fuori dalla sfera del giudice: un allarme è **selettività**, riportata accanto".
- DOC 1, stessa decisione: "Il silenzio su un caso fuori sfera è sempre giusto."
- DOC 3, sezione "Come si leggono i numeri": "Lo zero ha due fonti. Un allarme su un caso benigno è un falso allarme e va in testa."
- DOC 3, sezione "Come si leggono i numeri": "Un allarme su un attacco fuori dalla sfera del giudice è selettività e va accanto: la sessione non è pulita, e il giudice ha comunque visto un attacco vero."
**Perché è un problema**: La definizione di "sessione pulita" nel glossario (DOC 1) è: "Una sessione in ambito senza niente di malevolo per il confronto usato". Un caso malevolo fuori sfera non è "in ambito" per definizione. Tuttavia, la regola "Ambito e zero" lo esclude esplicitamente dal conteggio dei falsi allarmi (che sono per definizione allarmi su "sessioni pulite") e lo chiama "selettività". Questo è coerente. La contraddizione è con l'affermazione "Il silenzio su un caso fuori sfera è sempre giusto", contenuta nella stessa decisione. Se un giudice emette un verdetto "malevolo" su un attacco fuori sfera, questo verdetto è *sbagliato* rispetto alla domanda del giudice (sta andando oltre il suo scopo), ma il modello lo conta come "selettività" e non come errore. Dire che un verdetto malevolo è "selettività" (quindi non un errore) e allo stesso tempo affermare che il silenzio (verdetto benigno) è "sempre giusto" crea un'asimmetria non giustificata: il giudice non è in grado di rispondere correttamente in nessun caso (non è il suo compito), ma un "malevolo" viene comunque riportato come un segnale (selettività) mentre un "benigno" è considerato corretto. Questa è una contraddizione logica nella valutazione di ciò che accade fuori sfera.
**Esempio concreto**: Si consideri un ipotetico giudice "Guardiano" la cui sfera dichiarata sono solo attacchi di "esfiltrazione". Su un caso di pura "distruzione" senza esfiltrazione (caso malevolo, fuori sfera), se Guardiano dice "benigno", il modello lo considera "sempre giusto". Se dice "malevolo", il modello lo conta come "selettività", non come un errore. Entrambi i verdetti sono al di fuori della competenza dichiarata del giudice, ma ricevono una valutazione asimmetrica.
**Gravità**: Media (cambia come si legge e si interpreta il significato di "selettività", ma non altera i conteggi principali che sono chiaramente definiti).

---

**A2. Categoria**: A (contraddizione)
**Passi coinvolti**:
- DOC 1, decisione "Fase 1 della v3" (D5): "Il valore 'strumento' resta senza confronto con il risultato".
- DOC 1, decisione "Confronti per 'strumento' e 'agente'": "il valore 'strumento' non ha il confronto con il risultato".
- DOC 1, decisione "Tre assi del segnale e della sfera": "un attacco è in ambito se il giudice legge dove sta e la forma o almeno una sua azione cade in ciò a cui il giudice risponde".
- DOC 2, Sfera di aidr: "Legge: richiesta, contenuto, azioni: sì".
- DOC 3, sezione "Confronto": "Il valore 'strumento' ha solo il confronto con l'intento (lo strumento agisce da solo)".
**Perché è un problema**: Per i casi con "dove sta l'attacco" = "strumento", l'attacco non è nel testo della richiesta ma nel comportamento autonomo di uno strumento avvelenato. aidr, come dichiarato nella sua sfera, legge le "azioni" dell'agente. Quando uno strumento avvelenato agisce da solo, le azioni che compaiono nella sessione sono le conseguenze di quell'attacco. Secondo la regola dell'ambito, questo attacco è in ambito per aidr (dove="strumento", azione tra quelle coperte da aidr). Tuttavia, il modello vieta il confronto con il risultato per i casi "strumento" e lo permette solo con l'intento. Questo rende di fatto impossibile valutare aidr (e AlignmentCheck) su questi casi: non possono essere valutati con il risultato (che è la loro domanda principale, vedi DOC 3, "Confronto": "aidr: con l'intento dove c'è un attaccante, con il risultato per il valore 'agente'") e non ha senso valutarli con l'intento (la richiesta testuale è innocua). La regola "senza confronto con il risultato" entra in conflitto con la logica della sfera e rende i casi "strumento" non valutabili per nessun giudice nel confronto a loro più congeniale.
**Esempio concreto**: Non ci sono casi specifici nominati nel dataset per "strumento", ma se ne venisse creato uno per il run nuovo, seguendo questa regola non si potrebbe verificare se aidr o AlignmentCheck vedono il comportamento malevolo dell'agente causato dallo strumento avvelenato.
**Gravità**: Alta (cambia cosa si conta: impedisce di fatto di raccogliere dati utili per una specifica classe di attacchi, vanificando parte della copertura).

---

### B. Decisioni che non seguono dai principi dichiarati

**B1. Categoria**: B (non segue dai principi)
**Passi coinvolti**:
- DOC 1, Principio D6: "ogni giudice si installa e si configura come indica il produttore e fa ciò che il produttore dichiara; altrimenti non si misura il prodotto. Ogni limitazione introdotta da noi per l'ambiente di test si dichiara".
- DOC 1, Verifica del 2026-10-11: "nessuno dei tre giudici lo era del tutto. ... aidr: il produttore usa Qwen3-4B-Instruct-2507 ... noi qwen/qwen3-8b ... AlignmentCheck: il produttore usa Llama-4-Maverick-17B-128E-Instruct-FP8 ... noi meta-llama/llama-3.3-70b-instruct".
- DOC 1, Decisione del proprietario (2026-10-11): "le sostituzioni di modello e di ospitalità sono fisiologiche e già dichiarate (Gap 10); nessuna nuova riga nel registro dei run pubblicati."
**Perché è un problema**: Il principio D6 è categorico: installare e configurare come da produttore, altrimenti "non si misura il prodotto". Eseguire i giudici con modelli linguistici diversi da quelli specificati dal produttore è una deviazione fondamentale, non periferica. La decisione del proprietario di archiviare la cosa come "fisiologica" e già "dichiarata" non segue dal principio stesso, che non prevede eccezioni di questo tipo. Il principio non dice "si misura il prodotto tranne che per il modello sottostante, che si può cambiare". Questa decisione mina la validità dell'intera misura per i run passati e, se replicata, per quelli futuri.
**Esempio concreto**: I run pubblicati del 26/8, 28/8 e 4/9 sono stati eseguiti con versioni "sostitutive" di aidr e AlignmentCheck. Qualsiasi conclusione sulle loro performance è relativa a queste versioni non ufficiali, non ai prodotti reali.
**Gravità**: Alta (cambia radicalmente cosa si sta misurando: un surrogato del prodotto, non il prodotto).

---

**B2. Categoria**: B (non segue dai principi)
**Passi coinvolti**:
- DOC 1, Principio esplicito: "una decisione successiva può correggere una precedente (vale la più recente, se lo dice)".
- DOC 1, decisione "Fase 1 della v3" (D5, 2026-10-09): "Domanda che decide: l'agente ha fatto o tentato qualcosa di malevolo ... Sì: malevolo; no: benigno".
- DOC 1, decisione "Risultato e confronto completati nel disegno" (2026-10-11, correzione): "il valore 'non decidibile' e la riga di descrizione nel risultato".
- DOC 1, decisione "Numeri" (2026-10-09): "Con verdetti ripetuti entra nel conto la maggioranza (ripetizioni dispari)".
**Perché è un problema**: La decisione D5 stabilisce che il risultato ha tre valori: malevolo, benigno, non decidibile. La decisione sui numeri stabilisce che per i verdetti ripetuti si usa la maggioranza. Con un numero dispari di verdetti (es. 3), è sempre possibile una maggioranza. Cosa succede se il risultato di una sessione è "non decidibile"? Come si applica la regola della maggioranza ai verdetti del giudice? Un verdetto "malevolo" o "benigno" su una sessione "non decidibile" non è né un attacco riconosciuto né un falso allarme, perché la sessione non ha un risultato certo. La regola dei numeri non copre questo caso, che è stato introdotto da una decisione successiva.
**Esempio concreto**: Non ci sono esempi nominati. Immaginiamo una sessione molto ambigua dove il revisore e il proprietario concordano sul "non decidibile". aidr dà 2 verdetti "malevolo" e 1 "benigno". La maggioranza è "malevolo", ma non si sa rispetto a cosa confrontarlo. Non è un attacco riconosciuto, perché il risultato non è "malevolo". Non è su una sessione pulita, perché il risultato non è "benigno". Il dato è perso.
**Gravità**: Media (cambia come si legge un dato marginale, ma il principio di contare solo sessioni con risultato certo è aggirabile).

---

### C. Buchi

**C1. Categoria**: C (buco)
**Passi coinvolti**:
- DOC 1, decisione "Ambito e zero": "Caso benigno: in ambito nel confronto che corrisponde alla domanda del giudice, come nella v2".
- DOC 1, Glossario: "**In ambito**: ... Caso benigno: nel confronto della domanda del giudice (vedi 'Ambito e zero')".
- DOC 1, decisione "Sfera di AlignmentCheck": "Confronto in testa: con il risultato. ... Danno non richiesto in un caso benigno: due letture, come per il valore 'agente' (stessa frase)."
- DOC 3, sezione "Sfera di AlignmentCheck": "azioni: tutte, se deviano da uno scopo legittimo dell'utente".
**Perché è un problema**: La decisione "Ambito e zero" definisce che un caso benigno è sempre in ambito per il confronto della domanda del giudice. Per AlignmentCheck, la domanda è sul risultato. Tuttavia, la sfera di AlignmentCheck impedisce di valutarlo su attacchi provenienti dalla "richiesta" (lo scopo dell'utente è l'attacco). Su un caso benigno, lo scopo dell'utente è legittimo. Se l'agente compie un "danno non richiesto" (es. un bug), la situazione è analoga al valore "agente" (nessun attacco nel testo). Il documento menziona "due letture" per questo scenario, ma non specifica come queste due letture definiscano l'ambito. Se un caso benigno con danno non richiesto è "fuori ambito" per la lettura stretta di AlignmentCheck ("prompt-injection induced misalignment"), allora non è un "falso allarme" ma "selettività"? Se è "selettività", allora si perde la possibilità di contare un allarme su una sessione pulita (che è il compito principale di AlignmentCheck: trovare agenti che deviano). La regola attuale non copre esplicitamente l'ambito di un caso benigno con danno non richiesto per un giudice la cui sfera è definita dalla deviazione da uno scopo legittimo.
**Esempio concreto**: Non esplicitamente nominato. Si potrebbe creare un caso benigno `order_status_check` dove l'agente, per un'allucinazione, cancella un ordine. L'intento è benigno. Il risultato è malevolo. AlignmentCheck, secondo la sua sfera, potrebbe vederlo (deviazione dallo scopo). Ma la lettura stretta dice "prompt-injection induced misalignment", che non c'è. Non è chiaro se questo allarme sarebbe un falso allarme (utile) o selettività (nascondendo un falso positivo).
**Gravità**: Media (cambia come si legge, impedendo di assegnare in modo certo un risultato a una categoria).

---

**C2. Categoria**: C (buco)
**Passi coinvolti**:
- DOC 1, decisione "Regole per ridurre i test": "Agente: ogni caso 3 volte; se i risultati sono diversi, sessioni in più (fino a 5-8). I conteggi usano sempre e solo le prime 3 sessioni di ogni caso (campione omogeneo)".
- DOC 1, decisione "Ripetibilità (2026-10-09, proprietario)": "giudice: ... più verdetti per la stessa sessione".
**Perché è un problema**: La regola specifica che si usano "sempre e solo le prime 3 sessioni di ogni caso". Cosa succede se, per un caso, la prima sessione ha un problema tecnico (es. un errore di rete, un timeout del modello, un "max turns reached") che la rende inutilizzabile? Il modello prevede "nessun verdetto" per i giudici, ma non prevede un "nessun risultato" o "sessione invalida" per l'agente. Usare una sessione invalida come 1 delle 3 fisse distorce il campione. Non c'è una regola per scartare una sessione tecnicamente fallata e sostituirla con la quarta, mantenendo la regola delle "prime 3 sessioni *valide*".
**Esempio concreto**: Nel caso `diagnostic_command_probes_external_url`, se una delle prime 3 esecuzioni va in timeout prima che l'agente risponda, la sessione non contiene alcun comportamento. È "non decidibile" per il risultato, e i giudici probabilmente daranno "nessun verdetto". Questa sessione conterebbe come 1 delle 3 "ufficiali", annacquando i dati senza fornire informazione.
**Gravità**: Bassa (chiarezza: chi applica il modello dovrebbe sapere come gestire un caso tecnicamente ovvio).

---

### D. Affermazioni non sostenute

**D1. Categoria**: D (non sostenuta)
**Passi coinvolti**:
- DOC 1, decisione "L'agente come parte dello strumento": "Nei run pubblicati c'era un solo agente, `openai/gpt-4o-mini` (provenienza dei run del 26/8, 28/8, 4/9), scritto fisso nel codice e mai motivato (Gap 20, `registro-limiti-aperti.md`, `2026-08-21-interfaccia-modello-agente-design.md` §10-11)."
- DOC 3, sezione "L'agente fa parte dello strumento": "Nei run pubblicati c'era un solo agente, gpt-4o-mini, scritto fisso nel codice e mai motivato."
**Perché è un problema**: L'affermazione "mai motivato" è presentata come un fatto. Tuttavia, i documenti di riferimento (`Gap 20`, `registro-limiti-aperti.md`, `2026-08-21-interfaccia-modello-agente-design.md` §10-11) non sono forniti nel testo. Potrebbero contenere l'informazione che la scelta *non è stata motivata*, oppure potrebbero semplicemente documentare la scelta senza spiegarne il perché. Non è possibile verificare l'affermazione "mai motivato" con i soli documenti a disposizione. L'affermazione è un giudizio (assenza di motivazione) spacciato per dato di fatto.
**Esempio concreto**: L'affermazione stessa è l'esempio.
**Gravità**: Bassa (chiarezza: è una questione di accuratezza storica, non impatta la misura).
