FROM python:3.11-slim

# curl: needed for the egress/network verification checks in Task 4 (same
# reasoning as docker/control/Dockerfile in Plan 3 — python:3.11-slim ships
# neither curl nor wget).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /opt/toy_agent/pyproject.toml
COPY src/toy_agent /opt/toy_agent/src/toy_agent
WORKDIR /opt/toy_agent
RUN pip install --no-cache-dir -e .

# Same compensating control as docker/detector/Dockerfile (Task 3) and the
# retired docker/control/Dockerfile before it: perl-base ships in every
# python:3.11-slim image unconditionally (docs/design/2026-08-15-container-
# dependency-scan.md — 4 CRITICAL CVEs, no upstream fix). This image's own
# code never invokes perl on any path; stripping the execute bit closes that
# path without touching anything this image's build actually needs.
RUN chmod a-x /usr/bin/perl /usr/bin/perl5.40.1

COPY docker/agent/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
