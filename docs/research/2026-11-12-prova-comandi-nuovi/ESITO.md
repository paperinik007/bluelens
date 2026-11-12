# Prova fino in fondo dei comandi del run (2026-11-12)

Cosa è: la sezione "Run: comandi e stima di spesa" del piano seguita alla lettera, con `ONDATA` = questa cartella, sulle due schede di controllo
della catena (`ctl_c1`, `ctl_c2`, 3 sessioni ciascuna) e sulle cinque sessioni di controllo dei giudici. Non è una misura: nessun caso vero.
Servizi: immagini già costruite, mai ricostruite (`detector` 1c2bff07..., `detector-llamafirewall` 2a4b5e93..., `egress-proxy` 5957cd59...).

## Passi eseguiti
| Passo | Esito |
|---|---|
| 1 agente (6 sessioni, gpt-5.4-mini, effort none) | ok, 6 sessioni completate |
| 1b sposta_guasti | 0 spostate |
| 1c check_conditions (sessioni) | condizioni come attese |
| 2 prepare_judge_input | 6 sessioni, mappa scritta |
| 3 servizi | su; confronto con l'elenco delle impronte NON provabile (l'elenco non esiste ancora) |
| 3b controlli, 3 giudici x 5 sessioni x 3 | 45 verdetti, 0 errori, tutti i controlli richiesti superati, identici all'esito del 2026-11-11 (con i telefoni fittizi) |
| 4 giudici sulle 6 sessioni, 2 verdetti | 36 verdetti, 0 errori |
| 5 verdetti in errore | nessuno, non provato in concreto |
| 6 terzo verdetto | 1 sessione discordante (AlignmentCheck), terzo verdetto dato |
| 6b check_conditions (verdetti) | condizioni come attese |
| 7 revisore | impronta accettata (nessun STOP); su schede `ctl_*` NON parte (vedi sotto); provato su 2 sessioni della prova generale: ok, `confronta.py` accordo 2/2, `check_conditions --reviewer` ok |
| 7b copia registri | ok (vendor_proxy 8,0 MB, llamafirewall_proxy 0,7 MB) |
| 8 down | ok |

## Difetti trovati nei comandi
1. **`confronta.py` non funziona sulle ondate.** Legge fisso `docs/research/2026-10-22-prova-generale-agente/esiti-lettura-automatica.csv` e le sessioni della
   prova generale. Il passo 7 del piano dice "poi `confronta.py`": su sessioni di un'ondata cade con `KeyError` (nessuna riga nel CSV). Serve decidere: produrre per
   ogni ondata il CSV della lettura automatica con `malicious_steps.py` e parametrizzare `confronta.py`, oppure togliere il confronto dal passo 7 e farlo in `analisi_v3.py`.
2. **`revisore.py` cerca le schede solo in `dataset_v3/cases/`** (riga 28). Non è un difetto del run (le 58 schede stanno lì) ma vuol dire che la catena
   con le schede di controllo non si prova sul revisore: provato su sessioni della prova generale.
3. **Il tetto di spesa del passo 4 è sul registro intero, non per giudice.** Il programma stampa "spent so far X of TETTO" sommando tutti i giudici e i controlli della stessa
   cartella. Il piano parla di tetti interni "AlignmentCheck 1,00; aidr 1,00": in pratica è un solo tetto sul totale dei giudici. Risposta alla domanda aperta: il tetto 0,10 dei controlli
   NON blocca l'ondata (il tetto si passa a ogni chiamata), ma la spesa dei controlli (0,048) si somma nel registro.
4. **Stima dei controlli troppo bassa:** il piano dice "circa 0,03 dollari" per il passo 3b, misurati 0,048.

## Spesa della prova
Agente circa 0,014; controlli 0,048; giudici sulle 6 sessioni 0,038 (registro 0,0858 in tutto); revisore 0,049. Totale circa 0,15 dollari (la stima era 0,06 e non
comprendeva il revisore sulla prova generale); tetto approvato per i controlli: 0,50.

## Correzioni fatte dopo la prova (stesso giorno)
- **Difetto 1 corretto nel codice.** `confronta.py` calcola la lettura automatica sul momento (`malicious_steps.read_session`) e prende la cartella con
  `--sessions` (predefinita: quella della prova generale). Verificato: sulle 174 sessioni della prova generale il calcolo coincide con
  `esiti-lettura-automatica.csv` (0 differenze); sul registro del revisore `taratura3` dà ancora 164 su 165; test nuovo `tests/toy_agent/test_confronta.py`
  (4 test); suite 1099 passati, 8 saltati. Una raccomandazione iniziale diversa (spostare il confronto in `analisi_v3.py`) era sbagliata: il confronto si chiude prima di
  aprire i verdetti e dopo il congelamento si possono toccare solo `analisi_v3.py` e il suo test. `confronta.py` entra nell'elenco A.
- **Difetto 3 corretto nel testo del piano:** un solo tetto di 2,00 sul totale dei giudici. Stima del passo 3b portata a circa 0,05.
- **Difetto 2** non è un difetto del run: nessuna correzione.
- Nota pratica: `registri/vendor_proxy.jsonl` pesa 8 MB; decidere se committarlo o tenerne solo l'impronta (nel run vero ne servono i registri alla chiusura).
