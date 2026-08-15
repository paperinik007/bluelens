# agentic-security-audits

Ente indipendente di audit per tool di "agentic threat detection" — prodotti che
promettono di rilevare comportamenti malevoli negli agenti AI. La maggior parte dei
benchmark che li accompagnano è self-reported: lo stesso team che costruisce il
detector costruisce anche il benchmark che lo valuta. Questo repo esiste per fare da
controparte indipendente: metodologia trasparente, dataset propri, risultati
pubblicati per intero — inclusi i limiti statistici delle proprie misure.

Il perché, cosa questo progetto non è, e i principi metodologici che vincolano ogni
audit sono in [`SPIRIT.md`](SPIRIT.md) — leggerlo prima di qualunque contributo.

## Stato

**Fase 1** (in corso): audit indipendente di
[`agentic-threat-detection`](https://github.com/FareedKhan-dev/agentic-threat-detection)
di FareedKhan-dev. Design completo — toy agent, pipeline di misura indipendente dal
tool testato, schema dati, adapter, modulo metriche — passato per council checkpoint e
grill-with-docs. Vedi [`docs/design/2026-08-14-toy-agent-e-pipeline-misura.md`](docs/design/2026-08-14-toy-agent-e-pipeline-misura.md).
Implementazione in corso: Plan 1 (toy agent), Plan 2 (modulo metriche/report) e Plan 3
(container di controllo a due container, con egress di rete ristretto a
`openrouter.ai`) sono completi e testati.

## Struttura

- `SPIRIT.md` — perché esiste questo repo, principi metodologici.
- `docs/design/` — design doc per audit, con relativo gap-tracking doc companion.
- `docs/reports/` — report di audit pubblicati (uno per tool testato), quando pronti.
- `src/toy_agent/` — pacchetto del toy agent (schema, stato finto, tool, loop ReAct,
  modulo metriche, proxy di rimappatura verso OpenRouter).
- `tests/` — test automatici del pacchetto `toy_agent`.
- `docker/` — Dockerfile e configurazione dei due container del container di
  controllo (`control`, che esegue il toy agent e il tool vendor sotto audit, ed
  `egress-proxy`, l'unico varco con una rotta reale verso Internet).
- `docker-compose.yml` — orchestrazione dei due container.

## Come eseguire

Serve una chiave API OpenRouter (`OPENROUTER_API_KEY`) per far funzionare il thin
proxy verso i modelli usati dal tool vendor sotto audit.

```
cp .env.example .env
# poi modificare .env e impostare OPENROUTER_API_KEY=<la propria chiave>
docker compose build
docker compose up -d
```

Attenzione: `docker compose config` stampa `OPENROUTER_API_KEY` in chiaro — non
eseguirlo in una sessione di terminale condivisa o loggata.

## Licenza

Non ancora formalizzata. L'intento dichiarato in `SPIRIT.md` (principio 7) è una
licenza copyleft/share-alike, coerente con la scelta di pubblicare tutto (principio 6)
senza che chi forka il lavoro possa richiuderlo.
