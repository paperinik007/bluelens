from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

import httpx

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
PROXY_PORT = 8200
CHAT_PATH = "/chat/completions"

Forwarder = Callable[[dict], dict]


def _scrub(text: str, secret: str) -> str:
    if not secret:
        return text
    return text.replace(secret, "[REDACTED]")


def _append_log(log_path: Path, entry: dict, api_key: str) -> None:
    scrubbed = _scrub(json.dumps(entry), api_key)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(scrubbed + "\n")


def build_forwarder(
    api_key: str,
    proxy_url: str | None = None,
    transport: httpx.BaseTransport | None = None,
    log_path: Path | None = None,
) -> Forwarder:
    """Build a Forwarder that POSTs the request body verbatim to OpenRouter's
    chat completions endpoint — no tier remap (unlike aidr's
    vendor_proxy.py): LLMClient already sends a real OpenRouter model id."""
    client = httpx.Client(
        base_url=OPENROUTER_BASE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        proxy=proxy_url,
        timeout=120.0,
        transport=transport,
    )

    def forward(body: dict) -> dict:
        try:
            response = client.post(CHAT_PATH, json=body)
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            if log_path is not None:
                _append_log(log_path, {"request": body, "error": str(exc)}, api_key)
            raise
        if log_path is not None:
            _append_log(log_path, {"request": body, "response": result}, api_key)
        return result

    return forward


class _ForwardingHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], handler_cls: type, forward: Forwarder) -> None:
        super().__init__(address, handler_cls)
        self.forward = forward


class _ProxyHandler(BaseHTTPRequestHandler):
    server: _ForwardingHTTPServer

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            result = self.server.forward(body)
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

    def log_message(self, format: str, *args) -> None:
        pass


def serve_forever(port: int, forward: Forwarder) -> _ForwardingHTTPServer:
    """Start one listener on `port`, bound to 127.0.0.1 (matching
    OpenRouterAlignmentCheck.API_BASE_URL, Task 4)."""
    server = _ForwardingHTTPServer(("127.0.0.1", port), _ProxyHandler, forward)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    api_key = os.environ["LLAMAFIREWALL_OPENROUTER_API_KEY"]
    proxy_url = os.environ.get("HTTPS_PROXY")
    log_path_str = os.environ.get("LLAMAFIREWALL_PROXY_LOG_PATH")
    log_path = Path(log_path_str) if log_path_str else None
    forward = build_forwarder(api_key, proxy_url, log_path=log_path)
    serve_forever(PROXY_PORT, forward)
    threading.Event().wait()  # keep the process alive; server runs on a daemon thread


if __name__ == "__main__":
    main()
