"""How the agent pilot's estimates go into the quotation model (experiments/agent_pilot_plan.md, section 9.1).

The rules are fixed before the pilot's development run. These tests use made-up pilot frequencies only."""

import importlib.util
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml
from scipy.stats import qmc

from gca_sim.pilot.analysis import wilson
from gca_sim.simulator import designs, engine, params, random_streams as streams, ground_truth as truth
from gca_sim.simulator.decisions import agent_pick_note, agent_self_check
from gca_sim.simulator.observations import NoteChoiceObs, SelfCheckObs

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "experiments" / "e4_quotation" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_pilot = load("apply_pilot")
compare_runs = load("compare_runs")


def before_pilot() -> dict:
    """The declared assumptions as they stand before any pilot result: no constraints, the two new parameters at
    their defaults. (After the pilot is applied the file on disk holds more; these tests do not depend on that.)"""
    a = params.load_assumptions()
    a.pop("pilot_constraints", None)
    a["parameters"]["p_newest_note"]["range"] = [1.0, 1.0]
    a["parameters"]["p_flag_after_note"]["range"] = [0.0, 0.0]
    return a


# ---------------------------------------------------------------- the two new parameters

def test_the_26_earlier_draws_do_not_move_and_the_new_parameters_default_to_the_first_model():
    a = before_pilot()
    draws = params.latin_hypercube(32, seed=20261002, assumptions=a)
    r = params.ranges(a)
    unit = qmc.LatinHypercube(d=26, seed=20261002).random(32)
    assert len(params.LHS_NAMES) == 26 and params.PARAM_NAMES[-2:] == params.EXTRA_NAMES
    for j, name in enumerate(params.LHS_NAMES):
        expected = r[name][0] + unit[:, j] * (r[name][1] - r[name][0])
        assert [getattr(p, name) for p in draws] == list(map(float, expected)), name
    assert {p.p_newest_note for p in draws} == {1.0} and {p.p_flag_after_note for p in draws} == {0.0}
    c = params.central(a)
    assert c.p_newest_note == 1.0 and c.p_flag_after_note == 0.0 and c.e_visible == (r["e_visible"][0] + r["e_visible"][1]) / 2
    wider = yaml.safe_load(yaml.safe_dump(a))
    wider["parameters"]["p_newest_note"]["range"] = [0.2, 1.0]
    moved = params.latin_hypercube(32, seed=20261002, assumptions=wider)
    assert [replace(p, p_newest_note=1.0) for p in moved] == draws, "a new range for one moves no other parameter"
    assert len({p.p_newest_note for p in moved}) == 32 and all(0.2 <= p.p_newest_note <= 1.0 for p in moved)


def test_which_note_a_reader_takes():
    p = params.central(before_pilot())
    u = {"note_choice": 0.4, "note_pick": 0.75}
    assert agent_pick_note(NoteChoiceObs(0), u, p) == (None, ())
    assert agent_pick_note(NoteChoiceObs(1), u, p) == (0, ())
    assert agent_pick_note(NoteChoiceObs(3), u, p) == (2, ("p_newest_note",)), "the default takes the newest"
    assert agent_pick_note(NoteChoiceObs(3), {"note_choice": 0.999999, "note_pick": 0.0}, p)[0] == 2
    older = replace(p, p_newest_note=0.0)
    assert agent_pick_note(NoteChoiceObs(3), {"note_choice": 0.4, "note_pick": 0.25}, older)[0] == 0
    assert agent_pick_note(NoteChoiceObs(3), {"note_choice": 0.4, "note_pick": 0.75}, older)[0] == 1
    assert agent_pick_note(NoteChoiceObs(2), {"note_choice": 0.4, "note_pick": 0.9999}, older)[0] == 0
    half = replace(p, p_newest_note=0.5)
    assert agent_pick_note(NoteChoiceObs(2), {"note_choice": 0.49, "note_pick": 0.5}, half)[0] == 1
    assert agent_pick_note(NoteChoiceObs(2), {"note_choice": 0.51, "note_pick": 0.5}, half)[0] == 0


