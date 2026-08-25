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
COST_SOURCE = "OpenRouter response usage.cost"
_GIT_TIMEOUT_S = 10.0


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


def collect_provenance(env: Mapping[str, str], repo_root: Path = Path(".")) -> dict:
    head = _git_output(["rev-parse", "HEAD"], repo_root)
    dirty = _git_output(["status", "--porcelain"], repo_root)
    return {
        "measurer_commit": head,
        "measurer_dirty": None if dirty is None else bool(dirty),
        "vendor_commit": vendor_commit(repo_root),
        "agent_model": env.get("AGENT_MODEL") or _DEFAULT_MODEL,
        "sifter_model": env.get("SIFTER_MODEL") or "(default in detector_adapter)",
        "inspector_model": env.get("INSPECTOR_MODEL") or "(default in detector_adapter)",
        "embed_model": env.get("EMBED_MODEL") or "(default in detector_adapter)",
        "cost_source": COST_SOURCE,
        "agent_max_tokens": MAX_TOKENS,
        "agent_request_timeout_s": REQUEST_TIMEOUT_S,
        "agent_max_retries_per_case": MAX_RETRIES_PER_CASE,
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
        f"measurer_commit={commit}{dirty_note}",
        f"vendor_commit={prov.get('vendor_commit') or 'unknown'}",
        f"agent_model={prov.get('agent_model')}",
        f"sifter_model={prov.get('sifter_model')}",
        f"inspector_model={prov.get('inspector_model')}",
        f"embed_model={prov.get('embed_model')}",
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