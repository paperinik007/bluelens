import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "toy_agent"
DETECTOR_ADAPTER_ROOT = Path(__file__).resolve().parent.parent / "src" / "detector_adapter"
AIDR_VENDOR_ROOT = DETECTOR_ADAPTER_ROOT / "vendors" / "aidr"
LLAMAFIREWALL_VENDOR_ROOT = DETECTOR_ADAPTER_ROOT / "vendors" / "llamafirewall"


def _imported_top_level_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
    return names


def _files_importing(root: Path, forbidden_prefix: str) -> list[str]:
    offending = []
    for path in root.rglob("*.py"):
        for name in _imported_top_level_names(path):
            if name == forbidden_prefix or name.startswith(forbidden_prefix + "."):
                offending.append(str(path))
                break
    return offending


def test_toy_agent_package_never_imports_aidr():
    offending = _files_importing(SRC_ROOT, "aidr")
    assert not offending, f"toy_agent must never import aidr directly: {offending}"


def test_toy_agent_package_never_imports_llamafirewall():
    offending = _files_importing(SRC_ROOT, "llamafirewall")
    assert not offending, f"toy_agent must never import llamafirewall directly: {offending}"


def test_detector_adapter_package_never_imports_toy_agent():
    offending = _files_importing(DETECTOR_ADAPTER_ROOT, "toy_agent")
    assert not offending, f"detector_adapter must never import toy_agent: {offending}"


def test_vendors_aidr_never_imports_llamafirewall():
    offending = _files_importing(AIDR_VENDOR_ROOT, "llamafirewall")
    assert not offending, f"vendors/aidr must never import llamafirewall: {offending}"


def test_vendors_llamafirewall_never_imports_aidr():
    offending = _files_importing(LLAMAFIREWALL_VENDOR_ROOT, "aidr")
    assert not offending, f"vendors/llamafirewall must never import aidr: {offending}"


def test_toy_agent_package_never_imports_catalog():
    """Atlas 6-gap spec C10: src/toy_agent non importa da catalog/. Vincolo
    architetturale generale (design v4), promosso a test pytest reale — non
    un check manuale documentato."""
    offending = _files_importing(SRC_ROOT, "catalog")
    assert not offending, f"toy_agent must never import catalog: {offending}"
