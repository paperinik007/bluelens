#!/bin/sh
# One-time/occasional developer convenience: run the aidr-gated adapter tests
# (tests/detector_adapter/test_adapter_agent_event.py) plus the rest of the
# detector_adapter test suite — including test_evaluate_case.py's
# SIGALRM-based internal-deadline test, which only runs for real on Linux —
# for real, inside a running `detector` container. Not part of the image
# build, not invoked by any Dockerfile or CI — a committed script instead of
# a manual sequence described only in a plan document (council-advocate
# finding, Gap 9 targeted council: a step that lives only as prose is easy
# for a third-party reviewer to miss or fail to reproduce). Run from the repo
# root, with the stack up (`docker compose up -d detector`):
#
#     sh docker/detector/run_adapter_tests.sh
set -e
docker compose cp tests/detector_adapter detector:/opt/detector_adapter/tests
docker compose exec -T detector pip install --no-cache-dir pytest
docker compose exec -T detector python -m pytest /opt/detector_adapter/tests -v
