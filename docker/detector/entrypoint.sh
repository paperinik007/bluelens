#!/bin/sh
set -e
python -m detector_adapter.vendors.aidr.vendor_proxy &
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
