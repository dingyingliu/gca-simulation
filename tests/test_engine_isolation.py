"""The V8 engine stays confined to the golden-generation script, and nothing forces a successful exit.

os._exit skips clean-up and, if reached from code that
pytest imports, would end a test run early with exit code 0.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ENGINE_USERS = {Path("tests/golden/make_demo_golden.py")}
ENGINE_IMPORT = re.compile(r"^\s*(from|import)\s+py_mini_racer\b", re.M)
FORCED_EXIT = re.compile(r"\bos\._exit\s*\(")


def _python_files():
    for folder in ("gca_sim", "tests", "experiments"):
        yield from (ROOT / folder).rglob("*.py")


def test_mini_racer_only_in_golden_generator():
    offenders = [p.relative_to(ROOT) for p in _python_files()
                 if ENGINE_IMPORT.search(p.read_text(encoding="utf-8"))
                 and p.relative_to(ROOT) not in ALLOWED_ENGINE_USERS]
    assert not offenders, f"py_mini_racer imported outside the golden generator: {offenders}"


def test_no_forced_exit():
    this = Path(__file__).resolve()
    offenders = [p.relative_to(ROOT) for p in _python_files()
                 if p.resolve() != this and FORCED_EXIT.search(p.read_text(encoding="utf-8"))]
    assert not offenders, f"os._exit found in: {offenders}"
