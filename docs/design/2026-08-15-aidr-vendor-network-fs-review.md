# Review una tantum del codice vendor — chiamate di rete/filesystem non dichiarate

Verifica richiesta dal design doc, sezione "Container di controllo" — completata
prima di eseguire il primo caso reale (Task 6 di questo piano). Vendor:
`agentic-threat-detection-vendor`, commit pinnato
`7fad14d2478707e68a09b8ecd9942dec8fde1614` (verificato con `git log -1` e
`git status --porcelain` prima della scansione: HEAD al commit atteso, working
tree pulito).

## Scansione (Step 1 del piano)

    grep -rn "socket\.\|subprocess\.\|smtplib\|urllib\.request\|requests\.\|httpx\.\|open(" aidr --include="*.py"

Eseguito da dentro `agentic-threat-detection-vendor/`. Output reale ottenuto:

    aidr/config.py:12:        return cls(raw=yaml.safe_load(open(path))["threat_framework"])
    aidr/crucible/evolve.py:102:    repo = yaml.safe_load(open(repo_path))
    aidr/crucible/evolve.py:111:    yaml.safe_dump(repo, open(repo_path, "w"))
    aidr/detector/inspector.py:7:        config = json.loads(open(mcp_config_path).read())["mcpServers"]
    aidr/gauntlet/pack.py:20:    with open(out_path, "w") as f:
    aidr/gauntlet/runner.py:30:    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600).stdout
    aidr/gauntlet/servers/host_toolkit/host_toolkit.py:9:    resp = requests.get(url, timeout=20)
    aidr/gauntlet/servers/host_toolkit/host_toolkit.py:10:    with open(path, "wb") as f:
    aidr/providers/mcp_client.py:8:        self.proc = subprocess.Popen(
    aidr/providers/mcp_client.py:9:            launch_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    aidr/providers/policylens.py:5:POLICIES = yaml.safe_load(open("aidr/data/policy_store.yaml"))["policies"]
    aidr/providers/sourcelens.py:7:REGISTRY = yaml.safe_load(open("aidr/data/source_registry.yaml"))["servers"]
    aidr/providers/threatlens.py:8:_fw = yaml.safe_load(open("aidr/data/threat_repository.yaml"))["threat_framework"]

**Confronto col baseline del piano: identico**, riga per riga e numero di riga
per numero di riga (13 righe in entrambi i casi). Nessuna divergenza — il
clone vendor è confermato pinnato al commit atteso e il codice non è
cambiato dalla strutturazione del piano.

(esclusa di proposito, come nel piano: `aidr/serving/model_client.py`, la
chiamata OpenRouter già presa in carico e proxata da Task 1.)

## Classificazione (Step 2 del piano) — confermata leggendo il codice

Verificata leggendo `Inspector.__init__`/`analyze` e l'intero import graph a
partire da lì, non fidandomi della tabella del piano. File letti per intero:
`aidr/detector/inspector.py`, `aidr/detector/runtime.py`,
`aidr/detector/pipeline.py`, `aidr/detector/sifter.py`, `aidr/config.py`,
`aidr/providers/mcp_client.py`, `aidr/providers/sourcelens.py`,
`aidr/providers/threatlens.py`, `aidr/providers/policylens.py`,
`aidr/gauntlet/servers/host_toolkit/host_toolkit.py`,
`aidr/data/source_registry.yaml`.

**Percorso confermato**: `Pipeline.__init__` (`aidr/detector/pipeline.py:9-13`)
costruisce `Inspector(enabled=self.cfg.providers_enabled())`.
`PipelineConfig.providers_enabled()` (`aidr/config.py:26-33`) restituisce un
sottoinsieme di `["sourcelens", "threatlens", "policylens"]` letto da
`aidr/config.yaml` locale — nessun riferimento a `gauntlet` o `crucible` in
`config.py`. `Inspector.__init__` (`aidr/detector/inspector.py:31-38`) chiama
`discover_providers(set(enabled))` (`aidr/detector/runtime.py:6-12`), che fa
`glob("aidr/providers/*lens.py")` filtrato sui nomi abilitati — **per
costruzione può risolvere solo `sourcelens.py`, `threatlens.py`,
`policylens.py`**, mai un file sotto `aidr/gauntlet/`. Il risultato passa a
`write_mcp_config` (`runtime.py:14-21`), che scrive `.mcp.json` con
`{"command": "python", "args": [path]}` per ciascun provider trovato; questo
file guida `MCPRouter.__init__` (`inspector.py:6-12`), che per ogni entry
lancia `MCPClient([spec["command"], *spec["args"]])`
(`mcp_client.py:7-11`, `subprocess.Popen`). Confermato con
`grep -rn "import.*gauntlet\|from.*gauntlet\|import.*crucible\|from.*crucible" aidr`:
gli unici import di `gauntlet` sono interni a `aidr/gauntlet/` stesso
(`tasks.py` importa `pack`/`runner`, `runner.py` importa `tasks`); nessun
modulo in `aidr/detector/`, `aidr/config.py` o `aidr/providers/` importa mai
`aidr.gauntlet.*` o `aidr.crucible.*`.

| File | Call | Classificazione |
|---|---|---|
| `aidr/config.py:12`, `aidr/providers/policylens.py:5`, `aidr/providers/sourcelens.py:7`, `aidr/providers/threatlens.py:8` | `open(...)` su file YAML locali di config/registry | Dichiarata (README: rilevamento config-driven) e raggiungibile da `Pipeline().analyze()` — solo letture di file locali, tutti i percorsi puntano dentro il repo vendor, nessun percorso è influenzato dall'attaccante. |
| `aidr/detector/inspector.py:7` | `open(mcp_config_path)` | Dichiarata e raggiungibile — legge la config di lancio MCP che `Inspector.__init__` stesso scrive tramite `write_mcp_config` (vedi riga sotto). |
| `aidr/providers/mcp_client.py:8-9` | `subprocess.Popen(launch_cmd, ...)` | Dichiarata (README: "Inspector... calling context providers over MCP") e raggiungibile — così vengono lanciati SourceLens/ThreatLens/PolicyLens. Nessun I/O di rete proprio; le chiamate di rete dei sotto-processi sono coperte dalle altre righe di questa tabella. |
| `aidr/crucible/evolve.py:102,111` | `open(repo_path)` / `yaml.safe_dump(..., open(repo_path, "w"))` | Dichiarata (README: "Crucible... evolutionary red team") ma **non raggiungibile** da `Pipeline().analyze()`/`Inspector.analyze()` — Crucible è uno strumento offline mai invocato da questo progetto. Confermato: nessun modulo del percorso Pipeline/Inspector importa `aidr.crucible`. |
| `aidr/gauntlet/pack.py:20`, `aidr/gauntlet/runner.py:30`, `aidr/gauntlet/servers/host_toolkit/host_toolkit.py:9-10` | `open(...)`, `subprocess.run(...)`, `requests.get(...)` reale | Parte del benchmark Gauntlet del vendor stesso — **non raggiungibile** dal percorso di codice che questo progetto chiama (vedi Global Constraints: non importiamo mai `aidr.gauntlet.runner` né i tool server propri del Gauntlet). La chiamata HTTP in uscita reale di `host_toolkit.py` è l'unico reperto di questa scansione che conterebbe se fosse raggiungibile; non lo è, sul percorso che usiamo. Confermato: `discover_providers` può risolvere solo `*lens.py` sotto `aidr/providers/`, mai un modulo sotto `aidr/gauntlet/servers/`, quindi il *server* MCP `host_toolkit` non viene mai avviato da `Inspector.__init__`. |

**Nessuna correzione alla classificazione del piano**: ogni riga è stata
verificata contro il codice effettivo e risulta corretta.

## Scansione supplementare — I/O basato su `pathlib`, non catturato dal grep del piano

Durante la verifica ho letto per intero i tool MCP di SourceLens
(`aidr/providers/sourcelens.py`) e ho notato che `get_source_code` usa
`path.read_text(...)` (metodo `pathlib.Path`), non la funzione builtin
`open(...)` — quindi **non compare nell'output del grep dello Step 1**, il cui
pattern (`open(`) non cattura `.read_text()`/`.write_text()`. Ho rieseguito
una scansione mirata per colmare questo buco di copertura:

    grep -rn "\.read_text(\|\.write_text(\|os\.system\|os\.popen\|shutil\.\|ftplib\|\.connect(\|socket(" aidr --include="*.py"

Output:

    aidr/detector/runtime.py:20:    config_path.write_text(json.dumps({"mcpServers": mcp_servers}, indent=2))
    aidr/dredge/parsers.py:29:            for line in path.read_text(encoding="utf-8").splitlines():
    aidr/gauntlet/pack.py:28:    for line in Path(pack_path).read_text().splitlines():
    aidr/providers/sourcelens.py:26:            "source_code": path.read_text(encoding="utf-8"),

Ho anche riletto `host_toolkit.py` per intero e trovato una seconda lacuna del
pattern originale: `os.remove(path)` a `host_toolkit.py:16` (cancellazione
file, tool `delete_file`) — non catturata da nessuno dei due grep perché non
matcha `open(`/`subprocess`/`socket`/etc. Non cambia la classificazione:
`host_toolkit.py` resta un server MCP mai avviato dal percorso Inspector (vedi
sopra), quindi anche questa chiamata è non raggiungibile.

Classificazione dei 4 hit supplementari, verificata leggendo il codice:

| File | Call | Raggiungibile da `Inspector.analyze()`? | Classificazione |
|---|---|---|---|
| `aidr/detector/runtime.py:20` | `config_path.write_text(...)` in `write_mcp_config()` | **Sì** — chiamata da `Inspector.__init__` (`inspector.py:35`) | Dichiarata (implicita nel comportamento MCP descritto dal README) e raggiungibile — scrive `.mcp.json` dentro la `workspace` passata dal chiamante (parametro locale di `Inspector`, non derivato dal transcript). Controparte in scrittura della lettura già documentata a `inspector.py:7`. Nessun percorso controllato dall'attaccante. |
| `aidr/providers/sourcelens.py:26` | `path.read_text(encoding="utf-8")` nel tool MCP `get_source_code` | **Sì** — `get_source_code` è uno dei tool esposti dal router e invocato dall'LLM Inspector durante `analyze()` quando `enable_source_code` è attivo (default) | Dichiarata (è letteralmente lo scopo di SourceLens: "read a server's real implementation", README) e raggiungibile. Il percorso letto è vincolato a una whitelist: `path = BASE / entry["path"]` dove `entry` deve corrispondere per nome a una delle 3 righe di `aidr/data/source_registry.yaml` (`analytics_insights`, `business_metrics`, `host_toolkit`) — l'argomento `server_names` scelto dall'LLM seleziona solo *quale file whitelistato* leggere, non un percorso arbitrario. **Effetto pratico**: il codice sorgente di `host_toolkit.py` (incluso il suo `requests.get` reale) può essere restituito come *testo* all'LLM Inspector come evidenza da analizzare — non viene mai eseguito. Nessuna via di esecuzione o network I/O reale si apre da qui. |
| `aidr/gauntlet/pack.py:28` | `Path(pack_path).read_text()` | No | Stessa classificazione della riga Gauntlet già in tabella — parte del benchmark harness, mai importato dal percorso Pipeline/Inspector. |
| `aidr/dredge/parsers.py:29` | `path.read_text(encoding="utf-8")` | No | `aidr/dredge/` è un pacchetto a sé (collector/parser di transcript grezzi) importato solo al suo interno (`collector.py` importa `parsers.py`); confermato con `grep -rn dredge aidr` che l'unico hit fuori da `dredge/` stesso è nel file stesso — nessun modulo di `detector/`, `config.py` o `providers/` lo importa. Non raggiungibile da `Pipeline().analyze()`. |
| `aidr/gauntlet/servers/host_toolkit/host_toolkit.py:16` | `os.remove(path)` (tool `delete_file`) | No | Stessa classificazione della riga Gauntlet/host_toolkit già in tabella — il server MCP `host_toolkit` non viene mai avviato da `discover_providers`/`write_mcp_config` (che risolvono solo `aidr/providers/*lens.py`). |

**Esito della scansione supplementare**: 2 chiamate filesystem in più risultano
raggiungibili rispetto al grep letterale del piano
(`runtime.py:20`, `sourcelens.py:26`), entrambe già coerenti col comportamento
dichiarato (scrittura/lettura di file locali, whitelistati o non derivati dal
transcript), nessuna delle due è una chiamata di rete. **Non cambiano l'esito
complessivo** (nessuna chiamata di rete non dichiarata e raggiungibile), ma
segnalo esplicitamente che il pattern grep specificato nel piano ha un punto
cieco strutturale: cattura `open(` ma non `Path.read_text()`/`.write_text()`/
`os.remove()`/`os.rename()` e simili. Se questa scansione viene ripetuta in
futuro (es. dopo un aggiornamento del pin vendor), va rieseguita anche la
query supplementare sopra, non solo quella del piano.

## Esito

Nessuna chiamata di rete/filesystem/subprocess non dichiarata e raggiungibile
dal percorso `Pipeline().analyze()` / `Inspector.analyze()` che questo
progetto usa. L'unica chiamata di rete reale nell'intero pacchetto
(`host_toolkit.py`, `requests.get`) appartiene al Gauntlet del vendor, mai
importato né invocato dal nostro codice (vincolo esplicito in questo piano,
sezione "Global Constraints") — confermato leggendo l'intero import graph a
partire da `Inspector.__init__`, non solo la classificazione a priori del
piano.

La scansione supplementare basata su `pathlib` ha trovato 2 chiamate
filesystem raggiungibili in più che il grep letterale del piano non catturava
(`aidr/detector/runtime.py:20`, `aidr/providers/sourcelens.py:26`); entrambe
sono locali, coerenti con il comportamento dichiarato, senza percorsi
controllati dall'attaccante, e non aprono I/O di rete. **Task 6 resta sicuro
da eseguire** sulla base di questa verifica, con l'avvertenza sul punto cieco
del pattern grep documentata sopra per riferimento futuro.
