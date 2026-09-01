# syntax=docker/dockerfile:1
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

RUN pip install --no-cache-dir --no-deps llamafirewall==1.0.3
RUN pip install --no-cache-dir torch transformers 'huggingface_hub>=0.30.2,<1.0.0'
ENV HF_HOME=/opt/hf-cache
ENV HF_HUB_DISABLE_XET=1
RUN --mount=type=secret,id=hf_token \
    HF_TOKEN=$(cat /run/secrets/hf_token) python -c \
    "from llamafirewall.scanners.promptguard_utils import PromptGuard; PromptGuard()"
RUN pip install --no-cache-dir 'openai>=1.76.0' 'pydantic>=2.11.3'

COPY docker/detector-llamafirewall/detector_adapter.pyproject.toml /opt/detector_adapter/pyproject.toml
COPY src/detector_adapter/__init__.py /opt/detector_adapter/src/detector_adapter/__init__.py
COPY src/detector_adapter/vendors/__init__.py /opt/detector_adapter/src/detector_adapter/vendors/__init__.py
COPY src/detector_adapter/vendors/llamafirewall /opt/detector_adapter/src/detector_adapter/vendors/llamafirewall
WORKDIR /opt/detector_adapter
RUN pip install --no-cache-dir -e .

RUN pip install --no-cache-dir pytest

COPY docker/detector-llamafirewall/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

RUN chmod a-x /usr/bin/perl /usr/bin/perl5.40.1

WORKDIR /opt
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
