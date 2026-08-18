# Principio: strutturale-per-costruzione vs contingente-per-questo-caso

**Nota di lavoro, non ancora un principio formale di `SPIRIT.md`.** Da tenere aggiornata
finché il progetto genera nuove istanze del pattern, o da cancellare se si decide che
resta tacito / se viene assorbita altrove (es. promossa a principio 8 di `SPIRIT.md`).

## Il pattern (2026-08-18, sessione su Gap 14/15)

Ogni volta che in questo progetto è emersa una decisione, si è ripetuta la stessa
correzione: rifiutare che una condizione vera *solo per il caso specifico sotto mano ora*
si travasi in una regola trattata come strutturale o permanente. La correzione ha sempre
la stessa forma — separare esplicitamente:

- **ciò che deve valere sempre, per costruzione** (garantito dall'interfaccia, dallo
  schema, da un parametro dichiarato — non dipende da cosa fa un vendor specifico oggi)
- da **ciò che è vero oggi, per questo caso, e va dichiarato come tale**, non dato per
  scontato o cablato come se fosse universale

**In una frase**: non fidarsi mai di una scorciatoia che funziona nel caso che si ha sotto
mano — se qualcosa deve reggere per ogni audit futuro, deve essere garantito dalla
struttura (interfaccia, parametro dichiarato, primitiva separata dalla composizione), mai
dedotto dall'osservazione di un solo caso che oggi sembra andare bene.

## Istanze concrete nel progetto

1. **Gap 12** (`docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 14): prima proposta
   di chiusura basata sulla lettura del codice vendor pinnato ("`session_id` non compare
   in nessun prompt, quindi il campo è sicuro") — corretta: vale solo per quel vendor, quel
   commit, oggi. Il tool deve garantire l'assenza del segnale per costruzione (confine
   ingresso/uscita dichiarato), non per fortuna. Vedi memoria
   `feedback_blackbox_measured_system.md`.
2. **Inventario segnali prima del trattamento** (Gap 14): rifiutata la chiusura gap per
   gap in isolamento — prima la mappa completa dei segnali, poi la decisione su come
   trattarli, per non fissare un trattamento parziale scoperto poi incompleto.
3. **Repulisti vs ricostruzione container** (Gap 14, cluster B): "container nuovo o
   riusato" sembrava una decisione monolitica — scomposta in due assi indipendenti (quali
   residui vanno puliti / se pulirli richiede davvero ricostruire), evitando una decisione
   prematura su un problema che in realtà si spaccava in due domande diverse.
4. **Primitiva atomica vs sceneggiature composte** (Gap 15): la primitiva (un turno seed →
   un verdetto) resta fissa e corretta per costruzione; la flessibilità per test più
   elaborati si aggiunge sopra come composizione (nuovo livello di orchestrazione), non
   modificando la base che deve restare stabile.
5. **Ciclo di vita del container come parametro** (Gap 14): "container riusato" sembrava
   la risposta giusta perché oggi coincidono teoria della misura generale e dichiarazione
   di *questo* vendor (`Pipeline()` unica riusata per le 300 sessioni di Gauntlet) — ma
   cablarlo nell'infrastruttura sarebbe sbagliato per un vendor futuro con condizioni
   diverse. Reso un parametro esplicito dell'orchestratore, parte dichiarata della
   metodologia di misura per ogni audit.

## Collegamento con `SPIRIT.md`

Stessa logica di fondo del principio "non fidarsi di un benchmark self-reported perché ha
funzionato su un caso" — ma applicata non solo ai risultati del vendor testato, bensì a
ogni scelta che il progetto fa nel costruire lo strumento di misura stesso. Se il
misuratore stesso contiene scorciatoie valide solo per il vendor di turno, ricade nello
stesso difetto ("self-reported", vedi principio 6/7) che il progetto contesta ai vendor.

## Come Claude può essere utile su questo asse (proposte discusse, non ancora decise)

1. **Check esplicito prima di ogni proposta di chiusura**: dichiarare sempre, come parte
   della proposta stessa (non a margine), se la soluzione regge per un vendor/caso futuro
   con condizioni diverse o se è vera solo per il caso attuale — così la correzione non
   deve più partire dall'utente.
2. **Controllo sistematico proattivo**: rileggere periodicamente gap-tracking doc e design
   doc cercando altri punti dove qualcosa di vero solo per questo vendor/caso potrebbe
   essere scivolato dentro come se fosse strutturale, invece di aspettare che emerga per
   caso in conversazione.
3. **Codificarlo** come principio 8 di `SPIRIT.md` (non ancora fatto — richiede conferma
   esplicita dell'utente prima di toccare quel documento fondativo).

**Prossimo passo**: non ancora deciso quale delle tre proposte adottare per prima (vedi
conversazione, 2026-08-18).
