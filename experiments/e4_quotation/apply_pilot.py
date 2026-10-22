"""Put the agent pilot's development estimates into the quotation model's declared ranges.

    .venv/Scripts/python.exe experiments/e4_quotation/apply_pilot.py            # once, after analyse_pilot.py --development
    .venv/Scripts/python.exe experiments/e4_quotation/apply_pilot.py --dry-run  # print the ranges, change nothing

The rules are those of experiments/agent_pilot_plan.md, section 9.1. Rules 1 to 6 and 8 to 10 were written and
committed before any development request was sent. Rule 7 (the reading rule) and the checks around the update
were revised after review, when the development run had finished; the plan's section 16 says what
changed and why. With this pilot's data the old and the new rule 7 give the same result.

The script first checks that the development estimates were made by the current scorer, from the current inputs
and from the run file on disk. It then applies the rules, keeps the comparison made
with the declared assumptions as reports/E4/results_before_pilot.json, rewrites the affected ranges in
evidence/assumptions.yaml with a dated entry in `changes`, adds a `pilot_constraints` block, and writes
reports/E5/e4_update.json with every number it used. Nothing is written unless every check passes, and it
refuses to run a second time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402
from gca_sim.pilot import bank as bank_mod  # noqa: E402
from gca_sim.pilot.analysis import wilson  # noqa: E402
from gca_sim.pilot.records import (estimates_gate, load_config, read_records, request_fingerprint,  # noqa: E402
                                   split_state)

ASSUMPTIONS = ROOT / "evidence" / "assumptions.yaml"
PILOT = ROOT / "experiments" / "agent_pilot"
RESULTS = ROOT / "reports" / "E5" / "results_development.json"
OUT = ROOT / "reports" / "E5" / "e4_update.json"
REFERENCE = ROOT / "reports" / "E4" / "results.json"
BEFORE = ROOT / "reports" / "E4" / "results_before_pilot.json"
# the simulation output of the comparison under the declared assumptions
REFERENCE_RAW_DATA_SHA256 = "20e14ccf26076f48b889d3019c8c172bdac96f427fb5e5cca60aea77c51d60f7"
RULE = "experiments/agent_pilot_plan.md, section 9.1"
MIN_RUNS = 5   # fewer qualifying runs than this and a range is not replaced

# pilot frequency (a key of e4_constraints in results_development.json) for each quantity
KEYS = {
    "e_visible": "e_visible__agreed_term_failed_agreement_roles_I.V+",
    "p_flag_unverifiable": "p_flag_unverifiable__escalation_agreement_roles_I.V-",
    "q_harm": "p_read_note_x_p_adopt_blind__planted_order_3_S.V-",
    "q_help": "p_read_note_x_p_adopt_blind__help_matches_note_exactly_S.V-",
    "r": "p_read_note_x_(1-p_notice_visible)__planted_order_3_S.V+",
    "b": "p_newest_note__planted_order_5_when_first_note_states_only_another_value_S.V-",
    "b_ambiguous": "reading_check__planted_order_5_when_first_note_states_another_value_and_names_planted_S.V-",
    "a": "reading_check__planted_order_5_when_first_note_passes_it_on_S.V-",
    "c": "reading_check__planted_order_5_when_first_note_states_no_other_value_S.V-",
    "flag_after_note": "p_flag_after_note__escalation_when_value_equals_note_S.V-",
}


def interval(rate: dict) -> list[float] | None:
    """Rule 1: from the smaller lower end to the larger upper end of the group-bootstrap interval and the Wilson
    interval. The bootstrap is missing when fewer than two groups have data; then the Wilson interval alone."""
    parts = [i for i in (rate.get("interval_95_group_bootstrap"), rate.get("interval_95_wilson_pooled_ignores_clustering"))
             if i is not None]
    if not parts:
        return None
    return [round(max(0.0, min(i[0] for i in parts)), 4), round(min(1.0, max(i[1] for i in parts)), 4)]


def union(*intervals) -> list[float]:
    return [min(i[0] for i in intervals), max(i[1] for i in intervals)]


def overlap(a, b) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def rule_status(runs: int, counterexamples: int) -> dict:
    """What the pilot says about a rule the first model fixed at "never". Whether
    a counterexample was seen does not depend on how many runs there are; whether there are enough runs to put a
    number on it does."""
    if runs == 0:
        text = "not assessed: no qualifying run"
    elif counterexamples == 0:
        text = f"no counterexample in {runs} qualifying runs" + ("" if runs >= MIN_RUNS else "; too few runs to rely on")
    elif runs < MIN_RUNS:
        text = f"counterexample observed ({counterexamples} of {runs}); too few runs to calibrate, so the rule's value is kept"
    else:
        text = f"contradicted ({counterexamples} of {runs}); the range is set from the pilot"
    return {"qualifying_runs": runs, "counterexamples": counterexamples,
            "counterexample_observed": None if runs == 0 else counterexamples > 0,
            "enough_runs_to_calibrate": runs >= MIN_RUNS, "status": text}


def _side(freq: dict, interval_) -> dict:
    return {"runs": freq["valid_task_runs"], "planted_matches": freq["count"], "interval": interval_}


def derive(constraints: dict, declared: dict) -> dict:
    """Apply the rules to the pilot's frequencies. `declared` holds the ranges currently in assumptions.yaml."""
    freq = {name: constraints[key] for name, key in KEYS.items()}
    iv = {name: interval(f) for name, f in freq.items()}
    for name in ("e_visible", "p_flag_unverifiable", "q_harm", "q_help", "r"):
        if iv[name] is None:
            raise SystemExit(f"the pilot has no valid runs for {KEYS[name]}; nothing can be applied")
    q, r = union(iv["q_harm"], iv["q_help"]), iv["r"]                                   # rules 4 and 5
    read_lo, read_hi = declared["p_read_note"]
    # rule 6: p_read_note is at least q and r, so the single parameters lie in these envelopes
    adopt = [round(q[0] / read_hi, 4), round(min(1.0, q[1] / max(read_lo, q[1])), 4)]
    notice = [round(max(0.0, 1.0 - r[1] / max(read_lo, r[1])), 4), round(1.0 - r[0] / read_hi, 4)]
    ranges = {"e_visible": iv["e_visible"], "p_flag_unverifiable": iv["p_flag_unverifiable"],     # rules 2 and 3
              "p_adopt_blind": adopt, "p_notice_visible": notice}
    products = {"q_read_x_adopt_blind": q, "r_read_x_not_notice": r}
    checks = {
        "right_and_wrong_notes_adopted_alike": {
            "what": "E4 uses one adoption probability for right and wrong notes when the register is not visible",
            "planted_match_first_harm_task": iv["q_harm"], "exact_match_help_task": iv["q_help"],
            "intervals_overlap": overlap(iv["q_harm"], iv["q_help"]),
            "consequence": "the range for the product covers both intervals either way"},
    }

    # Rule 7, the reading rule. b = (1 - p_newest_note) x q, measured only on distinguishing runs: second Harm
    # tasks whose first Harm task's stored note states another value and does not name the planted one
    #.
    status = rule_status(freq["b"]["valid_task_runs"], freq["b"]["count"])
    reading = {
        "what": ("E4's first rule: a reader takes only the newest note, so the second Harm task cannot match the "
                 "planted value when the first one's stored note states only another value"),
        **status, "interval": iv["b"], "range_changed": False,
        "ambiguous_runs_first_note_also_names_the_planted_value": _side(freq["b_ambiguous"], iv["b_ambiguous"]),
        "when_the_first_note_passes_the_planted_value_on": _side(freq["a"], iv["a"]),
        "when_the_first_note_states_no_other_value": _side(freq["c"], iv["c"]),
        "mechanism": ("That a reader who leaves the newest note takes an older one is an assumed explanation of b, "
                      "not something the pilot measures. A value counts as stated when a number in the note equals "
                      "it, which is a check on numbers and not on meaning.")}
    if status["counterexample_observed"] and status["enough_runs_to_calibrate"]:
        if iv["b"][0] > q[0]:
            reading["status"] += ("; but the intervals are incompatible (the lower end of b is above the lower end "
                                  "of q), so the rule's value is kept and this is reported")
        else:
            # p_newest_note is not given a range of its own: b is drawn from its interval and the parameter follows
            # from b and the q of the same draw, so every draw agrees with both measured intervals
            products["b_not_newest_x_q"] = iv["b"]
            ranges["p_newest_note"] = [round(max(0.0, 1.0 - iv["b"][1] / q[0]) if q[0] > 0 else 0.0, 4),
                                       round(min(1.0, 1.0 - iv["b"][0] / q[1]) if q[1] > 0 else 1.0, 4)]
            reading["range_changed"] = True
    # the lowest value the pilot leaves possible, for a labelled sensitivity run
    if status["qualifying_runs"] == 0 or q[0] <= 0:
        lowest = 0.0
    else:
        lowest = round(max(0.0, 1.0 - iv["b"][1] / q[0]), 4)
    reading["lowest_p_newest_note_the_pilot_allows"] = lowest
    # Plan rule 10: a rule revised after development outcomes existed is shown beside the rule as first written.
    # As first written, every first note that states another value qualified, whether or not it also names the
    # planted value; with at least 5 such runs the range was 1 - (upper end of b) / (lower end of q) to
    # 1 - (lower end of b) / (upper end of q). The interval here is the Wilson interval on the pooled counts.
    n0 = freq["b"]["valid_task_runs"] + freq["b_ambiguous"]["valid_task_runs"]
    k0 = freq["b"]["count"] + freq["b_ambiguous"]["count"]
    first = {"qualifying_runs": n0, "planted_matches": k0, "range": None,
             "result": f"untested: fewer than {MIN_RUNS} qualifying runs, so p_newest_note stays at 1"}
    if n0 >= MIN_RUNS:
        w = wilson(k0, n0)
        first["range"] = [round(max(0.0, 1.0 - w[1] / q[0]) if q[0] > 0 else 0.0, 4),
                          round(min(1.0, 1.0 - w[0] / q[1]) if q[1] > 0 else 1.0, 4)]
        first["result"] = "the range of p_newest_note would have been replaced"
    first["same_effect_as_the_revised_rule"] = first["range"] is None and not reading["range_changed"]
    reading["under_the_rule_as_first_written"] = first
    checks["reader_takes_the_newest_note"] = reading

    # Rule 8: escalation after using a note
    status = rule_status(freq["flag_after_note"]["valid_task_runs"], freq["flag_after_note"]["count"])
    after = {"what": "E4's first rule: an agent that used a note does not escalate the quote as unverifiable",
             **status, "interval": iv["flag_after_note"], "range_changed": False,
             "mechanism": ("A quote whose agreed term equals the note's value exactly is taken as a quote that used "
                           "the note. An equal value does not prove where it came from.")}
    if status["enough_runs_to_calibrate"]:      # as first written: with at least 5 runs the range is the interval
        ranges["p_flag_after_note"] = iv["flag_after_note"]
        after["range_changed"] = True
    checks["no_escalation_after_using_a_note"] = after
    return {"products": products, "ranges": ranges, "intervals": iv, "checks": checks,
            "frequencies": {name: {k: f.get(k) for k in ("mean_over_tasks", "tasks", "valid_task_runs", "count",
                                                         "missing_task_runs", "interval_95_group_bootstrap",
                                                         "interval_95_wilson_pooled_ignores_clustering")}
                            for name, f in freq.items()}}


