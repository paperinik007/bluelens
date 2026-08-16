# Gap 9: Agent/Detector Container Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single `control` container (Plan 3, Task 2/3) with two containers — `agent` (only `toy_agent`) and `detector` (only `aidr` + a new `detector_adapter` package) — communicating exclusively through an external orchestrator via `docker compose exec` + JSON on stdin/stdout, with no direct network path between them, distinct API keys, an explicit infra/application error contract, and per-`case_id` external evidence collection for both containers. This closes Gap 9 (gap-tracking doc) and unblocks Plan 4 (adapter+orchestrator batch processing over a full dataset), which assumes this topology.

**Architecture:** `docker/agent/Dockerfile` builds a minimal image with only `src/toy_agent/` installed — no vendor code, no `aidr`. `docker/detector/Dockerfile` builds the pinned `aidr` clone (unchanged from Plan 3's `docker/control/Dockerfile`) plus a new `src/detector_adapter/` package (moved `vendor_proxy.py` + new `AgenticThreatDetectionAdapter` + the `evaluate_case` entrypoint). `docker-compose.yml` attaches `agent` and `detector` to two separate `internal: true` Docker networks, each shared only with `egress-proxy` (unchanged from Plan 3, Task 3) — no network `agent` and `detector` have in common. A new `toy_agent.orchestrator` module (never imports `aidr`, never runs inside either container) drives one `TestCase` at a time: `docker compose exec agent python -m toy_agent.run_case` (stdin `TestCase` JSON with a one-turn seed transcript, stdout full `Transcript` JSON), a truncate of the detector's thin-proxy log (scopes that evidence channel to this one case), then `docker compose exec detector python -m detector_adapter.evaluate_case` (stdin that `Transcript` JSON, stdout `Verdict` JSON), classifying every failure as `error_kind: "infra"` or `"application"` and returning both the `Transcript` and the `Verdict` to the caller. `evaluate_case` enforces its own internal wall-clock deadline (shorter than the orchestrator's outer timeout) and, on expiry, terminates the real MCP provider subprocesses Inspector spawned via direct process handles before exiting — the orchestrator's own post-timeout `pkill` (targeting both `evaluate_case` itself and its MCP children) is kept only as a last-resort fallback net. A new `toy_agent/evidence.py` collects the four generic external-evidence channels (container logs for both services + `egress-proxy`, `docker diff`, `docker stats`) plus the vendor-specific thin-proxy log (scrubbed of the API key) after each invocation.

**Tech Stack:** Docker Desktop (Linux containers), Docker Compose, Python 3.11, `httpx`, `openai` SDK (agent only), Squid (unchanged), Trivy.

**Spec:** `docs/design/2026-08-14-toy-agent-e-pipeline-misura.md` (sections: "Confine misuratore/misurato (risoluzione Gap 9)", "Meccanismo di handoff: orchestratore esterno, sottoprocessi separati", "Raccolta prove esterna durante ogni run", "Contratto riusabile del container detector", "Limiti dichiarati di questa architettura (Gap 9)"), `docs/design/2026-08-14-toy-agent-gap-tracking.md` (Gap 9). Supersedes Task 2 ("Immagine del container di controllo") and Task 3 ("Egress lockdown") of `docs/superpowers/plans/2026-08-15-control-container.md` — Task 1 (`vendor_proxy.py`, moved not rewritten here), Task 4 (Trivy scan — re-run here for the two new images, evidence doc updated in place), Task 5 (vendor code review — conclusions unchanged, container renamed only), and Task 6 (Gap 4 empirical verification — script moved, not re-run; the PASS result already recorded stands) of that plan are **not** reopened.

**Scope boundary with Plan 4** (explicit, since the design doc's own phrasing is easy to misread): this plan builds the single-`TestCase` mechanism end-to-end for real — `run_case` really runs the ReAct loop, `evaluate_case` really calls `Pipeline().analyze()`, `orchestrator.run_test_case()` really drives one round trip with the full error contract. Plan 4 ("adapter+orchestratore vero e proprio") adds the **batch** loop over a full dataset (`list[TestCase]` → `list[Verdict]`, wired to the metrics module and report — Gap 6's resolution, "Orchestrazione del run") — a thin wrapper around `run_test_case()`, not a redesign of it. `run_test_case()` returns both the `Transcript` it generated and the `Verdict` it collected (not the `Verdict` alone) precisely so that claim holds: Plan 4 needs the transcript to populate the final `TestCase` for the report's "Casi concreti" section, and if this plan discarded it, Plan 4 would have had to change this function's signature — a redesign, contradicting the claim above. `Verdict.cost_usd` is left `None` by `evaluate_case` here — the design doc assigns dollar-cost computation to the metrics module ("Schema di misura": "il modulo metriche deve calcolarlo a partire da token count + pricing noto"), not the adapter — but the raw `in_tokens`/`out_tokens` the metrics module will need for that computation are preserved as extra keys on the `Verdict` JSON, not discarded.

**Council mirato eseguito su questo piano (2026-08-16, roster completo)**: trovato un finding convergente reale da `council-skeptic` e `council-risk`, indipendentemente — il cleanup best-effort dei sottoprocessi MCP orfani, come originariamente scritto (un `pkill` esterno lanciato dall'orchestratore dopo un timeout), copriva solo lo scenario "sottoprocesso MCP bloccato su stdio", non quello — altrettanto plausibile dati gli 8 turni possibili di Inspector contro il timeout configurato — in cui è il processo padre `evaluate_case` stesso a restare bloccato/orfano, continuando nel frattempo a scrivere sul log cumulativo del thin proxy (canale di prova mai troncato per-caso, stesso problema di attribuzione già risolto per `docker diff`/`docker stats` ma mai esteso a questo canale). Risolto qui spostando il cleanup primario dentro `evaluate_case` stesso (opzione preferita dal design doc, con accesso diretto ai sottoprocessi via `Inspector.router.clients`), l'orchestratore tronca il log prima di ogni invocazione, e il `pkill` esterno resta come rete di sicurezza di ultima istanza. Trovati anche, e applicati: `Verdict.tool_name`/`cost_usd` ora documentati in `src/toy_agent/schema.py`; `in_tokens`/`out_tokens` preservati nel JSON invece di scartati; script di convenienza per eseguire i test `aidr`-gated (Task 6). Dettaglio completo nella sezione "Council mirato — findings applicati" in fondo a questo documento.

## Global Constraints

- `agent` must never have `aidr` installed or importable; `detector` must never have `toy_agent` installed or importable (Gap 9 mapping row) — enforced structurally (nothing copied into the image) and by a static test.
- No process anywhere in `toy_agent.orchestrator` or `src/detector_adapter/` may import both `toy_agent` and `aidr` — `toy_agent.orchestrator` never imports `aidr`; `detector_adapter` never imports `toy_agent` (Gap 9 mapping row, extends `tests/test_no_vendor_imports.py`).
- `agent` and `detector` share no Docker network directly — each is attached only to its own `internal: true` network, with `egress-proxy` as the sole common member (Gap 9 mapping row).
- `agent` and `detector` use two distinct `OPENROUTER_API_KEY` values, never the same secret (Gap 9 mapping row).
- Every `evaluate_case` implementation (this one and any future vendor's) writes **only** the final `Verdict` JSON to stdout — all diagnostics go to stderr (Gap 9 mapping row, council-mirato finding).
- The error contract for both `agent` and `detector` invocations: exit code `0` + only the expected JSON on stdout, or exit code ≠ `0` + error detail on stderr and nothing on stdout. The orchestrator never attempts to parse stdout as JSON when the exit code is nonzero, and classifies every failure as `error_kind: "infra"` (the invocation itself could not be started, or exceeded the wall-clock timeout) or `"application"` (the process ran and exited nonzero, or produced unparseable stdout despite exit 0).
- No bind-mounts of repo code into either container — everything enters via `COPY`/`git clone` at build time (unchanged from Plan 3, Gap 8).
- Neither image may have unresolved `CRITICAL` Trivy findings beyond the already-accepted `perl-base` exception (`docs/design/2026-08-15-container-dependency-scan.md`, updated by this plan for both new images).
- The thin-proxy log persisted as evidence must never contain the literal `OPENROUTER_API_KEY` value (Gap 9 mapping row, council-mirato finding).
- `evaluate_case`'s internal wall-clock deadline (`EVALUATE_CASE_DEADLINE_S`, Task 6) must always be shorter than `orchestrator.run_test_case()`'s `detector_timeout_s` (Task 7) — the internal one is meant to fire and let the process exit cleanly (with its own cleanup already done) before the external one has to fall back to a less precise, pattern-matching cleanup.
- The thin-proxy log's cumulative file (`VENDOR_PROXY_LOG_PATH`, one process for the whole life of the `detector` container) must be truncated by the orchestrator immediately before each detector invocation — otherwise the evidence persisted for `case_id` N also contains every prior case's entries, breaking the same per-`case_id` attribution requirement already enforced for `docker diff`/`docker stats`.

---

### Task 1: Move `vendor_proxy.py` into `detector_adapter`, add scrubbed request/response logging

**Files:**
- Create: `src/detector_adapter/__init__.py`
- Move: `src/toy_agent/vendor_proxy.py` → `src/detector_adapter/vendor_proxy.py`
- Move: `tests/toy_agent/test_vendor_proxy.py` → `tests/detector_adapter/test_vendor_proxy.py`
- Modify: `tests/test_no_vendor_imports.py`

**Interfaces:**
- Consumes: nothing new — `httpx`, stdlib only, same as the original.
- Produces: `TIER_TO_MODEL`, `PORT_TO_PATH`, `remap_tier`, `build_forwarder(api_key, proxy_url=None, transport=None, log_path=None)`, `serve_forever`, `main()` — same names as before, `build_forwarder` gains one new optional parameter. Later tasks import `detector_adapter.vendor_proxy.main` from `docker/detector/entrypoint.sh` (as `python -m detector_adapter.vendor_proxy`).

- [ ] **Step 1: Move the files**

```bash
mkdir -p src/detector_adapter tests/detector_adapter
git mv src/toy_agent/vendor_proxy.py src/detector_adapter/vendor_proxy.py
git mv tests/toy_agent/test_vendor_proxy.py tests/detector_adapter/test_vendor_proxy.py
```

Create `src/detector_adapter/__init__.py` (empty file) — makes `detector_adapter` importable as a package, mirroring `src/toy_agent/__init__.py`.

Edit `tests/detector_adapter/test_vendor_proxy.py`: replace the import line

```python
from toy_agent.vendor_proxy import (
    build_forwarder,
    remap_tier,
    serve_forever,
)
```

with

```python
from detector_adapter.vendor_proxy import (
    build_forwarder,
    remap_tier,
    serve_forever,
)
```

- [ ] **Step 2: Run the moved tests to confirm the move alone didn't break anything**

Run: `pytest tests/detector_adapter/test_vendor_proxy.py -v`
Expected: PASS, same 6 tests as before the move (`pythonpath = ["src"]` in the root `pyproject.toml` already covers `src/detector_adapter`, no config change needed).

- [ ] **Step 3: Write the failing tests for scrubbed logging**

Append to `tests/detector_adapter/test_vendor_proxy.py`:

```python
import json as _json


def test_build_forwarder_logs_request_and_response(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    log_path = tmp_path / "vendor_proxy.jsonl"
    forward = build_forwarder(
        api_key="sk-test-secret",
        transport=httpx.MockTransport(handler),
        log_path=log_path,
    )
    forward(8100, {"model": "sifter", "messages": [{"role": "user", "content": "hi"}]})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = _json.loads(lines[0])
    assert entry["port"] == 8100
    assert entry["request"]["model"] == "qwen/qwen3-4b-instruct-2507"
    assert entry["response"] == {"choices": []}
    assert "error" not in entry


def test_thin_proxy_log_never_contains_the_api_key(tmp_path):
    # httpx.HTTPStatusError's own message never includes the response body, so
    # a 4xx/5xx Response alone wouldn't actually exercise the scrub path here
    # (the secret would never be in str(exc) to begin with — a vacuous test).
    # Raising directly from the transport handler is what makes this a real
    # test: it simulates the scenario the council-risk finding actually
    # flagged (2026-08-16 targeted council on Gap 9) — an error whose message
    # echoes the Authorization header back — and gives forward()'s except
    # branch a str(exc) that genuinely contains the secret to scrub.
    def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError(f"upstream rejected request with header Bearer sk-test-secret")

    log_path = tmp_path / "vendor_proxy.jsonl"
    forward = build_forwarder(
        api_key="sk-test-secret",
        transport=httpx.MockTransport(handler),
        log_path=log_path,
    )
    with pytest.raises(RuntimeError):
        forward(8100, {"model": "sifter", "messages": []})

    persisted = log_path.read_text(encoding="utf-8")
    assert "sk-test-secret" not in persisted
    assert "[REDACTED]" in persisted


def test_no_log_path_means_no_logging(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    forward(8100, {"model": "sifter", "messages": []})
    # No log_path given: nothing should be written anywhere reachable from this
    # test — the only assertion possible is that forward() didn't raise.
```

- [ ] **Step 4: Run to verify the new tests fail**

Run: `pytest tests/detector_adapter/test_vendor_proxy.py -v`
Expected: FAIL — `build_forwarder() got an unexpected keyword argument 'log_path'`.

- [ ] **Step 5: Implement scrubbed logging in `vendor_proxy.py`**

In `src/detector_adapter/vendor_proxy.py`, add near the top (after the existing imports):

```python
from pathlib import Path
```

Replace the `build_forwarder` function with:

```python
def _scrub(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "[REDACTED]")


def _append_log(log_path: Path, entry: dict, api_key: str) -> None:
    # Evidence channel ("Log del nostro thin proxy", design doc, "Raccolta prove
    # esterna"): scrubbed at write time, not as a post-hoc pass over a raw file —
    # council-risk finding on the Gap 9 targeted council, 2026-08-16.
    scrubbed = _scrub(json.dumps(entry), api_key)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(scrubbed + "\n")


def build_forwarder(
    api_key: str,
    proxy_url: str | None = None,
    transport: httpx.BaseTransport | None = None,
    log_path: Path | None = None,
) -> Forwarder:
    """Build a Forwarder that POSTs a tier-remapped body to OpenRouter.

    proxy_url routes the outbound call through egress-proxy (the only container
    with a real route to the internet — see design doc, "Container di controllo").
    transport is for tests only, to bypass any real network call. Note: httpx gives
    a proxy-derived mount precedence over an injected transport for matching URLs,
    so passing both proxy_url and transport at once does not behave as "transport
    wins" — tests should pass transport alone (proxy_url=None, the default).

    log_path, when given, persists every request/response as one JSON line —
    the richest evidence channel for a real run (captures exactly what
    Sifter/Inspector reasoned, not just that a connection happened), scrubbed
    of api_key before it ever touches disk.
    """
    client = httpx.Client(
        base_url=OPENROUTER_BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        proxy=proxy_url,
        timeout=120.0,
        transport=transport,
    )

    def forward(port: int, body: dict) -> dict:
        path = PORT_TO_PATH.get(port)
        if path is None:
            raise ValueError(f"no OpenRouter path configured for port {port}")
        remapped = remap_tier(body)
        try:
            response = client.post(path, json=remapped)
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            if log_path is not None:
                _append_log(log_path, {"port": port, "request": remapped, "error": str(exc)}, api_key)
            raise
        if log_path is not None:
            _append_log(log_path, {"port": port, "request": remapped, "response": result}, api_key)
        return result

    return forward
```

Update `main()` to read the log path from the environment:

```python
def main() -> None:
    api_key = os.environ["OPENROUTER_API_KEY"]
    proxy_url = os.environ.get("HTTPS_PROXY")
    log_path_str = os.environ.get("VENDOR_PROXY_LOG_PATH")
    log_path = Path(log_path_str) if log_path_str else None
    forward = build_forwarder(api_key, proxy_url, log_path=log_path)
    serve_forever(list(PORT_TO_PATH), forward)
    threading.Event().wait()  # keep the process alive; servers run on daemon threads
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/detector_adapter/test_vendor_proxy.py -v`
Expected: PASS, 9 tests total.

- [ ] **Step 7: Extend the static import-boundary test**

Read `tests/test_no_vendor_imports.py` (existing, checks `toy_agent` never imports `aidr`). Add a second test to the same file, using the same AST-walk approach against `src/detector_adapter`:

```python
DETECTOR_ADAPTER_ROOT = Path(__file__).resolve().parent.parent / "src" / "detector_adapter"


def test_detector_adapter_package_never_imports_toy_agent():
    offending = []
    for path in DETECTOR_ADAPTER_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            else:
                continue
            if any(name is not None and (name == "toy_agent" or name.startswith("toy_agent.")) for name in names):
                offending.append(str(path))
    assert not offending, f"detector_adapter must never import toy_agent: {offending}"
```

- [ ] **Step 8: Run the full test suite to verify nothing else broke**

Run: `pytest tests/ -v`
Expected: PASS — `test_detector_adapter_package_never_imports_toy_agent` passes (only `vendor_proxy.py` exists in `detector_adapter` so far, and it imports nothing from `toy_agent`); `test_toy_agent_package_never_imports_aidr` still passes.

- [ ] **Step 9: Commit**

```bash
git add src/detector_adapter tests/detector_adapter tests/test_no_vendor_imports.py
git commit -m "refactor: move vendor_proxy.py into new detector_adapter package, add scrubbed request/response logging (Gap 9)"
```

---

### Task 2: `docker/agent/` image (misuratore only)

**Files:**
- Create: `docker/agent/Dockerfile`
- Create: `docker/agent/entrypoint.sh`

**Interfaces:**
- Consumes: `src/toy_agent/` (whole package, minus `vendor_proxy.py` which moved out in Task 1), root `pyproject.toml`.
- Produces: a buildable image (`agentic-security-audits-agent`, tagged by Compose in Task 4) with only `toy_agent` installed — no `aidr`, no `detector_adapter`.

- [ ] **Step 1: Write the Dockerfile**

`docker/agent/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# curl: needed for the egress/network verification checks in Task 4 (same
# reasoning as docker/control/Dockerfile in Plan 3 — python:3.11-slim ships
# neither curl nor wget).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /opt/toy_agent/pyproject.toml
COPY src/toy_agent /opt/toy_agent/src/toy_agent
WORKDIR /opt/toy_agent
RUN pip install --no-cache-dir -e .

# Same compensating control as docker/detector/Dockerfile (Task 3) and the
# retired docker/control/Dockerfile before it: perl-base ships in every
# python:3.11-slim image unconditionally (docs/design/2026-08-15-container-
# dependency-scan.md — 4 CRITICAL CVEs, no upstream fix). This image's own
# code never invokes perl on any path; stripping the execute bit closes that
# path without touching anything this image's build actually needs.
RUN chmod a-x /usr/bin/perl /usr/bin/perl5.40.1

COPY docker/agent/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
```

- [ ] **Step 2: Write the entrypoint**

`docker/agent/entrypoint.sh`:

```bash
#!/bin/sh
set -e
# agent runs no background process of its own (unlike detector's vendor_proxy,
# Task 3) — model_client.py calls OpenRouter directly, no local thin proxy to
# wait on. Fail fast on a missing key instead of failing later, mid-batch,
# inside toy_agent.run_case (Task 5).
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo "OPENROUTER_API_KEY is not set" >&2
    exit 1
fi
exec "$@"
```

- [ ] **Step 3: Build the image and verify the import boundary**

Run (from repo root):

```bash
docker build -f docker/agent/Dockerfile -t agentic-security-audits-agent .
```

Expected: builds successfully, exits 0.

Run:

```bash
docker run --rm agentic-security-audits-agent python -c "import toy_agent; print('ok')"
```

Expected: `ok`.

Run:

```bash
docker run --rm agentic-security-audits-agent python -c "import aidr"
```

Expected: `ModuleNotFoundError: No module named 'aidr'` (nonzero exit) — `aidr` is never installed in this image.

Run:

```bash
docker run --rm agentic-security-audits-agent python -c "import detector_adapter"
```

Expected: `ModuleNotFoundError: No module named 'detector_adapter'` — `detector_adapter` isn't copied into this image at all, so this fails even though `toy_agent` and `detector_adapter` will later live in the same repo.

- [ ] **Step 4: Trivy scan**

Run:

```bash
trivy image --severity CRITICAL --exit-code 1 agentic-security-audits-agent
```

Expected: exit 0 after the `chmod a-x` step above (Trivy still *reports* the 4 `perl-base` CVEs — it reads dpkg metadata, not file permissions — but per the already-accepted exception this is not a fresh finding to resolve; if any *other* CRITICAL appears, resolve it before proceeding — do not extend the accepted exception to cover it without discussing with the user first).

Update `docs/design/2026-08-15-container-dependency-scan.md`: add a new `## Immagine agent` section alongside the existing `control`/`egress-proxy` entries (do not delete the historical `control` entry — it documents what Plan 3 actually scanned; add, don't overwrite), recording the digest, date, and confirming the same 4 `perl-base` CRITICAL CVEs under the same already-accepted exception.

- [ ] **Step 5: Commit**

```bash
git add docker/agent/Dockerfile docker/agent/entrypoint.sh docs/design/2026-08-15-container-dependency-scan.md
git commit -m "feat: add agent container image (toy_agent only, no aidr — Gap 9)"
```

---

### Task 3: `docker/detector/` image (misurato only)

**Files:**
- Create: `docker/detector/Dockerfile`
- Create: `docker/detector/entrypoint.sh`
- Create: `docker/detector/source_registry.yaml` (moved content from `docker/control/source_registry.yaml`)
- Create: `docker/detector/verify_sourcelens.py` (moved content from `docker/control/verify_sourcelens.py`, unchanged)
- Create: `docker/detector/detector_adapter.pyproject.toml`

**Interfaces:**
- Consumes: the pinned vendor clone (build-time `git clone`, commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`), `src/detector_adapter/` (Task 1's `vendor_proxy.py`; Task 6 will add `adapter.py`/`evaluate_case.py` to this same directory — this Dockerfile's `COPY src/detector_adapter ...` line picks those up automatically once Task 6 lands, no Dockerfile change needed then), `src/toy_agent/tools.py` (single-file copy for the SourceLens registry, not a package install).
- Produces: a buildable image (`agentic-security-audits-detector`) with `aidr` + `detector_adapter` installed — no `toy_agent` package.

- [ ] **Step 1: Write the Dockerfile**

`docker/detector/Dockerfile`:

```dockerfile
# ---- Stage "vendor-source": clone the pinned vendor repo. -----------------
# Same reasoning as the retired docker/control/Dockerfile (Plan 3, Task 4
# finding): isolating git to a throwaway build stage keeps perl-modules-5.40/
# libperl5.40 (pulled in by Debian's git package) out of the final image.
FROM python:3.11-slim AS vendor-source

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/FareedKhan-dev/agentic-threat-detection.git aidr-vendor \
    && cd aidr-vendor \
    && git checkout 7fad14d2478707e68a09b8ecd9942dec8fde1614

# ---- Final stage: runtime image. -------------------------------------------
FROM python:3.11-slim

# curl: Task 4's egress/network verification checks. procps (for pkill):
# best-effort MCP-subprocess cleanup on a detector-invocation timeout
# (toy_agent.orchestrator, Task 7) targets processes by command-line pattern
# inside this container.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
COPY --from=vendor-source /opt/aidr-vendor /opt/aidr-vendor

WORKDIR /opt/aidr-vendor
RUN pip install --no-cache-dir -r requirements.txt

# Vendor's requirements.txt pins mcp[cli]>=1.2 with no upper bound, resolving
# to an incompatible mcp 2.x (Plan 3, Task 6 finding) — capped per upstream's
# own migration guidance.
RUN pip install --no-cache-dir 'mcp[cli]>=1.28,<2'

# aidr itself, editable (Plan 3, Task 6 finding: subprocess-launched provider
# scripts get their own directory on sys.path[0], not /opt/aidr-vendor).
RUN pip install --no-cache-dir -e .

# detector_adapter package (Gap 9): vendor_proxy.py (moved from toy_agent,
# Task 1), AgenticThreatDetectionAdapter + evaluate_case entrypoint (Task 6).
# A separate, dedicated pyproject.toml (docker/detector/detector_adapter.pyproject.toml)
# — never the repo-root one, which stays toy_agent's alone.
COPY docker/detector/detector_adapter.pyproject.toml /opt/detector_adapter/pyproject.toml
COPY src/detector_adapter /opt/detector_adapter/src/detector_adapter
WORKDIR /opt/detector_adapter
RUN pip install --no-cache-dir -e .

# SourceLens registry entry for toy_support (Gap 1/Gap 4/Gap 8): single-file
# COPY of the real tool source — toy_agent is never installed as a package
# here (Gap 9: detector must never import toy_agent), this is plain data.
RUN mkdir -p /opt/aidr-vendor/aidr/gauntlet/servers/toy_support
COPY src/toy_agent/tools.py /opt/aidr-vendor/aidr/gauntlet/servers/toy_support/toy_support.py
COPY docker/detector/source_registry.yaml /opt/aidr-vendor/aidr/data/source_registry.yaml

COPY docker/detector/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

# Gap 4 verification script (Plan 3, Task 6) — moved here unchanged so a
# fresh build can still reproduce it; re-running it is optional (not required
# by this plan, see Task 3 Step 4 below), the existing PASS result stands.
COPY docker/detector/verify_sourcelens.py /opt/aidr-vendor/verify_sourcelens.py

# perl-base compensating control (see docker/agent/Dockerfile, Task 2 — same
# reasoning, same accepted exception).
RUN chmod a-x /usr/bin/perl /usr/bin/perl5.40.1

WORKDIR /opt/aidr-vendor
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
```

- [ ] **Step 2: Write the entrypoint**

`docker/detector/entrypoint.sh` (same readiness-check pattern as Plan 3's `docker/control/entrypoint.sh`, module path updated):

```bash
#!/bin/sh
set -e
python -m detector_adapter.vendor_proxy &
proxy_pid=$!

for port in 8100 8101 8102; do
    ready=0
    for attempt in $(seq 1 20); do
        if ! kill -0 "$proxy_pid" 2>/dev/null; then
            echo "vendor_proxy exited before binding port $port — check OPENROUTER_API_KEY" >&2
            exit 1
        fi
        if python -c "import socket,sys; s=socket.socket(); s.settimeout(0.2); sys.exit(0 if s.connect_ex(('127.0.0.1', $port))==0 else 1)"; then
            ready=1
            break
        fi
        sleep 0.2
    done
    if [ "$ready" -ne 1 ]; then
        echo "vendor_proxy never bound port $port within 4s" >&2
        exit 1
    fi
done

exec "$@"
```

- [ ] **Step 3: Move the registry and verification script**

```bash
git mv docker/control/source_registry.yaml docker/detector/source_registry.yaml
git mv docker/control/verify_sourcelens.py docker/detector/verify_sourcelens.py
```

Neither file's content changes — `source_registry.yaml`'s four entries and `verify_sourcelens.py`'s logic (spy on `MCPClient.call`, compare hashes via `Path.read_text()`) are container-agnostic.

- [ ] **Step 4: Write the detector_adapter pyproject**

`docker/detector/detector_adapter.pyproject.toml`:

```toml
[project]
name = "detector-adapter"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.26",
]
```

(Same minimal shape as the repo-root `pyproject.toml` — no `[tool.setuptools]` overrides, relying on the same auto-detected `src/`-layout behavior already proven to work for `toy_agent`.)

- [ ] **Step 5: Build and verify**

Run (from repo root):

```bash
docker build -f docker/detector/Dockerfile -t agentic-security-audits-detector .
```

Expected: builds successfully, exits 0.

Run:

```bash
docker run --rm agentic-security-audits-detector python -c "import aidr; import detector_adapter; print('ok')"
```

Expected: `ok`.

Run:

```bash
docker run --rm agentic-security-audits-detector python -c "import toy_agent"
```

Expected: `ModuleNotFoundError: No module named 'toy_agent'`.

Run:

```bash
docker run --rm agentic-security-audits-detector sha256sum aidr/gauntlet/servers/toy_support/toy_support.py
```

Compare to a local `sha256sum src/toy_agent/tools.py` (or PowerShell `Get-FileHash`) — must match exactly (same check as Plan 3, Task 2, now against the `detector` image).

Run:

```bash
docker run --rm agentic-security-audits-detector grep toy_support aidr/data/source_registry.yaml
```

Expected: prints `  - name: toy_support`.

- [ ] **Step 6: Trivy scan**

Run:

```bash
trivy image --severity CRITICAL --exit-code 1 agentic-security-audits-detector
```

Expected: exit 0 under the same accepted `perl-base` exception as Task 2. Update `docs/design/2026-08-15-container-dependency-scan.md` with a new `## Immagine detector` section (digest, date), same exception referenced.

- [ ] **Step 7: Commit**

```bash
git add docker/detector docs/design/2026-08-15-container-dependency-scan.md
git commit -m "feat: add detector container image (aidr + detector_adapter, no toy_agent — Gap 9)"
```

---

### Task 4: `docker-compose.yml` two-network topology, remove `docker/control/`

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Delete: `docker/control/` (fully superseded by Tasks 2-3)

**Interfaces:**
- Consumes: Task 2's `agent` image build context, Task 3's `detector` image build context, the unchanged `docker/egress-proxy/` build context (Plan 3, Task 3).
- Produces: a running three-service stack (`agent`, `detector`, `egress-proxy`) where `agent` and `detector` each reach only `egress-proxy`, never each other.

- [ ] **Step 1: Rewrite the compose file**

`docker-compose.yml`:

```yaml
services:
  egress-proxy:
    build:
      context: ./docker/egress-proxy
    networks:
      agent_net:
      detector_net:
      default:
    expose:
      - "3128"

  agent:
    build:
      context: .
      dockerfile: docker/agent/Dockerfile
    depends_on:
      - egress-proxy
    environment:
      OPENROUTER_API_KEY: ${AGENT_OPENROUTER_API_KEY}
      HTTPS_PROXY: http://egress-proxy:3128
    cap_drop:
      - ALL
    security_opt:
      - "no-new-privileges:true"
    networks:
      agent_net:

  detector:
    build:
      context: .
      dockerfile: docker/detector/Dockerfile
    depends_on:
      - egress-proxy
    environment:
      OPENROUTER_API_KEY: ${DETECTOR_OPENROUTER_API_KEY}
      HTTPS_PROXY: http://egress-proxy:3128
      VENDOR_PROXY_LOG_PATH: /var/log/vendor_proxy.jsonl
    cap_drop:
      - ALL
    security_opt:
      - "no-new-privileges:true"
    networks:
      detector_net:

networks:
  agent_net:
    internal: true
  detector_net:
    internal: true
```

`egress-proxy` is the only service on both `agent_net` and `detector_net` — it doesn't route IP traffic between them (Squid is an application-layer HTTP(S) proxy, not an IP forwarder, and Docker containers don't get IP-forwarding rights by default), so being a common member of both networks does not create a path between `agent` and `detector`.

- [ ] **Step 2: Update the API key template**

`.env.example`:

```
# Warning: `docker compose config` prints these values in cleartext — never run
# that command in a shared or logged terminal session.
# Gap 9: agent and detector use distinct keys — a compromised container never
# spends or acts on behalf of the other (design doc, "Confine misuratore/misurato").
AGENT_OPENROUTER_API_KEY=
DETECTOR_OPENROUTER_API_KEY=
```

- [ ] **Step 3: Remove the retired single-container setup**

```bash
git rm -r docker/control
```

(All four of its files were either moved in Tasks 1/3 — `vendor_proxy.py`, `source_registry.yaml`, `verify_sourcelens.py` — or fully superseded — `Dockerfile`, `entrypoint.sh` by `docker/agent/` + `docker/detector/`.)

- [ ] **Step 4: Build, start, and verify egress + isolation**

Run:

```bash
docker compose build
docker compose up -d
docker compose ps
```

Expected: `agent`, `detector`, `egress-proxy` all running.

Run the egress battery from Plan 3, Task 3 (arbitrary domain fails including DNS, `openrouter.ai` via the proxy succeeds, `host.docker.internal` blocked) for **both** `agent` and `detector` — six checks total, substituting the service name:

```bash
docker compose exec agent sh -c "getent hosts example.com; echo exit=\$?"
docker compose exec detector sh -c "getent hosts example.com; echo exit=\$?"
```

Expected: nonzero exit for both.

```bash
docker compose exec agent sh -c "curl -s -o /dev/null -w '%{http_code}\n' -x http://egress-proxy:3128 https://openrouter.ai/api/v1/models"
docker compose exec detector sh -c "curl -s -o /dev/null -w '%{http_code}\n' -x http://egress-proxy:3128 https://openrouter.ai/api/v1/models"
```

Expected: `200` for both.

```bash
docker compose exec agent sh -c "curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 http://host.docker.internal || echo BLOCKED"
docker compose exec detector sh -c "curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 http://host.docker.internal || echo BLOCKED"
```

Expected: `BLOCKED` for both — same residual-side-channel caveat as Plan 3, Task 3: if either instead succeeds, record it as a declared limitation, don't silently accept it.

- [ ] **Step 5: Verify agent and detector cannot reach each other directly (Gap 9, new check)**

Run:

```bash
docker compose exec agent sh -c "curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 http://detector:8100 || echo BLOCKED"
docker compose exec detector sh -c "curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 http://agent:9 || echo BLOCKED"
```

Expected: `BLOCKED` for both — `agent` and `detector` are on disjoint Docker networks, so Compose's embedded DNS has no record for the other service's name from either side (name resolution itself fails, not just the connect).

- [ ] **Step 6: Verify the two API keys are distinct in the compose file**

Run:

```bash
grep -A1 "OPENROUTER_API_KEY:" docker-compose.yml
```

Expected: two occurrences, `${AGENT_OPENROUTER_API_KEY}` and `${DETECTOR_OPENROUTER_API_KEY}` — never the same variable twice.

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml .env.example
git rm -r docker/control
git commit -m "feat: split compose topology into isolated agent/detector networks, remove retired control container (Gap 9)"
```

---

### Task 5: `toy_agent.run_case` entrypoint

**Files:**
- Create: `src/toy_agent/run_case.py`
- Test: `tests/toy_agent/test_run_case.py`

**Interfaces:**
- Consumes: `toy_agent.agent_loop.build_tool_registry`/`run_agent` (Plan 1), `toy_agent.model_client.OpenRouterModelClient` (Plan 1), `toy_agent.state.fresh_state` (Plan 1), `toy_agent.schema.Transcript`/`Turn`/`ToolCall` (Plan 1).
- Produces: `run_case(data: dict, model_client) -> dict`, `transcript_to_dict(transcript: Transcript) -> dict`, `main()` — invoked as `python -m toy_agent.run_case` (stdin: `TestCase`-shaped JSON with exactly one seed `Turn`; stdout: full `Transcript` JSON).

- [ ] **Step 1: Write the failing tests**

`tests/toy_agent/test_run_case.py`:

```python
import json

import pytest

from toy_agent.model_client import ModelReply
from toy_agent.run_case import _extract_scenario, main, run_case, transcript_to_dict
from toy_agent.schema import Transcript, Turn, ToolCall


class FakeModelClient:
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        if not self._script:
            raise AssertionError("FakeModelClient script exhausted")
        return self._script.pop(0)


_SEED_INPUT = {
    "case_id": "case_001",
    "transcript": {
        "session_id": "case_001",
        "turns": [{"seq": 0, "role": "user", "content": "Can you help me?", "tool_call": None}],
        "stop_reason": None,
    },
    "label": "benign",
    "technique_target": None,
    "rationale": "smoke test seed",
}


def test_extract_scenario_reads_case_id_and_seed_content():
    case_id, scenario = _extract_scenario(_SEED_INPUT)
    assert case_id == "case_001"
    assert scenario == "Can you help me?"


def test_extract_scenario_rejects_missing_case_id():
    bad = {**_SEED_INPUT, "case_id": ""}
    with pytest.raises(ValueError):
        _extract_scenario(bad)


def test_extract_scenario_rejects_more_than_one_seed_turn():
    bad = json.loads(json.dumps(_SEED_INPUT))
    bad["transcript"]["turns"].append({"seq": 1, "role": "assistant", "content": "x", "tool_call": None})
    with pytest.raises(ValueError):
        _extract_scenario(bad)


def test_transcript_to_dict_round_trips_a_tool_turn():
    transcript = Transcript(
        session_id="s1",
        turns=[
            Turn(seq=0, role="user", content="hi"),
            Turn(
                seq=1, role="tool", content="result text",
                tool_call=ToolCall(tool_name="read_ticket_content", arguments={"ticket_id": "tkt_001"}, result="result text", status="ok"),
            ),
        ],
        stop_reason="completed",
    )
    d = transcript_to_dict(transcript)
    assert d["session_id"] == "s1"
    assert d["stop_reason"] == "completed"
    assert d["turns"][0] == {"seq": 0, "role": "user", "content": "hi", "tool_call": None}
    assert d["turns"][1]["tool_call"] == {
        "tool_name": "read_ticket_content", "arguments": {"ticket_id": "tkt_001"},
        "result": "result text", "status": "ok",
    }


def test_run_case_produces_a_transcript_dict_for_the_seed_scenario():
    client = FakeModelClient([ModelReply(content="All set!", tool_calls=[], cost_usd=0.001)])
    result = run_case(_SEED_INPUT, client)
    assert result["session_id"] == "case_001"
    assert result["turns"][0]["content"] == "Can you help me?"
    assert result["turns"][-1]["content"] == "All set!"
    assert result["stop_reason"] == "completed"


def test_main_writes_only_the_transcript_json_to_stdout(monkeypatch, capsys):
    import toy_agent.run_case as run_case_module

    monkeypatch.setattr(run_case_module.sys, "stdin", __import__("io").StringIO(json.dumps(_SEED_INPUT)))
    monkeypatch.setattr(
        run_case_module, "OpenRouterModelClient",
        lambda: FakeModelClient([ModelReply(content="done", tool_calls=[], cost_usd=0.0)]),
    )
    run_case_module.main()
    captured = capsys.readouterr()
    assert captured.err == ""
    parsed = json.loads(captured.out)
    assert parsed["session_id"] == "case_001"


def test_main_exits_nonzero_and_writes_to_stderr_on_bad_input(monkeypatch, capsys):
    import toy_agent.run_case as run_case_module

    monkeypatch.setattr(run_case_module.sys, "stdin", __import__("io").StringIO("not json"))
    with pytest.raises(SystemExit) as exc_info:
        run_case_module.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "run_case failed" in captured.err
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/toy_agent/test_run_case.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'toy_agent.run_case'`.

- [ ] **Step 3: Implement `run_case.py`**

`src/toy_agent/run_case.py`:

```python
from __future__ import annotations

import json
import sys

from .agent_loop import build_tool_registry, run_agent
from .model_client import OpenRouterModelClient
from .schema import ToolCall, Transcript, Turn
from .state import fresh_state


def _tool_call_to_dict(tc: ToolCall | None) -> dict | None:
    if tc is None:
        return None
    return {"tool_name": tc.tool_name, "arguments": tc.arguments, "result": tc.result, "status": tc.status}


def _turn_to_dict(turn: Turn) -> dict:
    return {"seq": turn.seq, "role": turn.role, "content": turn.content, "tool_call": _tool_call_to_dict(turn.tool_call)}


def transcript_to_dict(transcript: Transcript) -> dict:
    return {
        "session_id": transcript.session_id,
        "turns": [_turn_to_dict(t) for t in transcript.turns],
        "stop_reason": transcript.stop_reason,
    }


def _extract_scenario(data: dict) -> tuple[str, str]:
    case_id = data.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError("input JSON must have a non-empty string 'case_id'")
    transcript = data.get("transcript")
    if not isinstance(transcript, dict):
        raise ValueError("input JSON must have a 'transcript' object")
    turns = transcript.get("turns")
    if not isinstance(turns, list) or len(turns) != 1:
        raise ValueError("input 'transcript.turns' must contain exactly one seed turn")
    seed = turns[0]
    if seed.get("role") != "user" or not isinstance(seed.get("content"), str) or not seed["content"]:
        raise ValueError("the seed turn must have role 'user' and non-empty string content")
    return case_id, seed["content"]


def run_case(data: dict, model_client) -> dict:
    case_id, scenario = _extract_scenario(data)
    state = fresh_state()
    transcript = run_agent(
        scenario=scenario,
        tools=build_tool_registry(),
        state=state,
        model_client=model_client,
        session_id=case_id,
    )
    return transcript_to_dict(transcript)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        result = run_case(data, OpenRouterModelClient())
    except Exception as exc:
        # Never propagate the raw exception message — may contain the
        # OpenRouter API key (same discipline as agent_loop.py's own
        # exception handling).
        print(f"run_case failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/toy_agent/test_run_case.py -v`
Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/run_case.py tests/toy_agent/test_run_case.py
git commit -m "feat: add toy_agent.run_case CLI entrypoint (Gap 9 handoff mechanism)"
```

---

### Task 6: `detector_adapter.adapter` + `evaluate_case` entrypoint

**Files:**
- Create: `src/detector_adapter/adapter.py`
- Create: `src/detector_adapter/evaluate_case.py`
- Create: `docker/detector/run_adapter_tests.sh`
- Modify: `src/toy_agent/schema.py` (doc comments only — no behavior change)
- Test: `tests/detector_adapter/test_adapter_normalization.py`
- Test: `tests/detector_adapter/test_adapter_agent_event.py`
- Test: `tests/detector_adapter/test_evaluate_case.py`

**Interfaces:**
- Consumes: `aidr.detector.pipeline.Pipeline`, `aidr.schema.agent_event.AgentEvent`/`ChatMessage`/`ToolUsage` (vendor, pinned commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`) — imported **lazily inside functions**, never at module top level, so `detector_adapter.adapter`/`detector_adapter.evaluate_case` stay importable (and their pure logic testable) on a host that doesn't have `aidr` installed — it's only ever installed inside the `detector` image (Task 3).
- Produces: `transcript_dict_to_agent_event(transcript: dict)`, `detection_result_to_verdict(case_id: str, result) -> dict`, `AgenticThreatDetectionAdapter` (with `.evaluate(transcript: dict) -> dict` and `.terminate_subprocesses() -> None`), `run_evaluate_case(data: dict, adapter) -> dict`, `main()` — invoked as `python -m detector_adapter.evaluate_case` (stdin: `Transcript` JSON; stdout: `Verdict` JSON). `main()` enforces an internal wall-clock deadline (`EVALUATE_CASE_DEADLINE_S` env var, default 150s) via `signal.setitimer` — on expiry it calls `adapter.terminate_subprocesses()` before exiting nonzero (council-skeptic/council-risk finding, Gap 9 targeted council — see the "Council mirato" section at the top of this document).

**Test-running note for this task**: `tests/detector_adapter/test_adapter_agent_event.py` needs the real `aidr` package to construct/assert against real `ChatMessage`/`ToolUsage`/`AgentEvent` instances — it starts with `aidr = pytest.importorskip("aidr", ...)` and is skipped (not failed) on a host without `aidr` installed. Run it for real inside a running `detector` container with `docker/detector/run_adapter_tests.sh` (Step 6 below) — a small, committed, one-command wrapper around the `docker compose cp` + `pip install pytest` + `pytest` sequence, not just prose describing it (council-advocate finding, Gap 9 targeted council: a manual step described only in a plan document is easy for a future third-party reviewer to miss or fail to reproduce). The other two test files need no `aidr` and run everywhere, including the new timeout-handling tests in `test_evaluate_case.py` (Unix-only, `pytest.mark.skipif` guarded — this repo's dev machine is Windows, where `signal.SIGALRM` doesn't exist at all).

- [ ] **Step 1: Write the failing tests — pure normalization (no `aidr` needed)**

`tests/detector_adapter/test_adapter_normalization.py`:

```python
from types import SimpleNamespace

from detector_adapter.adapter import (
    DETECTOR_TOOL_NAME,
    AgenticThreatDetectionAdapter,
    detection_result_to_verdict,
)


def _result(**overrides):
    base = dict(is_malicious=False, confidence=0.0, technique="N/A", explanation="", latency_s=1.5, in_tokens=100, out_tokens=20)
    base.update(overrides)
    return SimpleNamespace(**base)


def test_malicious_result_maps_to_malicious_verdict():
    v = detection_result_to_verdict("case_1", _result(is_malicious=True, confidence=0.9, technique="T0007", explanation="hidden escalation"))
    assert v["case_id"] == "case_1"
    assert v["tool_name"] == DETECTOR_TOOL_NAME
    assert v["status"] == "ok"
    assert v["label"] == "malicious"
    assert v["confidence"] == 0.9
    assert v["technique_detected"] == "T0007"
    assert v["rationale"] == "hidden escalation"
    assert v["cost_usd"] is None  # computed later by the metrics module (design doc, "Schema di misura")
    assert v["latency_s"] == 1.5


def test_benign_result_normalizes_na_technique_to_none():
    v = detection_result_to_verdict("case_2", _result(technique="N/A"))
    assert v["label"] == "benign"
    assert v["technique_detected"] is None


def test_empty_explanation_normalizes_to_none_rationale():
    v = detection_result_to_verdict("case_3", _result(explanation=""))
    assert v["rationale"] is None


def test_token_counts_are_preserved_not_discarded():
    # council-skeptic finding, Gap 9 targeted council: DetectionResult is the
    # only object that ever has in_tokens/out_tokens — discarding them here
    # would make cost_usd permanently uncomputable by Plan 4's metrics module,
    # not just "computed later".
    v = detection_result_to_verdict("case_4", _result(in_tokens=1234, out_tokens=567))
    assert v["in_tokens"] == 1234
    assert v["out_tokens"] == 567


class _FakeProc:
    def __init__(self, alive: bool):
        self._alive = alive
        self.terminated = False
        self.killed = False

    def poll(self):
        return None if self._alive else 0

    def terminate(self):
        self.terminated = True
        self._alive = False

    def wait(self, timeout=None):
        pass

    def kill(self):
        self.killed = True


class _FakeMCPClient:
    def __init__(self, proc):
        self.proc = proc


def test_terminate_subprocesses_terminates_only_live_mcp_clients():
    live_proc = _FakeProc(alive=True)
    dead_proc = _FakeProc(alive=False)
    fake_pipeline = SimpleNamespace(
        inspector=SimpleNamespace(
            router=SimpleNamespace(clients={"sourcelens": _FakeMCPClient(live_proc), "threatlens": _FakeMCPClient(dead_proc)})
        )
    )
    adapter = AgenticThreatDetectionAdapter(pipeline=fake_pipeline)
    adapter.terminate_subprocesses()
    assert live_proc.terminated is True
    assert dead_proc.terminated is False  # already dead — no redundant signal


def test_terminate_subprocesses_never_raises_without_a_router():
    adapter = AgenticThreatDetectionAdapter(pipeline=SimpleNamespace())
    adapter.terminate_subprocesses()  # must not raise — called from an except branch
```

- [ ] **Step 2: Write the failing tests — evaluate_case CLI discipline (no `aidr` needed, adapter is faked)**

`tests/detector_adapter/test_evaluate_case.py`:

```python
import io
import json
import signal
import time

import pytest

import detector_adapter.evaluate_case as evaluate_case_module
from detector_adapter.evaluate_case import run_evaluate_case


class FakeAdapter:
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.terminate_called = False

    def evaluate(self, transcript):
        if self._raises is not None:
            raise self._raises
        return self._result

    def terminate_subprocesses(self):
        self.terminate_called = True


class SlowFakeAdapter(FakeAdapter):
    """Sleeps past the internal deadline before returning — the only way to
    exercise the real signal.setitimer mechanism without mocking signal
    itself, which would defeat the point of testing it."""

    def __init__(self, sleep_s, result):
        super().__init__(result=result)
        self._sleep_s = sleep_s

    def evaluate(self, transcript):
        time.sleep(self._sleep_s)
        return super().evaluate(transcript)


def test_run_evaluate_case_returns_the_adapter_result_unchanged():
    fake_verdict = {"case_id": "c1", "tool_name": "x", "status": "ok", "label": "benign"}
    result = run_evaluate_case({"session_id": "c1", "turns": []}, FakeAdapter(result=fake_verdict))
    assert result == fake_verdict


def test_main_writes_only_the_verdict_json_to_stdout(monkeypatch, capsys):
    fake_verdict = {"case_id": "c1", "tool_name": "x", "status": "ok", "label": "malicious"}
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps({"session_id": "c1", "turns": []})))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter", lambda: FakeAdapter(result=fake_verdict))
    evaluate_case_module.main()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == fake_verdict


def test_main_exits_nonzero_on_adapter_exception_never_touching_stdout(monkeypatch, capsys):
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps({"session_id": "c1", "turns": []})))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter", lambda: FakeAdapter(raises=RuntimeError("boom")))
    with pytest.raises(SystemExit) as exc_info:
        evaluate_case_module.main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "evaluate_case failed" in captured.err


@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="SIGALRM is Unix-only — the detector container is Linux-only by design, this test only runs where the real deadline mechanism exists")
def test_main_terminates_subprocesses_and_exits_nonzero_on_internal_deadline(monkeypatch, capsys):
    slow_adapter = SlowFakeAdapter(sleep_s=0.15, result={"case_id": "c1", "tool_name": "x", "status": "ok", "label": "benign"})
    monkeypatch.setenv("EVALUATE_CASE_DEADLINE_S", "0.05")
    monkeypatch.setattr(evaluate_case_module.sys, "stdin", io.StringIO(json.dumps({"session_id": "c1", "turns": []})))
    monkeypatch.setattr(evaluate_case_module, "AgenticThreatDetectionAdapter", lambda: slow_adapter)
    with pytest.raises(SystemExit) as exc_info:
        evaluate_case_module.main()
    assert exc_info.value.code == 1
    assert slow_adapter.terminate_called is True
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "TimeoutError" in captured.err
```

- [ ] **Step 3: Write the failing tests — `AgentEvent` construction (needs `aidr`, skipped otherwise)**

`tests/detector_adapter/test_adapter_agent_event.py`:

```python
import pytest

aidr = pytest.importorskip("aidr", reason="aidr is only installed inside the detector container (docker/detector/Dockerfile)")

from detector_adapter.adapter import transcript_dict_to_agent_event

_TRANSCRIPT = {
    "session_id": "case_007",
    "turns": [
        {"seq": 0, "role": "user", "content": "Please disable my account.", "tool_call": None},
        {
            "seq": 1, "role": "tool", "content": "account cust_001 field 'status' updated",
            "tool_call": {
                "tool_name": "update_account",
                "arguments": {"customer_id": "cust_001", "field": "status", "value": "disabled"},
                "result": "account cust_001 field 'status' updated",
                "status": "ok",
            },
        },
        {"seq": 2, "role": "assistant", "content": "Done, your account is now disabled.", "tool_call": None},
    ],
    "stop_reason": "completed",
}


def test_agent_event_carries_session_id_and_declares_toy_support():
    ev = transcript_dict_to_agent_event(_TRANSCRIPT)
    assert ev.session_id == "case_007"
    assert ev.declared_servers == ["toy_support"]


def test_tool_turn_produces_dotted_tool_name_and_a_result_message():
    ev = transcript_dict_to_agent_event(_TRANSCRIPT)
    calling = [m for m in ev.messages if m.message_type == "tool_calling"]
    assert len(calling) == 1
    usage = calling[0].tool_calls[0]
    assert usage.tool_name == "toy_support.update_account"
    assert usage.server_name == "toy_support"
    result_messages = [m for m in ev.messages if m.message_type == "tool_result"]
    assert result_messages[0].content == "account cust_001 field 'status' updated"


def test_transcript_string_contains_the_dotted_tool_name():
    # This is the exact signal Inspector's SourceLens step relies on (Gap 4) —
    # verified once empirically against a live Inspector in Plan 3, Task 6;
    # this test only pins the string-formatting contract that makes that
    # verification meaningful.
    ev = transcript_dict_to_agent_event(_TRANSCRIPT)
    assert "toy_support.update_account" in ev.transcript()
```

- [ ] **Step 4: Run to verify failures**

Run: `pytest tests/detector_adapter/test_adapter_normalization.py tests/detector_adapter/test_evaluate_case.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'detector_adapter.adapter'` / `'detector_adapter.evaluate_case'`.

Run: `pytest tests/detector_adapter/test_adapter_agent_event.py -v`
Expected: either SKIPPED (if `aidr` isn't on this host's Python path) or the same `ModuleNotFoundError` if it is — both are the expected "not implemented yet" states for this step.

- [ ] **Step 5: Implement `adapter.py`**

`src/detector_adapter/adapter.py`:

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SERVER_NAME = "toy_support"
# Identifies which detector produced a Verdict (design doc, "Schema di misura")
# — a constant today (one detector active per audit, design doc, "Limiti
# dichiarati"), populated so a future second-vendor Verdict is distinguishable
# without a schema change.
DETECTOR_TOOL_NAME = "agentic_threat_detection"


def _build_messages(turns: list[dict]) -> list[Any]:
    # Lazy import: this function is the one place that actually needs aidr's
    # real dataclasses (Pipeline().analyze() reads ev.messages/len(ev.messages)
    # directly, so a duck-typed stand-in wouldn't do) — keeping the import out
    # of module scope keeps detection_result_to_verdict and the CLI wiring in
    # evaluate_case.py importable on a host without aidr installed.
    from aidr.schema.agent_event import ChatMessage, ToolUsage

    messages: list[Any] = []
    for turn in turns:
        role = turn["role"]
        seq = turn["seq"]
        if role == "user":
            messages.append(ChatMessage(seq=seq, role="user", message_type="user_prompt", content=turn["content"]))
        elif role == "assistant":
            messages.append(ChatMessage(seq=seq, role="assistant", message_type="agent_response", content=turn["content"]))
        elif role == "tool":
            call = turn["tool_call"]
            usage = ToolUsage(
                tool_name=f"{SERVER_NAME}.{call['tool_name']}",
                server_name=SERVER_NAME,
                arguments=call["arguments"],
                result=call.get("result"),
                status=call.get("status", "ok"),
                call_id=f"call_{seq}",
            )
            messages.append(ChatMessage(seq=seq, role="assistant", message_type="tool_calling", content="", tool_calls=[usage]))
            messages.append(ChatMessage(seq=seq, role="tool", message_type="tool_result", content=call.get("result") or ""))
        else:
            raise ValueError(f"unknown turn role: {role!r}")
    return messages


def transcript_dict_to_agent_event(transcript: dict):
    """Build an AgentEvent from a Transcript JSON dict (design doc, 'Adapter').

    Reads the JSON's keys directly — never deserializes a toy_agent.schema.Transcript
    instance (detector_adapter must never import toy_agent, Gap 9).
    """
    from aidr.schema.agent_event import AgentEvent

    return AgentEvent(
        session_id=transcript["session_id"],
        source="toy_agent",
        timestamp=datetime.now(timezone.utc),
        declared_servers=[SERVER_NAME],
        messages=_build_messages(transcript["turns"]),
    )


def detection_result_to_verdict(case_id: str, result: Any) -> dict:
    """Normalize a vendor DetectionResult (duck-typed here — only attribute
    access, no isinstance check, so this stays testable without aidr) into
    our Verdict JSON shape.

    in_tokens/out_tokens are carried through as extra keys, not part of the
    toy_agent.schema.Verdict shape (which has no such fields) — preserved so
    Plan 4's metrics module can compute cost_usd from them later without
    reopening this function (council-skeptic finding, Gap 9 targeted council:
    discarding them here would make cost_usd permanently uncomputable, since
    DetectionResult is the only object that ever has them)."""
    technique = result.technique
    return {
        "case_id": case_id,
        "tool_name": DETECTOR_TOOL_NAME,
        "status": "ok",
        "label": "malicious" if result.is_malicious else "benign",
        "confidence": result.confidence,
        "technique_detected": None if technique in (None, "N/A") else technique,
        "rationale": result.explanation or None,
        "cost_usd": None,
        "latency_s": result.latency_s,
        "in_tokens": result.in_tokens,
        "out_tokens": result.out_tokens,
    }


class AgenticThreatDetectionAdapter:
    """TargetAdapter for agentic-threat-detection (aidr), pinned commit
    7fad14d2478707e68a09b8ecd9942dec8fde1614. Bypasses Dredge — builds an
    AgentEvent directly from the Transcript JSON dict received on stdin, calls
    Pipeline().analyze(), normalizes the result."""

    def __init__(self, pipeline: Any = None) -> None:
        if pipeline is not None:
            self._pipeline = pipeline
        else:
            from aidr.detector.pipeline import Pipeline
            self._pipeline = Pipeline()

    def evaluate(self, transcript: dict) -> dict:
        case_id = transcript["session_id"]
        ev = transcript_dict_to_agent_event(transcript)
        result = self._pipeline.analyze(ev)
        return detection_result_to_verdict(case_id, result)

    def terminate_subprocesses(self) -> None:
        """Best-effort termination of the real MCP provider subprocesses
        Inspector spawned (SourceLens/ThreatLens/PolicyLens) — called by
        evaluate_case.py's internal wall-clock deadline handler on expiry,
        never by evaluate() itself. Design doc, 'Meccanismo di handoff':
        cleanup 'dal processo evaluate_case stesso, prima di uscire' — the
        option this plan implements as primary (council-skeptic finding, Gap
        9 targeted council: an external pkill from outside the container
        cannot reach a hung Inspector call itself, only its child
        subprocesses at best — this method reaches both, via direct process
        handles, no name-pattern guessing). Never raises — an exception here
        would mask the real TimeoutError already being handled by the
        caller."""
        router = getattr(getattr(self._pipeline, "inspector", None), "router", None)
        if router is None:
            return
        for client in router.clients.values():
            proc = getattr(client, "proc", None)
            if proc is None or proc.poll() is not None:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
```

- [ ] **Step 6: Implement `evaluate_case.py`**

`src/detector_adapter/evaluate_case.py`:

```python
from __future__ import annotations

import json
import os
import signal
import sys

from .adapter import AgenticThreatDetectionAdapter

# Shorter than orchestrator.py's detector_timeout_s (Task 7, default 180s) on
# purpose (Global Constraints) — this internal deadline is meant to fire and
# let evaluate_case exit cleanly, with its own cleanup already done, before
# the orchestrator's outer timeout would otherwise have to kill the
# docker-compose-exec client and fall back to its own, less precise cleanup.
DEFAULT_DEADLINE_S = 150.0


def _install_deadline(deadline_s: float) -> None:
    if not hasattr(signal, "SIGALRM"):
        # The detector container is Linux-only (design constraint) — this
        # guard only matters when this module's tests run on a non-Linux
        # host (this repo's Windows dev machine), where SIGALRM doesn't exist
        # at all. No-op there; the real container always has it.
        return

    def _handler(signum, frame):
        raise TimeoutError(f"evaluate_case exceeded its internal {deadline_s}s deadline")

    signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, deadline_s)  # setitimer, not alarm(): sub-second precision, needed for a fast test suite


def _cancel_deadline() -> None:
    if hasattr(signal, "SIGALRM"):
        signal.setitimer(signal.ITIMER_REAL, 0)


def run_evaluate_case(data: dict, adapter) -> dict:
    return adapter.evaluate(data)


def main() -> None:
    deadline_s = float(os.environ.get("EVALUATE_CASE_DEADLINE_S", DEFAULT_DEADLINE_S))
    adapter = None
    try:
        _install_deadline(deadline_s)
        data = json.loads(sys.stdin.read())
        adapter = AgenticThreatDetectionAdapter()
        result = run_evaluate_case(data, adapter)
    except TimeoutError as exc:
        if adapter is not None:
            adapter.terminate_subprocesses()
        print(f"evaluate_case failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:
        # Global Constraints: stdout carries only the final Verdict JSON —
        # every diagnostic, here and in any future vendor's evaluate_case,
        # goes to stderr.
        print(f"evaluate_case failed: {exc.__class__.__name__}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        _cancel_deadline()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Document `Verdict.tool_name`/`cost_usd` in `schema.py` (council-advocate finding, doc-only, no behavior change)**

In `src/toy_agent/schema.py`, the `Verdict` dataclass currently has no comments on its fields — a third-party reviewer reading the schema alone (without also reading the design doc or `detector_adapter/adapter.py`) can't tell why `tool_name` exists on a per-session result, or why `cost_usd` might always be `None`. Replace:

```python
@dataclass
class Verdict:
    case_id: str
    tool_name: str
    status: Status
    label: Optional[Label] = None
    confidence: Optional[float] = None
    technique_detected: Optional[str] = None
    rationale: Optional[str] = None
    cost_usd: Optional[float] = None
    latency_s: Optional[float] = None
```

with:

```python
@dataclass
class Verdict:
    case_id: str
    tool_name: str  # which detector produced this Verdict — a constant today (one
                     # detector active per audit at a time, design doc, "Limiti
                     # dichiarati"), kept so a future second-vendor Verdict is
                     # distinguishable without a schema change; populated by
                     # detector_adapter (src/detector_adapter/adapter.py)
    status: Status
    label: Optional[Label] = None
    confidence: Optional[float] = None
    technique_detected: Optional[str] = None
    rationale: Optional[str] = None
    cost_usd: Optional[float] = None  # always None from detector_adapter — computed
                                       # later by the metrics module (Plan 4) from
                                       # token counts + known pricing, design doc,
                                       # "Schema di misura"
    latency_s: Optional[float] = None
```

- [ ] **Step 8: Write the `aidr`-gated test convenience script**

`docker/detector/run_adapter_tests.sh`:

```bash
#!/bin/sh
# One-time/occasional developer convenience: run the aidr-gated adapter tests
# (tests/detector_adapter/test_adapter_agent_event.py) for real, inside a
# running `detector` container. Not part of the image build, not invoked by
# any Dockerfile or CI — a committed script instead of a manual sequence
# described only in a plan document (council-advocate finding, Gap 9 targeted
# council: a step that lives only as prose is easy for a third-party reviewer
# to miss or fail to reproduce). Run from the repo root, with the stack up
# (`docker compose up -d detector`):
#
#     sh docker/detector/run_adapter_tests.sh
set -e
docker compose cp tests/detector_adapter detector:/opt/detector_adapter/tests
docker compose exec -T detector pip install --no-cache-dir pytest
docker compose exec -T detector python -m pytest /opt/detector_adapter/tests/test_adapter_agent_event.py -v
```

- [ ] **Step 9: Run to verify pass**

Run: `pytest tests/detector_adapter/test_adapter_normalization.py tests/detector_adapter/test_evaluate_case.py -v`
Expected: PASS, 10 tests (6 normalization/cleanup + 4 evaluate_case — the internal-deadline test SKIPPED on Windows, PASSED on Linux/macOS).

Run: `pytest tests/detector_adapter/test_adapter_agent_event.py -v`
Expected: SKIPPED on a host without `aidr` (message: "aidr is only installed inside the detector container"), or PASS if run where `aidr` is importable.

Run `sh docker/detector/run_adapter_tests.sh` against a running `detector` container (Step 8) once Task 3/4 have built and started the stack — this is the one point in this task where the `aidr`-gated tests actually execute for real, not just get collected-and-skipped.

- [ ] **Step 10: Run the full local suite + the import-boundary tests**

Run: `pytest tests/ -v`
Expected: PASS (the three new `detector_adapter` test files are collected; `test_adapter_agent_event.py`'s three tests show as skipped locally). `test_detector_adapter_package_never_imports_toy_agent` (Task 1) still passes — `adapter.py`/`evaluate_case.py` import only `aidr` (lazily) and stdlib.

- [ ] **Step 11: Commit**

```bash
git add src/detector_adapter/adapter.py src/detector_adapter/evaluate_case.py src/toy_agent/schema.py docker/detector/run_adapter_tests.sh tests/detector_adapter/test_adapter_normalization.py tests/detector_adapter/test_adapter_agent_event.py tests/detector_adapter/test_evaluate_case.py
git commit -m "feat: add AgenticThreatDetectionAdapter, evaluate_case CLI entrypoint with self-cleanup on timeout (Gap 9 handoff mechanism)"
```

---

### Task 7: `toy_agent.orchestrator` — single-`TestCase` invocation mechanism

**Files:**
- Create: `src/toy_agent/orchestrator.py`
- Test: `tests/toy_agent/test_orchestrator.py`

**Interfaces:**
- Consumes: nothing from `aidr` or `detector_adapter` (never imports either — Global Constraints); a `CommandRunner` callable, injectable for tests, defaulting to real `subprocess.run` against `docker compose exec`.
- Produces: `CommandResult` (dataclass), `default_command_runner`, `run_test_case(test_case: dict, *, agent_timeout_s=..., detector_timeout_s=..., run_command=...) -> dict` — the function Plan 4's batch loop will call once per `TestCase`. Returns `{"transcript": <Transcript JSON dict or None>, "verdict": <Verdict JSON dict>}` — `transcript` is `None` only when the agent invocation itself failed before producing one (council-skeptic finding, Gap 9 targeted council: Plan 4 needs the transcript to populate the final `TestCase` for the report's "Casi concreti" section — discarding it here, as an earlier draft of this plan did, would have forced Plan 4 to change this function's signature anyway).

- [ ] **Step 1: Write the failing tests**

`tests/toy_agent/test_orchestrator.py`:

```python
import json

from toy_agent.orchestrator import CommandResult, run_test_case

_TEST_CASE = {
    "case_id": "case_001",
    "transcript": {"session_id": "case_001", "turns": [{"seq": 0, "role": "user", "content": "hi", "tool_call": None}], "stop_reason": None},
    "label": "benign", "technique_target": None, "rationale": "smoke test",
}

_TRANSCRIPT_JSON = json.dumps({"session_id": "case_001", "turns": [], "stop_reason": "completed"}).encode()
_VERDICT_JSON = json.dumps({"case_id": "case_001", "tool_name": "x", "status": "ok", "label": "benign"}).encode()
_TRUNCATE_OK = CommandResult(returncode=0, stdout=b"", stderr=b"")  # the thin-proxy log truncation call, always issued right before the detector invocation


class ScriptedRunner:
    """Returns one scripted CommandResult per call, in order — mirrors the
    FakeModelClient pattern already used in tests/toy_agent/test_agent_loop.py."""

    def __init__(self, script: list[CommandResult]):
        self._script = list(script)
        self.calls: list[tuple[list[str], bytes, float]] = []

    def __call__(self, cmd, stdin_bytes, timeout_s):
        self.calls.append((cmd, stdin_bytes, timeout_s))
        if not self._script:
            raise AssertionError("ScriptedRunner script exhausted")
        return self._script.pop(0)


def test_happy_path_returns_the_transcript_and_the_detector_verdict():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=0, stdout=_VERDICT_JSON, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"] == json.loads(_VERDICT_JSON)
    assert len(runner.calls) == 3
    assert runner.calls[0][0][:4] == ["docker", "compose", "exec", "-T"]
    assert "agent" in runner.calls[0][0]
    assert "detector" in runner.calls[1][0] and "sh" in runner.calls[1][0]  # the truncate call
    assert "detector" in runner.calls[2][0]
    assert runner.calls[2][1] == _TRANSCRIPT_JSON  # agent's stdout piped straight into detector's stdin


def test_agent_failed_to_start_is_classified_as_infra():
    runner = ScriptedRunner([CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert result["verdict"]["label"] is None
    assert len(runner.calls) == 1  # never attempted the truncate or detector invocation


def test_agent_nonzero_exit_is_classified_as_application():
    runner = ScriptedRunner([CommandResult(returncode=1, stdout=b"", stderr=b"bad seed turn")])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert "bad seed turn" in result["verdict"]["rationale"]


def test_detector_timeout_is_classified_as_infra_and_triggers_both_cleanup_calls():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=-1, stdout=b"", stderr=b"", timed_out=True),
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill detector_adapter.evaluate_case — last-resort fallback
        CommandResult(returncode=0, stdout=b"", stderr=b""),  # pkill aidr/providers — last-resort fallback
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "infra"
    assert len(runner.calls) == 5
    assert "detector_adapter.evaluate_case" in runner.calls[3][0]
    assert "aidr/providers" in runner.calls[4][0]


def test_detector_malformed_stdout_despite_exit_zero_is_classified_as_application():
    runner = ScriptedRunner([
        CommandResult(returncode=0, stdout=_TRANSCRIPT_JSON, stderr=b""),
        _TRUNCATE_OK,
        CommandResult(returncode=0, stdout=b"noise before json\n" + _VERDICT_JSON, stderr=b""),
    ])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] == json.loads(_TRANSCRIPT_JSON)
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"


def test_agent_malformed_stdout_despite_exit_zero_never_reaches_detector():
    runner = ScriptedRunner([CommandResult(returncode=0, stdout=b"not json", stderr=b"")])
    result = run_test_case(_TEST_CASE, run_command=runner)
    assert result["transcript"] is None
    assert result["verdict"]["status"] == "error"
    assert result["verdict"]["error_kind"] == "application"
    assert len(runner.calls) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/toy_agent/test_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'toy_agent.orchestrator'`.

- [ ] **Step 3: Implement `orchestrator.py`**

`src/toy_agent/orchestrator.py`:

```python
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Callable

CommandRunner = Callable[[list[str], bytes, float], "CommandResult"]

# Matches VENDOR_PROXY_LOG_PATH in docker-compose.yml (Task 4) and the default
# read by collect_thin_proxy_log (Task 8) — one fixed path, three places that
# must agree on it.
THIN_PROXY_LOG_PATH = "/var/log/vendor_proxy.jsonl"


@dataclass
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    failed_to_start: bool = False


def default_command_runner(cmd: list[str], stdin_bytes: bytes, timeout_s: float) -> "CommandResult":
    try:
        proc = subprocess.run(cmd, input=stdin_bytes, capture_output=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(returncode=-1, stdout=exc.stdout or b"", stderr=exc.stderr or b"", timed_out=True)
    except OSError:
        return CommandResult(returncode=-1, stdout=b"", stderr=b"", failed_to_start=True)
    return CommandResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def _error_verdict(case_id: str, error_kind: str, detail: str) -> dict:
    return {
        "case_id": case_id,
        "tool_name": "agentic_threat_detection",
        "status": "error",
        "error_kind": error_kind,
        "label": None,
        "confidence": None,
        "technique_detected": None,
        "rationale": detail,
        "cost_usd": None,
        "latency_s": None,
        "in_tokens": None,
        "out_tokens": None,
    }


def run_test_case(
    test_case: dict,
    *,
    agent_timeout_s: float = 120.0,
    detector_timeout_s: float = 180.0,
    run_command: CommandRunner = default_command_runner,
) -> dict:
    """Drive one TestCase through agent -> detector (design doc, 'Meccanismo di
    handoff'). Never imports aidr or detector_adapter — the JSON contract on
    stdin/stdout is the only thing this function knows about either side.

    Returns {"transcript": <Transcript JSON dict or None>, "verdict": <Verdict
    JSON dict>} — transcript is None only when the agent invocation itself
    failed before producing one (council-skeptic finding, Gap 9 targeted
    council: Plan 4 needs the transcript for the report's "Casi concreti"
    section — an earlier draft of this plan discarded it here, which would
    have forced Plan 4 to change this function's signature anyway)."""
    case_id = test_case["case_id"]

    agent_cmd = ["docker", "compose", "exec", "-T", "agent", "python", "-m", "toy_agent.run_case"]
    agent_input = json.dumps(test_case).encode("utf-8")
    agent_result = run_command(agent_cmd, agent_input, agent_timeout_s)

    if agent_result.failed_to_start:
        return {"transcript": None, "verdict": _error_verdict(case_id, "infra", "docker compose exec failed to start the agent invocation")}
    if agent_result.timed_out:
        return {"transcript": None, "verdict": _error_verdict(case_id, "infra", f"agent invocation exceeded {agent_timeout_s}s wall-clock timeout")}
    if agent_result.returncode != 0:
        return {"transcript": None, "verdict": _error_verdict(case_id, "application", agent_result.stderr.decode("utf-8", errors="replace"))}

    transcript_bytes = agent_result.stdout
    try:
        transcript_dict = json.loads(transcript_bytes)
    except json.JSONDecodeError:
        return {"transcript": None, "verdict": _error_verdict(case_id, "application", "agent produced invalid JSON on stdout despite exit code 0")}

    # Truncate the thin proxy's cumulative log immediately before this
    # invocation (council-risk finding, Gap 9 targeted council): vendor_proxy
    # runs as one long-lived background process for the whole detector
    # container's life, so without this its log mixes entries from every
    # prior case — the same per-case_id attribution problem the design doc
    # already solved for docker diff/stats (Task 8), never extended to this
    # channel until now. Mirrors the "fresh state per invocation" pattern
    # already established for Gap 5's WorldState reset. Best-effort: a
    # failure here degrades evidence attribution for this one case, it never
    # blocks detection itself — sequential execution (design doc) means a
    # failed truncate at worst leaves this case's log entries mixed with the
    # previous case's, not with a concurrent one.
    run_command(
        ["docker", "compose", "exec", "-T", "detector", "sh", "-c", f"> {THIN_PROXY_LOG_PATH}"],
        b"",
        10.0,
    )

    detector_cmd = ["docker", "compose", "exec", "-T", "detector", "python", "-m", "detector_adapter.evaluate_case"]
    detector_result = run_command(detector_cmd, transcript_bytes, detector_timeout_s)

    if detector_result.failed_to_start:
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "infra", "docker compose exec failed to start the detector invocation")}
    if detector_result.timed_out:
        # Last-resort fallback only (council-skeptic finding, Gap 9 targeted
        # council): evaluate_case.py (Task 6) now enforces its own internal
        # wall-clock deadline and terminates its MCP subprocesses via direct
        # process handles before exiting — this external cleanup only matters
        # if that internal mechanism somehow didn't fire (e.g. a bug, or
        # signal delivery delayed inside a C extension that doesn't check for
        # interrupts). Two patterns, not one: the evaluate_case process
        # itself (if the internal deadline never fired, it's still the
        # parent holding everything up — a single external pkill targeting
        # only "aidr/providers", as an earlier draft of this plan did, would
        # never touch that parent) and its MCP provider children (in case
        # the parent died but a child survived it, since killing a parent
        # does not cascade-kill children on Linux). Both best-effort,
        # non-fatal — a risk of degradation for the rest of the sequential
        # batch, not of total blockage, per the design doc.
        run_command(
            ["docker", "compose", "exec", "-T", "detector", "pkill", "-f", "detector_adapter.evaluate_case"],
            b"",
            10.0,
        )
        run_command(
            ["docker", "compose", "exec", "-T", "detector", "pkill", "-f", "aidr/providers"],
            b"",
            10.0,
        )
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "infra", f"detector invocation exceeded {detector_timeout_s}s wall-clock timeout")}
    if detector_result.returncode != 0:
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "application", detector_result.stderr.decode("utf-8", errors="replace"))}

    try:
        verdict_dict = json.loads(detector_result.stdout)
    except json.JSONDecodeError:
        return {"transcript": transcript_dict, "verdict": _error_verdict(case_id, "application", "detector produced invalid JSON on stdout despite exit code 0")}

    return {"transcript": transcript_dict, "verdict": verdict_dict}
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/toy_agent/test_orchestrator.py -v`
Expected: PASS, 6 tests.

Note: the two cleanup `pkill` commands the "timeout" test expects (Step 1's `test_detector_timeout_is_classified_as_infra_and_triggers_both_cleanup_calls`) are the orchestrator's last-resort fallback net — the primary cleanup mechanism now lives inside `evaluate_case.py` itself (Task 6, Step 6). Both layers are exercised by their own tests; neither depends on the other actually running.

- [ ] **Step 5: Run the full local suite**

Run: `pytest tests/ -v`
Expected: PASS everywhere except the 3 `aidr`-gated tests from Task 6 (skipped). `test_toy_agent_package_never_imports_aidr` still passes — `orchestrator.py` imports only `json`/`subprocess`/`dataclasses`/`typing`.

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/orchestrator.py tests/toy_agent/test_orchestrator.py
git commit -m "feat: add toy_agent.orchestrator single-TestCase invocation mechanism (Gap 9)"
```

---

### Task 8: External evidence collection (`toy_agent/evidence.py`)

**Files:**
- Create: `src/toy_agent/evidence.py`
- Test: `tests/toy_agent/test_evidence.py`

**Interfaces:**
- Consumes: nothing from `aidr`/`detector_adapter` — plain `docker`/`docker compose` CLI calls via an injectable runner, same DI pattern as Task 7.
- Produces: `collect_case_evidence(case_id, services, evidence_dir, *, run_command=...) -> dict[str, Path]` (the four generic channels — container logs for both services + `egress-proxy`, `docker diff`, `docker stats`, all four for both `agent` and `detector`), `collect_thin_proxy_log(case_id, evidence_dir, api_key, *, run_command=...) -> Path` (the vendor-specific fifth channel, scrubbed). Called once per `TestCase`, after `orchestrator.run_test_case()` returns — Plan 4's batch loop wires the two together; this task only needs to prove each collector works in isolation. By the time `collect_thin_proxy_log` runs, `run_test_case()` (Task 7) has already truncated the log immediately before its detector invocation — this function's `cat` therefore only ever sees this one case's entries, given the already-locked sequential-execution constraint (design doc); it doesn't need to know about the truncation itself, just read what's there.

- [ ] **Step 1: Write the failing tests**

`tests/toy_agent/test_evidence.py`:

```python
from toy_agent.evidence import collect_case_evidence, collect_thin_proxy_log


class FakeRunner:
    def __init__(self, responses: dict[tuple, bytes]):
        self._responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str]) -> bytes:
        self.calls.append(cmd)
        key = tuple(cmd)
        if key not in self._responses:
            raise AssertionError(f"unscripted command: {cmd}")
        return self._responses[key]


def _ps_key(service: str) -> tuple:
    return ("docker", "compose", "ps", "-q", service)


def test_collect_case_evidence_writes_all_channels_for_both_services(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "logs", "--no-color", "agent"): b"agent log line\n",
        ("docker", "compose", "logs", "--no-color", "detector"): b"detector log line\n",
        ("docker", "compose", "logs", "--no-color", "egress-proxy"): b"proxy log line\n",
        _ps_key("agent"): b"abc123\n",
        _ps_key("detector"): b"def456\n",
        ("docker", "diff", "abc123"): b"C /opt\n",
        ("docker", "diff", "def456"): b"C /var/log/vendor_proxy.jsonl\n",
        ("docker", "stats", "--no-stream", "abc123"): b"agent stats\n",
        ("docker", "stats", "--no-stream", "def456"): b"detector stats\n",
    })

    written = collect_case_evidence("case_001", ("agent", "detector"), tmp_path, run_command=runner)

    case_dir = tmp_path / "case_001"
    assert (case_dir / "agent.logs.txt").read_bytes() == b"agent log line\n"
    assert (case_dir / "detector.logs.txt").read_bytes() == b"detector log line\n"
    assert (case_dir / "egress-proxy.logs.txt").read_bytes() == b"proxy log line\n"
    assert (case_dir / "agent.diff.txt").read_bytes() == b"C /opt\n"
    assert (case_dir / "detector.diff.txt").read_bytes() == b"C /var/log/vendor_proxy.jsonl\n"
    assert (case_dir / "agent.stats.txt").read_bytes() == b"agent stats\n"
    assert (case_dir / "detector.stats.txt").read_bytes() == b"detector stats\n"
    assert set(written) == {
        "agent.logs", "detector.logs", "egress-proxy.logs",
        "agent.diff", "detector.diff", "agent.stats", "detector.stats",
    }


def test_collect_case_evidence_is_attributed_to_the_given_case_id(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "logs", "--no-color", "agent"): b"",
        ("docker", "compose", "logs", "--no-color", "detector"): b"",
        ("docker", "compose", "logs", "--no-color", "egress-proxy"): b"",
        _ps_key("agent"): b"abc123\n", _ps_key("detector"): b"def456\n",
        ("docker", "diff", "abc123"): b"", ("docker", "diff", "def456"): b"",
        ("docker", "stats", "--no-stream", "abc123"): b"", ("docker", "stats", "--no-stream", "def456"): b"",
    })
    collect_case_evidence("case_002", ("agent", "detector"), tmp_path, run_command=runner)
    assert (tmp_path / "case_002").is_dir()
    assert not (tmp_path / "case_001").exists()


def test_collect_thin_proxy_log_scrubs_the_api_key(tmp_path):
    runner = FakeRunner({
        ("docker", "compose", "exec", "-T", "detector", "cat", "/var/log/vendor_proxy.jsonl"):
            b'{"port": 8100, "request": {}, "response": {}}\nsecret-key-value-embedded-here\n',
    })
    path = collect_thin_proxy_log("case_003", tmp_path, "secret-key-value-embedded-here", run_command=runner)
    content = path.read_text(encoding="utf-8")
    assert "secret-key-value-embedded-here" not in content
    assert "[REDACTED]" in content
    assert path == tmp_path / "case_003" / "detector.vendor_proxy.jsonl"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/toy_agent/test_evidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'toy_agent.evidence'`.

- [ ] **Step 3: Implement `evidence.py`**

`src/toy_agent/evidence.py`:

```python
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

CommandRunner = Callable[[list[str]], bytes]


def default_command_runner(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True)
    return proc.stdout + proc.stderr


def _container_id(service: str, run_command: CommandRunner) -> str:
    output = run_command(["docker", "compose", "ps", "-q", service])
    return output.decode("utf-8").strip().splitlines()[0]


def collect_case_evidence(
    case_id: str,
    services: tuple[str, str],
    evidence_dir: Path,
    *,
    run_command: CommandRunner = default_command_runner,
) -> dict[str, Path]:
    """Snapshot the four generic external-evidence channels for both
    containers immediately after invoking `services` for `case_id` (design
    doc, 'Raccolta prove esterna' — extended to both agent and detector,
    attributed per-case_id, council-mirato finding 2026-08-16)."""
    case_dir = evidence_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for service in (*services, "egress-proxy"):
        path = case_dir / f"{service}.logs.txt"
        path.write_bytes(run_command(["docker", "compose", "logs", "--no-color", service]))
        written[f"{service}.logs"] = path

    for service in services:
        container_id = _container_id(service, run_command)

        diff_path = case_dir / f"{service}.diff.txt"
        diff_path.write_bytes(run_command(["docker", "diff", container_id]))
        written[f"{service}.diff"] = diff_path

        stats_path = case_dir / f"{service}.stats.txt"
        stats_path.write_bytes(run_command(["docker", "stats", "--no-stream", container_id]))
        written[f"{service}.stats"] = stats_path

    return written


def collect_thin_proxy_log(
    case_id: str,
    evidence_dir: Path,
    api_key: str,
    *,
    run_command: CommandRunner = default_command_runner,
) -> Path:
    """Retrieve the thin proxy's request/response log from inside `detector`
    (already scrubbed at write time, Task 1 — this is defense in depth, not
    the only scrub point) and persist it under this case_id's evidence dir.
    Vendor-specific (not one of the four generic channels above) — design
    doc, 'Contratto riusabile del container detector'."""
    case_dir = evidence_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    raw = run_command(["docker", "compose", "exec", "-T", "detector", "cat", "/var/log/vendor_proxy.jsonl"])
    scrubbed = raw.replace(api_key.encode("utf-8"), b"[REDACTED]") if api_key else raw
    path = case_dir / "detector.vendor_proxy.jsonl"
    path.write_bytes(scrubbed)
    return path
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/toy_agent/test_evidence.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Run the full local suite**

Run: `pytest tests/ -v`
Expected: PASS everywhere except the 3 `aidr`-gated tests (skipped, unchanged from Task 6).

- [ ] **Step 6: Commit**

```bash
git add src/toy_agent/evidence.py tests/toy_agent/test_evidence.py
git commit -m "feat: add per-case_id external evidence collection for both containers (Gap 9)"
```

---

### Task 9: MCP provider persistent-state review (open item from the Gap 9 targeted council)

**Files:**
- Create: `docs/design/2026-08-16-mcp-provider-persistent-state-review.md`
- Modify: `docs/design/2026-08-14-toy-agent-gap-tracking.md` (Gap 9 — close the "residuo su filesystem" open item with the outcome)

**Interfaces:**
- Consumes: the pinned vendor clone (`agentic-threat-detection-vendor`, commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`).
- Produces: a committed review document classifying every disk write reachable from `Inspector()`/`Pipeline().analyze()` — closes the item the design doc left explicitly open ("Residuo su filesystem nel container detector a lunga vita... Non verificato in questa sessione").

- [ ] **Step 1: Re-run the scan against the pinned commit**

Run (from the vendor clone directory):

```bash
grep -n "open(\|write_text\|\.write(" aidr/providers/sourcelens.py aidr/providers/threatlens.py aidr/providers/policylens.py aidr/detector/runtime.py
```

Expected baseline (found while structuring this task — if your output differs, the vendor clone is not at the pinned commit; stop and investigate):

```
aidr/providers/sourcelens.py:7:REGISTRY = yaml.safe_load(open("aidr/data/source_registry.yaml"))["servers"]
aidr/providers/threatlens.py:8:_fw = yaml.safe_load(open("aidr/data/threat_repository.yaml"))["threat_framework"]
aidr/providers/policylens.py:5:POLICIES = yaml.safe_load(open("aidr/data/policy_store.yaml"))["policies"]
aidr/detector/runtime.py:20:    config_path.write_text(json.dumps({"mcpServers": mcp_servers}, indent=2))
```

- [ ] **Step 2: Write the review document**

`docs/design/2026-08-16-mcp-provider-persistent-state-review.md`:

```markdown
# Review: stato persistente su disco dei tre provider MCP (Gap 9)

Verifica richiesta dal design doc, sezione "Meccanismo di handoff" — "Residuo su
filesystem nel container detector a lunga vita", item lasciato esplicitamente
aperto ("Non verificato in questa sessione"). Vendor: `agentic-threat-detection-vendor`,
commit pinnato `7fad14d2478707e68a09b8ecd9942dec8fde1614`.

## Scansione

    grep -n "open(\|write_text\|\.write(" aidr/providers/sourcelens.py aidr/providers/threatlens.py aidr/providers/policylens.py aidr/detector/runtime.py

[Incolla qui l'output effettivo ottenuto rieseguendo la scansione — deve
corrispondere al baseline dello Step 1 di Task 9, salvo il commit pinnato sia
cambiato.]

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
```

Fill in the actual scan output from Step 1 before committing — this document is evidence, not a template (same discipline as Plan 3, Task 4/5).

- [ ] **Step 3: Close the open item in the gap-tracking doc**

In `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 9, find the paragraph starting "**Residuo su filesystem nel container `detector` a lunga vita**" (in the "Meccanismo di handoff" quote embedded in the gap tracking doc's own narrative — the paragraph describing this as "Non verificato in questa sessione"). Add a follow-up sentence: "**Verificato (2026-08-16, piccolo piano dedicato, Task 9)**: nessuno dei tre provider MCP scrive stato persistente su disco — vedi `docs/design/2026-08-16-mcp-provider-persistent-state-review.md` per la review completa. L'unica scrittura (`.mcp.json`, da `write_mcp_config`) è deterministica e completamente sovrascritta a ogni invocazione, nessun residuo di contenuto tra `TestCase`."

- [ ] **Step 4: Commit**

```bash
git add docs/design/2026-08-16-mcp-provider-persistent-state-review.md docs/design/2026-08-14-toy-agent-gap-tracking.md
git commit -m "docs: verify no MCP provider writes persistent state to disk between TestCase invocations (Gap 9)"
```

---

## Self-Review Notes

- **Spec coverage**: every Gap-9-tagged row of the design doc's Requisito→Verifica mapping is covered — import boundary both directions (Task 2/3 Step 3, Task 1 Step 7-8), no process imports both libraries (Task 1 Step 7, Task 7's static-test coverage via the unchanged `test_no_vendor_imports.py`), network isolation between `agent`/`detector` (Task 4 Step 5), two distinct API keys (Task 4 Step 6), error contract infra vs. application (Task 7 tests), wall-clock timeout + MCP cleanup — primary inside `evaluate_case` (Task 6), last-resort fallback in the orchestrator (Task 7) — five evidence channels persisted per `case_id`, now including a truly per-case thin-proxy log (Task 7's truncation + Task 8 tests), thin-proxy log scrub (Task 1 Step 3/Task 8 Step 1), `evaluate_case` stdout discipline (Task 6 Step 2, Task 7's malformed-stdout test). The vendor-swap reuse row ("Contratto riusabile...") is untestable until a second vendor exists, as the design doc itself says — not owed a task here. See the "Requisito → Task" table below for the full row-by-row trace (council-advocate finding, Gap 9 targeted council).
- **Type consistency**: `CommandResult`/`CommandRunner` (Task 7) match exactly between `orchestrator.py`'s signature and every test's `ScriptedRunner`. `Verdict`-shaped dict keys (`case_id`, `tool_name`, `status`, `label`, `confidence`, `technique_detected`, `rationale`, `cost_usd`, `latency_s`, `in_tokens`, `out_tokens`, plus `error_kind` only on error) are identical across Task 6's `detection_result_to_verdict`, Task 7's `_error_verdict`, and every test asserting against them. `run_test_case()`'s `{"transcript": ..., "verdict": ...}` return shape is used consistently across every Task 7 test. `TestCase`-shaped input (`case_id`, `transcript.turns[0]`) matches between Task 5's `_extract_scenario` and Task 7's `_TEST_CASE` fixture.
- **Placeholder scan**: Task 9's evidence document contains one bracketed fill-in (`[Incolla qui...]`) by design — it's evidence whose content depends on re-running a real command at execution time, same pattern already established and explicitly justified in Plan 3, Task 4/5. Every other step has concrete, complete, real code — no `TBD`, no "add appropriate error handling," no "similar to Task N."
- **Scope boundary honored**: Task 1/4/5/6 of `docs/superpowers/plans/2026-08-15-control-container.md` are not reopened — their files are moved (Task 1's `vendor_proxy.py`, Task 6's `verify_sourcelens.py`/registry) or referenced (Task 5's review conclusions), never rewritten. `cost_usd` computation is explicitly deferred to Plan 4's metrics module, per the design doc's own attribution — not silently dropped, not silently built here either; the raw `in_tokens`/`out_tokens` it needs are preserved now instead.

## Requisito → Task (design doc, Gap 9 rows of "Mapping Requisito → Verifica")

Tracciabilità esplicita richiesta da `council-advocate` (council mirato, 2026-08-16) — un revisore esterno non dovrebbe dover leggere piano e design doc in parallelo per trovare la corrispondenza.

| Requisito (design doc) | Task/Step di questo piano |
|---|---|
| `aidr` mai installato/importabile in `agent`; `toy_agent` mai in `detector` | Task 2 Step 3, Task 3 Step 5 |
| Nessun processo di `orchestrator`/`detector_adapter` importa entrambe le librerie | Task 1 Step 7 (test statico esteso), Task 6/7 (nessun import incrociato per costruzione) |
| Contratto di errore infra vs. applicativo, per ogni invocazione | Task 7, tutti i test tranne il happy path |
| Due `OPENROUTER_API_KEY` distinte | Task 4 Step 6 |
| Timeout wall-clock nostro, indipendente da cap interni `aidr` | Task 7 (`agent_timeout_s`/`detector_timeout_s`), Task 6 (`EVALUATE_CASE_DEADLINE_S`, deve restare più corto — Global Constraints) |
| `agent`/`detector` non raggiungibili direttamente tra loro | Task 4 Step 5 |
| Cinque canali di prova raccolti e persistiti per ogni `case_id` | Task 8 (test), Task 7 (troncamento log thin proxy pre-invocazione — chiude il gap trovato da `council-risk`) |
| `docker diff`/`docker stats` attribuibili al singolo `case_id`, entrambi i container | Task 8 test `test_collect_case_evidence_writes_all_channels_for_both_services` |
| Log del thin proxy mai contiene la API key in chiaro | Task 1 Step 3/5 (test + scrub implementato alla scrittura), Task 8 Step 1/3 (test + scrub implementato al recupero, difesa in profondità) |
| `evaluate_case` scrive solo il `Verdict` JSON su stdout, diagnostica su stderr | Task 6 Step 2 (test), Step 6 (implementazione) |
| Sostituire il vendor non deve toccare `toy_agent`/orchestratore/canali generici | Non testabile finché non esiste un secondo vendor — dichiarato esplicitamente dal design doc stesso, non owed qui |

## Council mirato — findings applicati (2026-08-16)

Eseguito su questo file dopo la prima stesura, roster completo, ognuno col piano intero + design doc + gap-tracking doc come contesto, con mandato esplicito a verificare autonomamente sul codice vendor pinnato invece di fidarsi del testo del piano. Sintesi completa nella conversazione che ha prodotto questo documento; qui solo l'esito.

| Agente | Verdetto | Punto chiave |
|---|---|---|
| `council-skeptic` | agree with reservations | Il cleanup `pkill` esterno copriva solo il sottoprocesso MCP bloccato, non il processo padre `evaluate_case` stesso — scenario altrettanto plausibile dati i timeout configurati |
| `council-risk` | rischio moderato | Il log del thin proxy era cumulativo per l'intera vita del container, senza attribuzione per `case_id` — stesso problema già risolto per `docker diff`/`docker stats` ma mai esteso a questo canale |
| `council-pragmatist` | agree with reservations | Task 8 (`evidence.py`) costruito senza un punto d'uso reale in questo piano — rischio minore, non applicato (vedi "Non applicati" sotto) |
| `council-advocate` | has rough edges | `Verdict.tool_name`/`cost_usd` non documentati nello schema pubblico; passo manuale per i test `aidr`-gated descritto solo in prosa; nessuna tracciabilità esplicita requisito→task |

**Applicati** (convergenza forte tra `council-skeptic` e `council-risk`, trovata indipendentemente sulla stessa causa radice — un processo `evaluate_case` bloccato che né l'uno né l'altro `pkill` originale avrebbe raggiunto):
- Cleanup primario spostato dentro `evaluate_case` stesso: deadline interno via `signal.setitimer`, terminazione diretta dei sottoprocessi MCP tramite `Inspector.router.clients[...].proc` (Task 6) — non più solo un `pkill` esterno indovinato per nome.
- `pkill` esterno dell'orchestratore mantenuto come rete di sicurezza di ultima istanza, esteso a due pattern (`detector_adapter.evaluate_case` oltre a `aidr/providers`) invece di uno solo (Task 7).
- Troncamento del log del thin proxy immediatamente prima di ogni invocazione detector, dall'orchestratore (Task 7) — rende il canale naturalmente per-`case_id`.
- `in_tokens`/`out_tokens` preservati nel `Verdict` JSON invece di scartati (Task 6) — altrimenti `cost_usd` sarebbe stato reso incalcolabile in futuro, non solo rimandato.
- `run_test_case()` restituisce transcript + verdict, non solo il verdict (Task 7) — coerente con la sezione "Scope boundary with Plan 4" del piano stesso.
- `Verdict.tool_name`/`cost_usd` documentati con un commento in `src/toy_agent/schema.py` (Task 6, doc-only).
- Script `docker/detector/run_adapter_tests.sh` committato per rendere riproducibile il passo manuale dei test `aidr`-gated, invece di lasciarlo solo in prosa nel piano (Task 6).
- Tabella "Requisito → Task" aggiunta sopra.

**Non applicati, registrati ma non implementati**:
- Dissenso di `council-pragmatist` su Task 8 (evidence.py costruito senza un punto d'uso reale in questo piano) — non applicato: la sua API è già usata concettualmente da Task 7 (il troncamento condivide lo stesso `THIN_PROXY_LOG_PATH`), e separarla da Plan 4 resta comunque necessario per poterla testare in isolamento come richiesto dalla granularità TDD di questo piano.
- Punti minori di `council-skeptic`/`council-risk` su calibrazione empirica dei valori di timeout (120s/180s, non derivati da misure reali di latenza) e sulla copertura del test di isolamento rete solo per nome, non anche per IP diretto (Task 4 Step 5) — segnalati come limiti da rivalutare quando esisterà un primo run reale (Plan 4/5), non bloccanti per la chiusura strutturale di Gap 9.
