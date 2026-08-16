from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

import httpx

# aidr/serving/model_client.py (vendor, pinned commit 7fad14d2478707e68a09b8ecd9942dec8fde1614)
# sends `model` as the literal tier name ("sifter"/"inspector"/"embed"), not a real
# OpenRouter model id (design doc, "Setup pratico del detector sotto test").
TIER_TO_MODEL: dict[str, str] = {
    "sifter": "qwen/qwen3-4b-instruct-2507",
    "inspector": "qwen/qwen3-30b-a3b-instruct-2507",
    "embed": "qwen/qwen3-embedding-4b",
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


class _ForwardingHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], handler_cls: type, forward: Forwarder) -> None:
        super().__init__(address, handler_cls)
        self.forward = forward


class _ProxyHandler(BaseHTTPRequestHandler):
    server: _ForwardingHTTPServer  # narrows the type for self.server.forward below

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
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
    log_path_str = os.environ.get("VENDOR_PROXY_LOG_PATH")
    log_path = Path(log_path_str) if log_path_str else None
    forward = build_forwarder(api_key, proxy_url, log_path=log_path)
    serve_forever(list(PORT_TO_PATH), forward)
    threading.Event().wait()  # keep the process alive; servers run on daemon threads


if __name__ == "__main__":
    main()