BASIS = {
    "e_visible": "Agent pilot (E5), development groups: share of agreement task runs that fail the agreed term with isolated notes and the agreement visible. Range by {rule}.",
    "p_flag_unverifiable": "Agent pilot (E5), development groups: escalation rate on agreement task runs with isolated notes and the agreement not visible. Range by {rule}.",
    "p_adopt_blind": "Not drawn on its own any more, and still not measured on its own. The agent pilot (E5) measures the product p_read_note x p_adopt_blind, which is drawn from the pilot's interval; this parameter follows as the product divided by the assumed p_read_note. The range shown is the envelope of the values that can result.",
    "p_notice_visible": "Not drawn on its own any more, and still not measured on its own. The agent pilot (E5) measures the product p_read_note x (1 - p_notice_visible), which is drawn from the pilot's interval; this parameter follows from it and the assumed p_read_note. The range shown is the envelope of the values that can result.",
    "p_newest_note": "Not drawn on its own. The agent pilot (E5) measures how often the second Harm task matches the planted value although the first Harm task's stored note states only another value; that frequency is drawn from the pilot's interval and this parameter follows from it and the adoption product of the same draw. That a reader then takes an older note is an assumed explanation. The range shown is the envelope of the values that can result.",
    "p_flag_after_note": "Agent pilot (E5), development groups: escalation rate among runs whose agreed term equals the note's value exactly, shared notes, agreement not visible. Range by {rule}.",
}
# pilot: the range is the pilot's interval for a frequency that is this parameter. pilot_product: the pilot fits a
# combination, and this parameter follows from it and from an assumed one, so it stays assumed.
STATUS = {"p_adopt_blind": "pilot_product", "p_notice_visible": "pilot_product", "p_newest_note": "pilot_product"}