def test_the_engine_reads_an_older_note_only_when_the_parameter_allows_it():
    """W0: Nexa has a stale note, Q02 (Brazil) then writes its own, and Q07 (Singapore) reads one of the two."""
    case = truth.walkthrough_case()
    ents = streams.case_entities(case)
    base = replace(params.central(before_pilot()), p_stale_note=1.0, p_read_note=1.0, p_adopt_blind=1.0)

    def q07_draft(p):
        res = engine.simulate(case, designs.DESIGNS["review"], "shared", p, streams.Streams(0, ents), log=True)
        return next(e for e in res.log if e["action"] == "draft" and e["quote"] == "Q07")

    newest = q07_draft(base)
    assert newest["info"]["readable_notes"] == 2 and newest["info"]["note_in_view_origin"] == "draft"
    assert "quotation.p_newest_note" in newest["evidence"]
    oldest = q07_draft(replace(base, p_newest_note=0.0))
    assert oldest["info"]["note_in_view_origin"] == "stale"


def test_escalation_after_using_a_note_follows_its_own_parameter():
    p = params.central(before_pilot())
    obs = dict(term="payment_days", drafted=45, requested_value=None, draft_exceeds_policy=False, register_value=None,
               cites_agreement=True)
    u = {"self_check": 0.5, "unverifiable": 0.05}
    assert agent_self_check(SelfCheckObs(**obs, note_used=True), u, p) == (None, ("p_flag_after_note",))
    assert agent_self_check(SelfCheckObs(**obs, note_used=True), u, replace(p, p_flag_after_note=0.3))[0] == "unverifiable"
    assert agent_self_check(SelfCheckObs(**obs, note_used=False), u, replace(p, p_flag_unverifiable=0.3)) == \
        ("unverifiable", ("p_flag_unverifiable",))
    assert agent_self_check(SelfCheckObs(**obs, note_used=False), u, replace(p, p_flag_unverifiable=0.01))[0] is None


# ---------------------------------------------------------------- the products

def with_products(q, r) -> dict:
    a = before_pilot()
    a["pilot_constraints"] = {"products": {"q_read_x_adopt_blind": list(q), "r_read_x_not_notice": list(r)}}
    return a


def test_draws_respect_the_products_the_pilot_measures():
    free = params.latin_hypercube(64, seed=20261002, assumptions=before_pilot())
    a = with_products((0.4, 0.9), (0.0, 0.2))
    draws = params.latin_hypercube(64, seed=20261002, assumptions=a)
    read_lo, read_hi = params.ranges(a)["p_read_note"]
    for p, f in zip(draws, free):
        q, r = p.p_read_note * p.p_adopt_blind, p.p_read_note * (1 - p.p_notice_visible)
        assert 0.4 - 1e-9 <= q <= 0.9 + 1e-9 and -1e-9 <= r <= 0.2 + 1e-9
        assert max(read_lo, q, r) - 1e-9 <= p.p_read_note <= read_hi + 1e-9
        assert 0 <= p.p_adopt_blind <= 1 and 0 <= p.p_notice_visible <= 1
        same = {n for n in params.PARAM_NAMES if n not in params.PRODUCT_PARAMS}
        assert all(getattr(p, n) == getattr(f, n) for n in same), "only the three note parameters move"
    qs = sorted(p.p_read_note * p.p_adopt_blind for p in draws)
    assert qs[0] < 0.42 and qs[-1] > 0.88, "the product covers the pilot's whole interval"
    c = params.central(a)
    assert c.p_read_note * c.p_adopt_blind == pytest.approx(0.65) and c.p_read_note * (1 - c.p_notice_visible) == pytest.approx(0.1)


def test_products_at_the_edges_and_bad_intervals():
    nothing = params.latin_hypercube(8, seed=1, assumptions=with_products((0.0, 0.0), (0.0, 0.0)))
    assert all(p.p_adopt_blind == 0.0 and p.p_notice_visible == 1.0 for p in nothing)
    always = params.latin_hypercube(8, seed=1, assumptions=with_products((1.0, 1.0), (0.0, 0.0)))
    assert all(p.p_read_note == 1.0 and p.p_adopt_blind == 1.0 for p in always)
    with pytest.raises(ValueError):
        params.latin_hypercube(8, seed=1, assumptions=with_products((0.6, 0.4), (0.0, 0.1)))
    with pytest.raises(ValueError):
        params.latin_hypercube(8, seed=1, assumptions=with_products((0.2, 1.2), (0.0, 0.1)))


# ---------------------------------------------------------------- the rules of section 9.1

def freq(k, n, bootstrap=None, tasks=5):
    return {"mean_over_tasks": None if n == 0 else round(k / n, 4), "tasks": tasks if n else 0, "valid_task_runs": n,
            "count": k, "missing_task_runs": 0, "interval_95_group_bootstrap": bootstrap,
            "interval_95_wilson_pooled_ignores_clustering": wilson(k, n)}


