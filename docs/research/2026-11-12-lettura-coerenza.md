# Lettura di coerenza del piano (2026-11-12)

Letti per intero: parte 12, parte 13 con "Aggiunte dell'11 novembre", sezione "Run: comandi", pagina dei limiti (voci 1-28). Ogni numero è stato
ricalcolato dai file (schede, `ondate.json`, `ambito.json`, `condizioni_attese.json`, CSV degli esiti, codice), non cercato per parole.
L'impronta delle istruzioni del revisore è rimasta `e5940b4d...e936f` dopo le correzioni (le sezioni del piano che il revisore legge non sono state toccate).

## Tornava già
Limiti di tempo (8 + 2) x 30 s + 4 s = 304 s (codice: 30 s, 2 ripetizioni, pause 1 s e 3 s); numeri dell'ambito (PromptGuard 26/8, AlignmentCheck 19/16,
aidr 35/28/3); 58 schede = 37 malevole + 21 benigne; 19/20/19 casi nelle ondate; sessioni valide `completed` e `max_turns`; condizioni attese di agente,
giudici e revisore; "sembra un test" 30 su 37 e 4 su 21; 16 casi di contenuto con 12 nostri e 4 pubblici.

## Corretto (frasi superate o cifre che non tornavano)
| Dove | Problema | Correzione |
|---|---|---|
| Parte 12, elenco, punto 1 | I campioni di controllo non erano nell'elenco A, ma si ripetono a ogni ondata | Aggiunta `dataset_v3/controls/` |
| Parte 12, "Ordine", testa del piano, titolo e riga di approvazione | Parlavano ancora di una "revisione indipendente" con modelli di altre famiglie, sostituita l'11 novembre da specialisti, council e controllo finale esterno non indipendente. Inoltre l'ordine nelle note di ripartenza metteva l'approvazione prima dell'elenco delle impronte, il piano dopo: il controllo finale esamina l'elenco, quindi l'elenco viene prima | Riscritto l'ordine: elenco in bozza, controllo finale esterno, approvazione, push; se il controllo porta una correzione l'elenco si rifà |
| Parte 12, punto 6 e parte 13, "Run in tre ondate" | "Ogni casella ha 3 casi, un caso per casella a ondata": falso. Le 12 caselle hanno 3 o 4 casi, ogni ondata ne prende 1 o 2 (tutte coperte) | Testo allineato a `ondate.json` |
| Parte 12, punto "prima di congelare" | "Campioni da scrivere e congelare", già scritti; "immagine dell'agente da verificare", verificato | Frasi aggiornate |
| Parte 13, Aggiunte 7 | "Passo 0" e "circa 0,03 dollari" | "Passo 3b", circa 0,05 |
| Parte 13, 8b c) e limiti voce 23 | Coppie n12/n13 e n09/n20 "non riverificate" | Verificate sui testi (stesso sotto-agente con e senza pretesto; stessa conferma falsa sull'ordine FH-58251) |
| Parte 13, 8b d) e limiti voce 22 | "Mediana 59,5" attribuita ai 12 ticket nostri: è la mediana dei 16 insieme. Per i 12 nostri è 65,5 (intervallo 48-85 giusto) | Corretta in entrambi |
| Decisione dopo la prova generale (limite dichiarato) | "26 sessioni su 111 in quattro luoghi, quattro forme, dodici azioni": 29 su 111 in 13 casi, tre luoghi, quattro forme più "nessuna", otto azioni | Corretta |
| Parti 4 e 5 | 36 malevoli, circa 63 casi, circa 190 sessioni | Nota: 37 malevole + 21 benigne = 58 schede, 174 sessioni |
| Limiti voci 5, 8, 10 | "17 schede su 29" senza dire che sono le non "solo testo" (verificato: 17 su 29); "resta da ricostruire l'immagine di aidr" (ricostruita il 5 novembre); fornitore dei giudici "da aggiungere" (ora nel verdetto, `served_by`) | Chiarite o chiuse |

## Aperti noti, chiusi
- Differenza 26 contro 29: il file degli esiti dà 29 sessioni in 13 casi (ricalcolo con `read_session` identico al CSV su 174 sessioni su 174); il 26 è un conteggio del 26 ottobre con una lettura precedente. Vale il file.
- Tetto 0,10 dei controlli e ondata: non blocca (il tetto è un argomento di ogni chiamata); la spesa dei controlli (0,048) si somma nel registro. Un solo tetto di 2,00 sui giudici (vedi `2026-11-12-prova-comandi-nuovi/ESITO.md`).

## Non toccato, da sapere
- La voce 2 della pagina dei limiti dice "cinque correzioni" ma ne elenca sei: la sesta è dichiarata "del lettore e non di un caso". Non è un errore.
- Il registro `vendor_proxy.jsonl` della prova pesa 8 MB: decidere se committarlo.
- `confronta.py` e `test_confronta.py` sono nuovi/modificati: non committati.
