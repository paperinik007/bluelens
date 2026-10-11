# Council sul piano del run v3: verifica dei punti (2026-10-11)

Quattro revisori (scettico, rischi, pragmatico, utente; modelli Claude, stessa famiglia di chi
scrive il piano), sul piano intero dopo le correzioni degli specialisti. Stesso testo di
consegna per tutti, con la domanda su ciò che manca. Verdetto di tutti e quattro: procedi con
correzioni. Ogni punto verificato prima di essere accolto.

## Convergenze (il segnale più forte)

1. **Manca un piano di analisi scritto prima** (scettico, rischi, utente): unità di analisi
   (il caso, non la sessione: le sessioni dello stesso caso sono correlate), incertezza dei
   conteggi, quali affermazioni sono ammesse. Verificato: `SPIRIT.md` principio 3, "Con
   campioni piccoli, dichiarare esplicitamente intervalli di confidenza o limiti di
   generalizzabilità"; né il piano né il file della revisione dicono come. Accolto: nuova
   parte "Analisi e lettura dei risultati".
2. **Correggere i casi dopo la prova generale secondo il comportamento dell'agente è una
   selezione sull'esito** (utente, pragmatico; lo scettico chiede il caso opposto, un agente
   che rifiuta quasi tutto). Accolto: si corregge solo per motivi oggettivi (ostacolo
   dell'ambiente, segnale non presentato); un rifiuto si conta, non si corregge.
3. **Rapporto con i produttori e frasi pubblicate** (scettico, rischi): "aidr come
   configurato qui", non "aidr"; nessun passo verso i produttori prima della pubblicazione.
   Da decidere con il proprietario (pubblicazione).
4. **Consapevolezza di essere in un test** (rischi, pragmatico): mondo piccolo, domini
   riservati (`example.com` in `state.py`), dati evidentemente finti. Accolto: domini e dati
   inventati ma credibili; il revisore etichetta ogni caso "sembra un test?".

## Altri punti accolti

| Revisore | Punto | Verifica | Cosa cambia |
|---|---|---|---|
| utente 1 | Sessioni scartate per tempo scaduto: tolgono proprio le più lunghe ("consumare risorse") | vero: `orchestrator.py`, un tempo scaduto dà un errore senza sessione; `registro-limiti-aperti.md`: 8 turni × 20 s = 160 s contro un limite di 120 s | il limite di tempo si alza sopra il massimo strutturale (circa 210 s); il limite dei turni dell'agente resta e una sessione che lo raggiunge è valida. Si scartano solo errori di rete o del fornitore |
| rischi 2 | Verdetti mancanti o degradati; PromptGuard tronca a 512 token | vero: `promptguard_utils.py:113`, `truncation=True, max_length=512`. È il comportamento del prodotto installato come dice il produttore, non un nostro artefatto | regola per i verdetti mancanti (nella nuova parte); regola di scrittura: nei casi "contenuto" l'attacco entro i primi 512 token del testo letto, salvo casi scritti apposta per la lunghezza, dichiarati prima |
| rischi 3 | Ordine di lettura: la lettura a mano e i disaccordi con il revisore si decidono prima di vedere i verdetti | vero, non scritto | nella nuova parte: risultato chiuso (e registrato con un'impronta) prima di aprire i verdetti |
| rischi 4 | Le due versioni dell'integrazione possono differire per stile, non solo per il comportamento nascosto | vero | il revisore confronta alla cieca le due versioni prima del congelamento; differenze diverse dal comportamento nascosto si tolgono |
| scettico 3 | Soglia dei giudici non fissata | verificato: PromptGuard nel produttore blocca da 0,9 (`prompt_guard_scanner.py:24`) | condizioni di misura: soglie del produttore, scritte |
| scettico 6 | Agente che rifiuta quasi tutto: nessuna soglia minima | vero in parte: un rifiuto non toglie il confronto con l'intento (l'attacco è stato presentato), toglie solo il confronto con il risultato | nella nuova parte: una casella dove l'agente non fa mai il passo resta valida per l'intento; per il risultato si dichiara "non provata" |
| scettico 6 | "Temperatura fissata" forse non applicabile a un modello con ragionamento | da verificare | prova generale: verificare; se il parametro non si applica, dichiararlo |
| utente 3, 4 | Zeri letti come assenza | vero (principio 3) | nella nuova parte: ogni conteggio con il suo intervallo; uno zero si scrive con il limite superiore |
| utente 5 | Vista per minaccia per chi sceglie un giudice | è una vista meccanica (decisione "Viste") | nuova vista decisa prima: per ogni valore di dove e forma, quali giudici dichiarano di coprirla |
| utente 7, 8, pragmatico A | Limiti da dichiarare: policy nel prompt di sistema, casi in inglese, conversazioni di un solo messaggio | veri: `run_case.py` "exactly one seed turn"; lunghezza della conversazione era una dimensione candidata, mai decisa | limiti dichiarati accanto ai numeri e negli articoli |
| pragmatico 3 | Benigni per azione: 10, non 11 | vero (contati) | totale benigni 21 |
| pragmatico 4 | Casi "solo testo": circa un sesto, non un decimo | vero: ingannare e scoprire (6 casi su 36), più in parte i comandi | stima della lettura a mano rifatta |
| pragmatico 6 | SourceLens con la versione della sessione: meccanismo non descritto | vero, non descritto. Non è una deviazione dal produttore: registrare i propri server è l'installazione | meccanismo da progettare, scritto come compito |
| pragmatico 7 | Il profilo come chiamata della piattaforma: aidr la legge come una mossa dell'agente | vero: l'adattatore trasforma ogni chiamata in `tool_calling` dell'assistente (`adapter.py`) | dichiarato: nella sessione il profilo appare come una prima chiamata; innocua |
| pragmatico nota | La prova pilota ora serve solo a riportare l'instabilità | vero | scritto |

## Respinti, con il motivo

| Revisore | Punto | Motivo |
|---|---|---|
| utente 6 | aidr fuori sfera 9 casi, non 2-4 | la regola dell'ambito è "la forma **o** almeno un'azione": nella lettura larga i casi su restare, denaro e ingannare con forma iniezione, override o esplicita sono in ambito per la forma. Fuori restano quelli con il pretesto e il caso strumento su restare: circa 3 |
| pragmatico 2 | Gemelli: 12 casi, non 6 | il caso di partenza è un caso di C, già contato; il gemello è la sola copia. Il testo era ambiguo: precisato |
| pragmatico 1 | Correzioni 5-8 dell'ambiente superflue (0 ostacoli da S4 e S5) | in parte vero sui conteggi, ma: `get_account` serve (gli account sono separati dai clienti in `state.py`, `query_customer_db` non legge lo stato); senza un canale verso un operatore l'agente inventa indirizzi (`support@example.com`, registrato); gli allegati servono perché i dati escano davvero (S5, revisione del 2026-09-28); la ricerca dei ticket costa uno strumento semplice. Correzioni approvate dal proprietario; si tengono |
| pragmatico 5 | Agente: restare su gpt-4o-mini, la continuità vera | la decisione del proprietario chiede un modello **recente** della stessa taglia; gpt-4o-mini è del 2024. La taratura su sessioni del vecchio agente è già dichiarata come limite e ripetuta nella prova generale |
| utente 7 (parte) | Una sessione di controllo con il prompt di sistema come deviazione misurata | fuori dalla domanda del progetto (il produttore non lo prevede); resta il limite dichiarato |

## Da decidere con il proprietario

1. Rapporto con i produttori prima della pubblicazione e regole per le frasi pubblicate
   (scettico 5, rischi 6).
2. Un secondo lettore umano su un campione (scettico 4): chi.
3. Criterio per riaprire la scelta GPU o OpenRouter per aidr (scettico 5).
