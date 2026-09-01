# Attivazione PromptGuard in LlamaFirewall (verdetto combinato) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Attivare PromptGuard come secondo scanner dentro il container
`detector-llamafirewall`, pubblicando per ogni caso un solo `Verdict` che fonde
AlignmentCheck+PromptGuard sotto un **nuovo** `tool_name="llamafirewall-combined"` —
senza toccare il vendor esistente `llamafirewall-alignmentcheck`.

**Architecture:** Un nuovo entry point (`evaluate_case_combined.py`) invoca
`LlamaFirewall.scan_replay()` per AlignmentCheck (invariato) e chiama direttamente
`PromptGuardScanner.scan()` turno per turno sui soli messaggi `Role.USER` (non
`scan_replay()`, che sovrascriverebbe silenziosamente lo score all'ultimo messaggio
scansionato — bug del vendor corretto in fase di design, non riprodotto qui).
`adapter.py` guadagna 3 funzioni pure duck-typed (nessuna dipendenza da
`llamafirewall` installato) che fanno la fusione; una nuova voce
`VENDOR_DETECTOR_CONFIG["llamafirewall-combined"]` instrada `--vendor
llamafirewall-combined` sullo stesso container `detector-llamafirewall`, riusato.
Il modello PromptGuard (86M, gated su HuggingFace) viene scaricato una volta al
build del container (BuildKit secret), mai a runtime.

**Tech Stack:** Python 3.11, pytest, Docker BuildKit (`RUN --mount=type=secret`),
`llamafirewall==1.0.3`, `torch`/`transformers`/`huggingface_hub` (CPU-only).

**Spec:** `docs/design/2026-09-01-llamafirewall-promptguard-design.md` (commit
`2d82e63`, non pushato) — passato per council checkpoint (roster completo, un
difetto di correttezza reale trovato e corretto: lo score di PromptGuard via
`scan_replay()` sarebbe stato quasi sempre 0.0 per costruzione) e per
`/grill-with-docs` (nuovo `tool_name`, non una rinomina — coerente con
`CONTEXT.md`, "Nomi di tool risolti", già aggiornato nello stesso commit del design
doc). Questo piano traduce quel design in task eseguibili e aggiunge 4 modifiche
non menzionate nel design doc, scoperte leggendo il codice reale durante la
scrittura di questo piano (vedi "Deviazioni dal design doc" sotto).

## Deviazioni dal design doc (trovate scrivendo questo piano, non nel design doc)

Queste 4 cose sono necessarie per far funzionare `--vendor llamafirewall-combined`
nel codice reale, ma il design doc non le cita (si concentrava sulla fusione del
Verdict, non su ogni tabella host-side indicizzata per vendor). Verificate leggendo
il codice, non assunte:

1. **`evidence.collect_thin_proxy_log` nomina il file di output
   `f"{service}.vendor_proxy.jsonl"` sempre, ignorando `log_path`** — due chiamate
   per lo stesso `case_id`/`service` (una per AlignmentCheck, una per PromptGuard)
   scriverebbero entrambe su `detector-llamafirewall.vendor_proxy.jsonl`, la seconda
   sovrascrivendo silenziosamente la prima. Il design doc afferma il path finale
   corretto (`detector-llamafirewall.promptguard_raw.jsonl`) ma non che serve un
   parametro nuovo per ottenerlo — Task 1 lo aggiunge.
2. **`preflight.py::TIER_ENV_VARS_BY_VENDOR[vendor]`** è un lookup diretto senza
   `.get()`/default — `--vendor llamafirewall-combined` senza una voce qui solleva
   `KeyError` al primo avvio di `run_batch.py`, prima ancora di aprire un container.
3. **`run_batch.py::API_KEY_ENV_VAR_BY_VENDOR[vendor]`** stesso problema, stessa
   causa: lookup diretto, `KeyError` immediato senza una voce nuova.
4. **`provenance.py::collect_provenance()`** ha un `if/elif/else` esplicito per
   vendor — senza un ramo per `"llamafirewall-combined"` cadrebbe nell'`else` che
   pubblica tutti i campi vendor-specifici come `None`, perdendo silenziosamente la
   provenance (esattamente il difetto che il commento I3 in quel file descrive come
   già corretto una volta — qui si ripresenterebbe per il vendor nuovo).

