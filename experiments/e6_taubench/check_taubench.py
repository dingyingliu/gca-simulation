"""E6: can τ-bench's historical retail trajectories supply evidence on escalation and verification?

Reads the two retail files from third_party/tau-bench (commit pinned in data/SOURCES.md), checks
what they record, measures three policy behaviours the written retail policy makes testable, and
converts a few runs to the event format.

    .venv/Scripts/python.exe experiments/e6_taubench/check_taubench.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402

REPO = ROOT / "third_party" / "tau-bench"
OUT = ROOT / "reports" / "E6"
ANALYSIS = "experiments/e6_taubench/check_taubench.py"
# the in-context confirmation check feeds the confirmation record, so its code and data count as analysis too
CONFIRMATION_FILES = ["experiments/e6_taubench/confirmation_sample.py",
                      "experiments/e6_taubench/confirmation_handcheck.py",
                      "reports/E6/confirmation_sample.json", "reports/E6/confirmation_handcheck.json"]
EXPECTED_SHA = {
    "gpt-4o-retail.json": "df01707894836168ff0ec9616b0bf08f66c7e5afcf313e5fe4f7a2f5c2ec938b",
    "sonnet-35-new-retail.json": "0df526398e9d2720c32d340815cffb04fe8c4f8a61b1f4f84bf3bb558f760131",
}
EXPECTED_COMMIT = "59a200c6d575d595120f1cb70fea53cef0632f6b"
AUTH = {"find_user_id_by_email", "find_user_id_by_name_zip"}
WRITE = {"cancel_pending_order", "modify_pending_order_items", "modify_pending_order_address",
         "modify_pending_order_payment", "return_delivered_order_items", "exchange_delivered_order_items",
         "modify_user_address"}
NEUTRAL = {"think", "calculate", "list_all_product_types", "transfer_to_human_agents"}
YES = re.compile(r"\byes\b", re.I)


def tool_calls(run: dict):
    """(message index, tool name, arguments) in order."""
    for i, m in enumerate(run["traj"]):
        if m.get("role") == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                yield i, tc["function"]["name"], tc["function"].get("arguments")


def actions_before_authentication(run: dict) -> tuple[bool, bool, bool]:
    """(any action, a read before authentication, a write before authentication).

    Authentication counts only once a lookup's result has come back without an error. A lookup that fails, a read using an id the customer supplied without a successful lookup,
    and a read issued in the same message as the lookup (before its result is seen) all count as acting
    before authentication."""
    authenticated = False
    acted = read_before = write_before = False
    for m in run["traj"]:
        role = m.get("role")
        if role == "tool" and m.get("name") in AUTH:
            if not str(m.get("content", "")).strip().lower().startswith("error"):
                authenticated = True
        elif role == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                name = tc["function"]["name"]
                if name in AUTH or name in NEUTRAL:
                    continue
                acted = True
                if not authenticated:
                    if name in WRITE:
                        write_before = True
                    else:
                        read_before = True
    return acted, read_before, write_before


def wilson(k: int, n: int) -> list[float]:
    if n == 0:
        return [None, None]
    z = 1.959964
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(c - h, 4), round(c + h, 4)]


def analyse(runs: list[dict]) -> dict:
    tasks = Counter(r["task_id"] for r in runs)
    trials = Counter(r["trial"] for r in runs)
    by_task = defaultdict(list)
    for r in runs:
        by_task[r["task_id"]].append(r["reward"])
    k = min(len(v) for v in by_task.values())
    out = {"runs": len(runs), "tasks": len(tasks), "trials_per_task": sorted(set(tasks.values())),
           "trial_ids": sorted(trials),
           "mean_reward": round(sum(r["reward"] for r in runs) / len(runs), 4),
           "share_tasks_all_trials_succeed": round(sum(all(v == 1 for v in vs) for vs in by_task.values())
                                                   / len(by_task), 4),
           "share_tasks_some_but_not_all_succeed": round(sum(0 < sum(vs) < len(vs) for vs in by_task.values())
                                                         / len(by_task), 4),
           "trials_compared": k}

    # verification 1: authenticate before acting on user data
    before_auth_write = before_auth_read = with_any = 0
    # verification 2: explicit "yes" in the latest user message before each database write
    writes = writes_after_yes = 0
    # escalation: transfer to a human agent
    transferred = expected = both = 0
    reward_by_transfer = defaultdict(list)
    wrong_writes = missing_writes = 0
    for r in runs:
        calls = list(tool_calls(r))
        gold = [a["name"] for a in r["info"]["task"]["actions"]]
        acted, read_before, write_before = actions_before_authentication(r)
        if acted:
            with_any += 1
            before_auth_write += write_before
            before_auth_read += read_before
        for idx, name, _ in calls:
            if name in WRITE:
                writes += 1
                last_user = next((m["content"] for m in reversed(r["traj"][:idx]) if m.get("role") == "user"), "")
                if YES.search(last_user or ""):
                    writes_after_yes += 1
        did = any(n == "transfer_to_human_agents" for _, n, _ in calls)
        exp = "transfer_to_human_agents" in gold
        transferred += did
        expected += exp
        both += did and exp
        reward_by_transfer["transferred" if did else "not_transferred"].append(r["reward"])
        made = Counter(n for _, n, _ in calls if n in WRITE)
        want = Counter(n for n in gold if n in WRITE)
        if r["reward"] == 0:
            wrong_writes += any(made[n] > want[n] for n in made)
            missing_writes += any(want[n] > made[n] for n in want)
    out["verification"] = {
        "runs_with_any_action": with_any,
        "runs_reading_user_data_before_authentication": before_auth_read,
        "runs_writing_before_authentication": before_auth_write,
        "database_writes": writes,
        "writes_after_explicit_yes": writes_after_yes,
        "share_writes_after_explicit_yes": round(writes_after_yes / writes, 4) if writes else None,
        "share_writes_after_explicit_yes_95ci_wilson": wilson(writes_after_yes, writes),
    }
    out["escalation"] = {
        "runs_transferring_to_human": transferred,
        "runs_where_gold_actions_include_transfer": expected,
        "transferred_and_expected": both,
        "transferred_not_expected": transferred - both,
        "expected_not_transferred": expected - both,
        "transfer_share": round(transferred / len(runs), 4),
        "mean_reward_transferred": round(sum(reward_by_transfer["transferred"]) / max(1, len(reward_by_transfer["transferred"])), 4),
        "mean_reward_not_transferred": round(sum(reward_by_transfer["not_transferred"]) / max(1, len(reward_by_transfer["not_transferred"])), 4),
    }
    failed = sum(1 for r in runs if r["reward"] == 0)
    out["failures"] = {"failed_runs": failed, "with_an_extra_or_wrong_write": wrong_writes,
                       "with_a_missing_write": missing_writes}
    return out


def to_events(run: dict, label: str) -> list[list]:
    """One run as an event log: case, activity, order (no timestamps are recorded), resource."""
    rows = []
    case = f"{label}:task{run['task_id']}:trial{run['trial']}"
    for i, m in enumerate(run["traj"]):
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                rows.append([case, f"tool:{tc['function']['name']}", i, "agent"])
        elif role == "assistant":
            rows.append([case, "agent_message", i, "agent"])
        elif role == "user":
            rows.append([case, "customer_message", i, "user simulator"])
        elif role == "tool":
            rows.append([case, f"result:{m.get('name')}", i, "environment"])
        elif role == "system":
            rows.append([case, "policy_loaded", i, "system"])
    return rows


def main() -> None:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    if commit != EXPECTED_COMMIT:
        raise SystemExit(f"tau-bench checkout is at {commit}, expected {EXPECTED_COMMIT}")
    OUT.mkdir(parents=True, exist_ok=True)
    git = evidence.git_state([ANALYSIS, *CONFIRMATION_FILES])
    result = {"generated_utc": evidence.utc_now(), "versions": git, "tau_bench_commit": commit, "files": {}}
    sample_rows = []
    for fname, sha in EXPECTED_SHA.items():
        path = REPO / "historical_trajectories" / fname
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != sha:
            raise SystemExit(f"{fname} sha256 {got} differs from the recorded {sha}")
        runs = json.loads(path.read_text(encoding="utf-8"))
        first = runs[0]
        recorded = {
            "top_level_fields": list(first.keys()),
            "info_fields": list(first["info"].keys()),
            "task_fields": list(first["info"]["task"].keys()),
            "message_fields": sorted({k for r in runs[:20] for m in r["traj"] for k in m}),
            "policy_in_system_message": first["traj"][0].get("role") == "system"
                                        and "Retail agent policy" in first["traj"][0].get("content", ""),
            "model_identified_by": "file name only; no model, version, date, temperature or seed field",
            "timestamps": "none; messages are ordered but not timed",
        }
        label = fname.replace(".json", "")
        result["files"][fname] = {"sha256": sha, "bytes": path.stat().st_size, "recorded": recorded,
                                  **analyse(runs)}
        for r in [x for x in runs if x["trial"] == 0][:3]:
            sample_rows.extend(to_events(r, label))
        transfer_runs = [x for x in runs if any(n == "transfer_to_human_agents" for _, n, _ in tool_calls(x))]
        if transfer_runs:
            sample_rows.extend(to_events(transfer_runs[0], label))
    with open(OUT / "events_sample.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["case_id", "activity", "order", "resource"])
        w.writerows(sample_rows)
    (OUT / "results.json").write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
    write_records(result, git)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("recorded",)}
                      for k, v in result["files"].items()}, indent=1))


def _handcheck() -> dict | None:
    path = OUT / "confirmation_handcheck.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def handcheck_tests() -> list[dict]:
    """The in-context check of the keyword heuristic:
    the annotation counts only, attributed to their annotator. The estimate inferred from them is a separate,
    fitted record."""
    d = _handcheck()
    if d is None:
        return []
    counts = {m: {"strata": {s: {k: st[k] for k in ("population", "sampled", "confirmed", "borderline")}
                             for s, st in r["strata"].items()},
                  "keyword_false_matches_in_sample": r["keyword_false_matches_in_sample"]}
              for m, r in d["models"].items()}
    return [{"test": "in-context check of the 'yes' keyword heuristic, stratified sample (annotation counts)",
             "file": "reports/E6/confirmation_handcheck.json", "judged_by": d["judged_by"],
             "standard": d["standard"], "sample": d["sample"], "counts": counts,
             "estimate": "confirm_before_write_in_context.taubench_retail (fitted)"}]


def write_in_context_record(source: dict, versions: dict, conditions: str, created: str) -> None:
    """The share of writes made with explicit confirmation, inferred from the annotated sample."""
    d = _handcheck()
    if d is None:
        return
    table = {m.replace(".json", ""): {
        "point": r["estimated_share_confirmed"], "credible_interval_95": r["estimated_share_credible_95"],
        "if_borderline_judgements_flipped": r["estimated_share_if_borderline_flipped"],
        "writes": r["writes"],
        "annotated": {s: {k: st[k] for k in ("population", "sampled", "confirmed", "borderline")}
                      for s, st in r["strata"].items()}}
        for m, r in d["models"].items()}
    evidence.write({
        "id": "confirm_before_write_in_context.taubench_retail",
        "mechanism": "An agent obtains explicit customer confirmation before an action that changes records",
        "measures": ("Estimated share of database-writing tool calls made after the customer explicitly approved the "
                     "action the agent had described (the standard in reports/E6/confirmation_handcheck.json), from "
                     "one annotator's in-context judgements of a stratified sample of 50 writes per model, weighted by "
                     "stratum size. A different estimand from the keyword share in "
                     "confirm_before_write.taubench_retail."),
        "simulator_parameter": "agent's own check before release (analogue for p_selfcheck)",
        "estimable": "partly",
        "estimable_note": ("Inferred from 50 annotated writes per model, not observed for every write. One annotator, "
                           "Claude Code (build); annotation error is not in the interval. Checks a procedural rule, "
                           "not whether the content was right. Not a general rate for these model versions: outdated "
                           "tasks, simulated customers, one domain."),
        "value": {"table": table, "summary": {"difference": d["difference"]},
                  "interval_95_meaning": ("95% Bayesian credible interval: each stratum's share has a Jeffreys "
                                          "Beta(0.5, 0.5) prior; posterior draws are combined with the stratum "
                                          "weights. It excludes annotation error and has no finite-population "
                                          "correction.")},
        "status": "fitted", "use": "reference_only",
        "source": source, "conditions": conditions,
        "transfer": "Analogue for procedural self-checks before release, for reference only. Not a term-error rate.",
        "versions": {**versions, "analysis": ("experiments/e6_taubench/confirmation_handcheck.py (estimate), "
                                              f"{ANALYSIS} (record)")},
        "disagreements": [], "tests": [],
        "notes": ("Sample: reports/E6/confirmation_sample.json (confirmation_sample.py). Judgements, borderline "
                  "flags and estimates: reports/E6/confirmation_handcheck.json. Method: "
                  + d["estimate_method"] + ". Limits: " + d["limits"] + "."),
        "created_utc": created})


def write_records(result: dict, git: dict) -> None:
    source = {"name": "τ-bench historical trajectories (retail), sierra-research/tau-bench",
              "url": "https://github.com/sierra-research/tau-bench", "doi": None, "licence": "MIT",
              "retrieved_utc": "2026-10-02"}
    versions = {**git, "analysis": ANALYSIS, "model": "as named in the file names only: gpt-4o, sonnet-35-new"}
    conditions = ("simulated customer-service conversations in the τ-bench retail domain; one agent with tools and a "
                  f"written policy; tau-bench commit {result['tau_bench_commit']}")
    g, s = result["files"]["gpt-4o-retail.json"], result["files"]["sonnet-35-new-retail.json"]
    common = {"source": source, "versions": versions, "disagreements": [], "tests": [],
              "created_utc": result["generated_utc"]}
    evidence.write({
        "id": "transfer_to_human.taubench_retail",
        "mechanism": "An agent hands a request to a person when the policy says it is outside its scope",
        "measures": "Share of runs calling transfer_to_human_agents, against whether the task's gold actions include a transfer",
        "simulator_parameter": "agent escalation when a request is outside its authority (analogue for p_flag_unverifiable)",
        "estimable": "partly",
        "estimable_note": ("Measures escalation of out-of-scope requests in customer service, not escalation of quotes whose "
                           "terms the agent cannot verify. No timestamps, one agent, no shared context."),
        "value": {"table": {"gpt-4o-retail": g["escalation"], "sonnet-35-new-retail": s["escalation"]}},
        "status": "observed", "conditions": conditions,
        "transfer": "Weak analogue only: shows that escalation decisions can be measured against a written rule.",
        **common})
    evidence.write({
        "id": "confirm_before_write.taubench_retail",
        "mechanism": "An agent obtains explicit customer confirmation before an action that changes records",
        "measures": "Share of database-writing tool calls whose latest preceding customer message contains the word 'yes'",
        "simulator_parameter": "agent's own check before release (analogue for p_selfcheck)",
        "estimable": "partly",
        "estimable_note": ("A keyword heuristic for confirmation; checks a procedural rule, not whether the content was "
                           "right. One annotator's in-context reading of a stratified sample of 50 writes per model "
                           "(tests: counts) found every sampled write after 'yes' confirmed and most writes without "
                           "it confirmed too, so the keyword shares understate confirmation. The share inferred from "
                           "that sample is a separate, fitted record: confirm_before_write_in_context.taubench_retail."),
        "value": {"table": {"gpt-4o-retail": g["verification"], "sonnet-35-new-retail": s["verification"]}},
        "status": "observed", "conditions": conditions,
        "transfer": "Analogue for procedural self-checks before release. Not a term-error rate.",
        **{**common, "tests": handcheck_tests()}})
    evidence.write({
        "id": "trial_consistency.taubench_retail",
        "mechanism": "The same agent on the same task succeeds on some trials and fails on others",
        "measures": "Share of tasks where every trial succeeds, and where some but not all succeed",
        "simulator_parameter": "run-to-run variation of agent behaviour (supports replicate runs per task)",
        "estimable": "yes",
        "value": {"table": {"gpt-4o-retail": {k: g[k] for k in ("mean_reward", "share_tasks_all_trials_succeed",
                                                                 "share_tasks_some_but_not_all_succeed",
                                                                 "trials_per_task")},
                            "sonnet-35-new-retail": {k: s[k] for k in ("mean_reward", "share_tasks_all_trials_succeed",
                                                                        "share_tasks_some_but_not_all_succeed",
                                                                        "trials_per_task")}}},
        "status": "observed", "conditions": conditions,
        "transfer": "Supports treating agent behaviour as stochastic and using several replicates per task (E2 plan).",
        **common})
    write_in_context_record(source, versions, conditions, result["generated_utc"])


if __name__ == "__main__":
    main()
