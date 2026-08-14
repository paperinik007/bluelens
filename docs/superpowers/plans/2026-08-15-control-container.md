# Control Container (Plan 3 of 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Linux control container that runs the pinned vendor `aidr` package (Sifter/Inspector/SourceLens/ThreatLens/PolicyLens) and the toy agent's tool execution with network egress locked down to OpenRouter only, pass a preventive security audit of that container, and produce the empirical verification that Inspector's SourceLens channel actually fires for `toy_support` (Gap 4).

**Architecture:** Two Docker Compose services. `control` runs the vendor's pinned `aidr` clone plus the `toy_agent` Python package (already built in Plan 1) and a small in-process OpenRouter tier-remapping proxy (`toy_agent.vendor_proxy`) bound to the loopback ports `model_client.py` hardcodes (8100/8101/8102). `control` sits on a Docker `internal: true` network with no route to the internet at all — DNS included. `egress-proxy`, the only service dual-homed onto both that internal network and a normal bridge network, runs Squid configured to splice (pass through, never terminate TLS) HTTPS CONNECT tunnels whose SNI is `openrouter.ai` and refuse everything else. `vendor_proxy` reaches OpenRouter exclusively through `egress-proxy` as its `HTTPS_PROXY`.

**Tech Stack:** Docker Desktop (Linux containers), Docker Compose, Python 3.11 (matches Plan 1), `httpx` (already a transitive dependency of the `openai` SDK from Plan 1), Squid, Trivy.

**Spec:** `docs/design/2026-08-14-toy-agent-e-pipeline-misura.md` (sections: "Setup pratico del detector sotto test", "Container di controllo: fedeltà d'ambiente e contenimento di sicurezza", "Registro SourceLens..."), `docs/design/2026-08-14-toy-agent-gap-tracking.md` (Gap 1, Gap 3, Gap 4, Gap 8). Vendor reference: `agentic-threat-detection-vendor` (sibling clone, pinned commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`).

## Global Constraints

- Nessun bind-mount a runtime della repo vendor o di `src/toy_agent` nel container — tutto il codice entra nell'immagine via `COPY`/`git clone` al build (Gap 8, principio 4 `SPIRIT.md`: riproducibilità da un checkout fresco).
- Il container `control` non ha alcuna rotta di rete diretta verso l'esterno: solo verso `egress-proxy` sulla rete Docker `internal_net` (`internal: true`).
- `egress-proxy` inoltra (mai termina TLS, solo `splice`) esclusivamente CONNECT il cui SNI è `openrouter.ai:443`; qualunque altro dominio, DNS incluso, deve fallire dall'interno di `control`.
- Nessuna credenziale reale nell'ambiente di `control` a parte `OPENROUTER_API_KEY`, iniettata a runtime via variabile d'ambiente (mai nell'immagine, mai committata — `.env` in `.gitignore`).
- L'immagine `control` non deve avere vulnerabilità `CRITICAL` irrisolte secondo Trivy.
- Il codice sorgente registrato in SourceLens per `toy_support` deve essere identico, byte per byte, a `src/toy_agent/tools.py` nel repo — mai una copia divergente (verificato con un hash).
- Il nostro codice non deve mai importare o invocare `aidr.gauntlet.runner` o i server del Gauntlet del vendor (`aidr/gauntlet/servers/...`, incluso `host_toolkit.py` che fa una vera `requests.get`) — quel percorso del pacchetto vendor non è mai sulla strada di `Pipeline().analyze()`/`Inspector.analyze()` per come li usiamo, e deve restarci estraneo.
- Il review del codice vendor per chiamate di rete/filesystem non dichiarate (Task 5) deve essere completato prima di eseguire la verifica empirica di Gap 4 (Task 6).

---

### Task 1: Thin proxy OpenRouter (`vendor_proxy.py`)

**Files:**
- Create: `src/toy_agent/vendor_proxy.py`
- Test: `tests/toy_agent/test_vendor_proxy.py`

**Interfaces:**
- Consumes: nothing from prior Plan 1 tasks (standalone infra module, same package).
- Produces: `TIER_TO_MODEL: dict[str, str]`, `PORT_TO_PATH: dict[int, str]`, `remap_tier(body: dict) -> dict`, `build_forwarder(api_key: str, proxy_url: str | None = None, transport: httpx.BaseTransport | None = None) -> Forwarder` where `Forwarder = Callable[[int, dict], dict]`, `serve_forever(ports: list[int], forward: Forwarder) -> list[_ForwardingHTTPServer]`, `main() -> None`.

- [ ] **Step 1: Write the failing tests**

`tests/toy_agent/test_vendor_proxy.py`:

```python
import json
import time
from http.client import HTTPConnection

import httpx
import pytest

from toy_agent.vendor_proxy import (
    build_forwarder,
    remap_tier,
    serve_forever,
)


def test_remap_tier_rewrites_model_field():
    body = {"model": "sifter", "messages": []}
    remapped = remap_tier(body)
    assert remapped["model"] == "qwen/qwen3-4b-instruct-2507"
    assert body["model"] == "sifter"  # original untouched


def test_remap_tier_rejects_unknown_tier():
    with pytest.raises(ValueError):
        remap_tier({"model": "unknown-tier"})


def test_build_forwarder_posts_remapped_body_to_openrouter_chat_endpoint():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    result = forward(8100, {"model": "sifter", "messages": [{"role": "user", "content": "hi"}]})

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == "qwen/qwen3-4b-instruct-2507"
    assert result == {"choices": []}


def test_build_forwarder_posts_embeddings_endpoint_for_embed_tier():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"data": []})

    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(handler))
    result = forward(8102, {"model": "embed", "input": "hello"})

    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["body"]["model"] == "qwen/qwen3-embedding-0.6b"
    assert result == {"data": []}


