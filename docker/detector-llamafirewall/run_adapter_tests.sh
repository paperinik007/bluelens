#!/bin/sh
# docker/detector-llamafirewall/run_adapter_tests.sh
# One-time/occasional developer convenience: run the llamafirewall-gated
# adapter tests for real, inside a running `detector-llamafirewall`
# container. Not part of the image build, not invoked by any Dockerfile or
# CI — same convention as docker/detector/run_adapter_tests.sh (aidr). Run
# from the repo root, with the stack up
# (`docker compose up -d detector-llamafirewall`):
#
#     sh docker/detector-llamafirewall/run_adapter_tests.sh
#
# Copies only the llamafirewall-specific test files, not the whole
# tests/detector_adapter/ directory — the aidr tests in that directory are
# not importable here (vendors/aidr/ is never copied into this container,
# Task 8's selective COPY) and would fail collection if copied wholesale.
set -e
docker compose exec -T detector-llamafirewall mkdir -p /opt/detector_adapter/tests
for f in test_llamafirewall_adapter_normalization.py \
         test_llamafirewall_adapter_serialization.py \
         test_llamafirewall_adapter_construction.py \
         test_llamafirewall_adapter_failopen.py \
         test_llamafirewall_openrouter_proxy.py; do
    docker compose cp "tests/detector_adapter/$f" "detector-llamafirewall:/opt/detector_adapter/tests/$f"
done
docker compose exec -T detector-llamafirewall pip install --no-cache-dir pytest
docker compose exec -T detector-llamafirewall python -m pytest /opt/detector_adapter/tests -v
