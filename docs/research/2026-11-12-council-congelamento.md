# Council sul testo di congelamento (2026-11-12)

Quattro pareri indipendenti e non vincolanti (scettico, rischio, pragmatico, utente) sulla parte 12 e sulle aggiunte della parte 13, con la domanda
anti-punto-cieco. Tutti e quattro: congelare dopo correzioni nominate (opzione b), nessuno "non è pronto". Ogni punto è stato verificato nei file e nel
codice prima di accoglierlo (un accordo tra agenti non vale come prova).

## Dove i pareri convergono
- Cosa si pubblica e cosa vuol dire "riprodotto" (tutti e quattro).
- Controllo fallito: il README dei controlli diceva "si corregge e si rifà tutto", il piano "ferma l'ondata" (pragmatico, utente).
- Il programma dei conteggi nasce dopo il congelamento (scettico, pragmatico).
- "Data certa" non garantita dal solo push (scettico, rischio).
- Ordine dei comandi e disciplina di apertura delle etichette (scettico, rischio, utente).

## Verificato e corretto (nessuna scelta di progetto)
| Punto | Verifica | Correzione |
|---|---|---|
| Versione datata dell'agente non controllata da nessun programma | Confermato: `condizioni_attese.json` aveva solo l'alias; nessun codice leggeva `/generation` | Nuovo `registra_versioni.py` + `check_conditions --generations`; provato su dati veri: 10 chiamate su 10 `openai/gpt-5.4-mini-20260317` / OpenAI. Comando 1d. |
| Verdetto con `served_by` vuoto passava come "coppie attese" | Confermato nel codice | `check_conditions` lo segnala (giudice con coppie attese e nessun registro letto). |
| Impronta del revisore controllata solo se si passava `--sistema-atteso` | Confermato | `instructions_sha256` nel file delle condizioni; `check_conditions --reviewer` la confronta con `sistema.sha256`. |
| Sessione che solleva un'eccezione scartata senza traccia e ritentata a ogni rilancio | Confermato in `run_card.py` | Salvata come guasto (`stop_reason` `exception`), la prende `sposta_guasti` e vale la rigenerazione unica. |
| Risposta illeggibile del revisore senza regola | Confermato (`parsed` nullo salvato e non ritentato) | Regola nel comando 7: al più 2 ripetizioni, poi solo lettura automatica e conteggio a parte. |
| README dei controlli e piano in contraddizione; tetto 0,50 contro 0,10 | Confermato | Regola per prima e dopo il congelamento; tetto 0,10 a ondata. |
| Ordine dei comandi: il comando 6 mostra dove i giudici sono instabili prima delle letture | Confermato; il revisore non dipende dai verdetti | Il comando 7 si esegue prima dei giudici. |
| Nessuna definizione di "riprodotto"; casi pubblici; costo dell'agente; cecità come disciplina; intervalli su casi costruiti; run fermato; correzione di sfera dei produttori | Confermato (assenza nel testo) | Frasi nel piano e voci 29-33 della pagina dei limiti. |
| Tetto 3,5 e segnaposto `TETTO` | Parziale: i segnaposto sono voluti (tetto approvato per ondata) | 3,5 = somma dei tetti più l'agente; impronta del revisore scritta per intero nel comando. |

## Decisioni del proprietario (12 novembre)
1. **Telefoni:** la storia del repository pubblico non si riscrive; rischio basso, si può intervenire dopo. Fatti verificati: `origin` è pubblico, due file con i numeri in forma reale (vecchia `world_base.yaml`, `input.md`) sono pubblici dal 19 ottobre, circa 340 file li hanno nella storia di `master`; 0 fork e 0 stelle. Le schede e il mondo congelati hanno solo numeri 555.
2. **Pubblicazione:** per ora tutto in privato (sessioni, verdetti, letture, registri nel backup); si pubblica con l'analisi (SPIRIT, principi 4 e 6); ai produttori prima. Immagini `docker save` non pubblicate.
3. **`analisi_v3.py` prima del congelamento:** si scrive e si prova su verdetti di prova, entra nell'elenco A. NON ancora scritto.
4. **Clausola "l'ondata diventa sviluppo":** tolta (contraddiceva il congelamento e il principio 2). Un cambiamento dopo il congelamento è un run nuovo; il run fermato si pubblica.
5. **Verdetti mancanti oltre il 10%:** si pubblica comunque, con "nessun verdetto in X%" e i due casi estremi (principi 3 e 6).
6. **Data:** nessuna marca esterna; il piano dice "data del push", non "data certa".

## Resta
Scrivere e provare `analisi_v3.py` con il suo test; bozza dell'elenco A e prova del passo 3 contro l'elenco; ripulire titolo e sezione "da verificare" del piano; controllo finale esterno; approvazione scritta; push.
Il vuoto più grande segnalato dallo scettico, i gradi di libertà dopo i dati (molte viste, nessun esito principale), è accolto: la parte 13 fissa ora un esito principale per giudice (i due conteggi sulla lettura larga) e dice che le altre viste sono descrittive e, se divergono, si riportano tutte.
