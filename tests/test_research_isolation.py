"""The research model never imports the prototype port (do not carry its routing into research)."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_code_does_not_import_the_prototype():
    offenders = []
    for path in (ROOT / "gca_sim").rglob("*.py"):
        rel = path.relative_to(ROOT)
        if rel.parts[:2] == ("gca_sim", "demo_replica"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            if any("demo_replica" in n for n in names):
                offenders.append(str(rel))
    assert not offenders, offenders
