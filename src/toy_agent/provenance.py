from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Mapping, Optional

from .model_client import _DEFAULT_MODEL, MAX_RETRIES_PER_CASE, MAX_TOKENS, REQUEST_TIMEOUT_S

PROVENANCE_FILENAME = "provenance.json"
VENDOR_PIN_PATH = Path("docker") / "detector" / "Dockerfile"
_VENDOR_PIN_RE = re.compile(r"git checkout ([0-9a-f]{7,40})")
LLAMAFIREWALL_PIN_PATH = Path("docker") / "detector-llamafirewall" / "Dockerfile"
_LLAMAFIREWALL_PIN_RE = re.compile(r"llamafirewall==([0-9][0-9A-Za-z.\-]*)")
COST_SOURCE = "OpenRouter response usage.cost"
_GIT_TIMEOUT_S = 10.0

# I3 (final review): collect_provenance() used to populate every field
# regardless of which vendor actually ran, so a llamafirewall run's
# provenance.json showed aidr's pinned commit and aidr's tier models as if
# they had been used for that run — actively misleading provenance on the
# document whose transparency this project cares most about (SPIRIT.md
# principle 6). This marker replaces a vendor-inapplicable field's value
# instead of leaving it populated with the OTHER vendor's data — distinct
# from None/"unknown", which already means "we tried to read this and
# couldn't", not "this field describes a different vendor than the one that
# ran".
NOT_APPLICABLE_FOR_VENDOR = "n/a (not applicable for this vendor)"


def _git_output(args: list[str], repo_root: Path) -> Optional[str]:
    try:
        proc = subprocess.run(["git", *args], cwd=str(repo_root), capture_output=True, timeout=_GIT_TIMEOUT_S)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace").strip()


def vendor_commit(repo_root: Path = Path(".")) -> Optional[str]:
    try:
        text = (repo_root / VENDOR_PIN_PATH).read_text(encoding="utf-8")
    except OSError:
        return None
    matches = _VENDOR_PIN_RE.findall(text)
    return matches[0] if len(matches) == 1 else None


def llamafirewall_pip_version(repo_root: Path = Path(".")) -> Optional[str]:
    """Mirrors vendor_commit() — a pip VERSION pin (Task 8), not a git
    commit: llamafirewall is consumed via pip, not vendored via git
    checkout like aidr."""
    try:
        text = (repo_root / LLAMAFIREWALL_PIN_PATH).read_text(encoding="utf-8")
    except OSError:
        return None
    matches = _LLAMAFIREWALL_PIN_RE.findall(text)
    return matches[0] if len(matches) == 1 else None


def collect_provenance(env: Mapping[str, str], vendor: str, repo_root: Path = Path(".")) -> dict:
    head = _git_output(["rev-parse", "HEAD"], repo_root)
    dirty = _git_output(["status", "--porcelain"], repo_root)

    # aidr-specific fields (git-pinned vendor, per-tier LLM models) and
    # llamafirewall-specific fields (pip-pinned vendor, single model) are
    # each populated only when that vendor is the one that actually ran —
    # the other vendor's fields get the explicit NOT_APPLICABLE_FOR_VENDOR
    # marker instead of silently carrying over stale data from a vendor
    # this run never invoked. An unrecognized vendor string gets None for
    # both (falls back to format_provenance's existing "unknown" wording;
    # this function has no registry of vendor names to validate against
    # without importing orchestrator.py, which regenerate_report.py/
    # run_batch.py already do at the call site).
    if vendor == "aidr":
        vendor_commit_value = vendor_commit(repo_root)
        vendor_pip_version_value = NOT_APPLICABLE_FOR_VENDOR
        sifter_model_value = env.get("SIFTER_MODEL") or "(default in detector_adapter)"
        inspector_model_value = env.get("INSPECTOR_MODEL") or "(default in detector_adapter)"
        embed_model_value = env.get("EMBED_MODEL") or "(default in detector_adapter)"
        llamafirewall_model_value = NOT_APPLICABLE_FOR_VENDOR
    elif vendor == "llamafirewall":
        vendor_commit_value = NOT_APPLICABLE_FOR_VENDOR
        vendor_pip_version_value = llamafirewall_pip_version(repo_root)
        sifter_model_value = NOT_APPLICABLE_FOR_VENDOR
        inspector_model_value = NOT_APPLICABLE_FOR_VENDOR
        embed_model_value = NOT_APPLICABLE_FOR_VENDOR
        llamafirewall_model_value = env.get("LLAMAFIREWALL_MODEL") or "(default in detector_adapter)"
    else:
        vendor_commit_value = None
        vendor_pip_version_value = None
        sifter_model_value = None
        inspector_model_value = None
        embed_model_value = None
        llamafirewall_model_value = None

    return {
        "vendor": vendor,
        "measurer_commit": head,
        "measurer_dirty": None if dirty is None else bool(dirty),
        "vendor_commit": vendor_commit_value,
        "vendor_pip_version": vendor_pip_version_value,
        "agent_model": env.get("AGENT_MODEL") or _DEFAULT_MODEL,
        "sifter_model": sifter_model_value,
        "inspector_model": inspector_model_value,
        "embed_model": embed_model_value,
        "llamafirewall_model": llamafirewall_model_value,
        "cost_source": COST_SOURCE,
        "agent_max_tokens": MAX_TOKENS,
        "agent_request_timeout_s": REQUEST_TIMEOUT_S,
        "agent_max_retries_per_case": MAX_RETRIES_PER_CASE,
        "run_id": None,
    }


def format_provenance(prov: Optional[dict]) -> str:
    if prov is None:
        return (
            "experimental conditions: not recorded (this run predates provenance capture; "
            "they are NOT reconstructed here, because guessing them is the defect this "
            "declaration exists to prevent)"
        )
    commit = prov.get("measurer_commit") or "unknown (no git repository at the run's working directory)"
    dirty = prov.get("measurer_dirty")
    dirty_note = "" if dirty is None else (" (working tree dirty)" if dirty else " (clean)")
    return " | ".join([
        f"vendor={prov.get('vendor') or 'unknown'}",
        f"measurer_commit={commit}{dirty_note}",
        f"vendor_commit={prov.get('vendor_commit') or 'unknown'}",
        f"vendor_pip_version={prov.get('vendor_pip_version') or 'unknown'}",
        f"agent_model={prov.get('agent_model')}",
        f"sifter_model={prov.get('sifter_model')}",
        f"inspector_model={prov.get('inspector_model')}",
        f"embed_model={prov.get('embed_model')}",
        f"llamafirewall_model={prov.get('llamafirewall_model')}",
        f"cost_source={prov.get('cost_source')}",
        f"agent_max_tokens={prov.get('agent_max_tokens')}",
        f"agent_request_timeout_s={prov.get('agent_request_timeout_s')}",
        f"agent_max_retries_per_case={prov.get('agent_max_retries_per_case')}",
    ])


def write_provenance(prov: dict, run_output_dir: Path) -> None:
    run_output_dir.mkdir(parents=True, exist_ok=True)
    (run_output_dir / PROVENANCE_FILENAME).write_text(json.dumps(prov, indent=2, sort_keys=True), encoding="utf-8")


def read_provenance(run_output_dir: Path) -> Optional[dict]:
    path = run_output_dir / PROVENANCE_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None