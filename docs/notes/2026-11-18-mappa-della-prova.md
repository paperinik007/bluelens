# Mappa della prova: cosa si può contestare, dove si vede, quando si fissa (18 novembre 2026)

Una pagina per tenere il controllo del processo: raccolta dei risultati, verifica, riutilizzo. Non decide niente: rimanda alle decisioni del piano
(`docs/design/2026-10-11-piano-run-v3.md`, parti 12 e 13) e ai file che le provano. Nota di lavoro: il piano non si modifica dopo l'approvazione.

## Cosa si potrebbe contestare, e la risposta
| Contestazione | Dove si vede | Quando si fissa | Come si verifica |
|---|---|---|---|
| «Avete scelto casi e regole guardando i risultati» | casi, ambito, piano, programmi di analisi con i loro test, nell'elenco A | al congelamento: push su `origin` pubblico (la data la registra GitHub) | `python -m toy_agent.elenco_a verifica ELENCO`: nessuna differenza |
| «L'ambiente del run era diverso da quello dichiarato» | `dataset_v3/condizioni_attese.json`, registro delle versioni, identificativi delle immagini nell'elenco A | prima di ogni ondata | `check_conditions` (sessioni e verdetti) e `verifica-immagini` (passo 3) |
| «Chi ha deciso se l'agente ha fatto danno?» | `letture-chiuse.json`: per sessione `danno`, `motivo` e, nei disaccordi, `da_parte` (automatico, revisore, lettura a mano) | prima che i verdetti dei giudici si aprano; impronta nell'elenco B | il rapporto elenca i disaccordi con la parte; il programma controlla la coerenza con la lettura automatica |
| «I verdetti sono stati ritoccati dopo» | cartella dei verdetti | elenco B, commit prima dell'apertura (impronta della cartella e delle letture) | si ricalcola l'impronta |
| «I numeri non tornano» | rapporto Markdown e JSON dello stesso calcolo, per giudice e per lettura (14 file), con i limiti nel JSON | a fine run, a letture chiuse | `python -m toy_agent.analisi_v3 ONDATA… --schede … --ambito … --plausibilita … --out USCITA` (non sovrascrive mai) |
| «Avete aggiunto viste dopo aver visto i risultati» | viste scritte dopo il congelamento (minaccia, sessioni guaste, selettività), con l'etichetta «scritto dopo il congelamento», in file nuovi | definizione nel piano prima; codice dopo l'elenco B, con il commit nominato nel rapporto | la storia del repository pubblico |
| «Avete cambiato qualcosa dopo» | registro del run; un bug del programma di analisi si dichiara e si pubblicano le due uscite (12 novembre, punto 6); un cambio alla misura è un run nuovo | per tutta la durata | confronto tra le due uscite e i commit |
| «Quanto è costato e chi l'ha approvato» | tetto di 3,5 dollari per ondata, approvato prima di ognuna | prima di ogni ondata | registro della spesa |

## Chi fa cosa, nell'ordine
1. Claude: decisioni piccole che seguono regole già decise, registrate nel piano come «di Claude» (si approvano una volta sola, con il piano).
2. Claude: elenco A definitivo (Docker acceso) e micro giro sui due casi di controllo e sui campioni dei giudici, come il 12 novembre (nessun caso vero).
3. Proprietario: approvazione scritta del piano e dell'elenco; push su `origin`.
4. Run in tre ondate: Claude lancia i comandi nell'ordine del piano; il proprietario approva la spesa prima di ognuna e chiude le letture a mano con l'impronta prima dei giudici.
5. Analisi a fine run; poi le viste dopo il congelamento, in file nuovi.
6. Prima della pubblicazione: i risultati vanno ai produttori, con un tempo per rispondere («Produttori prima della pubblicazione»).

## Riutilizzo
- Dopo il run si pubblicano insieme all'analisi: sessioni, verdetti, letture, registri dei giudici (ora nel backup privato). Si pubblica il sorgente, non le immagini.
- «Riprodotto» vuol dire *ricalcolabile dai dati pubblicati*: il run non si può rieseguire identico (l'agente non ha temperatura né seme impostabili, i fornitori cambiano) e nessun documento lo promette.
- Un run nuovo non riusa le letture di un run già aperto; un run fermato si pubblica comunque con il motivo.

## Cosa questa mappa NON prova
- La prova di data è solo il push (nessuna marca di tempo esterna: rischio accettato).
- La lettura a mano la fa Claude Code, della stessa famiglia che ha costruito il banco; il revisore è tarato sulla nostra lettura.
- La matrice di conformità controlla che citazione e test esistano, non che i test fallirebbero con la regola rotta (le voci deboli portano la nota).
- Tre sessioni per caso e un solo run: i numeri valgono per casi costruiti come questi.
