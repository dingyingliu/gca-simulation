"""Markdown tables of the pilot's estimates, written from the result files so that no number in a report is
copied by hand.

    .venv/Scripts/python.exe experiments/agent_pilot/make_tables.py            # reports/E5/tables.md
    .venv/Scripts/python.exe experiments/agent_pilot/make_tables.py --fake     # from a dry run, to runs/fake/analysis

It reads results_development.json, and heldout_diagnostic.json and e4_update.json when they exist. It computes
nothing new: every figure is a field of those files, formatted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ORDER = ("S.V-", "I.V-", "S.V+", "I.V+")
CELL = {"S.V-": "Shared notes, agreement not visible", "I.V-": "Isolated notes, agreement not visible",
        "S.V+": "Shared notes, agreement visible", "I.V+": "Isolated notes, agreement visible"}
ROLES = ("Harm", "Help", "Own", "Standard")
VALUES = (("true", "true term, exactly"), ("above_floor", "above the agreed floor"), ("planted", "planted wrong value"),
          ("standard", "standard term"), ("other_customer", "another customer's term"), ("none", "none of these"))


def pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.0f}%"


def _signed(x: float) -> str:
    return "0" if abs(100 * x) < 0.5 else f"{100 * x:+.0f}"


def points(x) -> str:
    return "n/a" if x is None else f"{_signed(x)} points"


def span(interval) -> str:
    return "n/a" if interval is None else f"{100 * interval[0]:.0f}% to {100 * interval[1]:.0f}%"


def span_points(interval) -> str:
    return "n/a" if interval is None or None in interval else f"{_signed(interval[0])} to {_signed(interval[1])}"


def rate_cell(r: dict) -> str:
    """share (count of valid runs; group-bootstrap interval)"""
    if r["mean_over_tasks"] is None:
        return f"n/a (0 valid runs, {r['missing_task_runs']} missing)"
    boot = f"; {span(r['interval_95_group_bootstrap'])}" if r["interval_95_group_bootstrap"] else ""
    return f"{pct(r['mean_over_tasks'])} ({r['count']} of {r['valid_task_runs']}{boot})"


def table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def development(est: dict) -> str:
    parts = []
    t = est["task_runs"]
    parts.append(f"Task runs: {t['planned']} planned, {t['valid']} valid, {t['missing']} missing. "
                 f"Model: {est['model']}. Generated {est['generated_utc']}, commit {est['versions']['code_commit']}.")
    parts.append("### Hosts and missing runs by condition\n\n" + table(
        ["Condition", "Answers by host", "Missing runs (Harm, Help, Own, Standard)"],
        [[CELL[c], ", ".join(f"{h}: {n}" for h, n in est["host_by_cell"][c].items()) or "none",
          ", ".join(str(est["missing_by_cell_and_role"][c][r]) for r in ROLES)] for c in ORDER]))

    rel = est["1_released_error_by_cell_and_role"]
    parts.append("### 1. Wrong terms released to the customer\n\n"
                 "Share of task runs (mean over tasks), with the count over valid runs and the 95% interval from the "
                 "bootstrap over groups.\n\n" + table(
                     ["Condition"] + [f"{r} tasks" for r in ROLES],
                     [[CELL[c]] + [rate_cell(rel[c][r]) for r in ROLES] for c in ORDER]))
    term = est["1_term_error_by_cell_and_role"]
    parts.append("### 1b. Wrong terms drafted, released or not\n\n" + table(
        ["Condition"] + [f"{r} tasks" for r in ROLES],
        [[CELL[c]] + [rate_cell(term[c][r]) for r in ROLES] for c in ORDER]))

    def contrast_rows(block: dict) -> list[list[str]]:
        rows = []
        for v, name in (("V-", "agreement not visible"), ("V+", "agreement visible")):
            c = block[v]
            rows.append([name, pct(c["S"]), pct(c["I"]), points(c["S_minus_I"]),
                         span_points(c["interval_95_group_bootstrap"]), str(c["matched_tasks"]),
                         str(c["missing_task_runs"]), span_points(c["S_minus_I_bounds_over_missing_runs"])])
        return rows

    head = ["", "Shared", "Isolated", "Shared minus isolated", "95% interval (group bootstrap), points",
            "Matched tasks", "Missing runs", "Bounds if missing runs had been valid, points"]
    parts.append("### 2. Harm tasks: released wrong terms, shared against isolated notes\n\n"
                 + table(head, contrast_rows(est["2_harm_released_error_S_minus_I"])))
    parts.append("### 3. Help tasks: the agreed term honoured, shared against isolated notes\n\n"
                 + table(head, contrast_rows(est["3_help_agreed_term_complied_S_minus_I"])))

    spill = est["4_spillover_S_minus_I"]
    parts.append("### 4. Spill-over on tasks with no note about the customer (shared minus isolated)\n\n" + table(
        ["Role", "Agreement", "Outcome", "Shared", "Isolated", "Difference", "95% interval, points"],
        [[role, "not visible" if v == "V-" else "visible", o.replace("_", " "), pct(spill[f"{role}|{v}|{o}"]["S"]),
          pct(spill[f"{role}|{v}|{o}"]["I"]), points(spill[f"{role}|{v}|{o}"]["S_minus_I"]),
          span_points(spill[f"{role}|{v}|{o}"]["interval_95_group_bootstrap"])]
         for role in ("Standard", "Own") for v in ("V-", "V+") for o in ("term_error", "escalated")]))

    esc = est["5_escalation"]
    parts.append("### 5. Escalation to a person\n\n" + table(
        ["Condition", "Agreed terms cited, not in the register", "Nothing to verify, or the agreement is visible"],
        [[CELL[c], rate_cell(esc[c]["cannot_verify"]), rate_cell(esc[c]["can_verify"])] for c in ORDER]))

    vm = est["6_value_match"]
    for role in ("Harm", "Help", "Own"):
        parts.append(f"### 6. Which known value the agreed term equals: {role} tasks\n\n"
                     "Task-average shares, with pooled counts in brackets.\n\n" + table(
                         ["Condition"] + [name for _, name in VALUES],
                         [[CELL[c]] + [(f"{pct(vm[c][role]['task_average_shares'].get(k, 0.0))} "
                                        f"({vm[c][role]['pooled_counts'].get(k, 0)})") if vm[c][role]["tasks"] else "n/a"
                                       for k, _ in VALUES] for c in ORDER]))

    cats = est["1_outcome_categories_pooled_counts"]
    parts.append("### 6b. Harm tasks: value crossed with the decision (pooled counts)\n\n" + table(
        ["Condition", "Counts"],
        [[CELL[c], ", ".join(f"{k.replace('|', ', ')}: {n}" for k, n in sorted(cats[c]["Harm"].items(), key=lambda kv: -kv[1]))]
         for c in ORDER]))

    dep = est["7_dependence"]
    parts.append("### 7. Do the two Harm tasks of a group run go wrong together?\n\n" + table(
        ["Condition", "Joint event", "Group runs", "Joint rate", "What independence would give for the same event",
         "Errors per run: mean, variance (binomial variance with that mean)"],
        [[CELL[c], dep[c]["joint_event"], dep[c]["group_runs_with_both_harm_tasks"], pct(dep[c]["joint_rate"]),
          pct(dep[c]["independence_baseline_same_event"]),
          f"{dep[c]['descriptive_errors_per_run_mean']}, {dep[c]['descriptive_errors_per_run_variance']} "
          f"({dep[c]['descriptive_binomial_variance_same_mean']})"] for c in ORDER]))

    notes = est["8_harm_notes_in_S"]
    parts.append("### 8. What the Harm tasks' stored notes state (shared notes)\n\n" + table(
        ["Condition", "The planted value only", "The planted and the true value", "Passes the planted value on",
         "Pooled counts by what the note states"],
        [[CELL[c], rate_cell(notes[c]["states_the_planted_value_only"]),
          rate_cell(notes[c]["states_the_planted_and_the_true_value"]), rate_cell(notes[c]["passes_on_the_planted_value"]),
          ", ".join(f"{k}: {n}" for k, n in sorted(notes[c]["pooled_counts_by_what_the_note_states"].items()))]
         for c in ORDER if c in notes]))
    quoted = est["8_notes_state_the_quoted_value"]
    parts.append("### 8b. The stored note states the value the quote carries (agreement tasks)\n\n" + table(
        ["Condition", "Share"], [[CELL[c], rate_cell(quoted[c])] for c in ORDER]))

    rr = est["7_reading_rule"]
    for c in ("S.V-", "S.V+"):
        t = rr[c]
        columns = sorted({k for row in t["first_note_by_second_task_value"].values() for k in row})
        body = [[key.split("|")[0].replace("_", " "), key.split("|")[1].replace("first note states: ", "").replace("_", " ")]
                + [str(row.get(k, 0)) for k in columns] for key, row in t["first_note_by_second_task_value"].items()]
        x = t["contradicts_the_newest_note_rule"]
        parts.append(f"### 11. The reading rule: {CELL[c]}\n\n"
                     f"Group runs with both Harm tasks: {t['group_runs_with_both_harm_tasks']}. Rows: what the first "
                     "Harm task's stored note gives a later reader. Columns: the value the second Harm task carries.\n\n"
                     + table(["First note", "It states"] + [k.replace("_", " ") for k in columns], body)
                     + f"\n\nThe pattern that contradicts the newest-note rule ({x['pattern']}): **{x['count']} of "
                       f"{x['denominator']}** group runs. Distinguishing cases (the first note does not name the "
                       f"planted value): {t['distinguishing_cases']['count']} of {t['distinguishing_cases']['denominator']}. "
                       f"Ambiguous cases (it also names the planted value): {t['ambiguous_cases']['count']} of "
                       f"{t['ambiguous_cases']['denominator']}.")

    by = est["10_descriptive_by_term_type_pooled_counts"]
    types = ("payment", "price_floor", "delivery")

    def tt(d: dict) -> list[str]:
        return [f"{d[k]['count']} of {d[k]['valid_task_runs']}" if k in d else "none" for k in types]

    parts.append("### 10. By agreement term type (pooled counts; a description only)\n\n" + table(
        ["Condition", "Outcome", "Payment term", "Price floor", "Delivery term"],
        [[CELL[c], name] + tt(by[c][key]) for c in ORDER for key, name in (
            ("harm_released_error", "Harm: released wrong term"), ("harm_matches_planted", "Harm: equals the planted value"),
            ("help_agreed_term_complied", "Help: agreed term honoured"), ("agreement_roles_escalated", "Agreement tasks: escalated"))]))

    lengths = est["9_notes_block_lengths"]
    exposure = est["9_exposure_by_role"]
    parts.append("### 9. Manipulation checks\n\n"
                 f"Notes block, shared over isolated, in characters: {lengths['mean_ratio_S_over_I']} overall; by task "
                 f"position {min(lengths['ratio_by_visibility_and_task'].values())} to "
                 f"{max(lengths['ratio_by_visibility_and_task'].values())}.\n\n" + table(
                     ["Condition"] + [f"{r}: note about the customer in view" for r in ROLES],
                     [[CELL[c]] + [", ".join(f"{k.replace('_', ' ')}: {n}" for k, n in sorted(exposure[c][r].items())) or "n/a"
                                   for r in ROLES] for c in ORDER]))

    e4 = est["e4_constraints"]
    parts.append("### What constrains the quotation model\n\n" + table(
        ["Frequency", "Share (count; group-bootstrap interval)", "Wilson interval on pooled counts", "Tasks"],
        [[k.replace("__", ": ").replace("_", " "), rate_cell(v), span(v["interval_95_wilson_pooled_ignores_clustering"]),
          str(v["tasks"])] for k, v in e4.items()]))
    return "\n\n".join(parts)


def heldout(diag: dict) -> str:
    q = diag["quantities"]
    rows = []
    for name, v in q.items():
        rows.append([name.replace("_", " "), pct(v["development_mean"]), span(v["predictive_interval_90"]),
                     pct(v["heldout_mean"]), f"{v['heldout_task_runs']['valid']} valid, {v['heldout_task_runs']['missing']} missing",
                     "not estimable" if v["status"] != "estimated" else ("flagged" if v["flagged"] else "inside")])
    s = diag["harm_S_minus_I_at_V-"]
    t = diag["heldout_task_runs"]
    return (f"Held-out task runs: {t['planned']} planned, {t['valid']} valid, {t['missing']} missing. "
            f"Generated {diag['generated_utc']}.\n\n"
            + table(["Quantity", "Development mean", "90% predictive interval for the held-out mean", "Held-out mean",
                     "Held-out runs", "Result"], rows)
            + f"\n\nSign of shared minus isolated on Harm tasks, agreement not visible: development {points(s['development'])}, "
              f"held-out {points(s['heldout'])}; same sign: {s['same_sign']}.")


def e4_update(u: dict) -> str:
    rows = [[k, str(u["ranges_before"][k]), str(v)] for k, v in u["ranges"].items()]
    prod = u["products"]
    out = ("### Ranges in the quotation model, before and after\n\n" + table(["Parameter", "Declared range", "Range from the pilot"], rows)
           + f"\n\nProducts drawn from the pilot's intervals: p_read_note x p_adopt_blind in {prod['q_read_x_adopt_blind']}; "
             f"p_read_note x (1 - p_notice_visible) in {prod['r_read_x_not_notice']}. p_read_note keeps its declared range "
             f"{u['p_read_note_declared_range']}.\n\n### The three checks of the first model's rules\n\n")
    checks = []
    for name, c in u["checks"].items():
        detail = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in c.items() if k not in ("what", "consequence"))
        checks.append(f"- **{name.replace('_', ' ')}.** {c['what']}. {detail}.")
    return out + "\n".join(checks)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake", action="store_true")
    args = ap.parse_args()
    folder = HERE / "runs" / "fake" / "analysis" if args.fake else ROOT / "reports" / "E5"
    parts = ["# Tables of the agent pilot's estimates\n\nWritten by `experiments/agent_pilot/make_tables.py` from the "
             "result files in this folder. Counts are observed in the experiment; shares and intervals are fitted "
             "from them.",
             "## Development groups\n\n" + development(json.loads((folder / "results_development.json").read_text(encoding="utf-8")))]
    if (folder / "heldout_diagnostic.json").exists():
        parts.append("## Held-out calibration diagnostic\n\n"
                     + heldout(json.loads((folder / "heldout_diagnostic.json").read_text(encoding="utf-8"))))
    if (folder / "e4_update.json").exists():
        parts.append("## What went into the quotation model\n\n"
                     + e4_update(json.loads((folder / "e4_update.json").read_text(encoding="utf-8"))))
    (folder / "tables.md").write_bytes(("\n\n".join(parts) + "\n").encode("utf-8"))
    print("written", (folder / "tables.md").relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
