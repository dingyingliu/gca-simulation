"""Flip points for the E4 design conclusions that hold across the declared ranges.

For each such conclusion (main configuration: isolated notes, notes record drafted terms) and each of its two
top drivers (by Spearman correlation across parameter draws), sweep the driver across its whole logical domain
(probabilities 0 to 1, times 0 to 3 working days) with every other parameter at its central value, and find
where the sign of the difference reverses. Development weeks pooled, 64 seeds.

    .venv/Scripts/python.exe experiments/e4_quotation/flip_points.py
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402
from gca_sim.simulator import designs, engine, params, random_streams as streams, ground_truth as truth  # noqa: E402

OUT = ROOT / "reports" / "E4" / "flip_points.json"
CASES_DIR = ROOT / "specs" / "simulated_weeks"
TIME_PARAMS = {"effort_lead", "delay_lead", "effort_ho", "delay_ho", "sigma_review"}
GRID = 21
SEEDS = list(range(64))


def domain(name: str) -> tuple[float, float]:
    return (0.0, 3.0) if name in TIME_PARAMS else (0.0, 1.0)


def sweep_plan(driver: str, assumptions: dict) -> dict:
    """What is swept for a driver, and the interval a flip is judged against.

    Ordinarily the driver itself, over its whole domain, judged against its declared range. Once the agent pilot
    has been applied, the note parameters are tied together: the pilot fixes intervals for the products
    q = p_read_note x p_adopt_blind and r = p_read_note x (1 - p_notice_visible), and the single parameters follow.
    Sweeping one of them alone would move a product outside the pilot's interval and could still read "inside the
    declared range". So for those drivers the product is swept, with p_read_note at its central value and the
    single parameter following, and a flip is judged against the pilot's interval for the product; p_read_note is
    swept with both products held at their central values."""
    ranges = params.ranges(assumptions)
    c = params.product_constraints(assumptions)
    central = params.central(assumptions)
    plain = {"quantity": driver, "domain": domain(driver), "judged_against": list(ranges[driver]),
             "replace": lambda v: {driver: v}}
    if c is None or driver not in (*params.PRODUCT_PARAMS, "p_newest_note"):
        return plain
    read = central.p_read_note
    q_mid, r_mid = sum(c["q"]) / 2, sum(c["r"]) / 2
    # The product is swept over 0 to 1, so the whole of the pilot's interval is covered. p_read_note is its central
    # value where that allows the product and otherwise the product itself, since it cannot be smaller; the other
    # product keeps its central value.
    if driver == "p_adopt_blind":
        return {"quantity": "p_read_note x p_adopt_blind, with p_read_note at the larger of its central value and "
                            "the product", "domain": (0.0, 1.0), "judged_against": list(c["q"]),
                "replace": lambda v: {"p_read_note": max(read, v), "p_adopt_blind": min(1.0, v / max(read, v)),
                                      "p_notice_visible": max(0.0, 1.0 - r_mid / max(read, v))}}
    if driver == "p_notice_visible":
        return {"quantity": "p_read_note x (1 - p_notice_visible), with p_read_note at the larger of its central "
                            "value and the product", "domain": (0.0, 1.0), "judged_against": list(c["r"]),
                "replace": lambda v: {"p_read_note": max(read, v), "p_notice_visible": 1.0 - v / max(read, v),
                                      "p_adopt_blind": min(1.0, q_mid / max(read, v))}}
    if driver == "p_read_note":
        floor = max(ranges["p_read_note"][0], q_mid, r_mid)
        return {"quantity": "p_read_note, with both products at their central values",
                "domain": (max(q_mid, r_mid, 1e-6), 1.0), "judged_against": [floor, ranges["p_read_note"][1]],
                "replace": lambda v: {"p_read_note": v, "p_adopt_blind": min(1.0, q_mid / v),
                                      "p_notice_visible": max(0.0, 1.0 - r_mid / v)}}
    if "b" not in c:   # p_newest_note is still a plain parameter
        return plain
    return {"quantity": "(1 - p_newest_note) x p_read_note x p_adopt_blind", "domain": (0.0, q_mid),
            "judged_against": list(c["b"]), "replace": lambda v: {"p_newest_note": 1.0 - v / q_mid if q_mid > 0 else 1.0}}


def measure_value(meas: dict, name: str) -> float:
    if name == "total_reviews":
        return meas["lead_reviews"] + meas["ho_reviews"]
    return meas[name]


def sweep_point(task) -> tuple:
    key, a, b, measure, driver, value, replacements = task
    cases = [truth.Case.from_json((CASES_DIR / f).read_text(encoding="utf-8"))
             for f in ("W0.json", "G1.json", "G2.json", "G3.json", "G4.json")]
    p = replace(params.central(), **replacements)
    diffs = []
    for case in cases:
        ents = streams.case_entities(case)
        for seed in SEEDS:
            s = streams.Streams(seed, ents)
            ra = engine.simulate(case, designs.DESIGNS[a], "isolated", p, s)
            rb = engine.simulate(case, designs.DESIGNS[b], "isolated", p, s)
            diffs.append(measure_value(ra.measures, measure) - measure_value(rb.measures, measure))
    return key, driver, value, float(np.mean(diffs))


def main() -> None:
    results = json.loads((ROOT / "reports" / "E4" / "results.json").read_text(encoding="utf-8"))
    assumptions = params.load_assumptions()
    plans = {}
    conclusions = [c for c in results["comparisons_pooled"]
                   if c["family"] == "design" and c["context"] == "isolated" and c["notes"] == "draft"
                   and c["robust_sign"] != 0]
    tasks = []
    meta = {}
    for c in conclusions:
        a, b = c["a"].split("|")[1], c["b"].split("|")[1]
        key = f"{a} vs {b}: {c['measure']}"
        drivers = [d for d, _ in c["top_drivers"][:2]]
        meta[key] = {"a": a, "b": b, "measure": c["measure"], "direction": c["robust_sign"],
                     "mean_diff": c["mean_diff"], "drivers": c["top_drivers"][:2]}
        for d in drivers:
            plan = plans.setdefault(d, sweep_plan(d, assumptions))
            lo, hi = plan["domain"]
            for v in np.linspace(lo, hi, GRID):
                tasks.append((key, a, b, c["measure"], d, float(v), plan["replace"](float(v))))
    with ProcessPoolExecutor(max_workers=16) as ex:
        points = list(ex.map(sweep_point, tasks))
    out = {"generated_utc": evidence.utc_now(),
           "versions": evidence.git_state(["gca_sim/simulator", "experiments/e4_quotation", "evidence/assumptions.yaml",
                                           "specs/simulated_weeks"]),
           "method": "one driver at a time, others at central values, development weeks pooled, 64 seeds, "
                     f"{GRID}-point grid over the driver's whole domain. For a note parameter tied to a product "
                     "the agent pilot measured, the product is swept and judged against the pilot's interval.",
           "conclusions": {}}
    for key, m in meta.items():
        entry = {**m, "sweeps": {}}
        for d, _ in m["drivers"]:
            curve = sorted((v, diff) for k, dd, v, diff in points if k == key and dd == d)
            lo_r, hi_r = plans[d]["judged_against"]
            flips = []
            for (v0, f0), (v1, f1) in zip(curve, curve[1:]):
                if f0 == 0 or f0 * f1 < 0:
                    x = v0 if f0 == 0 else v0 + (v1 - v0) * (f0 / (f0 - f1))
                    flips.append({"value": round(x, 3), "inside_declared_range": lo_r <= x <= hi_r})
            entry["sweeps"][d] = {"swept_quantity": plans[d]["quantity"], "swept_domain": list(plans[d]["domain"]),
                                  "declared_range": [lo_r, hi_r],
                                  "curve": [[round(v, 3), round(f, 4)] for v, f in curve],
                                  "flip_points": flips,
                                  "summary": ("no flip anywhere on the domain" if not flips else
                                              "; ".join(f"flips at {f['value']} "
                                                        f"({'inside' if f['inside_declared_range'] else 'outside'} "
                                                        f"the declared range)" for f in flips))}
        out["conclusions"][key] = entry
        print(key, {d: s["summary"] for d, s in entry["sweeps"].items()}, flush=True)
    OUT.write_bytes((json.dumps(out, indent=1) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
