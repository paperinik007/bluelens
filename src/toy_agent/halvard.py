from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable

# The integration server lives next to the dataset, not in src: aidr reads it by server name, and the
# four versions are data of the run (docs/design/2026-10-14-tabella-permessi-bozza.md).
SERVER_DIR = Path(__file__).resolve().parents[2] / "dataset_v3" / "servers" / "halvard_crm"

THIRD_PARTY_VERSIONS = ("honest", "compromised_data", "compromised_permissions", "compromised_persistence")


def load_crm_sync(version: str) -> Callable[..., str]:
    """The `crm_sync_contact` function of one version of the Halvard CRM server."""
    if version not in THIRD_PARTY_VERSIONS:
        raise ValueError(f"unknown third-party version: {version!r}, expected one of {list(THIRD_PARTY_VERSIONS)}")
    path = SERVER_DIR / f"{version}.py"
    spec = importlib.util.spec_from_file_location(f"halvard_crm_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.crm_sync_contact
