# Review: stato persistente su disco dei tre provider MCP (Gap 9)

Verifica richiesta dal design doc, sezione "Meccanismo di handoff" — "Residuo su
filesystem nel container detector a lunga vita", item lasciato esplicitamente
aperto ("Non verificato in questa sessione"). Vendor: `agentic-threat-detection-vendor`,
commit pinnato `7fad14d2478707e68a09b8ecd9942dec8fde1614`.

## Scansione

    grep -n "open(\|write_text\|\.write(" aidr/providers/sourcelens.py aidr/providers/threatlens.py aidr/providers/policylens.py aidr/detector/runtime.py

```
aidr/providers/sourcelens.py:7:REGISTRY = yaml.safe_load(open("aidr/data/source_registry.yaml"))["servers"]
aidr/providers/threatlens.py:8:_fw = yaml.safe_load(open("aidr/data/threat_repository.yaml"))["threat_framework"]
aidr/providers/policylens.py:5:POLICIES = yaml.safe_load(open("aidr/data/policy_store.yaml"))["policies"]
aidr/detector/runtime.py:20:    config_path.write_text(json.dumps({"mcpServers": mcp_servers}, indent=2))
```

## Classificazione

| File | Chiamata | Scrittura su disco? |
|---|---|---|
| `aidr/providers/sourcelens.py` | `open("aidr/data/source_registry.yaml")` (lettura), `path.read_text()` in `get_source_code` | No — solo letture. Nessuna delle tre `@mcp.tool()` (`get_source_code`, `list_mcp_servers`, `get_server_categories`) scrive mai su disco. |
| `aidr/providers/threatlens.py` | `open("aidr/data/threat_repository.yaml")` (lettura), `embed(...)` per costruire `_matrix` in memoria | No — `embed()` è una chiamata di rete verso il nostro thin proxy (Task 1), non una scrittura locale; `_matrix` vive solo in memoria del processo, mai persistita. Nessuna delle quattro `@mcp.tool()` scrive su disco. |
| `aidr/providers/policylens.py` | `open("aidr/data/policy_store.yaml")` (lettura) | No — solo letture. Nessuna delle quattro `@mcp.tool()` scrive su disco. |
| `aidr/detector/runtime.py`, `write_mcp_config` | `config_path.write_text(...)`, `config_path = workspace / ".mcp.json"` | **Sì** — ma `workspace` è passato esplicitamente da `Inspector.__init__(..., workspace=".")` (`aidr/detector/inspector.py`), invocato dal nostro `AgenticThreatDetectionAdapter` una volta per invocazione (`evaluate_case`, Task 6 di questo piano, un processo Python nuovo per ogni `case_id`). Il contenuto è interamente deterministico dato lo stesso insieme di provider abilitati (`sourcelens`, `threatlens`, `policylens` — fisso, mai variato tra `TestCase`), e `write_text` **sovrascrive** il file per intero a ogni chiamata, non lo estende — nessuna deriva di contenuto tra un `TestCase` e il successivo. |

## Esito

Nessuno dei tre provider MCP sotto test (`SourceLens`, `ThreatLens`, `PolicyLens`)
scrive stato persistente su disco — confermato leggendo il codice sorgente reale di
tutti e tre, non assunto. L'unica scrittura su disco nell'intero percorso
`Inspector()` → `Pipeline().analyze()` è `.mcp.json`, scritta da `write_mcp_config`
(chiamata da `Inspector.__init__`, non da uno dei tre provider), con contenuto
identico e completamente sovrascritto a ogni invocazione — nessun residuo di
contenuto attribuibile a un `TestCase` precedente.

**Effetto collaterale non pericoloso ma da documentare**: `docker diff detector`
(Task 8, canale di raccolta prove) mostrerà `/opt/aidr-vendor/.mcp.json` come file
modificato dopo **ogni** invocazione, non solo quando succede qualcosa di anomalo —
un evidenziatore automatico di anomalie sulla base del solo `docker diff` deve
trattare questa riga come rumore atteso, non come segnale.

**Conclusione per Gap 9**: il rischio di "validità della misura" sollevato dal
council mirato (2026-08-16) — un cache/memoization interno che fa leggere a un
`TestCase` uno stato lasciato dal precedente — non si materializza per nessuno dei
tre provider sotto test. Resta vero, come limite dichiarato indipendente, che un
vendor futuro diverso da `aidr` potrebbe comportarsi diversamente — questa
conclusione è specifica al codice pinnato di `agentic-threat-detection`, non una
proprietà generale del pattern architetturale (design doc, "Contratto riusabile del
container detector": il livello vendor-specifico va rivalidato per ogni nuovo
vendor).