def pilot(**over) -> dict:
    """Made-up development frequencies, keyed as analysis.e4_constraints keys them."""
    made_up = {"e_visible": freq(2, 45, [0.0, 0.1111]), "p_flag_unverifiable": freq(27, 45, [0.4, 0.8]),
               "q_harm": freq(12, 15, [0.6, 1.0]), "q_help": freq(10, 15, [0.4667, 0.8667]),
               "r": freq(1, 15, [0.0, 0.2]), "b": freq(0, 6), "b_ambiguous": freq(1, 3), "a": freq(7, 9, [0.5, 1.0]),
               "c": freq(1, 2), "flag_after_note": freq(3, 22, [0.0, 0.3])}
    made_up.update(over)
    return {apply_pilot.KEYS[name]: f for name, f in made_up.items()}


DECLARED = {k: list(v) for k, v in params.ranges(before_pilot()).items()}


def test_an_interval_is_the_union_of_the_bootstrap_and_wilson_intervals():
    w = wilson(12, 15)
    assert apply_pilot.interval(freq(12, 15, [0.6, 1.0])) == [min(0.6, w[0]), 1.0]
    assert apply_pilot.interval(freq(12, 15)) == w, "no bootstrap: the Wilson interval alone"
    assert apply_pilot.interval(freq(0, 0)) is None


def test_ranges_follow_the_rules():
    d = apply_pilot.derive(pilot(), DECLARED)
    iv = d["intervals"]
    assert d["ranges"]["e_visible"] == iv["e_visible"] and d["ranges"]["p_flag_unverifiable"] == iv["p_flag_unverifiable"]
    q = d["products"]["q_read_x_adopt_blind"]
    assert q == [min(iv["q_harm"][0], iv["q_help"][0]), max(iv["q_harm"][1], iv["q_help"][1])]
    assert d["products"]["r_read_x_not_notice"] == iv["r"]
    assert d["checks"]["right_and_wrong_notes_adopted_alike"]["intervals_overlap"] is True
    # the reading rule: no planted match in 6 distinguishing runs leaves the rule and its value of 1 standing
    # the width of an interval from six runs is not evidence against the rule
    newest = d["checks"]["reader_takes_the_newest_note"]
    assert newest["counterexample_observed"] is False and newest["range_changed"] is False
    assert "p_newest_note" not in d["ranges"] and "b_not_newest_x_q" not in d["products"]
    assert newest["lowest_p_newest_note_the_pilot_allows"] == pytest.approx(max(0.0, 1 - iv["b"][1] / q[0]), abs=1e-4)
    assert newest["ambiguous_runs_first_note_also_names_the_planted_value"]["runs"] == 3
    # escalation after a note: 3 of 22 contradicts "never", and 22 runs are enough to put a range on it
    after = d["checks"]["no_escalation_after_using_a_note"]
    assert after["counterexample_observed"] is True and after["range_changed"] is True
    assert d["ranges"]["p_flag_after_note"] == iv["flag_after_note"]
    # the envelopes of the two parameters that follow from the products
    adopt, notice = d["ranges"]["p_adopt_blind"], d["ranges"]["p_notice_visible"]
    a = with_products(q, d["products"]["r_read_x_not_notice"])
    for p in params.latin_hypercube(64, seed=3, assumptions=a):
        assert adopt[0] - 1e-4 <= p.p_adopt_blind <= adopt[1] + 1e-4
        assert notice[0] - 1e-4 <= p.p_notice_visible <= notice[1] + 1e-4


