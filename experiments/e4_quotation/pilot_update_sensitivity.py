"""Two descriptions that go with the quotation model's comparison after the agent pilot.

    .venv/Scripts/python.exe experiments/e4_quotation/pilot_update_sensitivity.py

1. **One rule at a time**. The update changes several ranges at once, so a comparison that changes
   cannot be traced to one of them. Here the comparison is run once per changed rule, with every other range as
   declared, and each run is compared with the run under the declared assumptions.
   Output: reports/E4/pilot_update_attribution.json.
2. **The reading rule at the lowest value the pilot allows**. When the pilot does not contradict
   "a reader takes the newest note", p_newest_note stays at 1 in the main comparison. Here the comparison is run
   once with p_newest_note at the lowest value the pilot leaves possible, and compared with the main comparison
   after the pilot. Output: reports/E4/reading_rule_sensitivity.json.

Both are labelled sensitivity runs: they describe, and no conclusion is frozen from them.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare_runs  # noqa: E402
import run_e4  # noqa: E402
from gca_sim import evidence  # noqa: E402
from gca_sim.simulator import params  # noqa: E402

OUT = ROOT / "reports" / "E4"
UPDATE = ROOT / "reports" / "E5" / "e4_update.json"
SEED = 20261002
# each rule of plan section 9.1 that can change the model, and the parameters whose declared range it replaces
RULES = {
    "rule 2: e_visible": ("e_visible",),
    "rule 3: p_flag_unverifiable": ("p_flag_unverifiable",),
    "rules 4 to 6: the two note products": ("p_adopt_blind", "p_notice_visible"),
    "rule 7: the reading rule": ("p_newest_note",),
    "rule 8: escalation after using a note": ("p_flag_after_note",),
}
PRODUCT_KEYS = {"rules 4 to 6: the two note products": ("q_read_x_adopt_blind", "r_read_x_not_notice"),
                "rule 7: the reading rule": ("b_not_newest_x_q",)}


def declared_assumptions(current: dict, update: dict) -> dict:
    """The assumptions as they were before the pilot: the changed ranges put back, and no constraints."""
    a = copy.deepcopy(current)
    a.pop("pilot_constraints", None)
    for name, rng in update["ranges_before"].items():
        a["parameters"][name]["range"] = list(rng)
    return a


def one_rule(current: dict, update: dict, rule: str) -> dict | None:
    """The declared assumptions with one rule's change applied, or None if that rule changed nothing."""
    names = [n for n in RULES[rule] if n in update["ranges"]]
    if not names:
        return None
    a = declared_assumptions(current, update)
    for name in names:
        a["parameters"][name]["range"] = list(update["ranges"][name])
    products = {k: update["products"][k] for k in PRODUCT_KEYS.get(rule, ()) if k in update["products"]}
    if rule == "rule 7: the reading rule" and products:
        # b is defined against q, so the reading rule cannot be applied without the adoption product
        products["q_read_x_adopt_blind"] = update["products"]["q_read_x_adopt_blind"]
        products["r_read_x_not_notice"] = update["products"]["r_read_x_not_notice"]
        for name in ("p_adopt_blind", "p_notice_visible"):
            a["parameters"][name]["range"] = list(update["ranges"][name])
    if products:
        a["pilot_constraints"] = {"products": products}
    return a


def comparison(draws, cases, seeds, workers: int, label: str) -> dict:
    """One development comparison, in the shape compare_runs.compare reads."""
    data = run_e4.run(cases, draws, seeds, workers)
    idx = list(range(len(cases)))
    return {"comparisons_pooled": run_e4.comparisons(data, idx, draws), "summary_pooled": run_e4.summarise(data, idx),
            "versions": evidence.git_state(run_e4.GUARDED_PATHS), "assumptions_sha256": label,
            "raw_data_sha256": evidence.array_sha256(data), "finished_utc": evidence.utc_now()}


def brief(result: dict) -> dict:
    return {"comparisons": result["comparisons"], "changed": result["changed"], "by_family": result["by_family"],
            "headline_measures": result["headline_measures"], "run": result["after"]}


def main(workers: int = 16) -> None:
    current = params.load_assumptions()
    if not current.get("pilot_constraints"):
        raise SystemExit("the pilot has not been applied to evidence/assumptions.yaml")
    update = json.loads(UPDATE.read_text(encoding="utf-8"))
    before = json.loads((OUT / "results_before_pilot.json").read_text(encoding="utf-8"))
    if before["raw_data_sha256"] != compare_runs.REFERENCE_RAW_DATA_SHA256:
        raise SystemExit("results_before_pilot.json is not the comparison under the declared assumptions")
    after = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    assumptions_now = hashlib.sha256((ROOT / "evidence" / "assumptions.yaml").read_bytes()).hexdigest()
    if after["assumptions_sha256"] != assumptions_now:
        raise SystemExit("reports/E4/results.json was not made with the assumptions file as it stands")
    cases = run_e4.load_cases("development")
    seeds = list(range(current["sampling"]["seeds_per_draw"]))
    n = current["sampling"]["parameter_draws"]

    # the declared assumptions rebuilt from the update record must reproduce the reference run exactly
    declared = declared_assumptions(current, update)
    check = comparison(params.latin_hypercube(n, SEED, declared), cases, seeds, workers, "declared, rebuilt")
    if check["raw_data_sha256"] != compare_runs.REFERENCE_RAW_DATA_SHA256:
        raise SystemExit("the declared assumptions rebuilt from e4_update.json do not reproduce the reference run")

    attribution = {"generated_utc": evidence.utc_now(), "label": "sensitivity runs; a description only",
                   "reference": "reports/E4/results_before_pilot.json", "rules": {}}
    for rule in RULES:
        variant = one_rule(current, update, rule)
        if variant is None:
            attribution["rules"][rule] = {"applied": False, "reason": "this rule left its range as declared"}
            continue
        result = comparison(params.latin_hypercube(n, SEED, variant), cases, seeds, workers, rule)
        attribution["rules"][rule] = {"applied": True, **brief(compare_runs.compare(before, result))}
        print(rule, "->", len(attribution["rules"][rule]["changed"]), "comparisons change", flush=True)
    (OUT / "pilot_update_attribution.json").write_bytes((json.dumps(attribution, indent=1) + "\n").encode("utf-8"))

    reading = update["checks"]["reader_takes_the_newest_note"]
    lowest = reading["lowest_p_newest_note_the_pilot_allows"]
    out = {"generated_utc": evidence.utc_now(), "label": "sensitivity run; a description only",
           "reference": "reports/E4/results.json (the comparison after the pilot)",
           "pilot_status_of_the_rule": reading["status"], "main_run_changed_the_rule": reading["range_changed"],
           "p_newest_note_in_this_run": lowest}
    if reading["range_changed"]:
        out["note"] = ("the main comparison already draws p_newest_note from the pilot's constraint; this run fixes "
                       "it at the lowest value that constraint allows")
    draws = [replace(p, p_newest_note=lowest) for p in params.latin_hypercube(n, SEED, current)]
    result = comparison(draws, cases, seeds, workers, f"after the pilot, p_newest_note = {lowest}")
    out.update(brief(compare_runs.compare(after, result)))
    (OUT / "reading_rule_sensitivity.json").write_bytes((json.dumps(out, indent=1) + "\n").encode("utf-8"))
    print("reading rule at", lowest, "->", len(out["changed"]), "comparisons change")


if __name__ == "__main__":
    main()
