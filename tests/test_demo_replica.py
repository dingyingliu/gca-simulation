"""E1 regression test: the Python port reproduces the original walkthrough JavaScript exactly.

Golden files come from running the original script in V8 (tests/golden/make_demo_golden.py).
"""

import json
from pathlib import Path

import pytest

from gca_sim.demo_replica import PrototypeAssumptions, WALKTHROUGH_ASSUMPTIONS, simulate, summary
from gca_sim.demo_replica.case import PNAME, PRESET

GOLDEN = Path(__file__).parent / "golden" / "demo_replica"
PRESETS = ["review", "limits", "local"]


def _load(name: str) -> dict:
    return json.loads((GOLDEN / name).read_text(encoding="utf-8"))


def _as_json(o: dict) -> dict:
    # JSON round trip, so the comparison is between the same types the golden file holds.
    return json.loads(json.dumps(o, ensure_ascii=False))


@pytest.mark.parametrize("preset", PRESETS)
def test_port_matches_original_javascript(preset):
    golden = _load(f"golden_{preset}.json")
    assert golden["source"] == "original"
    assert golden["design"] == PRESET[preset]
    assert golden["name"] == PNAME[preset]
    o = simulate(PRESET[preset], WALKTHROUGH_ASSUMPTIONS)
    assert _as_json(o) == golden["result"]
    assert summary(o) == golden["summary"]


@pytest.mark.parametrize("preset", PRESETS)
def test_bypass_off_matches_labelled_javascript_variant(preset):
    """With the bypass assumption off, the port matches the original code run with BYPASS=Infinity."""
    variant = _load(f"variant_nobypass_{preset}.json")
    assert variant["source"] == "variant: const BYPASS=Infinity"
    o = simulate(PRESET[preset])
    assert _as_json(o) == variant["result"]
    assert summary(o) == variant["summary"]


def test_bypass_assumption_is_off_by_default():
    assert PrototypeAssumptions().bypass_after_days is None
    for preset in PRESETS:
        o = simulate(PRESET[preset])
        assert o["unsigned"] == 0
        assert not any(r.get("bypass") for r in o["rows"])


def test_golden_files_unchanged():
    """The golden files are the ones listed in the manifest written when they were generated."""
    import hashlib

    manifest = _load("MANIFEST.json")
    assert manifest["script_sha256"] == "53cca498ebdea69261f20335c25d207477f4db729d860d1e698d195141c4fe3e"
    for name, sha in manifest["files"].items():
        assert hashlib.sha256((GOLDEN / name).read_bytes()).hexdigest() == sha, name