def test_a_counterexample_is_reported_whatever_the_number_of_runs():
    """Seeing a counterexample to a "never" rule is one thing, having enough runs to put a number on
    it is another."""
    def reading(b):
        d = apply_pilot.derive(pilot(b=b), DECLARED)
        return d, d["checks"]["reader_takes_the_newest_note"]

    d, none = reading(freq(0, 0))
    assert none["counterexample_observed"] is None and "not assessed" in none["status"]
    assert none["lowest_p_newest_note_the_pilot_allows"] == 0.0, "with no qualifying run the pilot does not bound it"
    assert "p_newest_note" not in d["ranges"]

    d, few_hit = reading(freq(1, 4))
    assert few_hit["counterexample_observed"] is True and few_hit["enough_runs_to_calibrate"] is False
    assert "counterexample observed" in few_hit["status"] and "too few runs" in few_hit["status"]
    assert few_hit["range_changed"] is False and "p_newest_note" not in d["ranges"]

    d, few_clean = reading(freq(0, 4))
    assert few_clean["counterexample_observed"] is False and "no counterexample in 4" in few_clean["status"]
    assert "p_newest_note" not in d["ranges"]

    d, enough_hit = reading(freq(3, 8))
    assert enough_hit["counterexample_observed"] is True and enough_hit["enough_runs_to_calibrate"] is True
    assert enough_hit["range_changed"] is True and "contradicted" in enough_hit["status"]
    assert d["products"]["b_not_newest_x_q"] == d["intervals"]["b"]
    assert d["ranges"]["p_newest_note"][1] < 1.0

    d, enough_clean = reading(freq(0, 8))
    assert enough_clean["counterexample_observed"] is False and enough_clean["range_changed"] is False

    after = apply_pilot.derive(pilot(flag_after_note=freq(1, 3)), DECLARED)
    check = after["checks"]["no_escalation_after_using_a_note"]
    assert check["counterexample_observed"] is True and check["range_changed"] is False
    assert "p_flag_after_note" not in after["ranges"]
    never = apply_pilot.derive(pilot(flag_after_note=freq(0, 10)), DECLARED)
    assert never["checks"]["no_escalation_after_using_a_note"]["counterexample_observed"] is False
    assert never["ranges"]["p_flag_after_note"] == [0.0, wilson(0, 10)[1]], "rule 8 as first written: 5 runs set the range"

    # plan rule 10: the reading rule as first written is evaluated beside the revised one
    first = apply_pilot.derive(pilot(b=freq(0, 0), b_ambiguous=freq(0, 1)), DECLARED)["checks"][
        "reader_takes_the_newest_note"]["under_the_rule_as_first_written"]
    assert first["qualifying_runs"] == 1 and first["range"] is None and first["same_effect_as_the_revised_rule"] is True
    differs = apply_pilot.derive(pilot(b=freq(0, 2), b_ambiguous=freq(2, 4)), DECLARED)["checks"][
        "reader_takes_the_newest_note"]
    assert differs["range_changed"] is False and differs["under_the_rule_as_first_written"]["range"] is not None
    assert differs["under_the_rule_as_first_written"]["same_effect_as_the_revised_rule"] is False
    with pytest.raises(SystemExit):
        apply_pilot.derive(pilot(r=freq(0, 0)), DECLARED)


def test_every_draw_agrees_with_the_measured_reading_rule_interval():
    """With q in [0.5, 0.8] and b in [0.1, 0.2], a range for p_newest_note on its own would allow
    q = 0.8 with p_newest_note = 0.6, which implies b = 0.32. Drawn jointly, every draw stays inside."""
    a = with_products((0.5, 0.8), (0.0, 0.2))
    a["pilot_constraints"]["products"]["b_not_newest_x_q"] = [0.1, 0.2]
    draws = params.latin_hypercube(64, seed=20261002, assumptions=a)
    for p in draws:
        q = p.p_read_note * p.p_adopt_blind
        b = (1 - p.p_newest_note) * q
        assert 0.5 - 1e-9 <= q <= 0.8 + 1e-9 and 0.1 - 1e-9 <= b <= 0.2 + 1e-9
        assert 0.0 <= p.p_newest_note <= 1.0
    bs = sorted((1 - p.p_newest_note) * p.p_read_note * p.p_adopt_blind for p in draws)
    assert bs[0] < 0.105 and bs[-1] > 0.195, "b covers its whole interval"
    c = params.central(a)
    assert (1 - c.p_newest_note) * c.p_read_note * c.p_adopt_blind == pytest.approx(0.15)
    free = params.latin_hypercube(64, seed=20261002, assumptions=with_products((0.5, 0.8), (0.0, 0.2)))
    assert all(replace(p, p_newest_note=1.0) == f for p, f in zip(draws, free)), "only p_newest_note moves"
    # b can reach q but not pass it: with a b interval wider than q allows, each draw is capped at its own q
    wide = with_products((0.2, 0.9), (0.0, 0.1))
    wide["pilot_constraints"]["products"]["b_not_newest_x_q"] = [0.1, 0.6]
    for p in params.latin_hypercube(64, seed=5, assumptions=wide):
        q = p.p_read_note * p.p_adopt_blind
        assert 0.1 - 1e-9 <= (1 - p.p_newest_note) * q <= min(0.6, q) + 1e-9 and p.p_newest_note >= -1e-12
    # a b interval that starts above the smallest q cannot be satisfied in every draw: refused, not clipped
    bad = with_products((0.2, 0.9), (0.0, 0.1))
    bad["pilot_constraints"]["products"]["b_not_newest_x_q"] = [0.3, 0.6]
    with pytest.raises(ValueError):
        params.latin_hypercube(8, seed=5, assumptions=bad)
    d = apply_pilot.derive(pilot(q_harm=freq(3, 15, [0.1, 0.3]), q_help=freq(3, 15, [0.1, 0.3]),
                                 b=freq(9, 10, [0.8, 1.0])), DECLARED)
    reading = d["checks"]["reader_takes_the_newest_note"]
    assert "incompatible" in reading["status"] and reading["range_changed"] is False
    assert "b_not_newest_x_q" not in d["products"] and "p_newest_note" not in d["ranges"]


