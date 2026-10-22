"""Compare two development runs of the quotation model: which comparisons changed.

    .venv/Scripts/python.exe experiments/e4_quotation/compare_runs.py

Reads reports/E4/results_before_pilot.json (the run with the declared assumptions, kept by apply_pilot.py when it
applies the pilot) and reports/E4/results.json (the run after the agent pilot's estimates were put in), and writes
reports/E4/pilot_update_comparison.json. It refuses a "before" run whose simulation output is not the one recorded
for the declared assumptions.

A comparison "holds" when its sign is the same in at least 95% of parameter draws (robust_sign +1 or -1) and
"depends on the assumptions" otherwise (0). A change is any comparison whose robust sign differs between the two
runs. Mean differences that move while the sign stays are listed for the main measures, as sizes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports" / "E4"
# the simulation output of the comparison under the declared assumptions
REFERENCE_RAW_DATA_SHA256 = "20e14ccf26076f48b889d3019c8c172bdac96f427fb5e5cca60aea77c51d60f7"
MAIN_MEASURES = ("wrong_terms", "days_mean", "total_reviews", "inconsistent_customers", "repeat_all_wrong")
HEADLINE = [f"full|{d}|{c}|draft" for d in ("review", "limits", "local") for c in ("isolated", "shared")]


def row_id(r: dict) -> str:
    return f"{r['family']}||{r['a']}||{r['b']}||{r['measure']}"


def share(r: dict) -> float:
    """The share of draws on the side the comparison leans to."""
    return max(r["share_draws_a_higher"], r["share_draws_a_lower"])


def compare(before: dict, after: dict) -> dict:
    b = {row_id(r): r for r in before["comparisons_pooled"]}
    a = {row_id(r): r for r in after["comparisons_pooled"]}
    if set(a) != set(b):
        raise SystemExit("the two runs do not hold the same comparisons")
    rows, changed = [], []
    for key in sorted(b):
        rb, ra = b[key], a[key]
        row = {"family": rb["family"], "a": rb["a"], "b": rb["b"], "measure": rb["measure"],
               "robust_sign_before": rb["robust_sign"], "robust_sign_after": ra["robust_sign"],
               "share_a_higher_before": rb["share_draws_a_higher"], "share_a_higher_after": ra["share_draws_a_higher"],
               "share_a_lower_before": rb["share_draws_a_lower"], "share_a_lower_after": ra["share_draws_a_lower"],
               "mean_diff_before": rb["mean_diff"], "mean_diff_after": ra["mean_diff"]}
        rows.append(row)
        if rb["robust_sign"] != ra["robust_sign"]:
            kind = ("reversed" if rb["robust_sign"] * ra["robust_sign"] == -1 else
                    "no longer holds" if ra["robust_sign"] == 0 else "now holds")
            changed.append({**row, "change": kind})
    summary = {}
    for label in HEADLINE:
        summary[label] = {m: {"before": before["summary_pooled"][label][m], "after": after["summary_pooled"][label][m]}
                          for m in MAIN_MEASURES}
    by_family = {}
    for r in rows:
        f = by_family.setdefault(r["family"], {"comparisons": 0, "changed": 0, "hold_before": 0, "hold_after": 0})
        f["comparisons"] += 1
        f["changed"] += int(r["robust_sign_before"] != r["robust_sign_after"])
        f["hold_before"] += int(r["robust_sign_before"] != 0)
        f["hold_after"] += int(r["robust_sign_after"] != 0)
    return {"before": {"versions": before["versions"], "assumptions_sha256": before["assumptions_sha256"],
                       "raw_data_sha256": before["raw_data_sha256"], "finished_utc": before["finished_utc"]},
            "after": {"versions": after["versions"], "assumptions_sha256": after["assumptions_sha256"],
                      "raw_data_sha256": after["raw_data_sha256"], "finished_utc": after["finished_utc"]},
            "comparisons": len(rows), "changed": changed, "by_family": by_family,
            "headline_measures": summary, "all_comparisons": rows}


def main() -> None:
    before = json.loads((OUT / "results_before_pilot.json").read_text(encoding="utf-8"))
    after = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    if before["raw_data_sha256"] != REFERENCE_RAW_DATA_SHA256:
        raise SystemExit("results_before_pilot.json is not the comparison under the declared assumptions")
    if before["assumptions_sha256"] == after["assumptions_sha256"]:
        raise SystemExit("both runs used the same assumptions; apply the pilot and rerun the comparison first")
    result = compare(before, after)
    (OUT / "pilot_update_comparison.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
    print(json.dumps({"comparisons": result["comparisons"], "changed": len(result["changed"]),
                      "by_family": result["by_family"]}, indent=1))
    for c in result["changed"]:
        print(f"  {c['change']}: {c['a']} against {c['b']} on {c['measure']} "
              f"(sign {c['robust_sign_before']} to {c['robust_sign_after']})")


if __name__ == "__main__":
    main()
