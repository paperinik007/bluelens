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
Implementazione in corso: Plan 1 (toy agent), Plan 2 (modulo metriche/report), Plan 3
(container di controllo con egress di rete ristretto a `openrouter.ai`) e Gap 9 (split
del container di controllo in `agent`/`detector` isolati, vedi "Struttura" sotto) sono
completi e testati.

## Struttura

- `SPIRIT.md` — perché esiste questo repo, principi metodologici.
- `docs/design/` — design doc per audit, con relativo gap-tracking doc companion.
- `docs/reports/` — report di audit pubblicati (uno per tool testato), quando pronti.
- `src/toy_agent/` — pacchetto del toy agent (schema, stato finto, tool, loop ReAct,
  modulo metriche, orchestrazione agent -> detector).
- `src/detector_adapter/` — pacchetto che gira nel container `detector`: adapter verso
  il tool vendor sotto audit (`AgenticThreatDetectionAdapter`, entrypoint
  `evaluate_case`) e `vendor_proxy.py`, il thin proxy di rimappatura verso OpenRouter
  usato dal tool vendor.
- `tests/` — test automatici dei pacchetti `toy_agent` e `detector_adapter`.
- `docker/` — Dockerfile e configurazione dei tre container: `agent` (esegue solo il
  toy agent), `detector` (clone del tool vendor sotto audit + `detector_adapter`) ed
  `egress-proxy`, l'unico intermediario di rete tra `agent`/`detector` e l'esterno —
  ed è anche l'unica rete Docker condivisa tra i due: `agent` e `detector` non hanno
  alcuna rotta di rete diretta l'uno verso l'altro (Gap 9, confine misuratore/misurato).
- `docker-compose.yml` — orchestrazione dei tre container.

## Come eseguire

Servono due chiavi API OpenRouter distinte, una per `agent` e una per `detector`
(`AGENT_OPENROUTER_API_KEY` e `DETECTOR_OPENROUTER_API_KEY`) — chiavi separate per
principio, non per necessità tecnica: un container compromesso non deve poter
spendere o agire per conto dell'altro (Gap 9, confine misuratore/misurato).

```
cp .env.example .env
# poi modificare .env e impostare AGENT_OPENROUTER_API_KEY=<chiave 1> e
# DETECTOR_OPENROUTER_API_KEY=<chiave 2>
docker compose build
docker compose up -d
```

Attenzione: `docker compose config` stampa entrambe le chiavi in chiaro — non
eseguirlo in una sessione di terminale condivisa o loggata.

## Licenza

Non ancora formalizzata. L'intento dichiarato in `SPIRIT.md` (principio 7) è una
licenza copyleft/share-alike, coerente con la scelta di pubblicare tutto (principio 6)
senza che chi forka il lavoro possa richiuderlo.