def test_right_and_wrong_notes_that_differ_widen_the_product():
    d = apply_pilot.derive(pilot(q_harm=freq(15, 15, [1.0, 1.0]), q_help=freq(1, 15, [0.0, 0.2])), DECLARED)
    assert d["checks"]["right_and_wrong_notes_adopted_alike"]["intervals_overlap"] is False
    q = d["products"]["q_read_x_adopt_blind"]
    assert q[0] < 0.01 and q[1] == 1.0


def declared_text() -> str | None:
    """The assumptions file as declared, or None once the pilot has been applied to it."""
    text = (ROOT / "evidence" / "assumptions.yaml").read_text(encoding="utf-8")
    return None if "pilot_constraints:" in text else text


def test_the_assumptions_file_is_rewritten_once_and_only_where_intended():
    original = declared_text()
    if original is None:
        pytest.skip("the pilot has been applied: the rewrite ran for real, and the next test checks its result")
    d = apply_pilot.derive(pilot(b=freq(3, 8)), DECLARED)
    new = apply_pilot.rewrite(original, d, "2026-10-03 12:00 UTC", "0" * 64)
    before, after = yaml.safe_load(original), yaml.safe_load(new)
    for name, rng in d["ranges"].items():
        assert [float(x) for x in after["parameters"][name]["range"]] == rng
        assert "gent pilot" in after["parameters"][name]["basis"]
    status = {name: after["parameters"][name]["status"] for name in d["ranges"]}
    assert status == {"e_visible": "pilot", "p_flag_unverifiable": "pilot", "p_flag_after_note": "pilot",
                      "p_adopt_blind": "pilot_product", "p_notice_visible": "pilot_product",
                      "p_newest_note": "pilot_product"}
    assert after["parameters"]["p_read_note"] == before["parameters"]["p_read_note"]
    assert after["parameters"]["effort_lead"] == before["parameters"]["effort_lead"]
    assert after["parameters"]["p_newest_note"]["declared_utc"] == "2026-10-03 10:25 UTC"
    assert len(after["changes"]) == len(before["changes"]) + 1 and after["changes"][-1]["utc"] == "2026-10-03 12:00 UTC"
    assert after["pilot_constraints"]["products"] == d["products"] and "b_not_newest_x_q" in d["products"]
    assert set(after["pilot_constraints"]["rules_of_the_first_model"]) == {"reader_takes_the_newest_note",
                                                                         "no_escalation_after_using_a_note"}
    assert "# ---- human reviewers (no evidence; HANDOFF 1.3 point 4)" in new, "comments survive"
    draws = params.latin_hypercube(16, seed=20261002, assumptions=after)
    q, b = d["products"]["q_read_x_adopt_blind"], d["products"]["b_not_newest_x_q"]
    for p in draws:
        product = p.p_read_note * p.p_adopt_blind
        assert q[0] - 1e-9 <= product <= q[1] + 1e-9
        assert b[0] - 1e-9 <= (1 - p.p_newest_note) * product <= b[1] + 1e-9
        assert d["ranges"]["p_newest_note"][0] - 1e-4 <= p.p_newest_note <= d["ranges"]["p_newest_note"][1] + 1e-4
    with pytest.raises(SystemExit):
        apply_pilot.rewrite(new, d, "2026-10-03 12:05 UTC", "0" * 64)


