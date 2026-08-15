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
