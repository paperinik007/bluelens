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
