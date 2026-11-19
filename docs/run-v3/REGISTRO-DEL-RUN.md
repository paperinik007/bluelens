# Registro del run v3

Cartella del run: dopo il push si scrive qui (e nelle cartelle delle ondate), non nei file dell'elenco A. Il piano (parte 12, «Dopo il congelamento» e «Run fermato») dice che ogni scarto dalle regole si scrive nel registro; questo è il registro.
Regole del registro: una voce si scrive PRIMA di agire quando si può, e comunque prima di rilanciare o di pubblicare. Una voce non si cancella e non si riscrive: una correzione è una voce nuova.

## Come classificare quello che succede
Quattro domande, in quest'ordine: (1) cambia ciò che viene misurato? → F. (2) cambia un numero già calcolato? → C o E. (3) aggiunge solo qualcosa di nuovo? → D. (4) era già previsto dalle regole? → A (o B se le regole non bastano).

| Classe | Cosa succede | Chi decide | Cosa si scrive e si pubblica | Cosa NON si fa |
|---|---|---|---|---|
| **A** ordinaria | guasto dell'ambiente coperto dalle regole (verdetto in errore, sessione guasta, nessun verdetto) | nessuno: si applicano le regole | una riga qui; i numeri stanno nel rapporto (rigenerate, errori, senza verdetto) | non si inventa un'altra regola |
| **B** run fermato | un guasto che le regole non coprono, o un controllo fallito (campioni, condizioni, immagini) | il proprietario, per iscritto, PRIMA di rilanciare | una voce con i fatti e la decisione; il run fermato si pubblica comunque con i conteggi parziali e il motivo; ogni versione avviata, anche interrotta, resta | non si corregge né si rifà in silenzio |
| **C** errata | un errore (bug) del programma di analisi | Claude propone, il proprietario conferma | la dichiarazione di errata (modello sotto) e le DUE uscite, prima e dopo, pubblicate affiancate, con il commit del programma | non si corregge in silenzio; la frase d'apertura non si tocca |
| **D** vista nuova | qualcosa non previsto, o previsto ma scritto dopo (minaccia, selettività, sessioni guaste con passo malevolo) | Claude | file NUOVO; etichetta «aggiunta dopo aver visto i risultati» (non prevista) o «scritto dopo il congelamento» (definita nel piano); commit nominato nel rapporto | non entra mai nella frase d'apertura |
| **E** regola di conteggio | il cambio di una regola che decide il risultato in testa (maggioranza, pari, denominatori, cosa conta come danno) | il proprietario, con la motivazione scritta | i numeri delle due versioni affiancati; la frase d'apertura resta quella congelata, salvo decisione scritta del proprietario che era sbagliata (non basta che fosse meno favorevole) | non si sceglie la regola guardando quale conviene |
| **F** run nuovo | qualunque cambio a ciò che entra nella misura: casi, giudici, condizioni, versione dell'agente, immagini, letture | il proprietario | il run vecchio resta pubblico com'è; il nuovo ha un'altra versione e NON riusa le letture di un run già aperto | non si «aggiusta» il run in corso |

## Modello di voce
```
### AAAA-MM-GG hh:mm, classe X, titolo breve
Fatti: cosa è successo, con nomi di file e comandi (niente interpretazioni).
Regola del piano applicata: parte e punto (o «nessuna: serve una decisione»).
Decisione e chi: ...  (per B, E, F: il proprietario, per iscritto, con la motivazione)
Effetto sui numeri: prima ... dopo ... (per C ed E sempre, affiancati)
File e commit coinvolti: ...
Cosa si pubblica: ...
```

## Modello di dichiarazione di errata (classe C)
«Il [data] abbiamo trovato che il programma di analisi [cosa faceva di sbagliato] invece di [cosa dice la regola, con citazione del piano]. Effetto: [quali numeri cambiano, di quanto]. Pubblichiamo le due uscite, prima e dopo, e il commit della correzione. I dati del run non sono stati modificati. La frase d'apertura [resta quella congelata / è stata decisa dal proprietario il ..., motivazione].»

## Voci
Nessuna voce. (Il run non è ancora iniziato.)
