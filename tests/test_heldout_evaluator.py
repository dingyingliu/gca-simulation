"""The held-out robustness check implements the declared rule, is bound to the model, weeks and conclusions it was
frozen from, and runs once.

Uses fabricated rows, bytes and temporary paths only; never touches the held-out weeks."""

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_e4", ROOT / "experiments" / "e4_quotation" / "run_e4.py")
run_e4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_e4)


def _row(a, b, m, hi, lo, sign=0, family="design"):
    return {"a": a, "b": b, "measure": m, "share_draws_a_higher": hi, "share_draws_a_lower": lo,
            "robust_sign": sign, "family": family}


def _dev(rows, dirty=False):
    return {"comparisons_pooled": rows, "versions": {"code_commit": "abc1234", "code_dirty": dirty},
            "assumptions_sha256": "assum"}


def test_freeze_keeps_conclusions_that_hold_and_drops_fixed_measures_and_sensitivities():
    rows = [_row("x", "y", "wrong_terms", 1.0, 0.0, 1), _row("x", "z", "wrong_terms", 0.6, 0.4, 0),
            _row("y", "z", "days_mean", 0.0, 0.97, -1), _row("x", "y", "total_reviews", 1.0, 0.0, 1),
            _row("x", "y", "releases_beyond_authority", 1.0, 0.0, 1, family="gate_effect")]
    frozen = run_e4.freeze_conclusions(_dev(rows), "sha", "assum")
    assert [(c["measure"], c["direction"]) for c in frozen["conclusions"]] == [("wrong_terms", 1), ("days_mean", -1)]
    assert frozen["rule"]["target_measures"] == ["wrong_terms", "days_mean"]
    assert frozen["assumptions_sha256"] == "assum" and frozen["development_results_sha256"] == "sha"


def test_targets_apply_to_each_measure_separately():
    dev = [_row(f"a{i}", "b", "wrong_terms", 1.0, 0.0, 1) for i in range(5)]
    dev += [_row(f"c{i}", "d", "days_mean", 1.0, 0.0, 1) for i in range(5)]
    dev += [_row(f"e{i}", "f", "inconsistent_customers", 1.0, 0.0, 1) for i in range(10)]
    frozen = run_e4.freeze_conclusions(_dev(dev), "sha", "assum")
    held = [_row(f"a{i}", "b", "wrong_terms", 0.95 if i < 4 else 0.5, 0.0) for i in range(5)]   # 4 of 5 pass
    held += [_row(f"c{i}", "d", "days_mean", 0.95 if i < 3 else 0.5, 0.0) for i in range(5)]  # 3 of 5 pass
    held += [_row(f"e{i}", "f", "inconsistent_customers", 0.95, 0.0) for i in range(10)]       # all pass
    out = run_e4.evaluate_conclusions(frozen, held)
    assert out["targets"] == {"wrong_terms": "pass", "days_mean": "fail"}
    assert out["passed"] is False  # 17 of 20 pass overall (85%), but days fails its own target
    assert out["by_measure"]["inconsistent_customers"]["pass_fraction"] == 1.0


def test_missing_and_tied_rows_fail_and_empty_targets_are_defined():
    frozen = run_e4.freeze_conclusions(_dev([_row("x", "y", "wrong_terms", 1.0, 0.0, 1)]), "sha", "assum")
    out = run_e4.evaluate_conclusions(frozen, [])
    assert out["results"][0]["passed"] is False and out["targets"]["wrong_terms"] == "fail"
    assert out["targets"]["days_mean"].startswith("not applicable")
    empty = run_e4.evaluate_conclusions(run_e4.freeze_conclusions(_dev([]), "sha", "assum"), [])
    assert empty["passed"] is None and empty["outcome"] == "no development conclusions to check"


MANIFEST = {"development": {"W0.json": {"sha256": "w0"}},
            "heldout": {f"H{i}.json": {"sha256": f"h{i}"} for i in range(1, 5)}}
ROWS = [_row("x", "y", "wrong_terms", 1.0, 0.0, 1), _row("x", "z", "days_mean", 0.0, 0.97, -1)]
OK = dict(changed_since=lambda c: False, dirty=lambda: False, committed=lambda: True)


def _b(obj) -> bytes:
    return json.dumps(obj, sort_keys=True).encode("utf-8")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _frozen(dirty=False, manifest=MANIFEST, assumptions=b"ranges: 1"):
    """A frozen specification as read back from its file, with the bytes it was frozen from."""
    res, man = _b(_dev(ROWS, dirty=dirty)), _b(manifest)
    frozen = run_e4.freeze_conclusions(json.loads(res), _sha(res), _sha(assumptions), _sha(man))
    return json.loads(json.dumps(frozen)), res, assumptions, man


