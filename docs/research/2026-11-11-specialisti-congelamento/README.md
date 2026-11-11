# Specialisti indipendenti prima del congelamento (definiti l'11 novembre 2026)

Tre specialisti, ognuno con una domanda sola, in `agenti/` (formato agente: nome, descrizione, strumenti in sola lettura, istruzioni):
- `specialista-metodologia`: la misura permette affermazioni vere? confini sviluppo/verifica, statistica, circolarità del revisore.
- `specialista-sicurezza`: il banco di prova misura ciò che dice? realismo, scorciatoie (30 malevoli su 37 sembrano un test, 4 benigni su 21), fedeltà delle sfere, rischi di pubblicazione.
- `specialista-integrita-tecnica`: dopo il congelamento il run è riproducibile? impronte, immagini, dipendenze, percorsi di perdita, comandi.

Il valore sta nella definizione (ambito, competenza, procedura, postura, formato di uscita, limiti già dichiarati da non ripetere). Il council
standard (scettico, rischio, pragmatico, utente) NON è fatto di specialisti: sono lenti generiche (27 righe ciascuna, uscita di una riga e poche frasi).

## Regole (le stesse del 2026-10-11)
Istruzioni salvate con le risposte; ogni punto si verifica nei documenti e nel codice prima di accoglierlo (un accordo tra modelli non
è prova); un solo giro; ognuno può chiedere al massimo un altro specialista, nominando un buco che nessuno copre. Si accoglie solo ciò che
cambia cosa si congela o come si formulano le affermazioni. Nessun file viene modificato dagli specialisti.

## Prova di confronto sul primo specialista (metodologia), scritta PRIMA di eseguire
Domanda del proprietario: il cambio di famiglia di modello è indispensabile, o conta solo la definizione?
- **Esecuzione interna:** sottoagente Claude con la definizione e accesso al repository (Read, Glob, Grep), modello più forte disponibile.
- **Esecuzione esterna:** `deepseek/deepseek-v3.2` via OpenRouter, fornitore fissato e registrato; la stessa definizione come istruzione di
  sistema e i documenti elencati nella definizione incollati per intero (circa 65 mila token); script di partenza
  `docs/research/2026-10-11-specialisti-piano/specialisti.py`. Spesa stimata sotto 0,2 dollari, tetto 1 dollaro.
- **Confondente da tenere presente:** l'interno vede il repository, l'esterno solo il testo. Ogni punto riporta "PROVA: solo testo" o un
  riferimento a file e riga: i punti che richiedono il codice si contano a parte.
- **Valutazione (io verifico ogni punto nei documenti e nel codice, e il proprietario rilegge la tabella):** ogni punto è confermato, in
  parte, falso, già dichiarato, oppure non verificabile. Si riportano per ciascuna esecuzione: punti confermati, falsi, già dichiarati,
  gravità dei confermati, punti confermati trovati solo da quell'esecuzione, punti che richiedevano il repository, costo, tempo.
- **Regola decisionale (scritta prima):** la famiglia diversa vale al controllo finale se l'esterno produce almeno un punto confermato
  di gravità "blocca il congelamento" o "cambia come si formulano le affermazioni" che l'interno non ha trovato. Altrimenti il controllo
  esterno resta facoltativo e, se omesso, si dichiara nella pagina dei limiti come "controllo finale non indipendente".
- Prima di valutare entrambe le esecuzioni non si applica nessuna correzione al testo.
