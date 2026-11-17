# Controllo finale esterno (preparato il 17 novembre 2026, NON ancora eseguito)

Piano del run, parte 12, «Ordine», passo 5, e parte 13, «Aggiunte», punto 10: un modello di un'altra famiglia, più forte di
`deepseek/deepseek-v3.2`, legge **le sole differenze e l'elenco A**. Non conta come indipendenza (l'autore del testo e del codice è Claude;
la famiglia diversa toglie solo un punto cieco). Se porta una correzione, l'elenco si rifà.

## Cosa legge
Solo testo, nessun accesso al repository, nessuno strumento, un solo giro. Il pacchetto lo costruisce `controllo_finale.py prepara`
dal commit `HEAD` (non dalla copia di lavoro) e registra in `contenuto.json` ogni parte con numero di caratteri e SHA-256:
1. le **differenze** dal testo che il council ha visto (`e2325fb`, 12 novembre) a oggi: piano, pagina dei limiti, README dei controlli,
   condizioni attese, `check_conditions.py`, `run_card.py` (come `git diff`);
2. l'**elenco A** (bozza) in forma compatta: gruppi e nomi dei file, pin dei produttori, immagini, voci da registrare a mano
   (gli SHA-256 per file stanno nell'elenco vero e non servono a un lettore di testo);
3. i **programmi nuovi** per intero: `analisi_v3.py`, `elenco_a.py`, `registra_versioni.py`, e i nomi dei loro test;
4. il **piano completo** e la **pagina dei limiti dichiarati**, i **principi del progetto** (`SPIRIT.md`);
5. ciò che è **già valutato**: council, lettura di coerenza, le due valutazioni degli specialisti, l'esito della prova dei comandi.

## Cosa deve fare, e cosa non deve fare
Istruzioni in `istruzioni-controllo-finale.md`. Una sola domanda: se il proprietario approva e pubblica questo pacchetto, c'è qualcosa che lo
rende non verificabile, contraddittorio, o che lascia scegliere le regole dopo aver visto i risultati? Max 12 punti, ognuno con gravità
(BLOCCA, CAMBIA, MINORE) e con una PROVA citata. **Non ripete** le voci della pagina dei limiti né i punti già valutati.

## Perché è fatta così (la lezione della prova dell'11 novembre)
Nella prova di confronto sullo specialista di metodologia il modello esterno era debole (deepseek-v3.2), vedeva solo testo e ripeteva 10 punti
su 12 già dichiarati: non ha trovato nulla di nuovo (`docs/research/2026-11-11-specialisti-congelamento/VALUTAZIONE-metodologia.md`). Qui:
modello più forte, input concentrato su differenze ed elenco, pagina dei limiti data con l'ordine di non ripeterla, formato di uscita
con prova obbligatoria.

## Regole scritte PRIMA di eseguire
- **Un solo giro.** Nessuna domanda di approfondimento al modello; nessuna seconda esecuzione con un altro modello senza una nuova decisione del proprietario.
- **Ogni punto si verifica** nei documenti e nel codice prima di accoglierlo (un modello che lo dice non è una prova). Esiti possibili:
  confermato, in parte, falso, già dichiarato, non verificabile.
- **Si accoglie solo** ciò che cambia cosa si congela o come si formulano le affermazioni. Nessuna modifica al testo prima di aver valutato tutti i punti.
- **Regola decisionale:** il controllo ha valso la pena se produce almeno un punto confermato BLOCCA o CAMBIA. Se produce solo MINORE o nulla, si
  scrive «controllo finale eseguito, nessun punto bloccante» e basta. In nessun caso si scrive «indipendente».
- Se una correzione tocca un file dell'elenco A: l'elenco si rigenera e si rifà `verifica`, ma non c'è un secondo giro del modello.
- Modello, fornitore, versione servita, token e costo si registrano in `meta.json`; la risposta grezza in `risposta.json`.

## Esecuzione (due fasi, la seconda non parte da sola)
```
python docs/research/2026-11-17-controllo-finale/controllo_finale.py prepara --out ESECUZIONE --elenco docs/design/elenco-A-impronte-BOZZA.json
python docs/research/2026-11-17-controllo-finale/controllo_finale.py lancia  --out ESECUZIONE --modello ID --fornitore NOME \
       --prezzo-in DOLLARI_PER_MILIONE --prezzo-out DOLLARI_PER_MILIONE --cap DOLLARI [--max-output 30000] [--si-lancia]
```
`prepara` lavora offline. `lancia` senza `--si-lancia` stampa solo la stima del caso peggiore e si ferma; con `--si-lancia` chiama il
fornitore (fissato, nessun ripiego). Si rifiuta di partire se il caso peggiore supera `--cap`. La chiave viene letta da `.env` solo dentro il
processo e non si stampa.

## Candidati (prezzi dell'elenco pubblico di OpenRouter, 17 novembre; stima del pacchetto: circa 95 mila token in ingresso)
| Modello | Famiglia | Fornitori | Prezzo ingresso / uscita ($ per milione) | Nota |
|---|---|---|---|---|
| `qwen/qwen4-max` | Alibaba, assente dal run | solo Alibaba | 1,42 / 4,27 | un solo punto di arrivo, niente livelli da distinguere |
| `openai/gpt-6.1-terra-pro` | OpenAI (è la famiglia dell'agente) | OpenAI e Azure, più livelli di prezzo | da 1,00 / 5,00 (livello normale) | un livello normale da fissare con cura; non accetta la temperatura |
| `google/gemini-4-carbon` | Google (è la famiglia del revisore) | Google AI Studio e Google, più livelli | da 1,00 / 5,00 a 2,00 / 10,00 | più livelli da distinguere |

La qualità relativa dei tre non si può giudicare dalla memoria (modelli successivi alla conoscenza di chi scrive): la scelta si fa su famiglia,
chiarezza del fornitore e prezzo. Costo del caso peggiore con 30 mila token di uscita: circa 0,27 dollari per Qwen4 Max.