def test_validation_refuses_any_mismatch():
    frozen, res, ass, man = _frozen()
    run_e4.validate_frozen(frozen, res, ass, man, **OK)  # all consistent: allowed
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(frozen, _b(_dev(ROWS[:1])), ass, man, **OK)
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(frozen, res, b"ranges: 2", man, **OK)
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(frozen, res, ass, man, **{**OK, "dirty": lambda: True})
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(frozen, res, ass, man, **{**OK, "changed_since": lambda c: True})
    dirty_frozen, dres, dass, dman = _frozen(dirty=True)
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(dirty_frozen, dres, dass, dman, **OK)


def test_validation_refuses_an_edited_case_even_with_a_matching_manifest_hash():
    frozen, res, ass, man = _frozen()
    edited = copy.deepcopy(MANIFEST)
    edited["heldout"]["H2.json"]["sha256"] = "h2-regenerated"  # the case and its manifest entry changed together
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(frozen, res, ass, _b(edited), **OK)


def test_validation_refuses_a_removed_heldout_week():
    frozen, res, ass, man = _frozen()
    fewer = copy.deepcopy(MANIFEST)
    del fewer["heldout"]["H4.json"]
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(frozen, res, ass, _b(fewer), **OK)


def test_validation_refuses_uncommitted_or_altered_conclusions_but_ignores_the_freeze_time():
    frozen, res, ass, man = _frozen()
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(frozen, res, ass, man, **{**OK, "committed": lambda: False})
    flipped = copy.deepcopy(frozen)
    flipped["conclusions"][0]["direction"] *= -1
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(flipped, res, ass, man, **OK)
    looser = copy.deepcopy(frozen)
    looser["rule"]["heldout_share"] = 0.5
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(looser, res, ass, man, **OK)
    unnamed = {k: v for k, v in frozen.items() if k != "heldout_manifest_sha256"}
    with pytest.raises(SystemExit):
        run_e4.validate_frozen(unnamed, res, ass, man, **OK)
    later = dict(frozen, frozen_utc="2099-01-01 00:00 UTC")
    run_e4.validate_frozen(later, res, ass, man, **OK)


def test_guarded_paths_cover_the_frozen_weeks_but_not_documentation():
    guarded = set(run_e4.GUARDED_PATHS)
    assert {"experiments/e4_quotation/heldout_manifest.json", "specs/simulated_weeks", "gca_sim",
            "experiments/e4_quotation/run_e4.py", "evidence/assumptions.yaml"} <= guarded
    assert not any(p.startswith(("reports", "LAB_LOG", "README")) for p in guarded)
    assert run_e4.CONCLUSIONS_REL not in guarded


def test_refreeze_is_refused_once_a_heldout_run_has_started(tmp_path, monkeypatch):
    lock = tmp_path / "heldout_started.lock"
    lock.write_text("started")
    monkeypatch.setattr(run_e4, "HELDOUT_LOCK", lock)
    monkeypatch.setattr(run_e4, "HELDOUT_RESULT", tmp_path / "results_heldout.json")
    monkeypatch.setattr(sys, "argv", ["run_e4.py", "--freeze-conclusions"])
    with pytest.raises(SystemExit):
        run_e4.main()


def test_guard_refuses_a_second_or_interrupted_run(tmp_path):
    result, lock = tmp_path / "results_heldout.json", tmp_path / "heldout_started.lock"
    run_e4.heldout_guard(result, lock)  # nothing there: allowed
    lock.write_text("started")
    with pytest.raises(SystemExit):
        run_e4.heldout_guard(result, lock)
    lock.unlink()
    result.write_text("{}")
    with pytest.raises(SystemExit):
        run_e4.heldout_guard(result, lock)


def test_the_one_heldout_evaluation_used_the_frozen_conclusions():
    """Until 2026-10-03 14:34 UTC this test asserted that no held-out result existed. The robustness check has now
    run, once: its result must name the committed frozen conclusions, and no unfinished run may be left behind."""
    import hashlib
    import json
    assert run_e4.HELDOUT_RESULT.exists() and not run_e4.HELDOUT_LOCK.exists()
    result = json.loads(run_e4.HELDOUT_RESULT.read_text(encoding="utf-8"))
    assert result["frozen_conclusions_sha256"] == hashlib.sha256(run_e4.CONCLUSIONS.read_bytes()).hexdigest()
    assert result["versions"]["code_dirty"] is False and result["robustness_check"]["n_conclusions"] == 51
    with pytest.raises(SystemExit):
        run_e4.heldout_guard()