def test_forward_raises_for_unconfigured_port():
    forward = build_forwarder(api_key="sk-test", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    with pytest.raises(ValueError):
        forward(9999, {"model": "sifter"})


def test_serve_forever_binds_loopback_and_serves_stubbed_response():
    def stub_forward(port: int, body: dict) -> dict:
        return {"echo": body, "port": port}

    servers = serve_forever([18100], stub_forward)
    try:
        time.sleep(0.05)  # let the background thread start listening
        conn = HTTPConnection("127.0.0.1", 18100, timeout=2)
        payload = json.dumps({"model": "sifter"}).encode()
        conn.request("POST", "/v1/chat/completions", body=payload, headers={"Content-Length": str(len(payload))})
        response = conn.getresponse()
        result = json.loads(response.read())
        assert response.status == 200
        assert result == {"echo": {"model": "sifter"}, "port": 18100}
    finally:
        for server in servers:
            server.shutdown()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/toy_agent/test_vendor_proxy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'toy_agent.vendor_proxy'`

- [ ] **Step 3: Implement vendor_proxy.py**

```python
from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

import httpx

# aidr/serving/model_client.py (vendor, pinned commit 7fad14d2478707e68a09b8ecd9942dec8fde1614)
# sends `model` as the literal tier name ("sifter"/"inspector"/"embed"), not a real
# OpenRouter model id (design doc, "Setup pratico del detector sotto test").
TIER_TO_MODEL: dict[str, str] = {
    "sifter": "qwen/qwen3-4b-instruct-2507",
    "inspector": "qwen/qwen3-30b-a3b-instruct-2507",
    "embed": "qwen/qwen3-embedding-0.6b",
}

# Port -> OpenRouter path, matching model_client.py's hardcoded ports:
# 8100=sifter, 8101=inspector (both chat completions), 8102=embed (embeddings).
PORT_TO_PATH: dict[int, str] = {
    8100: "/chat/completions",
    8101: "/chat/completions",
    8102: "/embeddings",
}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

Forwarder = Callable[[int, dict], dict]


def remap_tier(body: dict) -> dict:
    """Return a copy of body with body['model'] rewritten tier -> OpenRouter model id."""
    tier = body.get("model")
    if tier not in TIER_TO_MODEL:
        raise ValueError(f"unknown tier in request body: {tier!r}")
    remapped = dict(body)
    remapped["model"] = TIER_TO_MODEL[tier]
    return remapped


def build_forwarder(
    api_key: str,
    proxy_url: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> Forwarder:
    """Build a Forwarder that POSTs a tier-remapped body to OpenRouter.

    proxy_url routes the outbound call through egress-proxy (the only container
    with a real route to the internet — see design doc, "Container di controllo").
    transport is for tests only: it bypasses proxy_url and any real network call.
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
        response = client.post(path, json=remapped)
        response.raise_for_status()
        return response.json()

    return forward


class _ForwardingHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], handler_cls: type, forward: Forwarder) -> None:
        super().__init__(address, handler_cls)
        self.forward = forward


class _ProxyHandler(BaseHTTPRequestHandler):
    server: _ForwardingHTTPServer  # narrows the type for self.server.forward below

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        try:
            result = self.server.forward(self.server.server_port, body)
        except Exception as exc:  # noqa: BLE001 - the listener must never crash on a bad/failed call
            payload = json.dumps({"error": exc.__class__.__name__}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        payload = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:  # silence default stderr access log
        pass


def serve_forever(ports: list[int], forward: Forwarder) -> list[_ForwardingHTTPServer]:
    """Start one listener per port, each bound to 127.0.0.1 (model_client.py hardcodes loopback)."""
    servers = [_ForwardingHTTPServer(("127.0.0.1", port), _ProxyHandler, forward) for port in ports]
    for server in servers:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    return servers


def main() -> None:
    api_key = os.environ["OPENROUTER_API_KEY"]
    proxy_url = os.environ.get("HTTPS_PROXY")
    forward = build_forwarder(api_key, proxy_url)
    serve_forever(list(PORT_TO_PATH), forward)
    threading.Event().wait()  # keep the process alive; servers run on daemon threads


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/toy_agent/test_vendor_proxy.py -v`
Expected: PASS (no real network call is made anywhere in this suite — `MockTransport` for the outbound side, plain loopback sockets for the inbound side)

- [ ] **Step 5: Commit**

```bash
git add src/toy_agent/vendor_proxy.py tests/toy_agent/test_vendor_proxy.py
git commit -m "feat: add OpenRouter tier-remapping proxy for the vendor's model_client.py"
```

---

### Task 2: Immagine del container di controllo (`docker/control/`)

**Files:**
- Create: `docker/control/Dockerfile`
- Create: `docker/control/entrypoint.sh`
- Create: `docker/control/source_registry.yaml`

**Interfaces:**
- Consumes: `src/toy_agent/` (whole package, including Task 1's `vendor_proxy.py`), `pyproject.toml` (Plan 1, Task 1) — copied into the image.
- Produces: a buildable Docker image (`agentic-security-audits-control`, tag applied in Task 3's compose file) with the pinned vendor clone at `/opt/aidr-vendor`, the `toy_agent` package installed editable, and `aidr/data/source_registry.yaml` + `aidr/gauntlet/servers/toy_support/toy_support.py` baked in.

- [ ] **Step 1: Write the Dockerfile**

`docker/control/Dockerfile`:

```dockerfile
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Vendor code, pinned for reproducibility (SPIRIT.md principio 4) — cloned at
# build time, never bind-mounted from the host (Gap 8).
WORKDIR /opt
RUN git clone https://github.com/FareedKhan-dev/agentic-threat-detection.git aidr-vendor \
    && cd aidr-vendor \
    && git checkout 7fad14d2478707e68a09b8ecd9942dec8fde1614

WORKDIR /opt/aidr-vendor
RUN pip install --no-cache-dir -r requirements.txt

# toy_agent package (Plan 1 + this plan's vendor_proxy.py), installed editable so
# `python -m toy_agent.vendor_proxy` and (Plan 4) the orchestrator both work from
# the same image without a rebuild.
COPY pyproject.toml /opt/toy_agent/pyproject.toml
COPY src/toy_agent /opt/toy_agent/src/toy_agent
WORKDIR /opt/toy_agent
RUN pip install --no-cache-dir -e .

# SourceLens registry entry for toy_support (Gap 1/Gap 4/Gap 8): the registered
# source is a build-time COPY of the exact file in this repo, never hand-duplicated
# — verified byte-for-byte against src/toy_agent/tools.py in Task 2's Step 3 below.
RUN mkdir -p /opt/aidr-vendor/aidr/gauntlet/servers/toy_support
COPY src/toy_agent/tools.py /opt/aidr-vendor/aidr/gauntlet/servers/toy_support/toy_support.py
COPY docker/control/source_registry.yaml /opt/aidr-vendor/aidr/data/source_registry.yaml

COPY docker/control/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

# aidr's providers (sourcelens.py, threatlens.py, policylens.py) read relative
# paths from the vendor repo root (Gap 3) — cwd must be there for every command.
WORKDIR /opt/aidr-vendor
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
```

- [ ] **Step 2: Write the entrypoint**

`docker/control/entrypoint.sh`:

```bash
#!/bin/sh
set -e
# Start the OpenRouter tier-remapping proxy in the background so model_client.py's
# hardcoded http://127.0.0.1:8100/8101/8102 have something to talk to (Task 1).
python -m toy_agent.vendor_proxy &
proxy_pid=$!

# `set -e` does NOT catch a backgrounded job's failure (council-risk finding on
# this plan): without this check, a dead vendor_proxy (e.g. missing
# OPENROUTER_API_KEY, which raises KeyError in main()) would leave the container
# reporting "Up" via CMD ["sleep", "infinity"] with no working proxy at all —
# surfacing later as an opaque connection-refused error, at worst during Task 6
# after a billed OpenRouter call has already been attempted. Fail loudly here
# instead, before anything downstream depends on these ports being open.
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

- [ ] **Step 3: Write the extended SourceLens registry**

`docker/control/source_registry.yaml`:

```yaml
# Extends the vendor's original registry (aidr/data/source_registry.yaml, pinned
# commit 7fad14d2478707e68a09b8ecd9942dec8fde1614) with one entry for the toy
# agent's server. Baked into the control image at build time (Dockerfile COPY),
# replacing the vendor's original file — see design doc, "Registro SourceLens" +
# gap-tracking doc, Gap 8.
servers:
  - name: analytics_insights
    path: analytics_insights/function/analytics_insights.py
    category: analytics
    description: "Service-log analytics and insight generation."
  - name: business_metrics
    path: business_metrics/business_metrics.py
    category: analytics
    description: "Business KPI dashboard generation from seeded demo data."
  - name: host_toolkit
    path: host_toolkit/host_toolkit.py
    category: system
    description: "Host file utilities: download, delete, and list files."
  - name: toy_support
    path: toy_support/toy_support.py
    category: system
    description: "Customer support toy agent: customer DB, tickets, email, account updates, diagnostics, bulk export."
```

- [ ] **Step 4: Build the image and verify it**

Run (from repo root):

```bash
docker build -f docker/control/Dockerfile -t agentic-security-audits-control .
```

Expected: builds successfully, exits 0.

Run:

```bash
docker run --rm agentic-security-audits-control sha256sum aidr/gauntlet/servers/toy_support/toy_support.py
```

Compare the printed hash to a local `sha256sum src/toy_agent/tools.py` (or PowerShell `Get-FileHash`) — they must match exactly. This is the executable form of the mapping's requirement "hash del contenuto del codice sorgente registrato identico".

Run:

```bash
docker run --rm agentic-security-audits-control grep toy_support aidr/data/source_registry.yaml
```

Expected: prints `  - name: toy_support` (registry entry present).

- [ ] **Step 5: Commit**

```bash
git add docker/control/Dockerfile docker/control/entrypoint.sh docker/control/source_registry.yaml
git commit -m "feat: add control container image (pinned vendor clone + toy_agent + SourceLens registry)"
```

---

### Task 3: Egress lockdown (`egress-proxy` + `docker-compose.yml`)

**Nota su proporzionalità (council-pragmatist, checkpoint di questo piano)**: questo
contenimento a livello di rete protegge principalmente contro un rischio che Task 5
(review del codice vendor) dovrebbe dimostrare non esistere sul percorso che usiamo
(`Pipeline().analyze()`/`Inspector.analyze()`) — è quindi difesa in profondità
dichiarata, non l'unica linea. Stessa tensione già valutata e decisa dal council
originale sul design doc (`2026-08-14-toy-agent-e-pipeline-misura.md`, sezione "Esito
valutazione council": una proposta di alleggerire questo audit non è stata applicata
perché i sottoprocessi MCP reali del vendor leggono contenuto avversariale scritto
apposta per manipolare un LLM — un argomento di sicurezza che pesa più della sua
controparte YAGNI). Non riaperta qui: la stessa logica si applica identica al
meccanismo scelto per applicarla.

**Files:**
- Create: `docker/egress-proxy/Dockerfile`
- Create: `docker/egress-proxy/squid.conf`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: Task 2's `control` image build context (`docker/control/Dockerfile`).
- Produces: a running two-container stack (`control`, `egress-proxy`) where `control` has no direct internet route and can only reach `openrouter.ai:443` through `egress-proxy`.

- [ ] **Step 1: Write the Squid egress proxy**

`docker/egress-proxy/Dockerfile`:

```dockerfile
FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends squid openssl \
    && rm -rf /var/lib/apt/lists/*

# ssl_bump's config parser requires a cert/key pair on the listening port even
# though "peek" + "splice" (used below) never terminates TLS or uses this key to
# decrypt anything — self-signed and disposable, satisfies startup validation only.
RUN openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
    -keyout /etc/squid/squid.key -out /etc/squid/squid.crt \
    -subj "/CN=egress-proxy-placeholder"

COPY squid.conf /etc/squid/squid.conf
EXPOSE 3128
CMD ["squid", "-N", "-d", "1"]
```

`docker/egress-proxy/squid.conf`:

```
# Only egress path for the control container (docker-compose.yml). SNI-based
# allowlist: Squid peeks the TLS ClientHello to read the SNI, then either splices
# (pure byte passthrough, TLS never terminated) for openrouter.ai or terminates
# the connection for anything else. Design doc, "Container di controllo" — Gap 8.
http_port 3128 ssl-bump tls-cert=/etc/squid/squid.crt tls-key=/etc/squid/squid.key generate-host-certificates=off

acl step1 at_step SslBump1
ssl_bump peek step1
acl allowed_sni ssl::server_name openrouter.ai
ssl_bump splice allowed_sni
ssl_bump terminate all

acl SSL_ports port 443
acl CONNECT method CONNECT
http_access deny CONNECT !SSL_ports
http_access allow CONNECT allowed_sni
http_access deny CONNECT !allowed_sni
http_access deny all
```

- [ ] **Step 2: Write the compose file**

`docker-compose.yml` (repo root):

```yaml
services:
  egress-proxy:
    build:
      context: ./docker/egress-proxy
    networks:
      internal_net:
      default:
    expose:
      - "3128"

  control:
    build:
      context: .
      dockerfile: docker/control/Dockerfile
    depends_on:
      - egress-proxy
    environment:
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      HTTPS_PROXY: http://egress-proxy:3128
    networks:
      internal_net:

networks:
  internal_net:
    internal: true
```

- [ ] **Step 3: Wire the API key and gitignore it**

`.env.example` (repo root):

```
OPENROUTER_API_KEY=
```

Add to `.gitignore`:

```
.env
```

- [ ] **Step 4: Build, start, and verify the egress lockdown**

Run:

```bash
docker compose build
docker compose up -d
```

Expected: both services start; `docker compose ps` shows `control` and `egress-proxy` running.

Run (arbitrary domain must fail, DNS included):

```bash
docker compose exec control sh -c "getent hosts example.com; echo exit=\$?"
```

Expected: `exit=` a nonzero code — `control` has no DNS route to resolve anything outside the internal network, so resolution itself fails, not just the subsequent connect.

Run (arbitrary domain, direct connect attempt, no proxy):

```bash
docker compose exec control sh -c "curl -s -o /dev/null -w '%{http_code}\n' --max-time 5 https://example.com || echo BLOCKED"
```

Expected: `BLOCKED` (curl fails before getting any HTTP status — no route).

Run (the one allowed path, through egress-proxy, must succeed):

```bash
docker compose exec control sh -c "curl -s -o /dev/null -w '%{http_code}\n' -x http://egress-proxy:3128 https://openrouter.ai/api/v1/models"
```

Expected: `200` (OpenRouter's model listing is publicly readable; if the deployed OpenRouter API requires auth for this route by the time this runs, add `-H \"Authorization: Bearer $OPENROUTER_API_KEY\"` and expect `200` with the key set).

Run (confirm the allowlist is host-specific, not "any HTTPS through the proxy"):

```bash
docker compose exec control sh -c "curl -s -o /dev/null -w '%{http_code}\n' -x http://egress-proxy:3128 --max-time 5 https://example.com || echo BLOCKED"
```

Expected: `BLOCKED` — the proxy itself refuses non-`openrouter.ai` SNI, so this must fail exactly like the direct attempt above, not merely because `control` lacks a route.

Run (residual side-channel check, council-risk finding on this plan: Docker Desktop
injects `host.docker.internal` into a container's `/etc/hosts` on some
backends/versions independent of the `internal: true` network flag):

```bash
docker compose exec control sh -c "curl -s -o /dev/null -w '%{http_code}\n' --max-time 3 http://host.docker.internal || echo BLOCKED"
```

Expected: `BLOCKED`. If it instead succeeds, this is not a route to the internet
(`host.docker.internal` only reaches the Windows host's own loopback services) so it
is not an OpenRouter-bypass or exfiltration path — but it is a real residual gap in
"blocked except OpenRouter." Do not silently accept a non-`BLOCKED` result here:
record it as an explicitly declared limitation (mirroring how the design doc
declares the OpenRouter-vs-vLLM fidelity gap) in this task's commit message, rather
than treating the DNS/egress requirement as fully closed.

- [ ] **Step 5: Commit**

```bash
git add docker/egress-proxy/Dockerfile docker/egress-proxy/squid.conf docker-compose.yml .env.example .gitignore
git commit -m "feat: lock down control container egress to openrouter.ai via internal network + Squid sidecar"
```

---

### Task 4: Scan dipendenze immagine (Trivy)

**Files:**
- Create: `docs/design/2026-08-15-container-dependency-scan.md`

**Interfaces:**
- Consumes: the `control` and `egress-proxy` images built in Tasks 2-3.
- Produces: a committed record of the scan command, the image digests scanned, and the result — the audit evidence required before the container is used as a containment boundary.

- [ ] **Step 1: Install Trivy and identify the built image tags**

Run:

```bash
docker compose build
docker compose images
```

Note the exact image tag/ID Compose assigned to `control` and to `egress-proxy` (typically `<project>-control` and `<project>-egress-proxy`, but confirm against your local output rather than assuming).

- [ ] **Step 2: Scan both images**

Run:

```bash
trivy image --severity CRITICAL --exit-code 1 <control-image-tag>
trivy image --severity CRITICAL --exit-code 1 <egress-proxy-image-tag>
```

Expected: both commands exit 0 (no `CRITICAL` findings). If either exits 1, a `CRITICAL` vulnerability exists — this is a genuine result the plan cannot predict in advance. Resolve by bumping the affected package/base image tag in the relevant `Dockerfile` (e.g., pin a newer `python:3.11-slim` digest, or add `apt-get upgrade -y` for OS-level packages) and re-run the scan until both exit 0. Do not suppress or `--ignore-unfixed` a `CRITICAL` past this gate without discussing it explicitly with the user first — the mapping requires zero unresolved `CRITICAL` findings, not zero *reported* ones.

- [ ] **Step 3: Record the evidence**

`docs/design/2026-08-15-container-dependency-scan.md`:

```markdown
# Scan dipendenze del container di controllo (Trivy)

Verifica richiesta dal design doc, sezione "Container di controllo" — audit di
sicurezza preventivo prima di usare il container come confine di contenimento.

## Comando

    trivy image --severity CRITICAL --exit-code 1 <control-image-tag>
    trivy image --severity CRITICAL --exit-code 1 <egress-proxy-image-tag>

## Risultato

- Immagine `control` (digest: `<incolla qui l'image ID/digest effettivo>`): 0
  vulnerabilità CRITICAL, scansionata il <data>.
- Immagine `egress-proxy` (digest: `<incolla qui>`): 0 vulnerabilità CRITICAL,
  scansionata il <data>.

## Note

<eventuali CRITICAL trovate e come sono state risolte, o "nessuna" se lo scan è
passato al primo tentativo.>
```

Fill in the actual digests, dates, and any resolution notes from Step 2 — this file is evidence, not a template; it must reflect what the scan actually produced when you ran it, not be left with the placeholder brackets in it.

**Questo documento è evidenza permanente, non una bozza** (council-advocate, checkpoint
di questo piano): non committarlo con placeholder ancora presenti — un lettore esterno
che verifica la metodologia (principio 6, `SPIRIT.md`) deve trovare digest, date e
comando reali, non un modello da compilare.

- [ ] **Step 4: Commit**

```bash
git add docs/design/2026-08-15-container-dependency-scan.md
git commit -m "docs: record Trivy dependency scan evidence for the control container"
```

---

### Task 5: Review una tantum del codice vendor (rete/filesystem non dichiarati)

**Files:**
- Create: `docs/design/2026-08-15-aidr-vendor-network-fs-review.md`

**Interfaces:**
- Consumes: the pinned vendor clone (`agentic-threat-detection-vendor`, commit `7fad14d2478707e68a09b8ecd9942dec8fde1614`).
- Produces: a committed review document classifying every real network/filesystem/subprocess call in `aidr/` as declared-and-reachable, declared-and-unreachable, or undeclared — the audit evidence required before Task 6 runs the vendor's code against a live `TestCase`.

- [ ] **Step 1: Run the scan**

Run (from the vendor clone directory, e.g. `../agentic-threat-detection-vendor`):

```bash
grep -rn "socket\.\|subprocess\.\|smtplib\|urllib\.request\|requests\.\|httpx\.\|open(" aidr --include="*.py"
```

Expected baseline (found during this plan's structuring, 2026-08-15 — if your output differs, the vendor clone is not at the pinned commit, or the vendor's code changed; stop and investigate before proceeding):

```
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
```

(plus `aidr/serving/model_client.py`, excluded from this grep on purpose — it's the OpenRouter call already accounted for and proxied by Task 1, not a new finding.)

- [ ] **Step 2: Classify each hit**

Verify this classification against `Inspector.__init__` (`aidr/detector/inspector.py`): it calls `discover_providers({"sourcelens", "threatlens", "policylens"})` — the Gauntlet's own tool servers (`aidr/gauntlet/servers/...`, including `host_toolkit.py`'s real `requests.get`) and `aidr/gauntlet/runner.py`'s `subprocess.run` are never imported or invoked from that path. They belong to the vendor's own Gauntlet benchmark tooling, which this project never calls (see Global Constraints).

| File | Call | Classification |
|---|---|---|
| `aidr/config.py`, `aidr/providers/policylens.py`, `aidr/providers/sourcelens.py`, `aidr/providers/threatlens.py` | `open(...)` on local YAML config/registry files | Declared (README: config-driven detection) and reachable from `Pipeline().analyze()` — local file reads only, all paths point inside the vendor repo, no path is attacker-influenced. |
| `aidr/detector/inspector.py:7` | `open(mcp_config_path)` | Declared and reachable — reads the MCP server launch config `Inspector.__init__` itself writes via `write_mcp_config`. |
| `aidr/providers/mcp_client.py:8-9` | `subprocess.Popen(launch_cmd, ...)` | Declared (README: "Inspector... calling context providers over MCP") and reachable — this is how SourceLens/ThreatLens/PolicyLens are actually launched. No network I/O of its own; the subprocess's own network calls are covered by the other rows in this table. |
| `aidr/crucible/evolve.py:102,111` | `open(repo_path)` / `yaml.safe_dump(..., open(repo_path, "w"))` | Declared (README: "Crucible... evolutionary red team") but **not reachable** from `Pipeline().analyze()`/`Inspector.analyze()` — Crucible is an offline tool we never invoke. |
| `aidr/gauntlet/pack.py:20`, `aidr/gauntlet/runner.py:30`, `aidr/gauntlet/servers/host_toolkit/host_toolkit.py:9-10` | `open(...)`, `subprocess.run(...)`, real `requests.get(...)` | Part of the vendor's own Gauntlet benchmark harness — **not reachable** from the code path this project calls (see Global Constraints: we never import `aidr.gauntlet.runner` or the Gauntlet's own tool servers). `host_toolkit.py`'s real outbound HTTP call is the one finding in this scan that would matter if it were reachable; it is not, on the path we use. |

- [ ] **Step 3: Write the review document**

`docs/design/2026-08-15-aidr-vendor-network-fs-review.md`:

```markdown
# Review una tantum del codice vendor — chiamate di rete/filesystem non dichiarate

Verifica richiesta dal design doc, sezione "Container di controllo" — completata
prima di eseguire il primo caso reale (Task 6 di questo piano). Vendor:
`agentic-threat-detection-vendor`, commit pinnato `7fad14d2478707e68a09b8ecd9942dec8fde1614`.

## Scansione

    grep -rn "socket\.\|subprocess\.\|smtplib\|urllib\.request\|requests\.\|httpx\.\|open(" aidr --include="*.py"

[Incolla qui l'output effettivo ottenuto rieseguendo la scansione — deve
corrispondere al baseline dell'omonimo Step 1 di Task 5, salvo il commit pinnato
sia cambiato.]

## Classificazione

[Copia qui la tabella dello Step 2 sopra, confermata contro il codice effettivo.]

## Esito

Nessuna chiamata di rete/filesystem non dichiarata e raggiungibile dal percorso
`Pipeline().analyze()` / `Inspector.analyze()` che questo progetto usa. L'unica
chiamata di rete reale nell'intero pacchetto (`host_toolkit.py`,
`requests.get`) appartiene al Gauntlet del vendor, mai importato né invocato dal
nostro codice (vincolo esplicito in questo piano, sezione "Global Constraints").
```

**Questo documento è evidenza permanente, non una bozza** (council-advocate, checkpoint
di questo piano): non committarlo con `[Incolla qui...]` ancora presente — deve
riportare l'output reale della scansione rieseguita, non solo la tabella già scritta in
questo piano.

- [ ] **Step 4: Commit**

```bash
git add docs/design/2026-08-15-aidr-vendor-network-fs-review.md
git commit -m "docs: one-time review of aidr vendor code for undeclared network/filesystem calls"
```

---

### Task 6: Verifica empirica Gap 4 — SourceLens scatta davvero per `toy_support`

**Files:**
- Create: `docker/control/verify_sourcelens.py`
- Modify: `docs/design/2026-08-14-toy-agent-gap-tracking.md` (Gap 4 — chiudere con l'esito)

**Interfaces:**
- Consumes: the full stack from Tasks 1-3 (`control` + `egress-proxy` running, `vendor_proxy` reachable, `toy_support` registered in SourceLens), a real `OPENROUTER_API_KEY`.
- Produces: a one-shot, manually-run script (not part of the pytest suite — it makes a real, billed OpenRouter call) that proves Inspector calls `get_source_code(["toy_support"])` and that the content returned matches the registered file.

- [ ] **Step 1: Write the verification script**

`docker/control/verify_sourcelens.py`:

```python
"""
Empirical verification of Gap 4 (gap-tracking doc): does Inspector actually call
SourceLens's get_source_code("toy_support") when analyzing a transcript that uses
the toy agent's tools, and does the code it gets back match what's registered?

Run once, inside the control container, against a live OpenRouter-backed Inspector
(costs real money — this is why it is a standalone script, not a pytest test).
Intentionally imports aidr directly: this script runs only inside the control
container, never as part of the toy_agent package (which must never import aidr —
see tests/test_no_vendor_imports.py, Plan 1).

Observation point (council-skeptic finding on this plan, verified against the
pinned vendor clone before writing this version): SourceLens itself runs as a
*separate subprocess* (aidr/providers/sourcelens.py, launched by MCPClient via
subprocess.Popen, talked to over JSON-RPC/stdio — aidr/providers/mcp_client.py).
Patching `sourcelens.get_source_code` in this script's own process would never
see Inspector's real calls, which happen in a different interpreter entirely.
`MCPClient.call` (aidr/providers/mcp_client.py), by contrast, runs in *this*
process — it's what Inspector's MCPRouter.dispatch() calls directly — so it's
the correct interception point.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aidr.detector.inspector import Inspector
from aidr.providers.mcp_client import MCPClient

TOY_SUPPORT_PATH = Path("aidr/gauntlet/servers/toy_support/toy_support.py")

# A minimal transcript exercising update_account on a sensitive field (T0007
# tool-poisoning trigger, design doc "Set di tool") — enough for Inspector's
# workflow to have a reason to inspect toy_support's source.
_PROBE_TRANSCRIPT = (
    "USER: Please disable my account and refund my last order.\n"
    "TOOL CALL call_1: toy_support.update_account({'customer_id': 'cust_001', "
    "'field': 'status', 'value': 'disabled'})\n"
    "TOOL RESULT call_1: account cust_001 field 'status' updated\n"
)


def main() -> None:
    calls: list[tuple[str, dict, str]] = []
    original_call = MCPClient.call

    def spying_call(self, tool: str, arguments: dict) -> str:
        result = original_call(self, tool, arguments)
        calls.append((tool, arguments, result))
        return result

    MCPClient.call = spying_call
    try:
        inspector = Inspector()
        verdict = inspector.analyze(_PROBE_TRANSCRIPT, tactic="T0007")
    finally:
        MCPClient.call = original_call

    source_calls = [c for c in calls if c[0] == "get_source_code"]
    if not source_calls:
        print("FAIL: Inspector never called get_source_code")
        print(f"all MCP calls observed: {[(t, a) for t, a, _ in calls]}")
        raise SystemExit(1)

    # MCPClient.call returns the joined text content of the MCP tool result.
    # get_source_code's real return shape (aidr/providers/sourcelens.py, read
    # directly off the pinned vendor clone, not assumed):
    #   {"source_codes": [{"server_name": ..., "status": "found"|"not_found",
    #                       "metadata": {...}, "source_code": "..."}], ...}
    matching = None
    for tool, arguments, result in source_calls:
        payload = json.loads(result)
        for entry in payload["source_codes"]:
            if entry["server_name"] == "toy_support":
                matching = entry
        if matching is not None:
            break

    if matching is None or matching.get("status") != "found":
        print(f"FAIL: get_source_code was called {len(source_calls)} time(s), "
              f"but never returned a 'found' entry for toy_support")
        print(f"calls: {[(t, a) for t, a, _ in source_calls]}")
        raise SystemExit(1)

    expected_hash = hashlib.sha256(TOY_SUPPORT_PATH.read_bytes()).hexdigest()
    returned_hash = hashlib.sha256(matching["source_code"].encode()).hexdigest()

    print(f"PASS: get_source_code called {len(source_calls)} time(s), including toy_support")
    print(f"registered file hash:  {expected_hash}")
    print(f"returned content hash: {returned_hash}")
    print(f"hashes match: {expected_hash == returned_hash}")
    print(f"Inspector verdict: {verdict}")

    if expected_hash != returned_hash:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it inside the container and persist the raw output**

Run:

```bash
docker compose cp docker/control/verify_sourcelens.py control:/opt/aidr-vendor/verify_sourcelens.py
docker compose exec -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" control python verify_sourcelens.py | tee docs/design/2026-08-15-gap4-verification-output.txt
```

`tee` runs on the host (the shell invoking `docker compose exec`), so the file lands directly in the repo at `docs/design/2026-08-15-gap4-verification-output.txt` — the raw evidence (hashes, verdict, call count) is committed alongside the analysis, not left to evaporate in a terminal scrollback (principio 4/6, `SPIRIT.md`: risultati grezzi pubblicati insieme all'analisi).

Expected: `PASS: get_source_code called N time(s), including toy_support`, `hashes match: True`, exit code 0.

If it prints `FAIL`, this is a real result, not a bug in the plan — it means Gap 4's syntactic fix (the `toy_support.` dotted prefix) is not actually firing for this probe transcript, or that Inspector's actual workflow differs from what the design doc describes. Stop and investigate against `aidr/detector/inspector.py`'s `build_workflow()` rather than adjusting the script to force a PASS.

- [ ] **Step 3: Record the outcome in the gap-tracking doc**

In `docs/design/2026-08-14-toy-agent-gap-tracking.md`, Gap 4, replace the "Ancora aperto" paragraph with the actual outcome (date run, verdict, a pointer to `docs/design/2026-08-15-gap4-verification-output.txt` for the raw hashes), and change Gap 4's status line to reflect that the empirical half is now closed, not just the syntactic half.

- [ ] **Step 4: Commit**

```bash
git add docker/control/verify_sourcelens.py docs/design/2026-08-15-gap4-verification-output.txt docs/design/2026-08-14-toy-agent-gap-tracking.md
git commit -m "test: empirically verify Inspector's SourceLens channel fires for toy_support (Gap 4)"
```

---

## Self-Review Notes

- **Spec coverage**: every Plan-3-scoped row of the design doc's Requisito→Verifica mapping has a corresponding task — Trivy scan (Task 4), active DNS/egress test (Task 3, Step 4), vendor code review (Task 5), byte-identical SourceLens source (Task 2, Step 4), Gap 4 empirical verification (Task 6). Rows about the adapter's `tool_name` prefix, `TestCase` isolation, and the orchestrator belong to Plan 4, not this plan.
- **Type consistency**: `Forwarder = Callable[[int, dict], dict]` (Task 1) is used identically in `serve_forever`'s signature and in every test. `TIER_TO_MODEL`/`PORT_TO_PATH` keys match exactly what Task 2's Dockerfile and Task 6's probe assume (ports 8100/8101/8102, tiers `sifter`/`inspector`/`embed`).
- **Placeholder scan**: Task 4 and Task 5's output templates contain bracketed fill-in text (`[Incolla qui...]`, `<data>`) by design — they are evidence documents whose content depends on a real command's output at execution time, not predictable at plan-writing time. Every other step has concrete, complete content.
- **Gap 8 decisions applied**: Trivy over `pip-audit` (Task 4), internal network + dual-homed Squid sidecar over in-container iptables (Task 3), OpenRouter-proxied embeddings over local self-hosting or disabling ThreatLens (Task 1, `PORT_TO_PATH[8102]`), `COPY`/`git clone` at build over runtime mounts (Task 2) — all four traced to the gap-tracking doc entry added during this plan's structuring.

## Esito council checkpoint (2026-08-15)

Eseguito su questo file (draft, non ancora committato) + design doc + gap-tracking doc
completi, roster pieno (`council-skeptic`, `council-risk`, `council-pragmatist`,
`council-advocate`), ognuno col documento intero come contesto. Tutti e quattro:
`agree with reservations`.

- `council-skeptic`: ha trovato, verificandolo riga per riga contro il codice vendor
  pinnato (`aidr/providers/sourcelens.py`, `aidr/providers/mcp_client.py`), un difetto
  strutturale in Task 6 — lo script originale monkeypatchava
  `sourcelens.get_source_code` nel processo dello script stesso, ma SourceLens gira
  come sottoprocesso separato (MCP su stdio): lo script avrebbe sempre stampato `FAIL`
  indipendentemente dal comportamento reale di Inspector, dopo aver speso una chiamata
  reale a pagamento su OpenRouter. Trovata anche la forma di ritorno reale sbagliata
  (`source_codes`, lista di dict con chiave `source_code`, non un dizionario `{name:
  {source: ...}}`). **Applicato**: Task 6 riscritto per spiare `MCPClient.call`
  (corretto perché gira nello stesso processo dell'Inspector) e per leggere la forma di
  ritorno reale, verificata di persona leggendo il codice vendor prima di applicare la
  correzione, non fidandosi ciecamente della patch suggerita dall'agente.
- `council-risk`: ha trovato che `entrypoint.sh` avvia `vendor_proxy` in background con
  `&` senza mai verificare che sia rimasto vivo prima di `exec "$@"` — un crash
  all'avvio (es. `OPENROUTER_API_KEY` mancante) lascerebbe il container "Up" con un
  proxy morto, un fallimento silenzioso che emergerebbe solo più avanti, nel punto più
  costoso del piano (Task 6). **Applicato**: `entrypoint.sh` ora verifica che il
  processo sia vivo e che le tre porte siano effettivamente in ascolto prima di
  proseguire, uscendo con un messaggio esplicito altrimenti. Ha anche trovato
  `tty`/`stdin_open` come superficie non necessaria nel `docker-compose.yml`
  (**applicato**: rimossi) e un side-channel residuo non testato (`host.docker.internal`,
  iniettato da Docker Desktop indipendentemente da `internal: true` — **applicato**:
  aggiunto un test esplicito in Task 3, con istruzione di dichiararlo come limite se non
  bloccato, non di ignorarlo).
- `council-pragmatist`: ha segnalato che l'architettura a due container è difesa in
  profondità rispetto a un rischio che Task 5 (review del codice vendor) dovrebbe
  dimostrare non esistere sul percorso usato — una dipendenza logica tra i due task non
  dichiarata esplicitamente nel piano originale. Non ha proposto di rimuovere il
  meccanismo (già deciso con l'utente in Gap 8, e la stessa tensione era già stata
  valutata e decisa dal council originale sul design doc). **Applicato**: aggiunta una
  nota esplicita in apertura di Task 3 che traccia questa dipendenza e rimanda alla
  decisione già presa, invece di lasciarla implicita.
- `council-advocate`: ha trovato che Task 4/5 rischiano di restare documenti-scheletro
  con i placeholder non riempiti, e che l'output grezzo di Task 6 (hash, verdetto, costo)
  non veniva persistito da nessuna parte — solo riassunto nel gap-tracking doc, in
  contrasto col principio 4/6 di `SPIRIT.md` (risultati grezzi pubblicati insieme
  all'analisi). **Applicato**: nota esplicita "evidenza permanente, non una bozza" in
  Task 4/5; Task 6 ora salva l'output completo dello script in un file committato
  (`docs/design/2026-08-15-gap4-verification-output.txt`) invece di lasciarlo solo nel
  terminale.

**Esito mapping Requisito→Verifica** (per la traccia richiesta dall'estensione locale di
brainstorming): 2 righe di verifica proposte prima del council sono state contestate e
riviste (Task 6's meccanismo di osservazione, Task 6's forma di ritorno) — non semplici
aggiunte come nel checkpoint originale su Plan 1, ma correzioni di un difetto reale che
sarebbe stato scoperto solo eseguendo il piano e spendendo una chiamata reale a
pagamento. Segnale che il checkpoint ha pagato il proprio costo su questo piano in modo
particolarmente concreto.