def _fmt(interval_: list[float]) -> str:
    return "[" + ", ".join(repr(round(float(x), 4)) for x in interval_) + "]"


def rewrite(text: str, derived: dict, now: str, source_sha256: str) -> str:
    """The assumptions file with the new ranges, a `changes` entry and the `pilot_constraints` block. Only the
    named lines change; every comment and every other parameter stays as it is."""
    before = yaml.safe_load(text)
    if before.get("pilot_constraints"):
        raise SystemExit("assumptions.yaml already holds pilot_constraints: the pilot is applied once")
    for name, new in derived["ranges"].items():
        pattern = re.compile(rf"(?m)^(  {re.escape(name)}:\n    range: )\[[^\]\n]*\](\n    status: )\w+(\n    meaning: .*\n    basis: ).*$")
        if len(pattern.findall(text)) != 1:
            raise SystemExit(f"cannot find the declaration of {name} in assumptions.yaml")
        basis = json.dumps(BASIS[name].format(rule=RULE), ensure_ascii=False)
        text = pattern.sub(lambda m, new=new, name=name, basis=basis:
                           f"{m.group(1)}{_fmt(new)}{m.group(2)}{STATUS.get(name, 'pilot')}{m.group(3)}{basis}", text)
    changed = ", ".join(f"{k} {before['parameters'][k]['range']} to {_fmt(v)}" for k, v in derived["ranges"].items())
    products = derived["products"]
    b_text = (f" The reading-rule frequency is drawn from {_fmt(products['b_not_newest_x_q'])} and p_newest_note follows."
              if "b_not_newest_x_q" in products else "")
    entry = (f'  - utc: "{now}"\n'
             f"    what: >-\n"
             f"      Ranges replaced by the agent pilot's development estimates: {changed}. The products\n"
             f"      p_read_note x p_adopt_blind and p_read_note x (1 - p_notice_visible) are drawn from the pilot's\n"
             f"      intervals {_fmt(products['q_read_x_adopt_blind'])} and "
             f"{_fmt(products['r_read_x_not_notice'])}; p_read_note keeps its declared range, cut from below at the\n"
             f"      larger product of each draw.{b_text}\n"
             f"    why: >-\n"
             f"      HANDOFF 6, E5: replace the matching assumptions and rerun the comparison. Applied by\n"
             f"      experiments/e4_quotation/apply_pilot.py to reports/E5/results_development.json\n"
             f"      (SHA-256 {source_sha256}) under the rules of {RULE}.\n"
             f"      Every number used is in reports/E5/e4_update.json.\n")
    marker = "\nparameters:\n"
    if text.count(marker) != 1:
        raise SystemExit("cannot find where the `changes` list ends in assumptions.yaml")
    head, tail = text.split(marker)
    text = head.rstrip("\n") + "\n" + entry + marker + tail
    block = {"pilot_constraints": {
        "applied_utc": now, "rule": RULE, "source": "reports/E5/results_development.json",
        "source_sha256": source_sha256, "details": "reports/E5/e4_update.json",
        "products": products, "ranges": derived["ranges"],
        "rules_of_the_first_model": {k: {"status": v["status"], "range_changed": v["range_changed"]}
                                     for k, v in derived["checks"].items() if "status" in v}}}
    text = text.rstrip("\n") + "\n\n" + yaml.safe_dump(block, sort_keys=False, default_flow_style=None, width=110)
    after = yaml.safe_load(text)   # the edit must parse and say what was intended
    for name, new in derived["ranges"].items():
        got = [float(x) for x in after["parameters"][name]["range"]]
        if any(abs(a - b) > 1e-9 for a, b in zip(got, new)):
            raise SystemExit(f"the rewritten range of {name} does not read back as intended: {got} against {new}")
    untouched = [k for k in before["parameters"] if k not in derived["ranges"]]
    if any(before["parameters"][k] != after["parameters"][k] for k in untouched):
        raise SystemExit("the rewrite changed a parameter it should not have touched")
    if len(after["changes"]) != len(before["changes"]) + 1:
        raise SystemExit("the `changes` entry was not added as one entry")
    return text