def test_stale_estimates_change_nothing(tmp_path):
    """Estimates from another scorer, other inputs or another run file are refused before anything
    is written. The test uses the real development run and a doctored copy of its estimates."""
    import json
    real = ROOT / "reports" / "E5" / "results_development.json"
    if not real.exists():
        pytest.skip("no development estimates yet")
    assumptions = tmp_path / "assumptions.yaml"
    assumptions.write_bytes((ROOT / "evidence" / "assumptions.yaml").read_bytes())
    untouched = assumptions.read_bytes()
    out, before = tmp_path / "e4_update.json", tmp_path / "results_before_pilot.json"
    est = json.loads(real.read_text(encoding="utf-8"))
    import hashlib
    from gca_sim.pilot.records import load_config, request_fingerprint, scoring_fingerprint
    pilot_dir = ROOT / "experiments" / "agent_pilot"
    current_inputs = request_fingerprint(load_config(pilot_dir / "config.yaml", paid=True),
                                         hashlib.sha256((pilot_dir / "task_bank" / "manifest.json").read_bytes()).hexdigest())
    current_run = hashlib.sha256((pilot_dir / "runs" / "development.jsonl").read_bytes()).hexdigest()
    for field, message in (("scoring_inputs_sha256", "scorer"), ("request_inputs_sha256", "experiment inputs"),
                           ("run_sha256", "run file")):
        stale = tmp_path / f"stale_{field}.json"
        # everything current except the one field, whatever the state of the estimates on disk
        current = {**est, "scoring_inputs_sha256": scoring_fingerprint(),
                   "request_inputs_sha256": current_inputs, "run_sha256": current_run}
        stale.write_text(json.dumps({**current, field: "0" * 64}), encoding="utf-8")
        with pytest.raises(SystemExit) as refusal:
            apply_pilot.apply(results=stale, assumptions=assumptions, out=out, before=before)
        assert message in str(refusal.value), (field, str(refusal.value))
        assert assumptions.read_bytes() == untouched and not out.exists() and not before.exists()
    with pytest.raises(SystemExit):
        apply_pilot.apply(results=tmp_path / "missing.json", assumptions=assumptions, out=out, before=before)
    assert assumptions.read_bytes() == untouched and not out.exists() and not before.exists()


def test_the_reference_run_must_be_the_declared_comparison(tmp_path):
    """The "before" run is taken by the script, and only if it is the run it should be."""
    import hashlib
    import json
    assumptions = b"declared assumptions"
    good = {"raw_data_sha256": apply_pilot.REFERENCE_RAW_DATA_SHA256,
            "assumptions_sha256": hashlib.sha256(assumptions).hexdigest(), "versions": {"code_dirty": False}}
    path = tmp_path / "results.json"
    for bad in ({**good, "raw_data_sha256": "another run"}, {**good, "assumptions_sha256": "other assumptions"},
                {**good, "versions": {"code_dirty": True}}):
        path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(SystemExit):
            apply_pilot.checked_reference(assumptions, path)
    path.write_text(json.dumps(good), encoding="utf-8")
    assert json.loads(apply_pilot.checked_reference(assumptions, path)) == good


def test_an_applied_pilot_is_consistent_with_its_own_record():
    """After the real application: the ranges in assumptions.yaml are those the update report gives."""
    a = params.load_assumptions()
    if not a.get("pilot_constraints"):
        pytest.skip("the pilot has not been applied yet")
    import json
    report = json.loads((ROOT / "reports" / "E5" / "e4_update.json").read_text(encoding="utf-8"))
    assert a["pilot_constraints"]["products"] == report["products"]
    for name, rng in report["ranges"].items():
        assert [float(x) for x in a["parameters"][name]["range"]] == rng
    assert a["pilot_constraints"]["source_sha256"] == report["source_sha256"]
    before = json.loads((ROOT / "reports" / "E4" / "results_before_pilot.json").read_text(encoding="utf-8"))
    assert before["raw_data_sha256"] == apply_pilot.REFERENCE_RAW_DATA_SHA256


# ---------------------------------------------------------------- what changed between two runs

