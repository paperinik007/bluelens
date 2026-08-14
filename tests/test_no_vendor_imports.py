import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "toy_agent"


def test_toy_agent_package_never_imports_aidr():
    offending = []
    for path in SRC_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module] if node.module else []
            else:
                continue
            if any(name is not None and (name == "aidr" or name.startswith("aidr.")) for name in names):
                offending.append(str(path))
    assert not offending, f"toy_agent must never import aidr directly: {offending}"