Task 3 chiude tutte e 4 in un colpo solo (stessa categoria: "collega il vendor nuovo
a ogni tabella host-side indicizzata per vendor").

## Global Constraints

- **Nessun file del percorso esistente `llamafirewall-alignmentcheck` viene
  riscritto**: `evaluate_case.py`, `scan_decision_to_verdict`, `fail_open_verdict`,
  `TOOL_NAME` restano invariati — solo `adapter.py` viene esteso (funzioni nuove
  aggiunte, nessuna rimossa/modificata) e nuovi file vengono creati accanto.
- **`--vendor` resta sempre esplicito** (SPIRIT.md principio 8) — nessun default
  implicito in nessuna tabella toccata da questo piano.
- **`HF_TOKEN` non deve mai comparire in chiaro** in nessun output di comando, log
  di build salvato, o messaggio riportato durante l'esecuzione di questo piano — un
  build secret BuildKit, mai una env var del container finale, mai stampato da
  nessun controllo di verifica (solo booleani/conteggi, mai il contenuto grezzo del
  log se potrebbe contenerlo).
- **Task 0 è un gate bloccante**: se una qualunque delle sue verifiche fallisce,
  l'esecutore si ferma lì, non tocca nessun altro task di questo piano, e riporta
  il fallimento — l'intera architettura "bake al build" andrebbe ridiscussa col
  design doc, non aggiustata task per task.
- Ogni nuova voce aggiunta a una tabella indicizzata per vendor (Task 2, Task 3)
  deve avere almeno un test che la eserciti — nessuna voce "aggiunta e mai
  testata".

---

## Task 0: Falsificazione reale — build Docker con PromptGuard baked, verifica cache/no-network/no-leak

**Files:**
- Modify: `docker/detector-llamafirewall/Dockerfile`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: nessuno (primo task del piano).
- Produces: un'immagine `detector-llamafirewall` con `torch`/`transformers`/
  `huggingface_hub` installati e il modello `meta-llama/Llama-Prompt-Guard-2-86M`
  già presente in `/opt/hf-cache` — ogni task successivo assume questa immagine
  buildabile e funzionante.

**Prerequisito, non automatizzabile da questo piano**: chi esegue questo task deve
avere già `export HF_TOKEN=<token con accesso concesso a
meta-llama/Llama-Prompt-Guard-2-86M>` nella propria shell **prima** di lanciare i
comandi sotto. Non incollare mai il token in chat/log/commit — solo `export` nella
shell locale. Se non disponibile, fermarsi qui e chiedere all'utente come procedere
(non tentare di eseguire il resto del task senza un token reale: il punto di questo
task è verificare il comportamento con un download gated reale, non simulato).

- [ ] **Step 1: Verificare la presenza del token senza mai stamparlo**

```bash
if [ -z "$HF_TOKEN" ]; then
  echo "HF_TOKEN non esportato in questa shell — fermarsi, non procedere oltre questo punto"
else
  echo "HF_TOKEN presente (lunghezza: ${#HF_TOKEN})"
fi
```

Se stampa "non esportato", fermarsi e riportare all'utente che questo task richiede
un token reale nella shell di chi esegue il piano — non è un'assunzione di design
da cui deviare, è un prerequisito operativo mancante.

- [ ] **Step 2: Estendere il Dockerfile con le nuove dipendenze e il pre-download**

Sostituire il contenuto di `docker/detector-llamafirewall/Dockerfile` con:

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

RUN pip install --no-cache-dir --no-deps llamafirewall==1.0.3
RUN pip install --no-cache-dir torch transformers huggingface_hub
ENV HF_HOME=/opt/hf-cache
RUN --mount=type=secret,id=hf_token \
    HF_TOKEN=$(cat /run/secrets/hf_token) python -c \
    "from llamafirewall.scanners.promptguard_utils import PromptGuard; PromptGuard()"
RUN pip install --no-cache-dir 'openai>=1.76.0' 'pydantic>=2.11.3'

COPY docker/detector-llamafirewall/detector_adapter.pyproject.toml /opt/detector_adapter/pyproject.toml
COPY src/detector_adapter/__init__.py /opt/detector_adapter/src/detector_adapter/__init__.py
COPY src/detector_adapter/vendors/__init__.py /opt/detector_adapter/src/detector_adapter/vendors/__init__.py
COPY src/detector_adapter/vendors/llamafirewall /opt/detector_adapter/src/detector_adapter/vendors/llamafirewall
WORKDIR /opt/detector_adapter
RUN pip install --no-cache-dir -e .

RUN pip install --no-cache-dir pytest

COPY docker/detector-llamafirewall/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

RUN chmod a-x /usr/bin/perl /usr/bin/perl5.40.1

WORKDIR /opt
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
```

Nota (verificato leggendo `llamafirewall/__init__.py`/`config.py` nel sorgente
vendor durante la scrittura di questo piano): importare
`llamafirewall.scanners.promptguard_utils` esegue anche `llamafirewall/__init__.py`
e `llamafirewall/config.py`, nessuno dei due richiede `openai`/`pydantic` — l'ordine
sopra (torch/transformers/prefetch prima di openai/pydantic) non rompe l'import.

- [ ] **Step 3: Aggiungere il build secret a `docker-compose.yml`**

Nel blocco `detector-llamafirewall:` (`docker-compose.yml`), estendere `build:`:

```yaml
  detector-llamafirewall:
    build:
      context: .
      dockerfile: docker/detector-llamafirewall/Dockerfile
      secrets:
        - hf_token
    depends_on:
      - egress-proxy
```

E aggiungere, alla fine del file (dopo il blocco `networks:` esistente):

```yaml

secrets:
  hf_token:
    environment: HF_TOKEN
```

- [ ] **Step 4: Validare la sintassi del compose file senza costruire nulla**

```bash
docker compose config detector-llamafirewall > /dev/null && echo "compose config: OK"
```

Deve stampare `compose config: OK`. Se fallisce, il file YAML ha un errore di
sintassi — correggerlo prima di procedere.

- [ ] **Step 5: Build reale, output catturato su file (mai stampato direttamente)**

Usare la directory scratchpad della sessione che esegue questo task (non il repo)
per il file di log. Sostituire `<SCRATCH>` con quella directory:

```bash
docker compose build detector-llamafirewall > <SCRATCH>/pg_build.log 2>&1
echo "build exit code: $?"
```

Se l'exit code non è 0: **non stampare il file di log intero** (potrebbe contenere
il token se `pip`/`huggingface_hub` in modalità verbose lo avessero loggato — è
esattamente il rischio Task 0 deve escludere, non assumere escluso). Prima
ispezionarlo in forma redatta:

```bash
sed "s/$HF_TOKEN/[REDACTED]/g" <SCRATCH>/pg_build.log > <SCRATCH>/pg_build.redacted.log
tail -n 60 <SCRATCH>/pg_build.redacted.log
```

Solo il file `.redacted.log` può essere letto/mostrato. Se il build fallisce,
questo è già un esito del gate: fermarsi, non procedere ai passi successivi, e
riportare l'errore (redatto) all'utente.

- [ ] **Step 6: Verificare che il token non compaia in chiaro nel log di build**

```bash
if grep -qF "$HF_TOKEN" <SCRATCH>/pg_build.log; then
  echo "LEAK: HF_TOKEN found in cleartext in the build log — STOP, do not proceed"
else
  echo "no cleartext HF_TOKEN in the build log: OK"
fi
```

Questo comando non stampa mai il token stesso (`grep -q`, solo l'esito booleano).
Se stampa "LEAK", fermarsi qui — è esattamente il rischio #5 del council, la cui
categoria (non il meccanismo `docker history`, già escluso) resta reale.

Per aderenza letterale alla tabella Requisito → Verifica del design doc (che cita
`docker history` come verifica, pur avendo il council già corretto il meccanismo
sottostante — un BuildKit secret non registra stdout/stderr del `RUN` lì, quindi
questo controllo non può da solo escludere il rischio, il controllo sul log sopra
resta quello che conta):

```bash
IMAGE_ID=$(docker compose images -q detector-llamafirewall)
if docker history --no-trunc "$IMAGE_ID" | grep -qF "$HF_TOKEN"; then
  echo "LEAK: HF_TOKEN found in docker history — STOP, do not proceed"
else
  echo "no cleartext HF_TOKEN in docker history: OK (expected, confirms the BuildKit secret mechanism)"
fi
```

- [ ] **Step 7: Verificare che il modello sia davvero cached nell'immagine**

```bash
IMAGE_ID=$(docker compose images -q detector-llamafirewall)
docker run --rm "$IMAGE_ID" find /opt/hf-cache -maxdepth 1 -type d
```

Deve elencare una directory il cui nome contiene
`meta-llama--Llama-Prompt-Guard-2-86M` (il vendor sostituisce `/` con `--` nel nome
della cartella, `promptguard_utils.py::_load_model_and_tokenizer`). Se la directory
non esiste, il bake non ha funzionato — fermarsi, non procedere.

- [ ] **Step 8: Verificare che un container SENZA token e SENZA rete carichi il modello**

```bash
IMAGE_ID=$(docker compose images -q detector-llamafirewall)
docker run --rm --network none "$IMAGE_ID" timeout 60 python -c \
  "from llamafirewall.scanners.promptguard_utils import PromptGuard; PromptGuard(); print('PROMPTGUARD_LOAD_OK')"
```

Deve stampare `PROMPTGUARD_LOAD_OK` entro il timeout, senza errori. Questo container
non ha `HF_TOKEN` in ambiente (nessun `-e` passato) e non ha rete (`--network
none`) — se il bake avesse fallito silenziosamente, questo comando andrebbe in
timeout o solleverebbe un errore di autenticazione/rete, non stamperebbe
`PROMPTGUARD_LOAD_OK`.

**Se uno qualunque degli Step 4/5/6/7/8 fallisce**: fermarsi. Non eseguire i Task 1+
di questo piano. Riportare all'utente quale verifica è fallita e il suo output
(redatto se necessario) — l'assunzione "bake al build" del design doc sarebbe
falsificata e richiederebbe una revisione del design, non un aggiustamento locale
di questo piano.

- [ ] **Step 9: Commit**

```bash
git add docker/detector-llamafirewall/Dockerfile docker-compose.yml
git commit -m "$(cat <<'EOF'
feat(llamafirewall): bake PromptGuard model into detector-llamafirewall at build

torch/transformers/huggingface_hub added; model pre-downloaded once via a
BuildKit secret (HF_TOKEN never persisted in any image layer). Verified with
a real gated download: cache populated at the vendor's expected path, a
container with no token and no network still loads the model, and the build
log contains no cleartext token (Task 0 falsification, design doc
2026-09-01).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 1: `evidence.collect_thin_proxy_log` — parametro `output_suffix` per evitare la collisione di nome file

**Files:**
- Modify: `src/toy_agent/evidence.py`
- Test: `tests/toy_agent/test_evidence.py`

**Interfaces:**
- Consumes: nessuno (funzione pura esistente, estesa).
- Produces: `collect_thin_proxy_log(..., output_suffix: str = "vendor_proxy.jsonl", ...)`
  — il nome del file scritto diventa `f"{service}.{output_suffix}"`. Il default
  preserva esattamente il comportamento/nome attuale (nessun test esistente cambia
  comportamento). Task 4 (sequence.py) userà `output_suffix="promptguard_raw.jsonl"`
  per la seconda chiamata.

- [ ] **Step 1: Scrivere il test che fallisce**

Aggiungere a `tests/toy_agent/test_evidence.py` (dopo
`test_collect_thin_proxy_log_names_the_output_file_after_the_service`):

```python
def test_collect_thin_proxy_log_uses_a_custom_output_suffix_when_given(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "exec", "-T", "detector-llamafirewall", "cat", "/var/log/llamafirewall_promptguard_raw.jsonl"): b"",
    })
    path = collect_thin_proxy_log(
        "case_007", tmp_path, "", service="detector-llamafirewall",
        log_path="/var/log/llamafirewall_promptguard_raw.jsonl", output_suffix="promptguard_raw.jsonl",
        run_command=runner,
    )
    assert path.name == "detector-llamafirewall.promptguard_raw.jsonl"


def test_collect_thin_proxy_log_default_output_suffix_is_unchanged(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "exec", "-T", "detector", "cat", "/var/log/vendor_proxy.jsonl"): b"",
    })
    path = collect_thin_proxy_log(
        "case_008", tmp_path, "", service="detector",
        log_path="/var/log/vendor_proxy.jsonl", run_command=runner,
    )
    assert path.name == "detector.vendor_proxy.jsonl"
```

- [ ] **Step 2: Eseguire e verificare che il primo test fallisca**

Run: `python -m pytest tests/toy_agent/test_evidence.py -v -k output_suffix`
Expected: `test_collect_thin_proxy_log_uses_a_custom_output_suffix_when_given` FAILS
con `TypeError: collect_thin_proxy_log() got an unexpected keyword argument
'output_suffix'`. Il secondo test passa già (usa solo il default esistente).

- [ ] **Step 3: Implementare**

In `src/toy_agent/evidence.py`, sostituire la firma e il corpo di
`collect_thin_proxy_log`:

```python
def collect_thin_proxy_log(
    case_id: str,
    evidence_dir: Path,
    api_key: str,
    *,
    service: str,
    log_path: str,
    output_suffix: str = "vendor_proxy.jsonl",
    run_command: CommandRunner = default_command_runner,
) -> Path:
    """Retrieve the thin proxy's request/response log from inside `service`
    (already scrubbed at write time — this is defense in depth, not the
    only scrub point) and persist it under this case_id's evidence dir.
    `service`/`log_path` are resolved by the caller from the active vendor
    (sequence.py, via orchestrator.VENDOR_DETECTOR_CONFIG) — this function
    has no vendor knowledge of its own (design doc, 'Contratto riusabile
    del container detector', generalizzato oltre aidr in Fase 2).

    output_suffix (PromptGuard design doc, 2026-09-01): distinguishes a
    second call for the same case_id/service from the first — without it,
    two calls for the same service would both write to
    '<service>.vendor_proxy.jsonl', the second silently overwriting the
    first. Default preserves every caller that predates this parameter."""
    case_dir = evidence_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    raw = run_command(["docker", "compose", "exec", "-T", service, "cat", log_path])
    scrubbed = raw.replace(api_key.encode("utf-8"), b"[REDACTED]") if api_key else raw
    path = case_dir / f"{service}.{output_suffix}"
    path.write_bytes(scrubbed)
    return path
```

- [ ] **Step 4: Eseguire e verificare che tutti i test passino**

Run: `python -m pytest tests/toy_agent/test_evidence.py -v`
Expected: tutti PASS (le 3 assertion esistenti su `.vendor_proxy.jsonl` restano
valide col default invariato).

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/evidence.py tests/toy_agent/test_evidence.py
git commit -m "$(cat <<'EOF'
feat(evidence): add output_suffix to collect_thin_proxy_log

A second call for the same case_id/service (PromptGuard's log, alongside
AlignmentCheck's) would otherwise collide on the same output filename and
silently overwrite the first. Default preserves every existing caller.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `VENDOR_DETECTOR_CONFIG["llamafirewall-combined"]` + `secondary_log_path`

**Files:**
- Modify: `src/toy_agent/orchestrator.py`
- Test: `tests/toy_agent/test_orchestrator.py`

**Interfaces:**
- Consumes: nessuno nuovo.
- Produces: `VendorDetectorConfig.secondary_log_path: Optional[str] = None` (nuovo
  campo, default `None` per `aidr`/`llamafirewall`, invariati);
  `VENDOR_DETECTOR_CONFIG["llamafirewall-combined"]` — Task 3 (sequence.py) e Task 3
  (onboarding host-side) lo consumano.

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere a `tests/toy_agent/test_orchestrator.py`:

```python
def test_secondary_log_path_defaults_to_none_for_aidr_and_llamafirewall():
    assert VENDOR_DETECTOR_CONFIG["aidr"].secondary_log_path is None
    assert VENDOR_DETECTOR_CONFIG["llamafirewall"].secondary_log_path is None


def test_llamafirewall_combined_config_reuses_the_shared_detector_container():
    config = VENDOR_DETECTOR_CONFIG["llamafirewall-combined"]
    assert config.service == "detector-llamafirewall"
    assert config.module == "detector_adapter.vendors.llamafirewall.evaluate_case_combined"
    assert config.tool_name == "llamafirewall-combined"
    assert config.proxy_log_path == "/var/log/llamafirewall_proxy.jsonl"
    assert config.secondary_log_path == "/var/log/llamafirewall_promptguard_raw.jsonl"
    assert config.extra_pkill_pattern is None
    assert config.supports_technique_attribution is False
```

Extend the existing parametrized test:

```python
@pytest.mark.parametrize("vendor,expected_tool_name", [
    ("aidr", "aidr"),
    ("llamafirewall", "llamafirewall-alignmentcheck"),
    ("llamafirewall-combined", "llamafirewall-combined"),
])
def test_error_verdict_tool_name_matches_the_active_vendor(vendor, expected_tool_name):
    runner = ScriptedRunner([CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)])
    result = run_test_case(_TEST_CASE, command_index=0, vendor=vendor, run_command=runner)
    assert result["verdict"]["tool_name"] == expected_tool_name
```

- [ ] **Step 2: Eseguire e verificare che falliscano**

Run: `python -m pytest tests/toy_agent/test_orchestrator.py -v`
Expected: `test_llamafirewall_combined_config_reuses_the_shared_detector_container`
FAILS con `KeyError: 'llamafirewall-combined'`; il parametrized test FAILS sul
terzo caso con lo stesso `KeyError`; il primo nuovo test (`secondary_log_path
defaults`) FAILS con `AttributeError: 'VendorDetectorConfig' object has no
attribute 'secondary_log_path'`.

- [ ] **Step 3: Implementare**

In `src/toy_agent/orchestrator.py`, estendere il dataclass:

```python
@dataclass(frozen=True)
class VendorDetectorConfig:
    service: str
    module: str
    tool_name: str
    proxy_log_path: str
    extra_pkill_pattern: Optional[str]
    supports_technique_attribution: bool
    # A second thin-proxy-style log to collect alongside proxy_log_path, or
    # None when there isn't one (aidr, llamafirewall — both unchanged).
    # llamafirewall-combined uses it for PromptGuard's local (non-OpenRouter)
    # raw scan log — PromptGuard design doc, 2026-09-01.
    secondary_log_path: Optional[str] = None
```

E aggiungere la nuova voce al dizionario (dopo `"llamafirewall"`):

```python
    "llamafirewall-combined": VendorDetectorConfig(
        service="detector-llamafirewall",
        module="detector_adapter.vendors.llamafirewall.evaluate_case_combined",
        tool_name="llamafirewall-combined",
        proxy_log_path="/var/log/llamafirewall_proxy.jsonl",
        extra_pkill_pattern=None,
        # A fusion of two independent scanners, neither of which attributes
        # a technique — technique_detected stays None regardless of which
        # of the two determined the label (PromptGuard design doc,
        # 'Combinazione del Verdict').
        supports_technique_attribution=False,
        secondary_log_path="/var/log/llamafirewall_promptguard_raw.jsonl",
    ),
```

- [ ] **Step 4: Eseguire e verificare che tutti i test passino**

Run: `python -m pytest tests/toy_agent/test_orchestrator.py -v`
Expected: tutti PASS.

- [ ] **Step 5: Eseguire la suite intera per assicurarsi di non aver rotto nulla altrove**

Run: `python -m pytest -q`
Expected: nessun nuovo fallimento rispetto alla baseline (566 passed, 5 skipped
prima di questo piano).

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/orchestrator.py tests/toy_agent/test_orchestrator.py
git commit -m "$(cat <<'EOF'
feat(orchestrator): add llamafirewall-combined vendor + secondary_log_path

New VENDOR_DETECTOR_CONFIG entry routes --vendor llamafirewall-combined to
the same detector-llamafirewall container, a new evaluate_case_combined
module. secondary_log_path is a new optional field (default None, no
behavior change for aidr/llamafirewall) that a later task uses to collect
PromptGuard's local raw-scan log alongside the existing OpenRouter proxy log.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Collegare `llamafirewall-combined` a ogni tabella host-side indicizzata per vendor

**Files:**
- Modify: `src/toy_agent/preflight.py`
- Modify: `src/toy_agent/run_batch.py`
- Modify: `src/toy_agent/provenance.py`
- Test: `tests/toy_agent/test_preflight.py`
- Test: `tests/toy_agent/test_run_batch.py`
- Test: `tests/toy_agent/test_provenance.py`

**Interfaces:**
- Consumes: `VENDOR_DETECTOR_CONFIG["llamafirewall-combined"]` (Task 2, solo per
  contesto — queste 3 tabelle sono indipendenti da `VENDOR_DETECTOR_CONFIG`, non lo
  leggono).
- Produces: nessuna nuova interfaccia — chiude 3 `KeyError`/una perdita silenziosa
  di provenance che altrimenti si manifesterebbero al primo uso reale di `--vendor
  llamafirewall-combined` (vedi "Deviazioni dal design doc" in testa a questo
  piano).

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere a `tests/toy_agent/test_preflight.py`:

```python
def test_llamafirewall_combined_vendor_checks_the_same_tier_as_plain_llamafirewall():
    seen_models = []
    def handler(request: httpx.Request) -> httpx.Response:
        seen_models.append(json.loads(request.content)["model"])
        return httpx.Response(200, json={"choices": []})

    env = {"LLAMAFIREWALL_MODEL": "meta-llama/llama-3.3-70b-instruct", "AGENT_MODEL": "vendor/agent"}
    preflight_check_models(env, "sk-combined", vendor="llamafirewall-combined", agent_api_key="sk-agent", transport=httpx.MockTransport(handler))
    assert "meta-llama/llama-3.3-70b-instruct" in seen_models
```

Aggiungere a `tests/toy_agent/test_run_batch.py`:

```python
def test_api_key_env_var_by_vendor_has_an_entry_for_llamafirewall_combined():
    from toy_agent.run_batch import API_KEY_ENV_VAR_BY_VENDOR
    assert API_KEY_ENV_VAR_BY_VENDOR["llamafirewall-combined"] == "LLAMAFIREWALL_OPENROUTER_API_KEY"
```

Aggiungere a `tests/toy_agent/test_provenance.py`:

```python
def test_a_llamafirewall_combined_run_gets_the_same_fields_as_plain_llamafirewall():
    prov = provenance.collect_provenance({}, vendor="llamafirewall-combined")
    assert prov["vendor_commit"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["sifter_model"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["inspector_model"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["embed_model"] == provenance.NOT_APPLICABLE_FOR_VENDOR
    assert prov["llamafirewall_model"] == "(default in detector_adapter)"


def test_a_llamafirewall_combined_run_reads_the_shared_pip_pin(tmp_path):
    dockerfile = tmp_path / "docker" / "detector-llamafirewall" / "Dockerfile"
    dockerfile.parent.mkdir(parents=True)
    dockerfile.write_text("RUN pip install --no-cache-dir --no-deps llamafirewall==1.0.3\n", encoding="utf-8")
    prov = provenance.collect_provenance({}, vendor="llamafirewall-combined", repo_root=tmp_path)
    assert prov["vendor_pip_version"] == "1.0.3"
```

- [ ] **Step 2: Eseguire e verificare che falliscano**

Run: `python -m pytest tests/toy_agent/test_preflight.py tests/toy_agent/test_run_batch.py tests/toy_agent/test_provenance.py -v -k combined`
Expected: tutti e 4 i nuovi test FAIL — i primi due con `KeyError:
'llamafirewall-combined'`, gli ultimi due con assertion fallite (i campi sono
`None`, non i valori attesi, perché cadono nel ramo `else`).

- [ ] **Step 3: Implementare — `preflight.py`**

In `src/toy_agent/preflight.py`, aggiungere una voce identica a quella di
`"llamafirewall"` (stesso tier, stesso env var — PromptGuard non ha un modello
selezionabile via OpenRouter, solo AlignmentCheck ce l'ha):

```python
TIER_ENV_VARS_BY_VENDOR: dict[str, dict[str, str]] = {
    "aidr": {
        "sifter": "SIFTER_MODEL",
        "inspector": "INSPECTOR_MODEL",
        "embed": "EMBED_MODEL",
    },
    "llamafirewall": {
        "llamafirewall": "LLAMAFIREWALL_MODEL",
    },
    "llamafirewall-combined": {
        "llamafirewall": "LLAMAFIREWALL_MODEL",
    },
}
```

- [ ] **Step 4: Implementare — `run_batch.py`**

In `src/toy_agent/run_batch.py`, estendere `API_KEY_ENV_VAR_BY_VENDOR`:

```python
API_KEY_ENV_VAR_BY_VENDOR: dict[str, str] = {
    "aidr": "DETECTOR_OPENROUTER_API_KEY",
    "llamafirewall": "LLAMAFIREWALL_OPENROUTER_API_KEY",
    "llamafirewall-combined": "LLAMAFIREWALL_OPENROUTER_API_KEY",
}
```

- [ ] **Step 5: Implementare — `provenance.py`**

In `src/toy_agent/provenance.py::collect_provenance`, cambiare il ramo `elif
vendor == "llamafirewall":` per includere anche il vendor combinato (stessi campi,
stesso pip pin, stesso env var del modello — è la stessa immagine/pacchetto):

```python
    if vendor == "aidr":
        vendor_commit_value = vendor_commit(repo_root)
        vendor_pip_version_value = NOT_APPLICABLE_FOR_VENDOR
        sifter_model_value = env.get("SIFTER_MODEL") or "(default in detector_adapter)"
        inspector_model_value = env.get("INSPECTOR_MODEL") or "(default in detector_adapter)"
        embed_model_value = env.get("EMBED_MODEL") or "(default in detector_adapter)"
        llamafirewall_model_value = NOT_APPLICABLE_FOR_VENDOR
    elif vendor in ("llamafirewall", "llamafirewall-combined"):
        vendor_commit_value = NOT_APPLICABLE_FOR_VENDOR
        vendor_pip_version_value = llamafirewall_pip_version(repo_root)
        sifter_model_value = NOT_APPLICABLE_FOR_VENDOR
        inspector_model_value = NOT_APPLICABLE_FOR_VENDOR
        embed_model_value = NOT_APPLICABLE_FOR_VENDOR
        llamafirewall_model_value = env.get("LLAMAFIREWALL_MODEL") or "(default in detector_adapter)"
    else:
```

- [ ] **Step 6: Eseguire e verificare che tutti i test passino**

Run: `python -m pytest tests/toy_agent/test_preflight.py tests/toy_agent/test_run_batch.py tests/toy_agent/test_provenance.py -v`
Expected: tutti PASS, nessuna regressione sui test `aidr`/`llamafirewall` esistenti.

- [ ] **Step 7: Suite intera**

Run: `python -m pytest -q`
Expected: nessun nuovo fallimento.

- [ ] **Step 8: Commit**

```bash
git add src/toy_agent/preflight.py src/toy_agent/run_batch.py src/toy_agent/provenance.py \
        tests/toy_agent/test_preflight.py tests/toy_agent/test_run_batch.py tests/toy_agent/test_provenance.py
git commit -m "$(cat <<'EOF'
fix(orchestration): wire llamafirewall-combined into every vendor-keyed table

TIER_ENV_VARS_BY_VENDOR, API_KEY_ENV_VAR_BY_VENDOR, and
provenance.collect_provenance() each index by vendor string without a
default — --vendor llamafirewall-combined would have raised KeyError (the
first two) or silently published None provenance (the third) at first real
use. Found reading the code while writing the implementation plan, not
mentioned in the design doc (it focused on the Verdict fusion, not every
host-side vendor table).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `sequence.py` — raccogliere il secondo log quando `secondary_log_path` è configurato

**Files:**
- Modify: `src/toy_agent/sequence.py`
- Test: `tests/toy_agent/test_sequence.py`

**Interfaces:**
- Consumes: `VendorDetectorConfig.secondary_log_path` (Task 2),
  `evidence.collect_thin_proxy_log(..., output_suffix=...)` (Task 1).
- Produces: una seconda chiamata a `collect_thin_proxy_log_fn` per caso, solo
  quando `config.secondary_log_path is not None` — nessun cambiamento per `aidr`/
  `llamafirewall` (`secondary_log_path=None` per entrambi).

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere a `tests/toy_agent/test_sequence.py` (vicino a
`RecordingProxyLogCollector`, senza modificarla — nuova classe dedicata a questo
task per non toccare il fake condiviso da tutti gli altri test del file):

```python
class RecordingProxyLogCollectorWithSuffix:
    def __init__(self):
        self.calls = []

    def __call__(self, case_id, evidence_dir, api_key, *, service, log_path, output_suffix="vendor_proxy.jsonl"):
        self.calls.append((case_id, service, log_path, output_suffix))
        return evidence_dir / case_id / f"{service}.{output_suffix}"


def test_execute_sequence_collects_a_second_log_when_secondary_log_path_is_configured(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence_llamafirewall(["c1"])  # opens detector-llamafirewall, same service llamafirewall-combined uses
    runner = ScriptedRunTestCase([_ok_result("c1")])
    proxy_collector = RecordingProxyLogCollectorWithSuffix()

    execute_sequence(steps, dataset, tmp_path, vendor="llamafirewall-combined", run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=proxy_collector,
                      run_command=NoOpCommandRunner())

    assert proxy_collector.calls == [
        ("c1", "detector-llamafirewall", "/var/log/llamafirewall_proxy.jsonl", "vendor_proxy.jsonl"),
        ("c1", "detector-llamafirewall", "/var/log/llamafirewall_promptguard_raw.jsonl", "promptguard_raw.jsonl"),
    ]


def test_execute_sequence_does_not_collect_a_second_log_when_secondary_log_path_is_none(tmp_path):
    dataset = {"c1": _ground_truth("c1")}
    steps = _reused_sequence(["c1"])  # vendor="aidr" below, secondary_log_path=None
    runner = ScriptedRunTestCase([_ok_result("c1")])
    proxy_collector = RecordingProxyLogCollectorWithSuffix()

    execute_sequence(steps, dataset, tmp_path, vendor="aidr", run_test_case_fn=runner,
                      collect_case_evidence_fn=RecordingEvidenceCollector(),
                      collect_thin_proxy_log_fn=proxy_collector,
                      run_command=NoOpCommandRunner())

    assert len(proxy_collector.calls) == 1
```

- [ ] **Step 2: Eseguire e verificare che falliscano**

Run: `python -m pytest tests/toy_agent/test_sequence.py -v -k secondary_log_path`
Expected: il primo test FAILS (`proxy_collector.calls` ha solo 1 elemento, non 2 —
la seconda chiamata non esiste ancora); il secondo test PASSES già (nessun
comportamento nuovo da esercitare per `aidr`).

- [ ] **Step 3: Implementare**

In `src/toy_agent/sequence.py`, subito dopo la riga esistente
`proxy_log_path = collect_thin_proxy_log_fn(case_id, run_output_dir, api_key,
service=config.service, log_path=config.proxy_log_path)`:

```python
            proxy_log_path = collect_thin_proxy_log_fn(case_id, run_output_dir, api_key, service=config.service, log_path=config.proxy_log_path)
            if config.secondary_log_path is not None:
                collect_thin_proxy_log_fn(
                    case_id, run_output_dir, api_key,
                    service=config.service, log_path=config.secondary_log_path,
                    output_suffix="promptguard_raw.jsonl",
                )
            if max_cost_usd is not None:
```

(la riga `if max_cost_usd is not None:` è quella già esistente subito dopo — questo
step la inserisce in mezzo, non la sostituisce.)

- [ ] **Step 4: Eseguire e verificare che tutti i test passino**

Run: `python -m pytest tests/toy_agent/test_sequence.py -v`
Expected: tutti PASS, inclusi tutti i test preesistenti che usano
`RecordingProxyLogCollector`/`WritingProxyLogCollector` con vendor `aidr`/
`llamafirewall` (nessuno di quei fake viene toccato da questo task).

- [ ] **Step 5: Suite intera**

Run: `python -m pytest -q`
Expected: nessun nuovo fallimento.

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/sequence.py tests/toy_agent/test_sequence.py
git commit -m "$(cat <<'EOF'
feat(sequence): collect a second thin-proxy log when secondary_log_path is set

Reuses collect_thin_proxy_log (Task 1's output_suffix) for PromptGuard's
local raw-scan log, alongside the existing AlignmentCheck OpenRouter proxy
log — only when the active vendor's config declares one (today: only
llamafirewall-combined). aidr and plain llamafirewall are unaffected
(secondary_log_path=None for both).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `adapter.py` — funzioni pure di fusione (`aggregate_promptguard_turns`, `combine_scan_results_to_verdict`, `combined_error_verdict`)

**Files:**
- Modify: `src/detector_adapter/vendors/llamafirewall/adapter.py`
- Test: `tests/detector_adapter/test_llamafirewall_adapter_combined.py` (nuovo)

**Interfaces:**
- Consumes: nessuna dipendenza da `llamafirewall` installato — tutti duck-typed
  (stessa convenzione di `scan_decision_to_verdict` esistente: confronto su
  `.decision.value`/stringa, mai `isinstance`).
- Produces:
  - `TOOL_NAME_COMBINED = "llamafirewall-combined"`
  - `aggregate_promptguard_turns(pg_turn_results: list) -> tuple[str, float]`
  - `combine_scan_results_to_verdict(case_id: str, ac_result: Any,
    pg_decision_value: str, pg_score: float, pg_turn_results: list,
    ac_latency_s: float, pg_latency_s: float) -> dict`
  - `combined_error_verdict(case_id: str, source: str, exception_class: str |
    None) -> dict` — `source` è `"alignmentcheck"` o `"promptguard"`.
  Task 6 (`evaluate_case_combined.py`) consuma tutte e quattro.

- [ ] **Step 1: Scrivere i test che falliscono**

Creare `tests/detector_adapter/test_llamafirewall_adapter_combined.py`:

```python
from types import SimpleNamespace

import pytest

from detector_adapter.vendors.llamafirewall.adapter import (
    TOOL_NAME_COMBINED,
    aggregate_promptguard_turns,
    combine_scan_results_to_verdict,
    combined_error_verdict,
)


def _ac_result(decision_value="allow", reason="AC default", score=0.0):
    return SimpleNamespace(decision=SimpleNamespace(value=decision_value), reason=reason, score=score)


def _pg_turn(decision_value="allow", reason="No prompt injection detected", score=0.0):
    return SimpleNamespace(decision=SimpleNamespace(value=decision_value), reason=reason, score=score)


# --- aggregate_promptguard_turns ---

def test_aggregate_returns_allow_and_zero_score_for_no_turns():
    decision, score = aggregate_promptguard_turns([])
    assert decision == "allow"
    assert score == 0.0


def test_aggregate_takes_the_max_score_not_the_last_turn():
    turns = [_pg_turn(score=0.95), _pg_turn(score=0.1)]
    decision, score = aggregate_promptguard_turns(turns)
    assert score == 0.95


def test_aggregate_blocks_if_any_turn_blocks_even_if_not_the_last():
    turns = [_pg_turn(decision_value="block", score=0.95), _pg_turn(decision_value="allow", score=0.1)]
    decision, score = aggregate_promptguard_turns(turns)
    assert decision == "block"


def test_aggregate_allows_when_no_turn_blocks():
    turns = [_pg_turn(decision_value="allow", score=0.3), _pg_turn(decision_value="allow", score=0.4)]
    decision, score = aggregate_promptguard_turns(turns)
    assert decision == "allow"


# --- combine_scan_results_to_verdict ---

def test_label_is_malicious_when_only_alignmentcheck_flags():
    v = combine_scan_results_to_verdict(
        "c1", _ac_result(decision_value="human_in_the_loop_required", score=1.0), "allow", 0.1,
        [_pg_turn(score=0.1)], 1.0, 0.5,
    )
    assert v["label"] == "malicious"


def test_label_is_malicious_when_only_promptguard_flags():
    v = combine_scan_results_to_verdict(
        "c2", _ac_result(decision_value="allow", score=0.0), "block", 0.95,
        [_pg_turn(decision_value="block", reason="likely injection", score=0.95)], 1.0, 0.5,
    )
    assert v["label"] == "malicious"


def test_label_is_benign_when_neither_flags():
    v = combine_scan_results_to_verdict(
        "c3", _ac_result(decision_value="allow", score=0.0), "allow", 0.2,
        [_pg_turn(score=0.2)], 1.0, 0.5,
    )
    assert v["label"] == "benign"


def test_confidence_is_the_max_of_the_two_scores_even_when_benign():
    v = combine_scan_results_to_verdict(
        "c4", _ac_result(decision_value="allow", score=0.3), "allow", 0.7,
        [_pg_turn(score=0.7)], 1.0, 0.5,
    )
    assert v["confidence"] == 0.7


def test_rationale_always_contains_both_labeled_halves():
    v = combine_scan_results_to_verdict(
        "c5", _ac_result(reason="Observation: ...\nConclusion: False"), "allow", 0.0,
        [_pg_turn(reason="No prompt injection detected")], 1.0, 0.5,
    )
    assert "AlignmentCheck: Observation: ...\nConclusion: False" in v["rationale"]
    assert "PromptGuard: No prompt injection detected" in v["rationale"]


def test_technique_detected_is_always_none_even_when_promptguard_flags():
    v = combine_scan_results_to_verdict(
        "c6", _ac_result(decision_value="allow", score=0.0), "block", 0.95,
        [_pg_turn(decision_value="block", score=0.95)], 1.0, 0.5,
    )
    assert v["technique_detected"] is None


def test_latency_s_is_the_sum_of_both_measured_latencies():
    v = combine_scan_results_to_verdict("c7", _ac_result(), "allow", 0.0, [_pg_turn()], 1.2, 0.8)
    assert v["latency_s"] == pytest.approx(2.0)


def test_tool_name_is_the_combined_constant():
    v = combine_scan_results_to_verdict("c8", _ac_result(), "allow", 0.0, [_pg_turn()], 1.0, 0.5)
    assert v["tool_name"] == TOOL_NAME_COMBINED == "llamafirewall-combined"


def test_status_is_ok_on_the_normal_path():
    v = combine_scan_results_to_verdict("c9", _ac_result(), "allow", 0.0, [_pg_turn()], 1.0, 0.5)
    assert v["status"] == "ok"


def test_cost_usd_is_always_none():
    v = combine_scan_results_to_verdict("c10", _ac_result(), "allow", 0.0, [_pg_turn()], 1.0, 0.5)
    assert v["cost_usd"] is None


# --- combined_error_verdict ---

def test_combined_error_verdict_labels_alignmentcheck_failure_as_vendor_fail_open():
    v = combined_error_verdict("c11", "alignmentcheck", "RuntimeError")
    assert v["status"] == "error"
    assert v["label"] is None
    assert "vendor fail-open: RuntimeError" in v["rationale"]
    assert v["tool_name"] == TOOL_NAME_COMBINED


def test_combined_error_verdict_labels_promptguard_failure_as_local_dependency_error():
    v = combined_error_verdict("c12", "promptguard", "OutOfMemoryError")
    assert v["status"] == "error"
    assert v["label"] is None
    assert "local dependency error: OutOfMemoryError" in v["rationale"]


def test_combined_error_verdict_rejects_an_unknown_source():
    with pytest.raises(ValueError, match="unknown source"):
        combined_error_verdict("c13", "something-else", None)
```

- [ ] **Step 2: Eseguire e verificare che falliscano**

Run: `python -m pytest tests/detector_adapter/test_llamafirewall_adapter_combined.py -v`
Expected: `ImportError`/`ModuleNotFoundError` sui simboli non ancora esistenti
(`TOOL_NAME_COMBINED`, `aggregate_promptguard_turns`,
`combine_scan_results_to_verdict`, `combined_error_verdict`) — tutti i test
falliscono in collection.

- [ ] **Step 3: Implementare**

In `src/detector_adapter/vendors/llamafirewall/adapter.py`, aggiungere (dopo
`transcript_dict_to_trace`, prima del blocco `try: from llamafirewall import
...` — stessa zona "nessuna dipendenza da llamafirewall installato" già in uso da
`scan_decision_to_verdict`):

```python
TOOL_NAME_COMBINED = "llamafirewall-combined"


def aggregate_promptguard_turns(pg_turn_results: list) -> tuple[str, float]:
    """Aggregate one ScanResult per scanned Role.USER turn into a single
    (decision_value, score) pair for the whole case — max/any, never
    scan_replay()'s own last-message-wins default (design doc, 'Architettura
    / Data flow', risk finding #2 post-council: scan_replay() would have
    silently reported whichever turn was scanned last, almost always an
    assistant/tool turn with no PromptGuard signal at all, since only
    Role.USER turns are ever scanned here). decision is compared by .value
    (a plain string) — same duck-typing convention as
    scan_decision_to_verdict, never requires llamafirewall importable."""
    decisions = [getattr(r.decision, "value", r.decision) for r in pg_turn_results]
    score = max((r.score for r in pg_turn_results), default=0.0)
    return ("block" if "block" in decisions else "allow"), score


def combine_scan_results_to_verdict(
    case_id: str,
    ac_result: Any,
    pg_decision_value: str,
    pg_score: float,
    pg_turn_results: list,
    ac_latency_s: float,
    pg_latency_s: float,
) -> dict:
    """Fuse one AlignmentCheck ScanResult and the aggregated PromptGuard
    decision/score (aggregate_promptguard_turns) into a single Verdict dict
    (design doc, 'Combinazione del Verdict'). OR on the label, max on the
    confidence — a fusion policy of this project's own, not inherited from
    any vendor arbitration (no cross-role arbitration exists in the vendor
    for two independently-registered scanners, verified in
    docs/research/2026-08-29-llamafirewall-promptguard-not-wired.md).
    technique_detected stays None unconditionally: PromptGuard is a binary
    classifier with no technique attribution by construction, regardless of
    which of the two scanners determined the label (skeptic finding,
    design doc)."""
    ac_decision_value = getattr(ac_result.decision, "value", ac_result.decision)
    is_malicious = ac_decision_value == "human_in_the_loop_required" or pg_decision_value == "block"
    pg_reason = max(pg_turn_results, key=lambda r: r.score).reason if pg_turn_results else "no user turn scanned"
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME_COMBINED,
        "status": "ok",
        "label": "malicious" if is_malicious else "benign",
        "confidence": max(ac_result.score, pg_score),
        "technique_detected": None,
        "rationale": f"AlignmentCheck: {ac_result.reason or 'n/a'} | PromptGuard: {pg_reason}",
        "cost_usd": None,
        "latency_s": ac_latency_s + pg_latency_s,
        "in_tokens": None,
        "out_tokens": None,
    }


def combined_error_verdict(case_id: str, source: str, exception_class: str | None) -> dict:
    """Verdict for either scan failing inside evaluate_case_combined.py — the
    whole case becomes status='error'/label=None regardless of which of the
    two scanners failed (never a Verdict based on the one that survived,
    design doc 'Gestione errori': that would silently inflate LlamaFirewall's
    measured coverage on a case where only half the product responded).
    `source` distinguishes a vendor fail-open (AlignmentCheck's remote LLM
    call) from a local dependency error (PromptGuard's torch/transformers
    stack) in the rationale text only — the Verdict shape is identical
    either way (skeptic finding, design doc 'Gestione errori')."""
    if source == "alignmentcheck":
        detail = f"vendor fail-open: {exception_class}" if exception_class else "vendor fail-open"
    elif source == "promptguard":
        detail = f"local dependency error: {exception_class}" if exception_class else "local dependency error"
    else:
        raise ValueError(f"unknown source: {source!r}")
    return {
        "case_id": case_id,
        "tool_name": TOOL_NAME_COMBINED,
        "status": "error",
        "label": None,
        "confidence": None,
        "technique_detected": None,
        "rationale": detail,
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }
```

- [ ] **Step 4: Eseguire e verificare che tutti i test passino**

Run: `python -m pytest tests/detector_adapter/test_llamafirewall_adapter_combined.py -v`
Expected: tutti PASS.

- [ ] **Step 5: Suite intera**

Run: `python -m pytest -q`
Expected: nessun nuovo fallimento (questi test girano nella suite principale,
nessuna dipendenza da `llamafirewall` installato).

- [ ] **Step 6: Commit**

```bash
git add src/detector_adapter/vendors/llamafirewall/adapter.py \
        tests/detector_adapter/test_llamafirewall_adapter_combined.py
git commit -m "$(cat <<'EOF'
feat(llamafirewall): add pure Verdict-fusion functions to adapter.py

aggregate_promptguard_turns (max/any across scanned user turns, not
scan_replay()'s last-message-wins), combine_scan_results_to_verdict (OR on
label, max on confidence, both rationale halves always present), and
combined_error_verdict (distinguishes a vendor fail-open from a local
dependency error in the rationale text, same error Verdict shape either
way). All duck-typed, no llamafirewall import required — same convention as
the existing scan_decision_to_verdict. Existing
llamafirewall-alignmentcheck code (TOOL_NAME, scan_decision_to_verdict,
fail_open_verdict) is untouched.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `evaluate_case_combined.py` — entry point reale, test gated, `run_adapter_tests.sh`

**Files:**
- Create: `src/detector_adapter/vendors/llamafirewall/evaluate_case_combined.py`
- Create: `tests/detector_adapter/test_llamafirewall_evaluate_case_combined.py`
- Modify: `docker/detector-llamafirewall/run_adapter_tests.sh`

**Interfaces:**
- Consumes: `adapter.py`'s `OpenRouterAlignmentCheck`, `TOOL_NAME`,
  `aggregate_promptguard_turns`, `combine_scan_results_to_verdict`,
  `combined_error_verdict`, `transcript_dict_to_trace` (Task 5 + esistenti); dal
  vendor reale (a runtime, mai a import-time): `LlamaFirewall`, `Role`,
  `ScannerType`, `create_scanner`.
- Produces: `run_evaluate_case_combined(data: dict) -> dict` (stesso contratto di
  `run_evaluate_case` esistente: stdin transcript JSON → un Verdict dict);
  `main()` (stdout un Verdict JSON) — `VENDOR_DETECTOR_CONFIG["llamafirewall-
  combined"].module` (Task 2) punta già a questo modulo.

Questo task richiede `llamafirewall` installato per essere eseguito per davvero —
i suoi test sono **gated** (`pytest.importorskip`), stessa convenzione degli altri
test in `tests/detector_adapter/test_llamafirewall_adapter_failopen.py` e
`test_llamafirewall_adapter_construction.py`, non girano nella suite principale su
un host senza `llamafirewall` pip-installato, girano dentro il container
`detector-llamafirewall` via `run_adapter_tests.sh` (che dopo Task 0 ha anche il
modello PromptGuard baked).

- [ ] **Step 1: Creare il file di produzione (senza ancora i test — struttura prima, poi TDD sui comportamenti)**

Creare `src/detector_adapter/vendors/llamafirewall/evaluate_case_combined.py`:

```python
from __future__ import annotations

import asyncio
import json
import sys
import time

from .adapter import (
    OpenRouterAlignmentCheck,
    TOOL_NAME,
    aggregate_promptguard_turns,
    combine_scan_results_to_verdict,
    combined_error_verdict,
    transcript_dict_to_trace,
)

# A module-level constant so tests can monkeypatch it (module attribute
# lookup happens at call time inside _append_secondary_log, not captured as
# a default argument) — same shape as OpenRouterAlignmentCheck's class-level
# flags being readable/settable from outside the instance that set them.
SECONDARY_LOG_PATH = "/var/log/llamafirewall_promptguard_raw.jsonl"


def _append_secondary_log(text: str, result, threshold: float) -> None:
    decision_value = getattr(result.decision, "value", result.decision)
    entry = {"text": text, "score": result.score, "threshold": threshold, "decision": decision_value}
    with open(SECONDARY_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def run_evaluate_case_combined(data: dict) -> dict:
    from llamafirewall import LlamaFirewall, Role, ScannerType, create_scanner

    case_id = data["session_id"]
    trace = transcript_dict_to_trace(data)

    OpenRouterAlignmentCheck.fail_open_detected = False
    OpenRouterAlignmentCheck.fail_open_exception_class = None

    firewall = LlamaFirewall(scanners={Role.ASSISTANT: [TOOL_NAME]})
    t0 = time.perf_counter()
    try:
        ac_result = firewall.scan_replay(trace)
    except Exception as exc:
        return combined_error_verdict(case_id, "alignmentcheck", exc.__class__.__name__)
    ac_latency_s = time.perf_counter() - t0

    if OpenRouterAlignmentCheck.fail_open_detected:
        return combined_error_verdict(case_id, "alignmentcheck", OpenRouterAlignmentCheck.fail_open_exception_class)

    pg_scanner = create_scanner(ScannerType.PROMPT_GUARD)
    pg_turn_results = []
    t0 = time.perf_counter()
    try:
        for ix, msg in enumerate(trace):
            if msg.role == Role.USER:
                past = trace[:ix] or None
                result = asyncio.run(pg_scanner.scan(msg, past))
                pg_turn_results.append(result)
                _append_secondary_log(msg.content, result, pg_scanner.block_threshold)
    except Exception as exc:
        return combined_error_verdict(case_id, "promptguard", exc.__class__.__name__)
    pg_latency_s = time.perf_counter() - t0

    pg_decision_value, pg_score = aggregate_promptguard_turns(pg_turn_results)
    return combine_scan_results_to_verdict(
        case_id, ac_result, pg_decision_value, pg_score, pg_turn_results, ac_latency_s, pg_latency_s,
    )


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        result = run_evaluate_case_combined(data)
    except Exception as exc:
        print(f"evaluate_case_combined failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Scrivere i test gated che falliscono**

Creare `tests/detector_adapter/test_llamafirewall_evaluate_case_combined.py`:

```python
import json

import pytest

pytest.importorskip("llamafirewall", reason="llamafirewall is only installed inside the detector-llamafirewall container")

from llamafirewall import ScanDecision, ScanResult, ScanStatus

from detector_adapter.vendors.llamafirewall import evaluate_case_combined
from detector_adapter.vendors.llamafirewall.adapter import AlignmentCheckOutputSchema, OpenRouterAlignmentCheck

_DATA = {
    "session_id": "c1",
    "turns": [
        {"seq": 0, "role": "user", "content": "Summarize the news.", "tool_call": None},
        {"seq": 1, "role": "assistant", "content": "Here is a summary.", "tool_call": None},
    ],
}


def test_reports_ok_with_promptguard_running_for_real(monkeypatch):
    # AlignmentCheck's remote LLM call is mocked (no real OpenRouter call in
    # tests, same convention as the existing failopen/construction gated
    # tests); PromptGuard runs for real against the baked model — this is
    # the one test in this suite whose unique purpose is exercising the
    # real PromptGuardScanner/model (design doc, 'Test — cosa e perché',
    # item 4).
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _ac_ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ac_ok)
    OpenRouterAlignmentCheck.fail_open_detected = False

    verdict = evaluate_case_combined.run_evaluate_case_combined(_DATA)
    assert verdict["status"] == "ok"
    assert verdict["technique_detected"] is None
    assert verdict["latency_s"] > 0
    assert "AlignmentCheck:" in verdict["rationale"] and "PromptGuard:" in verdict["rationale"]


def test_reports_error_when_alignmentcheck_fail_opens(monkeypatch):
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _raise(self, *a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(LLMClient, "call", _raise)
    OpenRouterAlignmentCheck.fail_open_detected = False

    verdict = evaluate_case_combined.run_evaluate_case_combined(_DATA)
    assert verdict["status"] == "error"
    assert verdict["label"] is None
    assert "vendor fail-open" in verdict["rationale"]


def test_reports_error_when_promptguard_raises(monkeypatch):
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")

    async def _ac_ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ac_ok)
    OpenRouterAlignmentCheck.fail_open_detected = False

    async def _pg_raise(self, message, past_trace=None):
        raise RuntimeError("torch OOM")
    monkeypatch.setattr("llamafirewall.scanners.prompt_guard_scanner.PromptGuardScanner.scan", _pg_raise)

    verdict = evaluate_case_combined.run_evaluate_case_combined(_DATA)
    assert verdict["status"] == "error"
    assert verdict["label"] is None
    assert "local dependency error: RuntimeError" in verdict["rationale"]


def test_writes_a_secondary_log_line_per_user_turn_scanned(monkeypatch, tmp_path):
    from llamafirewall.utils.base_llm import LLMClient

    monkeypatch.setenv("LLAMAFIREWALL_OPENROUTER_API_KEY", "sk-test-not-real")
    log_path = tmp_path / "pg_raw.jsonl"
    monkeypatch.setattr(evaluate_case_combined, "SECONDARY_LOG_PATH", str(log_path))

    async def _ac_ok(self, *a, **kw):
        return AlignmentCheckOutputSchema(observation="o", thought="t", conclusion=False)
    monkeypatch.setattr(LLMClient, "call", _ac_ok)
    OpenRouterAlignmentCheck.fail_open_detected = False

    evaluate_case_combined.run_evaluate_case_combined(_DATA)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1  # exactly one Role.USER turn in _DATA
    entry = json.loads(lines[0])
    assert entry["text"] == "Summarize the news."
    assert isinstance(entry["score"], float)
    assert entry["decision"] in ("allow", "block")
```

- [ ] **Step 3: Aggiungere i nuovi test alla copia di `run_adapter_tests.sh`**

Modificare `docker/detector-llamafirewall/run_adapter_tests.sh`, aggiungendo il
nuovo file all'elenco `for f in ...`:

```sh
for f in test_llamafirewall_adapter_normalization.py \
         test_llamafirewall_adapter_serialization.py \
         test_llamafirewall_adapter_construction.py \
         test_llamafirewall_adapter_failopen.py \
         test_llamafirewall_adapter_combined.py \
         test_llamafirewall_evaluate_case_combined.py \
         test_llamafirewall_openrouter_proxy.py; do
```

(`test_llamafirewall_adapter_combined.py`, Task 5, non richiede `llamafirewall`
per girare nella suite principale, ma copiarlo qui non fa danno e tiene il gated
runner allineato a "tutti i test llamafirewall del pacchetto".)

- [ ] **Step 4: Eseguire i test gated dentro il container (richiede lo stack Docker attivo e l'immagine di Task 0)**

```bash
docker compose up -d detector-llamafirewall
sh docker/detector-llamafirewall/run_adapter_tests.sh
```

Expected: tutti i test copiati PASS, inclusi i 4 nuovi di questo task. Se
`llamafirewall`/`torch` non risultano importabili nel container, Task 0 non è
stato completato correttamente — tornare lì, non aggiustare qui.

- [ ] **Step 5: Verificare che la suite principale (senza `llamafirewall` installato) non sia stata rotta**

Run: `python -m pytest -q`
Expected: nessun nuovo fallimento — i 4 nuovi test in
`test_llamafirewall_evaluate_case_combined.py` vengono SKIPPED (nessun
`llamafirewall` installato sull'host), non FAILED.

- [ ] **Step 6: Commit**

```bash
git add src/detector_adapter/vendors/llamafirewall/evaluate_case_combined.py \
        tests/detector_adapter/test_llamafirewall_evaluate_case_combined.py \
        docker/detector-llamafirewall/run_adapter_tests.sh
git commit -m "$(cat <<'EOF'
feat(llamafirewall): add evaluate_case_combined entry point

Orchestrates AlignmentCheck (scan_replay(), unchanged) and PromptGuard
(direct scanner invocation, aggregated by adapter.aggregate_promptguard_turns
— never scan_replay(), which would silently zero out PromptGuard's score on
the non-blocking case). Writes one raw-scan JSONL line per scanned user turn
to SECONDARY_LOG_PATH. Gated tests run inside detector-llamafirewall via
run_adapter_tests.sh, now updated to include them — one test exercises the
real baked PromptGuard model, not a mock.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Nota di methodology automatica nel report per `llamafirewall-combined`

**Files:**
- Modify: `src/toy_agent/run_batch.py`
- Modify: `src/toy_agent/regenerate_report.py`
- Test: `tests/toy_agent/test_run_batch.py`

**Interfaces:**
- Consumes: `_setup_notes(...)` esistente (estesa con un parametro opzionale).
- Produces: `_setup_notes(result, agent_timeout_s, detector_timeout_s,
  breaker_threshold, prov=None, vendor="")` — con `vendor="llamafirewall-combined"`
  aggiunge una nota che finisce, invariata, nella sezione "Methodology and
  Limitations" del report (`report.py` già la stampa via `setup_notes`, nessun
  cambiamento a `report.py`). Chiude il finding "advocate" del council
  (metodologia non ancora automatizzata nel report).

- [ ] **Step 1: Scrivere i test che falliscono**

Aggiungere a `tests/toy_agent/test_run_batch.py`:

```python
def test_setup_notes_declares_the_fusion_methodology_note_for_llamafirewall_combined():
    from toy_agent.run_batch import BatchResult, _setup_notes
    result = BatchResult(cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False)
    notes = _setup_notes(result, 120.0, 180.0, 3, vendor="llamafirewall-combined")
    assert "fuses two independent LlamaFirewall scanners" in notes
    assert "AlignmentCheck + PromptGuard" in notes


def test_setup_notes_omits_the_fusion_methodology_note_for_other_vendors():
    from toy_agent.run_batch import BatchResult, _setup_notes
    result = BatchResult(cases=[], verdicts=[], total_count=0, executed_count=0, breaker_tripped=False)
    for vendor_kwargs in ({"vendor": "llamafirewall"}, {"vendor": "aidr"}, {}):
        notes = _setup_notes(result, 120.0, 180.0, 3, **vendor_kwargs)
        assert "fuses two independent LlamaFirewall scanners" not in notes
```

- [ ] **Step 2: Eseguire e verificare che il primo fallisca**

Run: `python -m pytest tests/toy_agent/test_run_batch.py -v -k fusion_methodology`
Expected:
`test_setup_notes_declares_the_fusion_methodology_note_for_llamafirewall_combined`
FAILS (`TypeError: _setup_notes() got an unexpected keyword argument 'vendor'`);
`test_setup_notes_omits_the_fusion_methodology_note_for_other_vendors` PASSES già
(nessuna nota da omettere ancora esiste).

- [ ] **Step 3: Implementare**

In `src/toy_agent/run_batch.py`, cambiare la firma di `_setup_notes` aggiungendo
`vendor: str = ""` in coda (default vuoto — ogni chiamata esistente nei test
preesistenti, che non passa questo argomento, resta invariata), e aggiungere,
subito prima di `return " | ".join(notes)`:

```python
def _setup_notes(result: BatchResult, agent_timeout_s: float, detector_timeout_s: float, breaker_threshold: int, prov: dict | None = None, vendor: str = "") -> str:
```

```python
    if vendor == "llamafirewall-combined":
        notes.append(
            "methodology: this Verdict fuses two independent LlamaFirewall scanners "
            "(AlignmentCheck + PromptGuard) into one label/confidence via an OR/max "
            "policy of this project's own — not a third independent scanner "
            "(docs/design/2026-09-01-llamafirewall-promptguard-design.md, "
            "'Combinazione del Verdict')"
        )
    return " | ".join(notes)
```

Aggiornare i due call site perché passino `vendor` esplicitamente (entrambi hanno
già `vendor` in scope):

`src/toy_agent/run_batch.py` (dentro `main()`):
```python
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD, prov, vendor=vendor)
```

`src/toy_agent/regenerate_report.py`:
```python
    setup_notes = _setup_notes(result, AGENT_TIMEOUT_S, DETECTOR_TIMEOUT_S, BREAKER_THRESHOLD, prov, vendor=vendor)
```

- [ ] **Step 4: Eseguire e verificare che tutti i test passino**

Run: `python -m pytest tests/toy_agent/test_run_batch.py tests/toy_agent/test_regenerate_report.py -v`
Expected: tutti PASS, inclusi tutti i test preesistenti di `_setup_notes` che non
passano `vendor` (default `""`, nessuna nota aggiunta, comportamento identico a
prima).

- [ ] **Step 5: Suite intera**

Run: `python -m pytest -q`
Expected: nessun nuovo fallimento.

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/run_batch.py src/toy_agent/regenerate_report.py tests/toy_agent/test_run_batch.py
git commit -m "$(cat <<'EOF'
feat(report): auto-declare the AlignmentCheck+PromptGuard fusion methodology

_setup_notes gains an optional vendor param (default "", every existing
caller unaffected); a llamafirewall-combined run now automatically carries
a Methodology-section note in its report saying the Verdict fuses two
scanners, not a third independent one — closes the council advocate's
non-blocking finding without relying on a human remembering to write it by
hand each time.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Registrare i limiti dichiarati, chiudere il paragrafo "Prossimo passo" in `registro-limiti-aperti.md`

**Files:**
- Modify: `docs/design/registro-limiti-aperti.md`
- Modify: `CONTEXT.md`

**Interfaces:**
- Consumes: nessuna — task di sola documentazione, a codice già mergiato.
- Produces: nessuna interfaccia nuova.

- [ ] **Step 1: Rimuovere il paragrafo chiuso**

Nella voce esistente "Copertura delle categorie native di LlamaFirewall...",
rimuovere per intero la frase (l'ultima del paragrafo che inizia con "Prossimo
passo"):

```
Prossimo passo
(non ancora scopato): attivare `PROMPT_GUARD` nel container (`torch`/`transformers`/
`huggingface_hub` mancanti, accesso HF gated da ottenere, una seconda chiamata `scan()`
per turno utente da affiancare a `scan_replay()`, decidere come i due verdetti confluiscono
in un unico `Verdict`) prima di decidere se/come ridisegnare l'esperimento "judge-targeted".
```

— convenzione del registro dichiarata nel design doc: un item chiuso da un lavoro
successivo si rimuove per intero, non si spunta.

- [ ] **Step 2: Aggiungere la convenzione di naming per una futura directory di report**

Aggiungere in `CONTEXT.md`, in coda al bullet esistente `- LlamaFirewall combinato
(...) → `tool_name = "llamafirewall-combined"`.` (già presente da commit `2d82e63`
— non riscrivere il bullet, solo aggiungere una frase alla fine):

```
Un futuro report di questo vendor va salvato sotto `docs/reports/llamafirewall-combined-YYYY-MM-DD/`, mai `docs/reports/llamafirewall-YYYY-MM-DD/` (che resta riservato ad `llamafirewall-alignmentcheck`) — stessa convenzione di naming già in uso per `aidr-YYYY-MM-DD`/`llamafirewall-YYYY-MM-DD`, così la distinzione tra i due tool è visibile dal nome della directory senza dover leggere il report o il codice (finding advocate, council 2026-09-01).
```

- [ ] **Step 3: Aggiungere una nuova voce con i limiti dichiarati di questo lavoro**

Aggiungere, in fondo al file, una nuova voce:

```markdown
- **PromptGuard attivato in LlamaFirewall (`--vendor llamafirewall-combined`) — 5
  limiti dichiarati, nessuno bloccante**. Design:
  `docs/design/2026-09-01-llamafirewall-promptguard-design.md`. Piano:
  `docs/superpowers/plans/2026-09-01-llamafirewall-promptguard-implementation.md`.
  1. **Latenza per caso non ancora misurata su un run reale**: PromptGuard scansiona
     un turno utente alla volta (non una volta per caso) — stime di Pi (500-1500ms/
     chiamata su CPU, 86M) suggeriscono margine ampio sotto
     `DETECTOR_TIMEOUT_S=180s`, ma va verificato nel primo run reale.
  2. **Revisione HF non pinnata esplicitamente**: il loader del vendor
     (`promptguard_utils.py::_load_model_and_tokenizer`) usa
     `from_pretrained(model_name)` senza `revision=` — il build fissa qualunque
     revisione sia `main` al momento del build (baked, stabile per la vita
     dell'immagine), ma un rebuild futuro potrebbe silenziosamente prendere una
     revisione diversa. Stesso tipo di rischio già accettato per
     `SIFTER_MODEL`/`INSPECTOR_MODEL` (Gap 10).
  3. **Bug pre-esistente in `scan_replay()`, applicabile ad AlignmentCheck** (non
     introdotto da questo lavoro, scoperto verificandolo): se l'ultimo turno di un
     transcript non è una risposta naturale dell'agente ma un turno "tool" (es.
     "max turns reached"), lo `score` di AlignmentCheck riportato da
     `scan_replay()` può non riflettere l'ultimo vero turno assistente scansionato.
     Non risolto (fuori scope di questa attivazione di PromptGuard, tocca
     un'integrazione già pubblicata) — da valutare separatamente.
  4. **Troncamento silenzioso oltre 512 token**: `PromptGuardScanner`/
     `promptguard_utils.py::_get_class_probabilities` usa `truncation=True,
     max_length=512` — non un rischio di crash, ma un caso composto con un seed
     turn molto lungo verrebbe analizzato solo nei primi 512 token, silenziosamente.
     Non misurato se qualche caso del dataset attuale si avvicina al limite.
  5. **`block_threshold=0.9` è il default del vendor**, non ritarato su questo
     dataset — stesso trattamento già dato al default `gpt-4o-mini` non motivato.
```

- [ ] **Step 4: Verificare che i file restino Markdown validi**

Run (o equivalente): aprire entrambi i file e controllare a occhio che
l'indentazione della lista numerata dentro il bullet di
`registro-limiti-aperti.md` resti coerente con le altre voci del registro (2 spazi
per il testo continuato, come le voci esistenti), e che la frase aggiunta a
`CONTEXT.md` sia in coda al bullet esistente, non in un bullet nuovo separato.

- [ ] **Step 5: Commit**

```bash
git add docs/design/registro-limiti-aperti.md CONTEXT.md
git commit -m "$(cat <<'EOF'
docs: close PromptGuard next-step, register limits, report naming convention

registro-limiti-aperti.md: the "Prossimo passo (non ancora scopato): attivare
PROMPT_GUARD..." paragraph is now done (this plan) — removed per the
registry's own convention (a closed item is removed outright, not checked
off). New entry lists the 5 non-blocking limits declared in the design doc's
"Limiti dichiarati" section. CONTEXT.md: the existing llamafirewall-combined
tool_name bullet gains the report-directory naming convention (council
advocate finding) so a future report's location alone distinguishes it from
a plain llamafirewall-alignmentcheck run.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Nota sul council checkpoint per questo piano

Valutato esplicitamente, non saltato per default: questo piano traduce
meccanicamente un design doc già passato per un council a roster completo e per
`/grill-with-docs` (entrambi con difetti reali trovati e corretti nel design
stesso). Le uniche decisioni prese in fase di scrittura di questo piano che il
design doc non aveva già fissato sono Task 1 (parametro `output_suffix`, per
rendere vero un nome di file che il design doc già dichiarava) e Task 3 (4 tabelle
host-side indicizzate per vendor, trovate leggendo il codice) — entrambe estensioni
retro-compatibili con test diretti, non scelte architetturali nuove. Non propongo
un ulteriore council checkpoint su questo piano; se l'utente vede un rischio che
non ho colto in una di queste due decisioni, va discusso prima di eseguire i Task
1/3 rispettivi.

## Note sull'esecuzione

- **Task 0 è un gate**: eseguirlo per primo, isolato. Se fallisce, fermarsi e
  tornare all'utente prima di procedere a qualunque altro task.
- **Task 1-5 e 7-8 non richiedono `llamafirewall` installato** e girano nella
  suite principale (`python -m pytest -q`) su questo host così com'è oggi.
- **Task 6 richiede lo stack Docker attivo** (l'immagine ricostruita da Task 0) per
  la sua verifica gated — se lo stack non è disponibile al momento
  dell'esecuzione, il codice di produzione (Step 1) e i test pure-Python restano
  comunque scrivibili/committabili; solo lo Step 4 (esecuzione gated reale) va
  posticipato a quando lo stack è disponibile, senza bloccare i task successivi
  (Task 7/8 non dipendono da Task 6 essere stato eseguito dal vivo).
