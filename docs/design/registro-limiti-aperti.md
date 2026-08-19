# Registro dei limiti aperti

Indice, non contenuto: una riga per ogni limite dichiarato o debito tecnico trovato
durante una review (task, whole-branch, o discussione ad-hoc) e non ancora risolto. Il
dettaglio pieno resta nel documento più pertinente — questa pagina punta lì, non lo
ripete, per evitare due copie che divergono.

Complementare, non sostitutivo, ai doc "gap-tracking" già esistenti
(`2026-08-14-toy-agent-gap-tracking.md`, `2026-08-14-metrics-gap-tracking.md`): quelli
tracciano una tassonomia specifica (Gap 1-15, segnali dell'effetto osservatore / gap
sulle metriche), già con una propria convenzione di stato ("Come si chiude un gap"). Qui
finisce tutto il resto — limiti a livello di implementazione, vincoli di design per un
piano futuro — che non ha già una casa strutturata.

**Quando aggiungere una riga**: ogni volta che una review o una discussione fa emergere
un limite reale, dichiarato esplicitamente invece che silenziosamente accettato o
ignorato (principio 8, `SPIRIT.md`), e non risolto subito nel codice.

**Quando rimuovere una riga**: quando il limite viene risolto nel codice — cancellare la
riga qui, la risoluzione stessa (commit, test) diventa il record.

## Aperti

- **Sequenze composte con `case_id` ripetuto** — un comando ripetuto con lo stesso
  `case_id` nella stessa sceneggiatura sovrascrive silenziosamente transcript grezzo ed
  evidenza raccolta di tutte le esecuzioni tranne l'ultima (`verdicts.jsonl` unico canale
  append-only che sopravvive). Non raggiungibile da nessun percorso di codice esistente
  oggi. Dettaglio, soluzione decisa (contatore per-`case_id`, non `command_index`
  grezzo), costo stimato e quando implementarlo (insieme a Plan 5, non prima):
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`, sezione Gap 15, dopo "Prossimo
  passo". Origine del limite: `docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md:226-256`.

- **Nessuna attesa esplicita di readiness del `detector` prima della prima invocazione
  in una sequenza** — `_open_container()` ritorna appena Docker segnala il container
  avviato, non appena l'entrypoint del detector ha finito di aprire le proprie porte
  interne. Chiuso in pratica dal tempo del round-trip LLM lato agente (che precede
  sempre l'invocazione al detector), ma incidentale, non garantito per costruzione — un
  verdetto classificato come infra-failure per detector non ancora pronto resta una
  possibilità teorica. Nessuna analisi di costo/quando fatta ancora. Dettaglio:
  `docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md`, sezione "Meccanica
  Docker per open/close".

- **Interfaccia di autoring non tecnica (Excel) per sceneggiature composte, Plan 5** —
  l'interfaccia con cui un umano non tecnico definirà davvero una sceneggiatura
  deliberata (Gap 15 modalità 2) sarà verosimilmente una tabella Excel, non YAML scritto
  a mano — serve un programma di traduzione Excel → sequenza, non ancora progettato,
  nessun precedente nel codice (`load_dataset()` parsa solo `*.yaml` oggi). Legato al
  punto sopra (case_id ripetuto): se l'autoring passa da Excel, i `case_id` ripetuti
  diventano più probabili, non meno. Dettaglio e vincolo completo:
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`, sezione Gap 15, dopo "Prossimo
  passo".

## Risolti (storico, rimossi da "Aperti" quando chiusi nel codice)

Nessuno ancora — registro appena creato (2026-08-19).