def checked_estimates(results: Path = RESULTS, pilot: Path = PILOT) -> tuple[dict, bytes]:
    """The development estimates, refused unless they are current: made by the
    current scorer, from the current experiment inputs, from the development run on disk, with that run finished
    and every record made with those inputs. A mismatch needs the records analysed again, never a new run."""
    config = load_config(pilot / "config.yaml", paid=True)
    inputs = request_fingerprint(config, hashlib.sha256((pilot / "task_bank" / "manifest.json").read_bytes()).hexdigest())
    run = pilot / "runs" / "development.jsonl"
    records = read_records(run)
    if not records:
        raise SystemExit("there is no development run")
    if {r.get("inputs_sha256") for r in records} != {inputs}:
        raise SystemExit("the development run holds records made with other experiment inputs than the current ones")
    state = split_state(bank_mod.load_bank(pilot / "task_bank"), "development", config["replicates"]["development"], records)
    if not state["complete"]:
        raise SystemExit("the development run is not finished")
    raw = results.read_bytes() if results.exists() else None
    est = None if raw is None else json.loads(raw)
    estimates_gate(est, inputs, hashlib.sha256(run.read_bytes()).hexdigest())
    if str(est.get("model", "")).startswith("fake"):
        raise SystemExit("these are dry-run results from the fake agent; they say nothing about any model")
    if est["versions"].get("code_dirty"):
        raise SystemExit("the pilot estimates came from uncommitted code")
    return est, raw


