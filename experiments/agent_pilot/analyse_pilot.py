"""Score and analyse the agent pilot (plan section 7).

    .venv/Scripts/python.exe experiments/agent_pilot/analyse_pilot.py --setup-checks --label 2
    .venv/Scripts/python.exe experiments/agent_pilot/analyse_pilot.py --development
    .venv/Scripts/python.exe experiments/agent_pilot/analyse_pilot.py --heldout-final     # once, at the end of E5
    add --fake to any of them to analyse a dry run (outputs go to runs/fake/analysis, never to reports/)

Every analysis checks that its records were made with the current experiment inputs (prompt, schema, task bank,
request settings) and writes the fingerprints of those inputs and of the scorer into its output. The held-out
diagnostic is written once and refuses to run again.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402
from gca_sim.pilot import bank as bank_mod  # noqa: E402
from gca_sim.pilot.analysis import development_estimates, heldout_diagnostic, setup_checks  # noqa: E402
from gca_sim.pilot.records import (estimates_gate, final_outputs, load_config, read_records,  # noqa: E402
                                   request_fingerprint, scoring_fingerprint)

HERE = Path(__file__).resolve().parent
ANALYSIS = "experiments/agent_pilot/analyse_pilot.py"
CODE_PATHS = ["gca_sim/pilot", "experiments/agent_pilot/analyse_pilot.py", "experiments/agent_pilot/task_bank",
              "experiments/agent_pilot/config.yaml", "experiments/agent_pilot_plan.md"]
ROLES = ("Harm", "Help", "Own", "Standard")
CELL_NAME = {"S.V-": "shared notes, agreement not visible", "I.V-": "isolated notes, agreement not visible",
             "S.V+": "shared notes, agreement visible", "I.V+": "isolated notes, agreement visible"}
SHORT_CELL = {"S.V-": "shared\nnot visible", "I.V-": "isolated\nnot visible", "S.V+": "shared\nvisible",
              "I.V+": "isolated\nvisible"}
ORDER = ("S.V-", "I.V-", "S.V+", "I.V+")
ROLE_NAME = {"Harm": "Harm tasks\n(a wrong note about the customer\nis in the shared store)",
             "Help": "Help tasks\n(a correct note about the customer\nis in the shared store)",
             "Own": "Own tasks\n(an agreement, and no note\nabout the customer)",
             "Standard": "Standard tasks\n(no agreement)"}


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_records(path: Path, inputs: str) -> list[dict]:
    """The run's records, refused if any was made with other experiment inputs."""
    records = read_records(path)
    if not records:
        raise SystemExit(f"{path.name} has no records")
    other = {r.get("inputs_sha256") for r in records} - {inputs}
    if other:
        raise SystemExit(f"{path.name} was made with other experiment inputs than the current ones")
    return records


