# Lettura a freddo del 18 novembre 2026 (due revisori senza memoria del lavoro)

Scelta dal proprietario il 18 novembre (alternativa al secondo giro esterno), con la skill `code-review` in due assi. Punto fisso: `3da9813`
(il commit prima che nascesse `analisi_v3.py`); 15 commit, file `src` e `tests` (non `docs/research/2026-11-17-controllo-finale/`).
Spec = piano `docs/design/2026-10-11-piano-run-v3.md`, `2026-11-05-limiti-dichiarati-run-v3.md`, `SPIRIT.md`. Standard = `SPIRIT.md`, `CONTEXT.md`,
`docs/agents/*.md` più gli odori di Fowler. I revisori avevano solo lettura. Un solo giro; ogni punto va verificato prima di accoglierlo.
373 test dei quattro file verdi: la lettura a freddo mostra che il verde prova meno di quanto sembra.

Stato di verifica: **V** = riletto da Claude su codice e piano (18 novembre); **R** = riportato dal revisore, da verificare prima di toccarlo.

## Il limite della matrice di conformità (ammesso)
`tests/toy_agent/conformita_piano.py` controlla che la citazione del piano esista e che i test elencati esistano; NON controlla che quei test
fallirebbero se la regola fosse rotta. Esempio (V): il piano fissa «4 casi non bastano a dire che…», il codice scrive «Pochi casi non bastano…»
(`analisi_v3.py:509`) e la voce passa. Voci non provate secondo il revisore (R): frase dei benigni con ticket, «mai sessioni in più di tre per caso»,
«viste sempre in fondo» (la sezione dei limiti sta dopo), «mai mescolare casi e sessioni» (si guardano solo i titoli), «divisi per luogo»,
«nessuna classifica», rifiuto che non toglie il confronto con l'intento, nome debole di aidr, e la completezza (una voce con molte regole passa con una citazione).

## Asse standard
1. (V) Quattro moduli importati da moduli dell'elenco A ma non nell'elenco: `orchestrator.py`, `halvard.py`, `schema.py`, `run_case.py`. SPIRIT principio 6: per criterio, non per elenco.
2. (V) `check_conditions.check_generations` passa a vuoto con sessione senza `call_log` o cartella vuota.
3. (V) `risultati_falsi_allarmi`: il totale dei benigni con ticket conta solo i casi con sessioni, può scendere sotto 4 senza dirlo.
4. (V) `_pct` arrotonda al più vicino: il limite superiore 28,49% si stampa «fino a 28%» (la quota senza verdetto invece sale).
5. (V) `frase_zero` non usa `casi()`: «0 riconosciuti su 1 casi».
6. (V) `elenco_a.py` (righe 78, 85, 185-189, 288-289) stampa il messaggio grezzo di docker e git: regola di `implementer.md`/`reviewer.md`.
7. (R, rinviati per Pareto) odori: duplicazione fra `frase_apertura` e `analizza`; nome `casi` doppio; stringhe al posto di tipi; `verifica` cattura ogni `ValueError`; `file_copiati` non gestisce `COPY` con `\`, liste JSON, glob (i Dockerfile attuali non li hanno).

## Asse specifica
1. (V) `_estremi` ignora i casi attesi senza nessuna sessione; `invariati` confronta solo i «sì».
2. (V) I benigni non sono mai letti per il danno (`analisi_v3.py` righe 705-706); il piano: «Elenco comune su ogni sessione, benigni compresi» e, nelle sfere, «due letture» per un benigno con danno.
3. (V) Le sessioni fuori sfera sono scartate (righe 718-720): la selettività non compare, il piano dice «restano accanto, mai in testa».
4. (V) Frase fissa dei benigni con ticket cambiata (vedi sopra).
5. (V, da leggere nel piano) La frase d'apertura dice solo «oltre il 10%» e non porta i due estremi (stanno nella sezione 1 del rapporto): il piano dice «numero in testa… non si legge senza i due estremi».
6. (R) La soglia «non vista» (almeno 3 casi) conta anche i casi senza verdetto: con 3 casi, 2 senza verdetto e 1 «no» esce «0 riconosciuti su 1 casi… fino a 98%».
7. (R) Tre sessioni per caso non imposte: cinque sessioni dello stesso caso sono contate in silenzio.
8. (R) Nome e limiti di aidr più poveri di quelli del piano (riga ~971; temperatura, CodeShield, lettura a mano di Claude, revisore tarato su di noi, benigni più brevi).
9. (R) Danno vero: elenca solo i casi riconosciuti, mai quelli con danno non riconosciuto (11 novembre, punto 5).
10. (R) Accordo tra lettura automatica e revisore e disaccordi decisi dal proprietario non compaiono (11 novembre, punto 6): si stampa solo l'impronta.
11. (R) Tabelle delle viste senza pari e senza verdetto per riga e senza intervallo (12 novembre 4a/b, 13.2); la tabella della sezione 2 mette casi e sessioni insieme (12 novembre 4e); limiti dopo le viste e non nel JSON.
12. (R) Oltre lo spec: formato inventato di `letture-chiuse.json` (può sovrascrivere la lettura di qualunque sessione); un solo verdetto valido su due scartato come «nessun verdetto» (riga ~565).

## Decisione del proprietario (18 novembre)
«Procedi così»: (1) salvare questa situazione con un commit; (2) correggere nell'ordine: elenco A per criterio (chiusura degli import) più test;
controlli e frasi; conteggi (verificando ogni punto sul piano prima di toccarlo); rinforzo della matrice con una nota su cosa prova e cosa no;
(3) verificare e committare. Arrotondamento del limite superiore per eccesso: scelta di Claude, coerente con la quota senza verdetto.
Nessun push su `origin`.

## Esito delle correzioni (18 novembre, commit ca42400, 98a98f4, b8e65d4 e il successivo)
Corretti e provati (suite 1481 passati, 8 saltati): standard 1-6; specifica 1 (estremi con i casi senza sessione, conteggi interi), 4 (frase fissa), 5 (estremi nella frase
d'apertura oltre il 10%), 7 (stop con più di tre sessioni per caso), 9 (casi con danno non riconosciuti), 10 in parte (frase sull'accordo), 11 in parte (colonne «A pari» e
«Senza verdetto» nelle viste). Elenco A: ora 127 file con i quattro moduli.
Lasciati com'erano, con la ragione: «fino a 28%» invece di 28,49% (la frase fissa del piano dice «fino a X%», senza «circa»; il piano scrive i suoi numeri 16, 71, 60 arrotondati
al più vicino: arrotondare per eccesso li contraddirebbe); soglia «non vista» che conta i casi senza verdetto (il piano dice «almeno 3 casi in ambito»); nome di aidr (già «come
configurato in questo test»); odori di codice e casi teorici dei Dockerfile (rinviati per Pareto).
Ancora aperti, da decidere con il proprietario: lettura del danno sui benigni; selettività (sessioni fuori sfera); elenco dei disaccordi decisi con il verso (manca un formato);
tensione 12 novembre 4e / 13 punto 1 (unità nella stessa tabella); limiti stampati più corti di quelli del piano; viste e limiti: i limiti stanno dopo le viste.