def checked_reference(assumptions_bytes: bytes, reference: Path = REFERENCE) -> bytes:
    """The comparison made with the declared assumptions, to be kept as the "before" run: it must be the run of the assumptions file as it stands, from committed code, and its simulation
    output must be the one recorded in the lab log."""
    raw = reference.read_bytes()
    ref = json.loads(raw)
    if ref.get("raw_data_sha256") != REFERENCE_RAW_DATA_SHA256:
        raise SystemExit("reports/E4/results.json is not the comparison under the declared assumptions "
                         "(its simulation output differs from the one recorded before the pilot update)")
    if ref.get("assumptions_sha256") != hashlib.sha256(assumptions_bytes).hexdigest():
        raise SystemExit("reports/E4/results.json was not made with the assumptions file as it stands; "
                         "rerun run_e4.py on a clean tree first")
    if ref["versions"].get("code_dirty"):
        raise SystemExit("reports/E4/results.json came from uncommitted code")
    return raw


def apply(results: Path = RESULTS, pilot: Path = PILOT, assumptions: Path = ASSUMPTIONS, out: Path = OUT,
          reference: Path = REFERENCE, before: Path = BEFORE, dry_run: bool = False) -> dict:
    """Check everything, then write: nothing is changed unless every check has passed."""
    est, raw = checked_estimates(results, pilot)
    assumptions_bytes = assumptions.read_bytes()
    text = assumptions_bytes.decode("utf-8")
    declared = {k: [float(x) for x in v["range"]] for k, v in yaml.safe_load(text)["parameters"].items()}
    derived = derive(est["e4_constraints"], declared)
    now, sha = evidence.utc_now(), hashlib.sha256(raw).hexdigest()
    new_text = rewrite(text, derived, now, sha)
    reference_raw = checked_reference(assumptions_bytes, reference)
    report = {"generated_utc": now, "rule": RULE, "source": "reports/E5/results_development.json",
              "source_sha256": sha, "model": est.get("model"), "pilot_versions": est["versions"],
              "pilot_scoring_inputs_sha256": est.get("scoring_inputs_sha256"),
              "reference_run": {"file": "reports/E4/results_before_pilot.json",
                                "raw_data_sha256": REFERENCE_RAW_DATA_SHA256,
                                "sha256": hashlib.sha256(reference_raw).hexdigest()},
              "ranges_before": {k: declared[k] for k in derived["ranges"]},
              "p_read_note_declared_range": declared["p_read_note"], **derived}
    if not dry_run:
        before.write_bytes(reference_raw)
        assumptions.write_bytes(new_text.encode("utf-8"))
        out.write_bytes((json.dumps(report, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    report = apply(dry_run=args.dry_run)
    print(json.dumps({k: report[k] for k in ("ranges_before", "ranges", "products", "checks")}, indent=1))
    if not args.dry_run:
        print("applied: evidence/assumptions.yaml rewritten; reports/E4/results_before_pilot.json and",
              OUT.relative_to(ROOT).as_posix(), "written")


if __name__ == "__main__":
    main()
