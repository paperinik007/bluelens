# Punti da verificare, per momento (19 novembre 2026)

Una spunta si mette solo dopo aver visto l'esito del comando, non prima. I comandi esatti stanno nella parte 12 del piano, «Run: comandi e stima di spesa». Un punto che fallisce non si corregge in silenzio: si classifica nel registro (`REGISTRO-DEL-RUN.md`).

## 1. Prima del push su `origin`
- [x] Piano e elenco A approvati per iscritto (`docs/design/2026-11-19-approvazione-del-proprietario.md`).
- [x] `elenco_a verifica` e `verifica-immagini --a-fondo`: nessuna differenza.
- [x] Impronta delle istruzioni del revisore invariata; nessuna chiave nei file e nella storia che esce.
- [x] `git status` senza file tracciati modificati; registro e documenti del run committati. (19 novembre: nessun file tracciato modificato; solo le bozze dell'elenco e i registri, volutamente non tracciati.)
- [x] Push di prova verso `origin` (non pubblica): avanzamento semplice da `e45f210` a `acfb859`, account `paperinik007`, repository pubblico, nessun file sopra 0,3 MB; suite 1502 passati; impronta del revisore invariata.
- [ ] Il proprietario dice «pubblica». Dopo il push: annotare la data e l'ora del push come prova di data.

## 2. Prima di ogni ondata
- [ ] Tetto di 3,5 dollari approvato per iscritto dal proprietario.
- [ ] Docker acceso, le tre immagini presenti, MAI `prune` né `down --rmi` fino alla fine del run.
- [ ] `elenco_a verifica` e `verifica-immagini`: nessuna differenza. Altrimenti si ferma l'ondata (classe B).
- [ ] Passo 3b, i controlli dei giudici sui cinque campioni: tutti i criteri superati. Un controllo fallito ferma l'ondata (classe B).

## 3. Durante l'ondata
- [ ] Agente: dopo 3 sessioni di fila in errore il comando si ferma da solo: lo decide il proprietario.
- [ ] `sposta_guasti` prima di ogni lettura; le sessioni guaste si rigenerano UNA volta; si contano a parte.
- [ ] `check_conditions` sulle sessioni e sulla versione datata (uscita 0), e sui verdetti. Uscita 1 ferma l'ondata.
- [ ] Verdetti in errore: rilancio al massimo due volte; poi «nessun verdetto». Terzo verdetto dove i primi due discordano.
- [ ] Registri dei giudici copiati prima di `down`, con l'impronta.

## 4. Prima di aprire i verdetti
- [ ] Letture a mano chiuse nel file delle letture chiuse, con `da_parte` nei disaccordi, e l'impronta registrata.
- [ ] Elenco B committato (impronta della cartella dei verdetti e delle letture) PRIMA di leggere un solo verdetto.
- [ ] Nessuno apre le etichette tra un'ondata e l'altra.

## 5. Dopo l'apertura: analisi
- [ ] `analisi_v3` su tutte le ondate: 14 file, nessun errore; i denominatori coincidono con la tabella dell'ambito (casi in ambito per giudice e lettura, 21 benigni).
- [ ] Sessioni senza verdetto sopra il 10%: si pubblica comunque, con la frase e i due casi estremi.
- [ ] Benigni con danno: il rapporto li nomina. Casi senza sessioni: nominati.
- [ ] Viste scritte dopo il congelamento: file nuovo, etichetta, commit nominato; mai nella frase d'apertura.

## 6. Prima di pubblicare
- [ ] I risultati vanno prima ai produttori, con un tempo per rispondere (parte 12, «Produttori prima della pubblicazione»).
- [ ] Si pubblicano sessioni, verdetti, letture e registri insieme all'analisi; i limiti accanto alle cifre.
- [ ] Il registro è completo: ogni scarto ha la sua voce. Le lezioni imparate della parte «dopo» sono scritte.