def events_csv(records: list[dict], path: Path) -> None:
    """Each task run as a case in the event format, so it can be process-mined with the other logs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["case_id", "activity", "timestamp_utc", "resource", "group", "cell", "role"])
        for (group, cell, rep, order), r in sorted(final_outputs(records).items()):
            case = f"{r['run_id']}:{group}:{cell}:r{rep}:T{order}"
            agent = f"agent:{r['region']}"
            common = [group, cell, r["role"]]
            w.writerow([case, "prompt_assembled", r["utc_sent"], "harness", *common])
            w.writerow([case, "draft_returned", r["utc_received"], agent, *common])
            w.writerow([case, f"decision:{r['parsed']['decision']}", r["utc_received"], agent, *common])
            w.writerow([case, "note_written", r["utc_received"], agent, *common])


def figures(est: dict, out: Path, model: str) -> dict:
    """The three pictures of the development estimates. A rate with no valid answer behind it, or for a case
    that does not occur in a condition, gets no bar and the mark "n/a"; a measured zero gets a "0". Returns which positions were which, so that this can be tested."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    colours = {"S.V-": "#c4652b", "I.V-": "#e8b38f", "S.V+": "#3b6fb6", "I.V+": "#9fbce0"}
    na_text = 'Where a bar would be, "n/a" means no valid answer or a case that does not occur there; "0" is a measured zero.'
    label = (f"Development groups, {model}. Bars: mean over tasks; lines: 95% interval from a bootstrap over 5 groups.\n"
             + na_text)
    drawn = {"not_available": [], "measured_zero": []}

    def mark(ax, x, v, where):
        """A bar position that holds no bar: say why."""
        if v["mean_over_tasks"] is None:
            ax.text(x, 0.02, "n/a", ha="center", va="bottom", fontsize=6, color="#666666", rotation=90)
            drawn["not_available"].append(where)
        elif v["mean_over_tasks"] == 0:
            ax.text(x, 0.01, "0", ha="center", va="bottom", fontsize=6, color="#333333")
            drawn["measured_zero"].append(where)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(ROLES))
    for k, cell in enumerate(ORDER):
        vals = [est["1_released_error_by_cell_and_role"][cell][r] for r in ROLES]
        have = [v["mean_over_tasks"] is not None for v in vals]
        xs = (x + (k - 1.5) * 0.2)
        means = np.array([v["mean_over_tasks"] if h else 0.0 for v, h in zip(vals, have)])
        lo = np.array([(v["interval_95_group_bootstrap"] or [m, m])[0] for v, m in zip(vals, means)])
        hi = np.array([(v["interval_95_group_bootstrap"] or [m, m])[1] for v, m in zip(vals, means)])
        keep = np.array(have)
        ax.bar(xs[keep], means[keep], 0.2, color=colours[cell], label=CELL_NAME[cell],
               yerr=[np.clip(means - lo, 0, None)[keep], np.clip(hi - means, 0, None)[keep]], capsize=2,
               ecolor="#333333")
        for xi, v, role in zip(xs, vals, ROLES):
            mark(ax, xi, v, ("released_errors_by_role", cell, role))
    ax.set_xticks(x, [ROLE_NAME[r] for r in ROLES], fontsize=8)
    ax.set_ylabel("Share of task runs released with a wrong term")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("Wrong terms released to the customer, by task role and condition", fontsize=10)
    fig.text(0.01, 0.01, label, fontsize=7)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out / "released_errors_by_role.png", dpi=150)
    plt.close(fig)

    kinds = [("true", "#4c8c4a", "the true agreed term, exactly"), ("above_floor", "#a6d3a0", "a price above the agreed floor"),
             ("planted", "#c4652b", "the planted wrong note's value"), ("standard", "#999999", "the standard term"),
             ("other_customer", "#8e6bbf", "another customer's term"), ("none", "#dddddd", "none of these")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), sharey=True)
    for ax, role in zip(axes, ("Harm", "Help", "Own")):
        have = np.array([est["6_value_match"][c][role]["tasks"] > 0 for c in ORDER])
        bottom = np.zeros(len(ORDER))
        positions = np.arange(len(ORDER))
        for key, colour, name in kinds:
            share = np.array([est["6_value_match"][c][role]["task_average_shares"].get(key, 0.0) for c in ORDER])
            ax.bar(positions[have], share[have], bottom=bottom[have], color=colour, label=name)
            bottom += share
        for xi, c, h in zip(positions, ORDER, have):
            if not h:
                ax.text(xi, 0.02, "n/a", ha="center", va="bottom", fontsize=7, color="#666666")
                drawn["not_available"].append(("value_matches", c, role))
        ax.set_xticks(positions, [SHORT_CELL[c] for c in ORDER], fontsize=8)
        ax.set_xlim(-0.6, len(ORDER) - 0.4)
        ax.set_title(ROLE_NAME[role], fontsize=9)
    axes[0].set_ylabel("Share of task runs (task average)")
    axes[2].legend(fontsize=7, frameon=False, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle("Which known value the agreed term on the quote equals\n"
                 "Columns: notes shared or isolated; the customer's agreement visible in the register or not. "
                 f"{model}, development groups.", fontsize=9)
    fig.text(0.01, 0.01, '"n/a": no valid answer in that condition.', fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out / "value_matches.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    x = np.arange(len(ORDER))
    for k, (key, colour, name) in enumerate((("cannot_verify", "#c4652b", "agreed terms cited, not in the register"),
                                             ("can_verify", "#3b6fb6", "nothing to verify, or the agreement is visible"))):
        vals = [est["5_escalation"][c][key] for c in ORDER]
        keep = np.array([v["mean_over_tasks"] is not None for v in vals])
        means = np.array([v["mean_over_tasks"] if h else 0.0 for v, h in zip(vals, keep)])
        xs = x + (k - 0.5) * 0.36
        ax.bar(xs[keep], means[keep], 0.36, color=colour, label=name)
        for xi, v, c in zip(xs, vals, ORDER):
            mark(ax, xi, v, ("escalation", c, key))
    ax.set_xticks(x, [SHORT_CELL[c] for c in ORDER], fontsize=8)
    ax.set_xlim(-0.6, len(ORDER) - 0.4)
    ax.set_ylabel("Share of task runs escalated to a person")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=8, frameon=False)
    ax.set_title("When the agent escalates. Columns: notes shared or isolated; agreement visible or not", fontsize=10)
    fig.text(0.01, 0.01, f"Development groups, {model}. Bars: mean over tasks.\n" + na_text, fontsize=7)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(out / "escalation.png", dpi=150)
    plt.close(fig)
    return drawn


# record id -> (key in e4_constraints, mechanism, what is measured, the E4 parameter or product it constrains)
RECORDS = {
    "e_visible.agent_pilot": (
        "e_visible__agreed_term_failed_agreement_roles_I.V+",
        "The agent gets the agreed term wrong although the agreement is in the register it sees",
        "Share of agreement-role task runs that fail the agreed term, with isolated notes and the agreement visible (I.V+)",
        "e_visible"),
    "note_adoption_blind.agent_pilot": (
        "p_read_note_x_p_adopt_blind__planted_order_3_S.V-",
        "The agent uses a wrong shared note when it cannot see the agreement",
        "Share of first Harm tasks (order 3) whose agreed term equals the planted note's value, shared notes, agreement not visible (S.V-)",
        "the product p_read_note x p_adopt_blind"),
    "note_adoption_help.agent_pilot": (
        "p_read_note_x_p_adopt_blind__help_matches_note_exactly_S.V-",
        "The agent uses a correct shared note when it cannot see the agreement",
        "Share of Help tasks whose agreed term equals the correct note's value exactly, shared notes, agreement not visible (S.V-)",
        "the product p_read_note x p_adopt_blind (should agree with note_adoption_blind)"),
    "note_adoption_visible.agent_pilot": (
        "p_read_note_x_(1-p_notice_visible)__planted_order_3_S.V+",
        "The agent uses a wrong shared note although the register shows the true agreement",
        "Share of first Harm tasks (order 3) whose agreed term equals the planted note's value, shared notes, agreement visible (S.V+)",
        "the product p_read_note x (1 - p_notice_visible)"),
    "flag_unverifiable.agent_pilot": (
        "p_flag_unverifiable__escalation_agreement_roles_I.V-",
        "The agent escalates a quote whose agreed terms it cannot verify",
        "Escalation rate on agreement-role tasks with isolated notes and the agreement not visible (I.V-)",
        "p_flag_unverifiable"),
    "unnecessary_escalation.agent_pilot": (
        "unnecessary_escalation__can_verify",
        "The agent escalates a quote it could verify",
        "Escalation rate on tasks where the agreement is visible or the customer has none",
        None),
    "note_reading_rule.agent_pilot": (
        "p_newest_note__planted_order_5_when_first_note_states_only_another_value_S.V-",
        "The agent follows an older note although a newer note about the same customer states another value",
        "Share of second Harm tasks (order 5) whose agreed term equals the planted note's value, among group runs "
        "in which the first Harm task's stored note states another value and does not name the planted one, shared "
        "notes, agreement not visible (S.V-)",
        "(1 - p_newest_note) x p_read_note x p_adopt_blind"),
    "flag_after_note.agent_pilot": (
        "p_flag_after_note__escalation_when_value_equals_note_S.V-",
        "The agent escalates a quote although it used a note's value",
        "Escalation rate among first Harm tasks that equal the planted value and Help tasks that equal the correct "
        "note's value exactly, shared notes, agreement not visible (S.V-)",
        "p_flag_after_note"),
}


def write_evidence(est: dict, config: dict, git: dict, runs_sha: str, created: str) -> None:
    source = {"name": "GCA controlled agent pilot (E5), development groups",
              "url": "experiments/agent_pilot/runs/development.jsonl", "doi": None, "licence": None,
              "retrieved_utc": created[:10], "file_sha256": runs_sha}
    conditions = (f"synthetic quotation tasks, one fixed prompt, model {config['model']} through {config['provider']} "
                  f"(host {config.get('provider_order')}), reasoning effort {config.get('reasoning_effort')}, "
                  "5 development groups, 3 replicates")
    for rid, (key, mechanism, measures, parameter) in RECORDS.items():
        q = est["e4_constraints"][key]
        if q["valid_task_runs"] == 0:
            # no qualifying run: an observed absence, not a fitted rate, and no constraint on any parameter
            evidence.write({
                "id": rid, "mechanism": mechanism, "measures": measures, "simulator_parameter": parameter,
                "estimable": "no",
                "estimable_note": "No qualifying observations in the development groups, so no fitted constraint.",
                "value": {"point": None, "n": 0, "summary": q},
                "status": "observed", "use": "reference_only", "source": source, "conditions": conditions,
                "transfer": "None: the pilot had no run of this kind.",
                "versions": {**git, "analysis": ANALYSIS, "model": config["model"]},
                "disagreements": [], "tests": [], "created_utc": created,
                "notes": "The frequency could not be estimated. It says nothing about the parameter named."})
            continue
        evidence.write({
            "id": rid, "mechanism": mechanism, "measures": measures, "simulator_parameter": parameter,
            "estimable": "partly",
            "estimable_note": ("A pilot: few tasks per cell, one model, one prompt, synthetic tasks. The frequency is "
                               "over valid answers. It constrains the named parameter or product; it does not "
                               "identify the latent steps behind it."),
            "value": {"point": q["mean_over_tasks"], "n": q["valid_task_runs"], "summary": q,
                      **({"interval_95": q["interval_95_group_bootstrap"]} if q["interval_95_group_bootstrap"] else {}),
                      "interval_95_meaning": ("bootstrap over the 5 development groups (crude); the Wilson interval "
                                              "in summary ignores clustering")},
            "status": "fitted", "use": "range_only", "source": source, "conditions": conditions,
            "transfer": "Analogue for the quotation episode: synthetic tasks, one model, one prompt.",
            "versions": {**git, "analysis": ANALYSIS, "model": config["model"]},
            "disagreements": [], "tests": [], "created_utc": created})


def diagnostic_gate(results_path: Path, inputs: str, development_run_sha256: str) -> None:
    """The held-out diagnostic scores the development run again, so it must use the scorer that produced the
    development estimates, on the same run file and the same inputs."""
    est = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else None
    estimates_gate(est, inputs, development_run_sha256)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup-checks", action="store_true")
    ap.add_argument("--development", action="store_true")
    ap.add_argument("--heldout-final", action="store_true")
    ap.add_argument("--label", default="1")
    ap.add_argument("--fake", action="store_true")
    args = ap.parse_args()

    config = load_config(HERE / "config.yaml", paid=not args.fake)
    bank = bank_mod.load_bank(HERE / "task_bank")
    inputs = request_fingerprint(config, sha256_file(HERE / "task_bank" / "manifest.json"))
    runs = HERE / "runs" / "fake" if args.fake else HERE / "runs"
    out = runs / "analysis" if args.fake else ROOT / "reports" / "E5"
    git = evidence.git_state(CODE_PATHS)
    now = evidence.utc_now()
    model = "fake agent (pipeline test only)" if args.fake else config["model"]
    stamp = {"generated_utc": now, "versions": git, "model": model, "request_inputs_sha256": inputs,
             "scoring_inputs_sha256": scoring_fingerprint()}

    if args.setup_checks:
        path = runs / f"setup_{args.label}.jsonl"
        records = checked_records(path, inputs)
        checks = {**stamp, "run_file": path.name, "run_sha256": sha256_file(path), **setup_checks(bank, records)}
        write_json(out / f"setup_checks_{args.label}.json", checks)
        write_json(out / "setup_checks.json", checks)
        print(json.dumps({k: v for k, v in checks.items() if k.startswith("P") or k == "all_pass"}, indent=1))
    if args.development:
        path = runs / "development.jsonl"
        records = checked_records(path, inputs)
        est = {**stamp, "run_sha256": sha256_file(path),
               **development_estimates(bank, records, "development", config["replicates"]["development"])}
        write_json(out / "results_development.json", est)
        events_csv(records, out / "events_development.csv")
        figures(est, out, model)
        if not args.fake:
            write_evidence(est, config, git, est["run_sha256"], now)
        print(json.dumps({"task_runs": est["task_runs"], "host_by_cell": est["host_by_cell"],
                          "harm_S_minus_I": est["2_harm_released_error_S_minus_I"]}, indent=1))
    if args.heldout_final:
        target = out / "heldout_diagnostic.json"
        if target.exists():
            raise SystemExit(f"{target.name} exists: the held-out groups are evaluated once")
        dev_path, held_path = runs / "development.jsonl", runs / "heldout.jsonl"
        dev, held = checked_records(dev_path, inputs), checked_records(held_path, inputs)
        diagnostic_gate(out / "results_development.json", inputs, sha256_file(dev_path))
        diag = {**stamp,"development_run_sha256": sha256_file(dev_path), "heldout_run_sha256": sha256_file(held_path),
                **heldout_diagnostic(bank, dev, held, config["replicates"])}
        write_json(target, diag)
        events_csv(held, out / "events_heldout.csv")
        print(json.dumps({"flags": diag["flags"], "inside": diag["quantities_inside_interval"],
                          "not_estimable": diag["not_estimable"], "harm_sign": diag["harm_S_minus_I_at_V-"],
                          "task_runs": diag["heldout_task_runs"]}, indent=1))


if __name__ == "__main__":
    main()