def test_changed_comparisons_are_found_and_named():
    def run(rows, sha):
        summary = {label: {m: {"mean": 1.0} for m in compare_runs.MAIN_MEASURES} for label in compare_runs.HEADLINE}
        return {"comparisons_pooled": rows, "summary_pooled": summary, "versions": {"code_commit": sha},
                "assumptions_sha256": sha, "raw_data_sha256": sha, "finished_utc": "t"}

    def row(measure, sign, higher, lower):
        return {"family": "design", "a": "full|review|isolated|draft", "b": "full|limits|isolated|draft",
                "measure": measure, "robust_sign": sign, "share_draws_a_higher": higher, "share_draws_a_lower": lower,
                "mean_diff": 0.5 * sign}

    before = run([row("wrong_terms", 1, 1.0, 0.0), row("days_mean", 1, 0.96, 0.04), row("total_reviews", 0, 0.9, 0.1),
                  row("repeat_all_wrong", 1, 0.97, 0.03)], "a")
    after = run([row("wrong_terms", 1, 0.98, 0.02), row("days_mean", 0, 0.9, 0.1), row("total_reviews", 1, 0.96, 0.04),
                 row("repeat_all_wrong", -1, 0.02, 0.98)], "b")
    out = compare_runs.compare(before, after)
    assert out["comparisons"] == 4 and {c["measure"]: c["change"] for c in out["changed"]} == {
        "days_mean": "no longer holds", "total_reviews": "now holds", "repeat_all_wrong": "reversed"}
    assert out["by_family"]["design"] == {"comparisons": 4, "changed": 3, "hold_before": 3, "hold_after": 3}
    with pytest.raises(SystemExit):
        compare_runs.compare(before, run(after["comparisons_pooled"][:3], "b"))


def test_records_say_what_the_pilot_fitted_and_what_stays_assumed():
    """A frequency the pilot measured gives a fitted record. A parameter that only follows from a
    fitted combination and an assumed parameter stays assumed. Each record carries the time its
    parameter or its range was set."""
    from gca_sim import evidence
    records = load("write_assumption_records")
    versions = {"code_commit": "test", "code_dirty": False, "analysis": "test", "model": None}
    declared = before_pilot()
    constraints = {"applied_utc": "2026-10-03 14:00 UTC",
                   "products": {"q_read_x_adopt_blind": [0.4, 1.0], "r_read_x_not_notice": [0.0, 0.2]}}

    def record(name, status):
        spec = {**declared["parameters"][name], "status": status, "range": [0.1, 0.4],
                "basis": apply_pilot.BASIS[name].format(rule=apply_pilot.RULE)}
        rec = records.parameter_record(name, spec, versions, declared["declared_utc"], constraints)
        evidence.validate(rec)
        return rec

    for name in ("e_visible", "p_flag_unverifiable", "p_flag_after_note"):
        rec = record(name, "pilot")
        assert rec["status"] == "fitted" and rec["use"] == "range_only" and rec["estimable"] == "partly"
        assert "agent_pilot" in rec["notes"] and "pilot" in rec["source"]["name"]
        assert rec["value"]["distribution"].startswith("uniform over the range")
    for name in ("p_adopt_blind", "p_notice_visible", "p_newest_note"):
        rec = record(name, "pilot_product")
        assert rec["status"] == "assumed" and "use" not in rec and rec["estimable"] == "no"
        assert rec["estimable_note"].startswith("Not identified on its own")
        assert rec["value"]["distribution"].startswith("not drawn on its own")
        assert rec["notes"].startswith("Constrained through the fitted pilot records") and "agent_pilot" in rec["notes"]
    assert record("e_visible", "pilot")["declared_utc"] == declared["declared_utc"], "declared with the file"
    assert "Range set on 2026-10-03 14:00 UTC" in record("e_visible", "pilot")["notes"]
    assert record("p_flag_after_note", "pilot")["declared_utc"] == "2026-10-03 10:25 UTC", "the parameter's own time"

    read = records.parameter_record("p_read_note", declared["parameters"]["p_read_note"], versions,
                                    declared["declared_utc"], constraints)
    evidence.validate(read)
    assert read["status"] == "assumed" and "cut from below" in read["value"]["distribution"]
    assert "does not measure reading" in read["notes"] and read["declared_utc"] == declared["declared_utc"]
    plain = records.parameter_record("p_read_note", declared["parameters"]["p_read_note"], versions,
                                     declared["declared_utc"])
    assert plain["value"]["distribution"].startswith("uniform over the range") and "notes" not in plain
    cue = records.parameter_record("p_cue", declared["parameters"]["p_cue"], versions, declared["declared_utc"], constraints)
    evidence.validate(cue)
    assert cue["status"] == "assumed" and "use" not in cue and cue["declared_utc"] == declared["declared_utc"]
    new = records.parameter_record("p_newest_note", declared["parameters"]["p_newest_note"], versions,
                                   declared["declared_utc"])
    assert new["declared_utc"] == "2026-10-03 10:25 UTC" and new["status"] == "assumed"
    assert set(records.PILOT_RECORDS) == set(apply_pilot.BASIS), "every range the pilot can set names its records"


