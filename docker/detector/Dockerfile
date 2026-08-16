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

# pytest, pre-installed at build time (Task 6 fix): docker/detector/run_adapter_tests.sh
# runs pytest inside this container at exec time, but detector_net is internal-only
# and the egress-proxy allowlists just openrouter.ai (Gap 8) — a runtime
# `pip install pytest` can never reach pypi.org there. Build time uses the
# host's unrestricted network instead, so installing it here is the only way
# run_adapter_tests.sh's committed pip-install step actually succeeds.
RUN pip install --no-cache-dir pytest

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
