#!/bin/sh
# docker/detector-llamafirewall/entrypoint.sh
set -e
python -m detector_adapter.vendors.llamafirewall.openrouter_proxy &
proxy_pid=$!

ready=0
for attempt in $(seq 1 20); do
    if ! kill -0 "$proxy_pid" 2>/dev/null; then
        echo "openrouter_proxy exited before binding port 8200 — check LLAMAFIREWALL_OPENROUTER_API_KEY" >&2
        exit 1
    fi
    if python -c "import socket,sys; s=socket.socket(); s.settimeout(0.2); sys.exit(0 if s.connect_ex(('127.0.0.1', 8200))==0 else 1)"; then
        ready=1
        break
    fi
    sleep 0.2
done
if [ "$ready" -ne 1 ]; then
    echo "openrouter_proxy never bound port 8200 within 4s" >&2
    exit 1
fi

exec "$@"
