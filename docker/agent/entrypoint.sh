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
