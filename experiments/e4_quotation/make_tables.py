"""Markdown tables of the quotation model's development comparison, before and after the agent pilot's estimates
went in, written from the result files so that no number in a report is copied by hand.

    .venv/Scripts/python.exe experiments/e4_quotation/make_tables.py     # reports/E4/tables_pilot_update.md

Reads reports/E4/results_before_pilot.json, reports/E4/results.json and, when present,
reports/E4/pilot_update_comparison.json and reports/E4/results_heldout.json. It computes nothing new.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "E4"
DESIGNS = (("review", "Review every quote"), ("limits", "Release within shared limits"), ("local", "Refer local exceptions"))
NAME = dict(DESIGNS)


def table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def cell(s: dict, digits: int = 2) -> str:
    return f"{s['mean']:.{digits}f} ({s['param_p05']:.{digits}f} to {s['param_p95']:.{digits}f}; run SD {s['run_sd']:.{digits}f})"


def label(config: str) -> str:
    model, d, c, n = config.split("|")
    extra = {"full": "", "baseline": ", independent errors", "bypass3": ", bypass after 3 days", "nogate": ", gate off"}[model]
    return f"{NAME[d]}, {c} notes, notes record {n} terms{extra}"


def headline(r: dict, context: str = "isolated", notes: str = "draft") -> str:
    s = r["summary_pooled"]
    rows = []
    for key, name, digits in (("wrong_terms", "Quotes with wrong terms reaching customers (of 20)", 2),
                              ("days_mean", "Average days to customer", 2),
                              ("lead_reviews", "Reviews by regional leads", 1), ("ho_reviews", "Reviews by head office", 1),
                              ("lead_util_max", "Busiest lead's review effort, share of the week", 2),
                              ("inconsistent_customers", "Customers with inconsistent terms across quotes", 2),
                              ("repeat_all_wrong", "Repeat customers with every quote wrong", 2),
                              ("errors_standard", "Wrong terms: standard quotes (11 a week)", 2),
                              ("errors_agreement", "Wrong terms: written agreements (5 a week)", 2),
                              ("errors_verbal", "Wrong terms: verbal promise (1 a week)", 2)):
        rows.append([name] + [cell(s[f"full|{d}|{context}|{notes}"][key], digits) for d, _ in DESIGNS])
    return table(["Measure, per week"] + [n for _, n in DESIGNS], rows)


def shared_minus_isolated(r: dict) -> str:
    rows = []
    for d, name in DESIGNS:
        row = [name]
        for n in ("draft", "released"):
            c = next(x for x in r["comparisons_pooled"] if x["family"] == "context" and x["measure"] == "wrong_terms"
                     and x["a"] == f"full|{d}|shared|{n}" and x["b"] == f"full|{d}|isolated|{n}")
            share = max(c["share_draws_a_higher"], c["share_draws_a_lower"])
            holds = "holds across ranges" if c["robust_sign"] else f"{100 * share:.0f}% of draws one way"
            row.append(f"{c['mean_diff']:+.3f} ({c['param_p05']:+.2f} to {c['param_p95']:+.2f}); {holds}")
        rows.append(row)
    return table(["Design", "Notes record drafted terms", "Notes record released terms"], rows)


def design_conclusions(r: dict, context: str = "isolated", notes: str = "draft") -> str:
    rows = []
    for c in r["comparisons_pooled"]:
        if c["family"] != "design" or c.get("context") != context or c.get("notes") != notes:
            continue
        a, b = c["a"].split("|")[1], c["b"].split("|")[1]
        verdict = {1: "holds: first is higher", -1: "holds: first is lower", 0: "depends on the assumptions"}[c["robust_sign"]]
        rows.append([f"{NAME[a]} against {NAME[b]}", c["measure"].replace("_", " "), f"{c['mean_diff']:+.2f}",
                     f"{100 * c['share_draws_a_higher']:.0f}%", f"{100 * c['share_draws_a_lower']:.0f}%", verdict,
                     str(len(c["reversals"]))])
    return table(["Comparison (first minus second)", "Measure", "Mean difference", "Draws first higher", "Draws first lower",
                  "Verdict (95% rule)", "Reversing draws listed"], rows)


def changes(comp: dict) -> str:
    if not comp["changed"]:
        return f"No comparison changed its verdict ({comp['comparisons']} comparisons)."
    rows = [[c["family"], label(c["a"]), label(c["b"]), c["measure"].replace("_", " "), c["change"],
             f"{100 * c['share_a_higher_before']:.0f}% / {100 * c['share_a_lower_before']:.0f}%",
             f"{100 * c['share_a_higher_after']:.0f}% / {100 * c['share_a_lower_after']:.0f}%",
             f"{c['mean_diff_before']:+.3f}", f"{c['mean_diff_after']:+.3f}"] for c in comp["changed"]]
    fam = table(["Family", "Comparisons", "Changed", "Held before", "Hold after"],
                [[k, v["comparisons"], v["changed"], v["hold_before"], v["hold_after"]] for k, v in comp["by_family"].items()])
    return (f"{len(comp['changed'])} of {comp['comparisons']} comparisons changed their verdict.\n\n" + fam + "\n\n"
            + table(["Family", "First", "Second", "Measure", "Change", "Draws higher / lower, before", "after",
                     "Mean difference before", "after"], rows))


def robustness(h: dict) -> str:
    c = h["robustness_check"]
    rows = [[m, v["n"], v["passed"], f"{100 * v['pass_fraction']:.0f}%", c["targets"].get(m, "reported only")]
            for m, v in c["by_measure"].items()]
    failed = [r for r in c["results"] if not r["passed"]]
    out = (f"Outcome: **{c['outcome']}**. {c.get('n_passed', 0)} of {c['n_conclusions']} frozen conclusions pass.\n\n"
           + table(["Measure", "Conclusions", "Passed", "Share", "Target (80%)"], rows))
    if failed:
        out += "\n\nConclusions that did not pass:\n\n" + table(
            ["First", "Second", "Measure", "Share of held-out draws with the frozen sign"],
            [[label(r["a"]), label(r["b"]), r["measure"].replace("_", " "),
              "missing" if r["heldout_share"] is None else f"{100 * r['heldout_share']:.0f}%"] for r in failed])
    return out


def main() -> None:
    after = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    parts = ["# Tables of the quotation model's comparison, before and after the agent pilot\n\nWritten by "
             "`experiments/e4_quotation/make_tables.py` from the result files in this folder. Every number is a model "
             "output. Before the pilot every parameter range is assumed. After it, the frequencies and "
             "products the pilot measured are fitted; the single parameters that only follow from a fitted product "
             "stay assumed under that constraint; and everything about human reviewers stays assumed."]
    before_path = OUT / "results_before_pilot.json"
    if before_path.exists():
        before = json.loads(before_path.read_text(encoding="utf-8"))
        parts.append(f"## Before the pilot (commit {before['versions']['code_commit']}, {before['finished_utc']})\n\n"
                     + headline(before) + "\n\n### Shared minus isolated notes, wrong terms per week\n\n"
                     + shared_minus_isolated(before) + "\n\n### Design comparisons, isolated notes, drafted terms\n\n"
                     + design_conclusions(before))
    parts.append(f"## After the pilot (commit {after['versions']['code_commit']}, {after['finished_utc']})\n\n"
                 + headline(after) + "\n\n### The same with shared notes\n\n" + headline(after, "shared")
                 + "\n\n### Shared minus isolated notes, wrong terms per week\n\n" + shared_minus_isolated(after)
                 + "\n\n### Design comparisons, isolated notes, drafted terms\n\n" + design_conclusions(after)
                 + "\n\n### Design comparisons, shared notes, drafted terms\n\n" + design_conclusions(after, "shared"))
    comp_path = OUT / "pilot_update_comparison.json"
    if comp_path.exists():
        parts.append("## Which comparisons changed\n\n" + changes(json.loads(comp_path.read_text(encoding="utf-8"))))
    held_path = OUT / "results_heldout.json"
    if held_path.exists():
        parts.append("## Robustness check on the held-out weeks\n\n"
                     + robustness(json.loads(held_path.read_text(encoding="utf-8"))))
    (OUT / "tables_pilot_update.md").write_bytes(("\n\n".join(parts) + "\n").encode("utf-8"))
    print("written reports/E4/tables_pilot_update.md")


if __name__ == "__main__":
    main()
