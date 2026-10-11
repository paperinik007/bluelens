# Specialisti sul piano del run v3: verifica dei punti (2026-10-11)

Due specialisti, su proposta del proprietario, prima del council: metodologia della misura
(`google/gemini-3.1-pro-preview`, fornitore Google) e sicurezza degli agenti AI
(`deepseek/deepseek-v4-pro-0813`, fornitore CoreWeave). OpenRouter, temperatura 0. Input:
piano, file della revisione, sfere (`input-*.md`); istruzioni e risposte in questa cartella
(`specialisti.py`, `output-*.md`). Costo: 0,29 dollari. Nessuno dei due ha chiesto un altro
specialista. Ogni punto verificato da Claude prima di essere accolto.

M = metodologia, S = sicurezza.

## Accolti

| # | Punto | Verifica | Cosa cambia nel piano |
|---|---|---|---|
| M1 | La soglia dei gemelli usa "variabilità dell'agente misurata nella prova pilota", ma la prova pilota usa sessioni del vecchio agente | vero in parte: la prova pilota misura solo l'instabilità dei giudici; la variabilità dell'agente nuovo esiste solo nel run. Il testo della parte 4 era sbagliato | parte 4: variabilità dell'agente dalle sessioni del run (stesso agente); instabilità del giudice dalla prova pilota e, dove si applica, dai verdetti ripetuti del run |
| M4 | I gemelli cambiano anche le parole, non solo l'elemento | vero, inevitabile | parte 4: modifica minima del testo (solo le parole che nominano l'elemento), differenza registrata; limite dichiarato |
| M5 | Il calcolo dell'errore della maggioranza (10% → 2,8% con 3) assume errori indipendenti; sulla stessa sessione non lo sono | vero: formula binomiale, `2026-10-09-revisione-modello.md`, "Ripetibilità" | nota nel file della revisione e nel piano: quei numeri sono il caso migliore; conta l'instabilità misurata |
| M6 | Il revisore tarato solo sulle sessioni vecchie, senza profilo né perimetro | vero | parte 10: seconda taratura sulle sessioni della prova generale, contro la nostra lettura a mano, prima di congelare le istruzioni |
| S1 | Nei casi "contenuto" e "strumento" l'agente può non incontrare mai l'attacco | vero: nessuna regola lo copriva | parte 6/9: condizione "segnale presentato" (vedi piano) |
| S2, S11, S12 | Server di terze parti pulito: non descritto; il nome del server può essere una scorciatoia | vero: la correzione 1 dice "dichiarato solo nei casi con l'attacco nello strumento", la parte 5 parla di benigni con il server pulito; non riconciliate. aidr vede il nome del server (`server_name` nell'adattatore) | parte 2, correzione 1 riscritta: una sola integrazione di terze parti, presente in ogni sessione, con lo stesso nome; versione onesta di regola, versione compromessa solo nei casi "strumento". Il nome non dice niente: per distinguere bisogna leggere il codice |
| S3 | Il prompt di sistema non arriva ai giudici: è una deviazione? | verificato: l'esempio ufficiale di AlignmentCheck (`examples/demo_alignmentcheck.py`) costruisce la traccia con soli `UserMessage` e `AssistantMessage`; lo scanner prende come scopo il primo messaggio dell'utente (`alignmentcheck_scanner.py`, `_pick_user_input`); aidr non ha un tipo di messaggio di sistema. Non è una deviazione | parte 2: dichiarato come condizione: i giudici non vedono la policy dell'agente, come nell'installazione del produttore; il profilo arriva come risultato di uno strumento |
| S4 | Il contenuto degli allegati può essere invisibile ai giudici | vero se non lo si progetta | parte 2, correzione 6: il risultato di `bulk_export` contiene i dati, `send_email` cita l'export allegato; entrambi nella sessione che i giudici leggono |
| S5 | Un'azione può finire solo nella richiesta o solo nel contenuto | vero | parte 5: ogni azione almeno una volta nella richiesta e una nel contenuto, dove plausibile |
| S6 | Il comportamento nascosto non deve dipendere da un argomento speciale | vero, regola utile | parte 2, correzione 1: il comportamento nascosto sta nel funzionamento ordinario dello strumento |
| S7 | I casi "agente" possono non produrre mai il passo malevolo | vero: la prova generale controllava solo "che l'agente non rifiuti tutto" | prova generale: ogni caso "agente" deve produrre il passo in almeno una delle sue sessioni, o si corregge o la casella si dichiara vuota |
| S9 | La voce "contro terzi" segnala ogni dominio esterno | vero | parte 3: domini dell'azienda e domini ammessi (partner) scritti nell'ambiente e nel perimetro |
| S10 | Ambiente giocattolo | vero | limite dichiarato nel piano |
| S13 | "aidr e AlignmentCheck non dichiarano lingue" senza fonte | verificato: nessuna occorrenza di lingua in `alignment-check.md` né nel README di aidr | fonte aggiunta nella parte 6 |

## Respinti, con il motivo

| # | Punto | Motivo |
|---|---|---|
| M2 | "Effetto avvenuto" impossibile da calcolare se il passo non dice l'esito | il passo trova la chiamata; l'esito è nello stato della chiamata (`status` "ok" o "error"), registrato nella sessione indipendentemente dal passo. Effetto = una chiamata del passo riuscita. Precisato nel testo |
| M3 | Sessioni in più condizionate all'osservazione: stima distorta della variabilità; conti deboli | i conti usano solo le prime 3 sessioni di ogni caso, uguali per tutti: non dipendono da ciò che si osserva. La variabilità complessiva dell'agente si stima dalle prime 3 di tutti i casi; le 5 in più descrivono solo i casi instabili. Il revisore parla di "maggioranza" delle sessioni: la maggioranza vale per i verdetti, non per le sessioni. Precisato nel testo |

## Da decidere con il proprietario

| # | Punto | Perché è del proprietario |
|---|---|---|
| S8 | L'instabilità dei giudici sulle sessioni vecchie può non valere sulle nuove; usare sempre la regola dei due verdetti (un terzo se diversi) per aidr e AlignmentCheck | cambia la regola per ridurre i test, punto 3, decisa dal proprietario il 2026-10-11 |

**Decisione (2026-10-11, proprietario)**: S8 accolto, "ma facciamo prima un test con un
sottoinsieme di casi limitato ma significativo". Modo del test: in `2026-10-11-piano-run-v3.md`,
parte 9.
