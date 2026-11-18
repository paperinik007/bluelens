# Parere esterno sulla decisione «selettività» (18 novembre 2026, scritto PRIMA di lanciare)

Il proprietario deve scegliere come trattare la selettività (le sessioni dei casi malevoli fuori dalla sfera di un giudice, oggi scartate da
`analisi_v3.py`): ora, definizione nel piano e codice dopo il congelamento, oppure mai. Claude (autore del codice e del piano) raccomanda la strada 2.
Il proprietario, stanco, chiede un parere esterno: un modello di un'altra famiglia riceve l'analisi, verifica i fatti che il testo permette di
verificare, dice se concorda e perché.

## Regole dell'esecuzione
- Un solo giro, un solo modello (`qwen/qwen4-max`, fornitore Alibaba fissato, nessun ripiego), come il controllo finale del 17 novembre; caso peggiore
  circa 0,04 dollari (tetto 0,30). Nessun accesso al repository né strumenti: solo il testo di `esecuzione/input-utente.md`.
- Il pacchetto lo costruisce `prepara_parere.py` dal commit HEAD (estratti verbatim; `contenuto.json` ha numero di caratteri e SHA-256 di ogni parte).
  Non contiene nomi o dati personali.
- Il parere NON decide: ogni affermazione si verifica su documenti e codice prima di accoglierla (`VALUTAZIONE.md`, da scrivere dopo), e la decisione resta
  del proprietario. L'analisi di Claude dichiara il suo interesse (scrivere meno codice prima del congelamento).
- Esito: `esecuzione/output.md`, `risposta.json`, `meta.json` (modello, fornitore, token, costo).
