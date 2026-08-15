# ---- Stage "vendor-source": clone the pinned vendor repo. -----------------
# git is only needed here, at build time, to fetch one pinned commit — never
# at runtime. Debian's `git` package depends on `perl`, which pulls in
# `perl-modules-5.40` and `libperl5.40` (Task 4 / Trivy finding: 4 CRITICAL
# CVEs on those packages, none with a Debian fix yet — see
# docs/design/2026-08-15-container-dependency-scan.md). Isolating git to a
# throwaway build stage keeps those 3 packages out of the final image
# entirely (`perl-base` itself still ships in bare python:3.11-slim
# regardless of anything here, so it isn't affected by this split — see the
# scan doc for why that residual is accepted).
FROM python:3.11-slim AS vendor-source

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Vendor code, pinned for reproducibility (SPIRIT.md principio 4) — cloned at
# build time, never bind-mounted from the host (Gap 8).
WORKDIR /opt
RUN git clone https://github.com/FareedKhan-dev/agentic-threat-detection.git aidr-vendor \
    && cd aidr-vendor \
    && git checkout 7fad14d2478707e68a09b8ecd9942dec8fde1614

# ---- Final stage: runtime image. No git/perl/libperl5.40/perl-modules-5.40
# installed here — only what's copied from vendor-source above. ------------
FROM python:3.11-slim

# curl (deviation from Task 2, discovered in Task 3 Step 4 verification): Task 3's
# egress-lockdown checks run curl-based probes inside this container to prove DNS
# resolution and direct connects fail while only the openrouter.ai path through
# egress-proxy succeeds. python:3.11-slim ships neither curl nor wget, so without
# this, every curl-based check reports "BLOCKED" merely from command-not-found
# (exit 127), not from an actual network block — meaningless as evidence either way.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
COPY --from=vendor-source /opt/aidr-vendor /opt/aidr-vendor

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

# Defense-in-depth compensating control for the 4 residual perl-base CRITICAL
# CVEs that can't be removed from the image (Task 4 /
# docs/design/2026-08-15-container-dependency-scan.md): perl-base ships in
# every python:3.11-slim image regardless of anything above, and Debian has
# not shipped a fix for these 4 CVEs as of 2026-08-15. All 4 require
# attacker-controlled input actually being *executed* by perl (a crafted
# regex, a crafted Storable payload, or a crafted tar with symlinks) — this
# image's own code (entrypoint.sh, toy_agent, aidr) never invokes perl on any
# path, verified by grep. Stripping the execute bit on the interpreter
# closes that path entirely; it's applied last, after every apt/pip step
# that could need perl-driven maintainer scripts has already run, so it
# cannot break this image's own build. Trivy still reports the 4 CVEs (it
# scans dpkg package metadata, not file permissions) — that's expected and
# documented, not a bug in this line.
RUN chmod a-x /usr/bin/perl /usr/bin/perl5.40.1

# aidr's providers (sourcelens.py, threatlens.py, policylens.py) read relative
# paths from the vendor repo root (Gap 3) — cwd must be there for every command.
WORKDIR /opt/aidr-vendor
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
