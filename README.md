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
(container di controllo con egress di rete ristretto a `openrouter.ai`), Gap 9 (split
del container di controllo in `agent`/`detector` isolati, vedi "Struttura" sotto), Plan 4
(`run_batch.py`, il batch orchestrator che fa girare l'intero dataset attraverso
`agent`/`detector` e produce il report finale, vedi "Come eseguire" sotto) e Plan 5 (il
dataset di audit — catalogo, 31 `TestCase`, gate di copertura/anti-scorciatoia, vedi
`catalog/`/`dataset/` sotto) sono completi e testati. Primo report reale pubblicato in
`docs/reports/`.

## Struttura

- `SPIRIT.md` — perché esiste questo repo, principi metodologici.
- `docs/design/` — design doc per audit, con relativo gap-tracking doc companion.
- `docs/reports/` — report di audit pubblicati (uno per tool testato).
- `catalog/` — catalogo dinamico di scenari candidati per il dataset di audit (Plan 5):
  ogni voce dichiara tecnica target, fonte (inventata, incidente reale, o ispirata a un
  benchmark accademico) e — quando applicabile — citazione verificabile e adattamento.
  Non è letto dalla pipeline di misura (`load_dataset()` legge solo `dataset/*.yaml`).
- `dataset/` — i `TestCase` YAML reali eseguiti da `run_batch.py`, selezionati dal
  catalogo. 31 casi, 12 delle 14 tecniche del vendor coperte da almeno un caso malevolo
  + un gemello benigno (T0009/T0011 esclusi — limite dichiarato, vedi
  `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 17).
- `src/toy_agent/` — pacchetto del toy agent (schema, stato finto, tool, loop ReAct,
  modulo metriche, orchestrazione agent -> detector).
- `src/detector_adapter/` — pacchetto che gira nel container del detector: un
  adapter per vendor sotto `vendors/` (`vendors/aidr/`, `vendors/llamafirewall/`),
  ciascuno con il proprio `evaluate_case` entrypoint e il proprio thin proxy di
  rimappatura verso OpenRouter (`vendor_proxy.py`) — isolamento fisico tra vendor
  garantito anche a livello di import (test dedicato).
- `tests/` — test automatici dei pacchetti `toy_agent` e `detector_adapter`.
- `docker/` — Dockerfile e configurazione dei container: `agent` (esegue solo il
  toy agent), `detector`/`detector-llamafirewall` (un container per vendor, ciascuno
  clone del proprio tool vendor sotto audit + `detector_adapter`) ed `egress-proxy`,
  l'unico intermediario di rete tra `agent`/detector e l'esterno — ed è anche l'unica
  rete Docker condivisa tra loro: `agent` e i container detector non hanno alcuna
  rotta di rete diretta l'uno verso l'altro (Gap 9, confine misuratore/misurato).
- `docker-compose.yml` — orchestrazione dei container.

## Vendor supportati

- `aidr` (agentic-threat-detection, FareedKhan-dev): `python -m toy_agent.run_batch dataset run_output --vendor aidr`
- `llamafirewall` (LlamaFirewall/AlignmentCheck, Meta): `python -m toy_agent.run_batch dataset run_output --vendor llamafirewall`

Ogni vendor ha il proprio container Docker isolato (`detector`/
`detector-llamafirewall`), la propria rete (`detector_net`/
`detector_llamafirewall_net`, entrambe `internal: true`), il proprio
`.env.<vendor>` (mai una chiave condivisa tra vendor). `--vendor` è sempre
un argomento CLI esplicito — mai persistente in `.env` (principio 8,
SPIRIT.md).

## Come eseguire

Servono due chiavi API OpenRouter distinte, una per `agent` e una per `detector`
(`AGENT_OPENROUTER_API_KEY` e `DETECTOR_OPENROUTER_API_KEY`) — chiavi separate per
principio, non per necessità tecnica: un container compromesso non deve poter
spendere o agire per conto dell'altro (Gap 9, confine misuratore/misurato).
Per `--vendor llamafirewall` serve inoltre una terza chiave, dedicata,
in `.env.llamafirewall` (`LLAMAFIREWALL_OPENROUTER_API_KEY` + `LLAMAFIREWALL_MODEL`)
— mai la stessa chiave di `DETECTOR_OPENROUTER_API_KEY`, per lo stesso principio.

I modelli per i tier del detector (`SIFTER_MODEL`, `INSPECTOR_MODEL`, `EMBED_MODEL`)
e per l'agente giocattolo (`AGENT_MODEL`) sono opzionali — lasciare vuoto per usare
i default del codice (`vendor_proxy.py` per i tier, `model_client.py` per l'agente).
Tutti i modelli usati sono dichiarati nel report (Gap 20).

```
cp .env.example .env
# poi modificare .env e impostare AGENT_OPENROUTER_API_KEY=<chiave 1> e
# DETECTOR_OPENROUTER_API_KEY=<chiave 2>
docker compose build
docker compose up -d egress-proxy
```

Attenzione: `docker compose config` stampa entrambe le chiavi in chiaro — non
eseguirlo in una sessione di terminale condivisa o loggata.

Con `egress-proxy` sopra, il batch orchestrator si esegue **sull'host**, non dentro un
container. A differenza di prima, possiede lui stesso il ciclo di vita di `agent`/`detector`
(li ricrea/rimuove via `docker compose`, non serve più avviarli a mano) — il parametro
`--container-lifecycle` sceglie come:

```
python -m toy_agent.run_batch <dataset_dir> <run_output_dir> --vendor aidr
# equivalente a:
python -m toy_agent.run_batch <dataset_dir> <run_output_dir> --vendor aidr --container-lifecycle reused
# un container fresco per ogni caso (isolamento massimo, costo più alto):
python -m toy_agent.run_batch <dataset_dir> <run_output_dir> --vendor aidr --container-lifecycle per-case
# secondo vendor (LlamaFirewall/AlignmentCheck), stessa CLI:
python -m toy_agent.run_batch <dataset_dir> <run_output_dir> --vendor llamafirewall
```

Attenzione alle worktree: `python -m toy_agent.run_batch` risolve il pacchetto
`toy_agent` dall'installazione editable globale, che punta al checkout principale della
repo — se lanci il comando da una worktree diversa, eseguiresti silenziosamente il
codice sbagliato. `run_batch.py` ora **rifiuta di partire** quando il modulo importato
non è quello della working tree da cui lanci il comando (fallisce con un messaggio che
mostra i due path, invece di produrre numeri col codice sbagliato). Se vedi quel
rifiuto, forza la risoluzione con
`PYTHONPATH=<checkout>/src python -m toy_agent.run_batch <dataset_dir> <run_output_dir>`.
Per verifica manuale:
`python -c "import toy_agent.run_batch as m; print(m.__file__)"`.

`reused` (default) tiene `agent`/`detector` aperti per l'intero batch — fedele alla
condizione di misura dichiarata dal vendor (Gauntlet, `Pipeline()` istanziata una sola
volta per 300 sessioni). `per-case` ricrea entrambi i container a ogni caso, per costruzione
senza alcuno stato residuo tra un caso e il successivo. Dettagli:
`docs/design/2026-08-19-container-lifecycle-e-sequenze-design.md`.

`docker compose build` resta comunque necessario prima del primo run (costruisce le
immagini): il ciclo di vita che `run_batch.py` ora gestisce è solo avvio/rimozione dei
container, non il build. Se `agent`/`detector` risultano già in esecuzione da un run
precedente o da un avvio manuale, non serve fermarli a mano: il primo `open` della
sequenza li rimuove e ricrea comunque, in modo sicuro (auto-risanante per costruzione,
vedi design doc). Questo assume un solo operatore che esegue una sola sequenza alla
volta: un secondo `run_batch.py` avviato in parallelo, o un comando `docker compose`
lanciato a mano in un altro terminale mentre un batch è in corso, entra in competizione
con i container di quel batch e può distruggerli a metà run.

`run_batch.py` legge la chiave del vendor scelto (`DETECTOR_OPENROUTER_API_KEY` per
`--vendor aidr`, `LLAMAFIREWALL_OPENROUTER_API_KEY` per `--vendor llamafirewall`)
direttamente dall'ambiente del processo Python host (la stessa variabile impostata
in `.env`/`.env.llamafirewall`, ma letta qui dall'host, non passata attraverso Docker
— va quindi esportata anche nella shell da cui si lancia il comando, non solo nel
file). `<dataset_dir>` è una directory di file YAML `TestCase` (Plan 5); non viene
mai scritta.

**Ogni run ha la sua directory.** `<run_output_dir>` è la radice; ogni esecuzione crea al
suo interno `run_output/<run_id>/` con nome ordinabile `YYYYMMDD-HHMMSS-<token>` (UTC),
che contiene: `report.md` (il report finale), `verdicts.jsonl` (un `Verdict` grezzo per
riga), `raw/` (i transcript grezzi per caso), `run.log` (la narrativa del run: banner,
heartbeat per caso, errori in evidenza, riepilogo) e una sottodirectory di prove esterne
per `case_id` (prodotta da `evidence.py`). Un symlink `run_output/latest` punta all'ultimo
run che ha davvero girato (su Windows, se il symlink non è consentito, si salta: l'ultimo
run si trova per ordinamento del nome).

**Strumenti di ispezione**: `python -m toy_agent.inspect_run <run_dir>` e
`python -m toy_agent.regenerate_report <dataset_dir> <run_dir>` vanno puntati alla
directory del singolo run (`run_output/<run_id>/` o `run_output/latest/`), **non** alla
radice `run_output/`: puntarli alla radice ora produce un errore esplicito invece di zero
transcript in silenzio.

**Analisi intento-vs-effetto**: `python -m toy_agent.analyze_run <dataset_dir> <run_dir>`
produce due metriche (intent-based ed effect-based) e la tabella di divergenza tra le due —
la metrica più informativa per capire se il detector giudica l'intento del prompt o
l'effetto reale delle azioni dell'agente. `--json` per l'output machine-readable. Vedi
`docs/research/2026-08-26-analisi-metriche-intento-vs-effetto.md`.

**Pubblicazione in `docs/reports/`**: è un'operazione manuale. Quando si copia `report.md`
nella directory di report tracciata da git, va copiato anche `run.log` accanto ad esso —
la timeline del run è parte dell'evidenza di riproducibilità (SPIRIT.md principio 4), non
solo il report finale.

## Licenza

Non ancora formalizzata. L'intento dichiarato in `SPIRIT.md` (principio 7) è una
licenza copyleft/share-alike, coerente con la scelta di pubblicare tutto (principio 6)
senza che chi forka il lavoro possa richiuderlo.