def test_flip_points_sweep_the_product_once_the_pilot_ties_the_note_parameters():
    """Sweeping one note parameter alone would move a product outside the pilot's interval."""
    flip = load("flip_points")
    plain = flip.sweep_plan("p_adopt_blind", before_pilot())
    assert plain["quantity"] == "p_adopt_blind" and plain["replace"](0.4) == {"p_adopt_blind": 0.4}
    a = with_products((0.4, 0.9), (0.0, 0.2))
    read = params.central(a).p_read_note
    adopt = flip.sweep_plan("p_adopt_blind", a)
    assert adopt["judged_against"] == [0.4, 0.9] and adopt["domain"] == (0.0, 1.0)
    assert adopt["domain"][0] <= 0.4 and adopt["domain"][1] >= 0.9, "the sweep covers the pilot's whole interval"
    assert adopt["replace"](0.5)["p_adopt_blind"] == pytest.approx(0.5 / read)
    high = adopt["replace"](0.88)        # above the central p_read_note: reading rises with the product
    assert read < 0.88 and high["p_read_note"] == 0.88 and high["p_adopt_blind"] == 1.0
    assert high["p_read_note"] * (1 - high["p_notice_visible"]) == pytest.approx(0.1)
    notice = flip.sweep_plan("p_notice_visible", a)
    assert notice["judged_against"] == [0.0, 0.2] and notice["domain"] == (0.0, 1.0)
    assert notice["replace"](0.1)["p_notice_visible"] == pytest.approx(1 - 0.1 / read)
    tables = load("make_tables")
    import inspect
    assert "six ranges" not in inspect.getsource(tables) and "stay assumed under that constraint" in inspect.getsource(tables)
    reading = flip.sweep_plan("p_read_note", a)["replace"](0.8)
    assert reading["p_read_note"] == 0.8 and reading["p_read_note"] * reading["p_adopt_blind"] == pytest.approx(0.65)
    assert reading["p_read_note"] * (1 - reading["p_notice_visible"]) == pytest.approx(0.1)
    assert flip.sweep_plan("effort_lead", a)["quantity"] == "effort_lead"
    assert flip.sweep_plan("p_newest_note", a)["quantity"] == "p_newest_note", "no reading-rule constraint yet"
    a["pilot_constraints"]["products"]["b_not_newest_x_q"] = [0.1, 0.2]
    newest = flip.sweep_plan("p_newest_note", a)
    assert newest["judged_against"] == [0.1, 0.2]
    assert newest["replace"](0.13)["p_newest_note"] == pytest.approx(1 - 0.13 / 0.65)


def test_one_rule_at_a_time_rebuilds_the_declared_assumptions():
    """Each rule's change is applied alone, on top of the ranges as declared."""
    import sys
    sys.path.insert(0, str(ROOT / "experiments" / "e4_quotation"))
    sensitivity = load("pilot_update_sensitivity")
    assert compare_runs.REFERENCE_RAW_DATA_SHA256 == apply_pilot.REFERENCE_RAW_DATA_SHA256
    declared = before_pilot()
    d = apply_pilot.derive(pilot(b=freq(3, 8)), DECLARED)
    update = {"ranges": d["ranges"], "products": d["products"],
              "ranges_before": {k: DECLARED[k] for k in d["ranges"]}}
    current = yaml.safe_load(yaml.safe_dump(declared))
    for name, rng in d["ranges"].items():
        current["parameters"][name]["range"] = rng
    current["pilot_constraints"] = {"products": d["products"]}
    rebuilt = sensitivity.declared_assumptions(current, update)
    assert params.latin_hypercube(16, 7, rebuilt) == params.latin_hypercube(16, 7, declared)
    alone = sensitivity.one_rule(current, update, "rule 2: e_visible")
    draws, base = params.latin_hypercube(16, 7, alone), params.latin_hypercube(16, 7, declared)
    assert all(replace(p, e_visible=b.e_visible) == b for p, b in zip(draws, base)) and draws != base
    notes = sensitivity.one_rule(current, update, "rules 4 to 6: the two note products")
    assert set(notes["pilot_constraints"]["products"]) == {"q_read_x_adopt_blind", "r_read_x_not_notice"}
    rule7 = sensitivity.one_rule(current, update, "rule 7: the reading rule")
    assert "b_not_newest_x_q" in rule7["pilot_constraints"]["products"]
    unchanged = {**update, "ranges": {k: v for k, v in d["ranges"].items() if k != "p_newest_note"},
                 "products": {k: v for k, v in d["products"].items() if k != "b_not_newest_x_q"}}
    assert sensitivity.one_rule(current, unchanged, "rule 7: the reading rule") is None
