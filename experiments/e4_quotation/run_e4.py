"""E4: compare the three designs, and shared against isolated notes, with both kinds of uncertainty.

Outer loop: parameter draws (Latin hypercube over evidence/assumptions.yaml) = parameter uncertainty.
Inner loop: seeds (matched random streams) = run-to-run variation.
Configurations: 3 designs x 2 contexts x 2 notes assumptions, each also run as the independent-errors
baseline, plus two labelled sensitivities: the walkthrough's bypass, and the policy gate switched off.

    .venv/Scripts/python.exe experiments/e4_quotation/run_e4.py                       # development weeks
    .venv/Scripts/python.exe experiments/e4_quotation/run_e4.py --freeze-conclusions  # after the final development run
    .venv/Scripts/python.exe experiments/e4_quotation/run_e4.py --heldout-final       # once, at the end of the round

The held-out weeks are a robustness check across synthetic weeks. The
evaluation applies the rule declared in evidence/assumptions.yaml to the development conclusions frozen
in experiments/e4_quotation/dev_conclusions.json, and refuses to run twice.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402
from gca_sim.simulator import independent_errors as baseline, designs, engine, params, random_streams as streams, ground_truth as truth  # noqa: E402

OUT = ROOT / "reports" / "E4"
RAW = ROOT / "data" / "derived"
CASES_DIR = ROOT / "specs" / "simulated_weeks"
MANIFEST = Path(__file__).resolve().parent / "heldout_manifest.json"
ANALYSIS = "experiments/e4_quotation/run_e4.py"

MEASURES = ("errors", "wrong_terms", "days_mean", "total_reviews", "lead_reviews", "ho_reviews", "lead_util_max", "ho_util",
            "no_approval", "inconsistent_customers", "repeat_all_wrong", "errors_standard", "errors_agreement",
            "errors_verbal", "errors_beyond_policy", "lead_changed", "agent_releases", "gate_escalations",
            "releases_beyond_authority")
FULL = [(d, c, n) for d in designs.DESIGNS for c in designs.CONTEXTS for n in ("draft", "released")]
CONFIGS = ([("full", d, c, n) for d, c, n in FULL] + [("baseline", d, c, n) for d, c, n in FULL]
           + [("bypass3", d, "isolated", "draft") for d in designs.DESIGNS]
           + [("nogate", d, "isolated", "draft") for d in designs.DESIGNS])
CONFIG_LABELS = [f"{m}|{d}|{c}|{n}" for m, d, c, n in CONFIGS]


def _vector(meas: dict) -> list[float]:
    meas = dict(meas, total_reviews=meas["lead_reviews"] + meas["ho_reviews"])
    return [float(meas[k]) for k in MEASURES]


def worker(task: tuple) -> tuple:
    """One (case, parameter draw): every configuration over every seed."""
    case_json, draw_index, pdict, seeds = task
    case = truth.Case.from_json(case_json)
    p = params.Params(**pdict)
    ents = streams.case_entities(case)
    ss = [streams.Streams(s, ents) for s in seeds]
    out = np.zeros((len(CONFIGS), len(seeds), len(MEASURES)), dtype=np.float64)
    full_results = {}
    for ci, (model, d, c, n) in enumerate(CONFIGS):
        if model != "full":
            continue
        runs = [engine.simulate(case, designs.DESIGNS[d], c, p, s, notes_record=n) for s in ss]
        full_results[(d, c, n)] = runs
        for si, res in enumerate(runs):
            out[ci, si] = _vector(res.measures)
    for ci, (model, d, c, n) in enumerate(CONFIGS):
        if model == "baseline":
            dist = baseline.draft_distribution(full_results[(d, c, n)])
            for si, s in enumerate(ss):
                res = engine.simulate(case, designs.DESIGNS[d], c, p, s, notes_record=n, baseline=dist)
                out[ci, si] = _vector(res.measures)
        elif model == "bypass3":
            for si, s in enumerate(ss):
                res = engine.simulate(case, designs.DESIGNS[d], c, p, s, notes_record=n, bypass_after=3.0)
                out[ci, si] = _vector(res.measures)
        elif model == "nogate":
            for si, s in enumerate(ss):
                res = engine.simulate(case, designs.DESIGNS[d], c, p, s, notes_record=n, enforce_policy_gate=False)
                out[ci, si] = _vector(res.measures)
    return draw_index, out


def load_cases(split: str) -> list[truth.Case]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    side = "heldout" if split == "heldout" else "development"
    cases = []
    for fname, meta in manifest[side].items():
        case = truth.Case.from_json((CASES_DIR / fname).read_text(encoding="utf-8"))
        if case.sha256() != meta["sha256"]:
            raise SystemExit(f"{fname} does not match the frozen manifest")
        cases.append(case)
    return cases


def run(cases, draws, seeds, workers: int) -> np.ndarray:
    """Array [case, draw, config, seed, measure]."""
    data = np.zeros((len(cases), len(draws), len(CONFIGS), len(seeds), len(MEASURES)))
    tasks = [(ci, (case.to_json(), di, p.__dict__, seeds)) for ci, case in enumerate(cases)
             for di, p in enumerate(draws)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(worker, t): ci for ci, t in tasks}
        for f, ci in futures.items():
            di, arr = f.result()
            data[ci, di] = arr
    return data


# ---------------------------------------------------------------- analysis

def cfg(model, d, c, n) -> int:
    return CONFIGS.index((model, d, c, n))


def summarise(data: np.ndarray, case_idx: list[int]) -> dict:
    """Per configuration and measure: mean, parameter range of draw means, run-to-run SD."""
    sub = data[case_idx]                       # [week, draw, config, seed, measure]
    week_means = sub.mean(axis=3)              # [week, draw, config, measure]
    draw_means = week_means.mean(axis=0)       # [draw, config, measure]
    run_sd = sub.std(axis=3, ddof=1).mean(axis=0).mean(axis=0)  # [config, measure]
    out = {}
    for k, label in enumerate(CONFIG_LABELS):
        out[label] = {}
        for m, name in enumerate(MEASURES):
            dm = draw_means[:, k, m]
            out[label][name] = {
                "mean": round(float(dm.mean()), 4),
                "param_p05": round(float(np.quantile(dm, 0.05)), 4),
                "param_p95": round(float(np.quantile(dm, 0.95)), 4),
                "param_sd": round(float(dm.std(ddof=1)), 4),
                "run_sd": round(float(run_sd[k, m]), 4),
            }
    return out


def seed_level_se(diff: np.ndarray) -> np.ndarray:
    """Run-to-run standard error of each draw's pooled difference; `diff` is [week, draw, seed].

    The weeks are fixed cases, not random replicates, and every week reuses the same seeds and region streams,
    so the paired difference is first averaged over the weeks within each seed, and the standard error is the
    spread of those seed-level differences over the seeds. Differences between
    weeks are not run noise, and seeds shared across weeks are not independent observations."""
    pooled = diff.mean(axis=0)                           # [draw, seed]
    return pooled.std(axis=1, ddof=1) / np.sqrt(pooled.shape[1])


def compare(data: np.ndarray, case_idx: list[int], a: int, b: int, measure: str, draws) -> dict:
    """A minus B on one measure: draw-level differences (parameter uncertainty) and the run-to-run
    standard error of the pooled difference within a draw (matched streams)."""
    m = MEASURES.index(measure)
    sub = data[case_idx]
    diff = sub[:, :, a, :, m] - sub[:, :, b, :, m]      # [week, draw, seed]
    per_draw = diff.mean(axis=(0, 2))                    # [draw]
    se = seed_level_se(diff)
    eps = 1e-9
    pos, neg = float((per_draw > eps).mean()), float((per_draw < -eps).mean())
    sign = 1 if pos >= 0.95 else (-1 if neg >= 0.95 else 0)
    names = params.PARAM_NAMES
    pvals = np.array([[getattr(p, k) for k in names] for p in draws])
    drivers = []
    if per_draw.std() > 0:
        from scipy.stats import spearmanr
        for j, k in enumerate(names):
            rho = spearmanr(pvals[:, j], per_draw).statistic
            if np.isfinite(rho):
                drivers.append((k, round(float(rho), 3)))
        drivers.sort(key=lambda kv: -abs(kv[1]))
    reversals = []
    if sign != 0 and (pos if sign > 0 else neg) < 1.0:
        # every parameter value and both configurations' utilisation, not only the top drivers: a reversal can
        # need a parameter that is no top driver
        util = {k: sub[..., MEASURES.index(k)].mean(axis=(0, 3)) for k in ("ho_util", "lead_util_max")}  # [draw, config]
        for i in np.where((per_draw * sign) <= eps)[0]:
            reversals.append({"draw": int(i), "diff": round(float(per_draw[i]), 4), "run_se": round(float(se[i]), 4),
                              "beyond_two_run_se": bool(abs(per_draw[i]) > 2 * se[i]),
                              "utilisation": {k: {"a": round(float(u[i, a]), 3), "b": round(float(u[i, b]), 3)}
                                              for k, u in util.items()},
                              "parameters": {k: round(float(getattr(draws[i], k)), 4) for k in names}})
    return {
        "a": CONFIG_LABELS[a], "b": CONFIG_LABELS[b], "measure": measure,
        "reversals": reversals,
        "mean_diff": round(float(per_draw.mean()), 4),
        "param_p05": round(float(np.quantile(per_draw, 0.05)), 4),
        "param_p95": round(float(np.quantile(per_draw, 0.95)), 4),
        "share_draws_a_higher": round(pos, 4), "share_draws_a_lower": round(neg, 4),
        "robust_sign": sign,
        "run_se_median": round(float(np.median(se)), 4),
        "top_drivers": drivers[:4],
    }


def comparisons(data, case_idx, draws) -> list[dict]:
    rows = []
    key_measures = ("wrong_terms", "days_mean", "total_reviews", "inconsistent_customers", "repeat_all_wrong")
    pairs = [("review", "limits"), ("review", "local"), ("limits", "local")]
    for c in designs.CONTEXTS:
        for n in ("draft", "released"):
            for d1, d2 in pairs:
                for meas in key_measures:
                    rows.append({"family": "design", "context": c, "notes": n,
                                 **compare(data, case_idx, cfg("full", d1, c, n), cfg("full", d2, c, n), meas, draws)})
    for d in designs.DESIGNS:
        for n in ("draft", "released"):
            for meas in key_measures:
                rows.append({"family": "context", "design": d, "notes": n,
                             **compare(data, case_idx, cfg("full", d, "shared", n), cfg("full", d, "isolated", n),
                                       meas, draws)})
            for meas in ("wrong_terms", "inconsistent_customers", "repeat_all_wrong"):
                rows.append({"family": "baseline", "design": d, "notes": n, "context": "shared",
                             **compare(data, case_idx, cfg("full", d, "shared", n), cfg("baseline", d, "shared", n),
                                       meas, draws)})
        for meas in ("wrong_terms", "inconsistent_customers"):
            rows.append({"family": "notes_assumption", "design": d, "context": "shared",
                         **compare(data, case_idx, cfg("full", d, "shared", "released"),
                                   cfg("full", d, "shared", "draft"), meas, draws)})
        # the policy gate: what switching it off changes in each design
        for meas in ("wrong_terms", "releases_beyond_authority", "days_mean", "ho_reviews"):
            rows.append({"family": "gate_effect", "design": d, "context": "isolated", "notes": "draft",
                         **compare(data, case_idx, cfg("nogate", d, "isolated", "draft"),
                                   cfg("full", d, "isolated", "draft"), meas, draws)})
    for d1, d2 in pairs:
        for meas in ("wrong_terms", "releases_beyond_authority", "errors"):
            rows.append({"family": "gate_off_design", "context": "isolated", "notes": "draft",
                         **compare(data, case_idx, cfg("nogate", d1, "isolated", "draft"),
                                   cfg("nogate", d2, "isolated", "draft"), meas, draws)})
    return rows


def dominance(data, case_idx) -> dict:
    """Share of parameter draws in which each full configuration is not dominated (no other
    configuration is at least as good on wrong terms, days and total reviews, and better on one)."""
    sub = data[case_idx].mean(axis=3).mean(axis=0)  # [draw, config, measure]
    idx = [cfg("full", d, c, n) for d, c, n in FULL]
    ms = [MEASURES.index(k) for k in ("wrong_terms", "days_mean", "total_reviews")]
    counts = {CONFIG_LABELS[i]: 0 for i in idx}
    for draw in range(sub.shape[0]):
        vals = {i: sub[draw, i, ms] for i in idx}
        for i in idx:
            dominated = any(np.all(vals[j] <= vals[i] + 1e-12) and np.any(vals[j] < vals[i] - 1e-12)
                            for j in idx if j != i)
            counts[CONFIG_LABELS[i]] += 0 if dominated else 1
    return {k: round(v / sub.shape[0], 4) for k, v in counts.items()}


def figures(summary: dict, rows: list[dict], data, case_idx, draws) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colours = {"review": "#c4652b", "limits": "#3b6fb6", "local": "#4c8c4a"}
    sub = data[case_idx].mean(axis=3).mean(axis=0)  # [draw, config, measure]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for ax, n in zip(axes, ("draft", "released")):
        for d in designs.DESIGNS:
            for c, marker in (("isolated", "o"), ("shared", "^")):
                i = cfg("full", d, c, n)
                x, y = sub[:, i, MEASURES.index("days_mean")], sub[:, i, MEASURES.index("wrong_terms")]
                ax.scatter(x, y, s=8, alpha=0.25, color=colours[d], marker=marker)
                ax.scatter([x.mean()], [y.mean()], s=90, color=colours[d], marker=marker, edgecolor="black",
                           label=f"{designs.DESIGNS[d].name}, {c} notes")
        ax.set_title(f"Notes record {n} terms", fontsize=10)
        ax.set_xlabel("Average days to customer")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Quotes with wrong terms reaching customers per week")
    axes[1].legend(fontsize=7, frameon=False, loc="upper right")
    fig.suptitle("Trade-off between errors and speed. Small marks: one parameter draw each (mean over 64 seeds); "
                 "large marks: mean over draws. Assumed parameters.", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "tradeoff_errors_days.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(15, 4.2))
    for ax, meas in zip(axes, ("wrong_terms", "days_mean", "total_reviews", "inconsistent_customers")):
        labels, means, lo, hi, rsd = [], [], [], [], []
        for d in designs.DESIGNS:
            for c in designs.CONTEXTS:
                s = summary[f"full|{d}|{c}|draft"][meas]
                labels.append(f"{d}\n{c}")
                means.append(s["mean"]); lo.append(s["param_p05"]); hi.append(s["param_p95"]); rsd.append(s["run_sd"])
        x = np.arange(len(labels))
        means, lo, hi, rsd = map(np.array, (means, lo, hi, rsd))
        ax.errorbar(x - 0.08, means, yerr=[means - lo, hi - means], fmt="o", color="#3b6fb6", capsize=3,
                    label="parameter range (5% to 95% of draws)")
        ax.errorbar(x + 0.08, means, yerr=rsd, fmt="s", color="#c4652b", capsize=3,
                    label="run-to-run SD (one week)")
        ax.set_xticks(x, labels, fontsize=7)
        ax.set_title(meas.replace("_", " "), fontsize=9)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=7, frameon=False)
    fig.suptitle("Each measure separately, notes recording drafted terms: the two kinds of uncertainty kept apart "
                 "(assumed parameters)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "measures_two_uncertainties.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    k = 0
    ticks = []
    for d in designs.DESIGNS:
        for n in ("draft", "released"):
            a, b = cfg("full", d, "shared", n), cfg("full", d, "isolated", n)
            diff = (data[case_idx][:, :, a, :, MEASURES.index("wrong_terms")]
                    - data[case_idx][:, :, b, :, MEASURES.index("wrong_terms")]).mean(axis=(0, 2))
            ax.scatter(np.full(len(diff), k) + np.random.default_rng(k).uniform(-0.15, 0.15, len(diff)), diff,
                       s=10, alpha=0.5, color=colours[d])
            ax.plot([k - 0.25, k + 0.25], [diff.mean()] * 2, color="black")
            ticks.append(f"{d}\nnotes {n}")
            k += 1
    ax.axhline(0, color="#999999", lw=0.8)
    ax.set_xticks(range(k), ticks, fontsize=8)
    ax.set_ylabel("Shared minus isolated: wrong terms per week")
    ax.set_title("Effect of sharing notes on errors, one dot per parameter draw (assumed parameters)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "shared_minus_isolated_errors.png", dpi=150)
    plt.close(fig)


def write_traces(cases, git: dict) -> None:
    """Decision-consequence logs for one illustrative run per configuration (W0, central values, seed 0)."""
    tdir = OUT / "traces"
    tdir.mkdir(parents=True, exist_ok=True)
    case = cases[0]
    p = params.central()
    s = streams.Streams(0, streams.case_entities(case))
    for d, c, n in FULL:
        meta = {"parameter_draw": "central values", "seed": 0, "code_commit": git["code_commit"],
                "code_dirty": git["code_dirty"], "analysis": ANALYSIS}
        res = engine.simulate(case, designs.DESIGNS[d], c, p, s, notes_record=n, log=True, run_meta=meta)
        stem = f"W0_{d}_{c}_{n}"
        with open(tdir / f"{stem}.jsonl", "w", encoding="utf-8", newline="\n") as f:
            for e in res.log:
                f.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")
        with open(tdir / f"{stem}.events.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["case_id", "activity", "timestamp_days", "resource", "rule"])
            for e in res.log:
                w.writerow([e["quote"], e["action"], e["t"], e["actor"], e["rule"] or ""])


CONCLUSIONS = Path(__file__).resolve().parent / "dev_conclusions.json"
HELDOUT_RESULT = OUT / "results_heldout.json"
HELDOUT_LOCK = OUT / "heldout_started.lock"
DEV_SHARE, HELDOUT_SHARE, TARGET = 0.95, 0.90, 0.80  # evidence/assumptions.yaml heldout.criterion
FIXED_BY_DESIGN = ("total_reviews", "lead_reviews", "ho_reviews")  # set by the designs and the case composition
TARGET_MEASURES = ("wrong_terms", "days_mean")                       # the 80% target applies to each separately
CONCLUSION_FAMILIES = ("design", "context", "baseline", "notes_assumption")
# What the held-out check must find unchanged since the development run: the model, the runner, the declared ranges
# and the frozen weeks with their manifest. Documentation, reports and
# the conclusions file itself are not in this list, so later commits of those stay allowed.
GUARDED_PATHS = ["gca_sim", "experiments/e4_quotation/run_e4.py", "evidence/assumptions.yaml",
                 "experiments/e4_quotation/heldout_manifest.json", "specs/simulated_weeks"]
CONCLUSIONS_REL = "experiments/e4_quotation/dev_conclusions.json"


def conclusion_id(row: dict) -> str:
    return f"{row['a']}||{row['b']}||{row['measure']}"


def freeze_conclusions(dev_result: dict, dev_sha256: str, assumptions_sha256: str | None = None,
                       manifest_sha256: str | None = None) -> dict:
    """The development conclusions: pooled comparisons whose sign holds in at least 95% of draws, leaving out
    sensitivities and measures fixed by the designs and the case composition.
    Bound to the development results, the declared ranges and the code that produced them, and to the held-out manifest. Deterministic apart from
    `frozen_utc`, so the held-out run can recompute it and compare."""
    rows = [r for r in dev_result["comparisons_pooled"] if r["robust_sign"] != 0
            and r["family"] in CONCLUSION_FAMILIES and r["measure"] not in FIXED_BY_DESIGN]
    return {"frozen_utc": evidence.utc_now(), "development_results_sha256": dev_sha256,
            "assumptions_sha256": assumptions_sha256 or dev_result.get("assumptions_sha256"),
            "heldout_manifest_sha256": manifest_sha256 or dev_result.get("heldout_manifest_sha256"),
            "development_versions": dev_result["versions"],
            "rule": {"development_share": DEV_SHARE, "heldout_share": HELDOUT_SHARE, "target_pass_fraction": TARGET,
                     "target_measures": list(TARGET_MEASURES), "excluded_measures": list(FIXED_BY_DESIGN),
                     "families": list(CONCLUSION_FAMILIES)},
            "conclusions": [{"id": conclusion_id(r), "a": r["a"], "b": r["b"], "measure": r["measure"],
                             "direction": r["robust_sign"], "family": r["family"]} for r in rows]}


def _git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def model_changed_since(commit: str) -> bool:
    r = _git("diff", "--quiet", commit, "HEAD", "--", *GUARDED_PATHS)
    if r.returncode not in (0, 1):
        raise SystemExit(f"cannot compare the model with commit {commit}: {r.stderr.strip()}")
    return r.returncode == 1


def model_dirty() -> bool:
    return evidence.git_state(GUARDED_PATHS)["code_dirty"]


def conclusions_committed(path: str = CONCLUSIONS_REL) -> bool:
    """The frozen conclusions are tracked by git and have no uncommitted changes."""
    tracked = _git("ls-files", "--error-unmatch", path)
    return tracked.returncode == 0 and not evidence.git_state([path])["code_dirty"]


def _without_time(spec: dict) -> dict:
    return {k: v for k, v in spec.items() if k != "frozen_utc"}


def validate_frozen(frozen: dict, results_bytes: bytes, assumptions_bytes: bytes, manifest_bytes: bytes,
                    changed_since=model_changed_since, dirty=model_dirty, committed=conclusions_committed) -> None:
    """Refuse to evaluate unless the model, ranges, frozen weeks and development results are those the
    conclusions were frozen from, and the conclusions are exactly the committed freeze of that result."""
    if hashlib.sha256(results_bytes).hexdigest() != frozen["development_results_sha256"]:
        raise SystemExit("reports/E4/results.json is not the development result the conclusions were frozen from")
    if hashlib.sha256(assumptions_bytes).hexdigest() != frozen["assumptions_sha256"]:
        raise SystemExit("evidence/assumptions.yaml has changed since the conclusions were frozen")
    if not frozen.get("heldout_manifest_sha256"):
        raise SystemExit("the frozen conclusions do not name the held-out manifest; freeze them again")
    if hashlib.sha256(manifest_bytes).hexdigest() != frozen["heldout_manifest_sha256"]:
        raise SystemExit("the held-out manifest has changed since the conclusions were frozen")
    expected = freeze_conclusions(json.loads(results_bytes), frozen["development_results_sha256"],
                                  frozen["assumptions_sha256"], frozen["heldout_manifest_sha256"])
    if _without_time(frozen) != _without_time(expected):
        raise SystemExit("dev_conclusions.json differs from the freeze recomputed from the development result")
    if not committed():
        raise SystemExit("dev_conclusions.json must be committed and unchanged before the held-out run")
    v = frozen["development_versions"]
    if v.get("code_dirty"):
        raise SystemExit("the development results were produced from uncommitted code")
    if dirty():
        raise SystemExit("the model, runner, assumptions or frozen weeks have uncommitted changes")
    if changed_since(v["code_commit"]):
        raise SystemExit(f"the model, runner, assumptions or frozen weeks changed after commit {v['code_commit']}")


def evaluate_conclusions(frozen: dict, heldout_rows: list[dict]) -> dict:
    """Apply the declared rule: a conclusion passes if its sign holds in at least 90% of held-out draws. The 80%
    target applies to each target measure separately; other measures are reported.
    Ties and missing rows count as failures."""
    rule = frozen["rule"]
    by_id = {conclusion_id(r): r for r in heldout_rows}
    results = []
    for c in frozen["conclusions"]:
        r = by_id.get(c["id"])
        if r is None:
            results.append({**c, "heldout_share": None, "passed": False, "reason": "missing on held-out"})
            continue
        share = r["share_draws_a_higher"] if c["direction"] > 0 else r["share_draws_a_lower"]
        results.append({**c, "heldout_share": share, "passed": share >= rule["heldout_share"]})
    by_measure = {}
    for r in results:
        m = by_measure.setdefault(r["measure"], {"n": 0, "passed": 0})
        m["n"] += 1
        m["passed"] += int(r["passed"])
    for m in by_measure.values():
        m["pass_fraction"] = round(m["passed"] / m["n"], 4)
    targets = {}
    for meas in rule.get("target_measures", []):
        m = by_measure.get(meas)
        targets[meas] = ("not applicable: no development conclusions" if m is None
                         else ("pass" if m["pass_fraction"] >= rule["target_pass_fraction"] else "fail"))
    applicable = [v for v in targets.values() if not v.startswith("not applicable")]
    if not results or not applicable:
        return {"n_conclusions": len(results), "passed": None, "by_measure": by_measure, "targets": targets,
                "outcome": "no development conclusions to check", "results": results}
    passed = all(v == "pass" for v in applicable)
    return {"n_conclusions": len(results), "n_passed": sum(r["passed"] for r in results), "by_measure": by_measure,
            "targets": targets, "passed": passed,
            "outcome": "pass" if passed else "fail: narrow the claims to the measures and conclusions that pass",
            "results": results}


def heldout_guard(result_path: Path = HELDOUT_RESULT, lock_path: Path = HELDOUT_LOCK) -> None:
    """Refuse a second held-out evaluation, and an evaluation after an interrupted one."""
    if result_path.exists():
        raise SystemExit(f"held-out result already exists ({result_path}); the held-out weeks are used once")
    if lock_path.exists():
        raise SystemExit(f"an earlier held-out run started and did not finish ({lock_path}); recovery must be "
                         "recorded and approved before anything is rerun")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heldout-final", action="store_true")
    ap.add_argument("--freeze-conclusions", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    if args.freeze_conclusions:
        if HELDOUT_LOCK.exists() or HELDOUT_RESULT.exists():
            raise SystemExit("a held-out run has started or finished; the conclusions cannot be frozen again")
        raw = (OUT / "results.json").read_bytes()
        dev = json.loads(raw)
        if dev["versions"].get("code_dirty"):
            raise SystemExit("the development results came from uncommitted code; rerun on a clean tree first")
        if model_dirty() or model_changed_since(dev["versions"]["code_commit"]):
            raise SystemExit("the model, runner, assumptions or frozen weeks changed after the development run; "
                             "rerun it on a clean tree first")
        manifest_sha = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        if dev.get("heldout_manifest_sha256") not in (None, manifest_sha):
            raise SystemExit("the held-out manifest differs from the one recorded with the development run")
        frozen = freeze_conclusions(dev, hashlib.sha256(raw).hexdigest(),
                                    hashlib.sha256((ROOT / "evidence" / "assumptions.yaml").read_bytes()).hexdigest(),
                                    manifest_sha)
        CONCLUSIONS.write_bytes((json.dumps(frozen, indent=1) + "\n").encode("utf-8"))
        print("frozen", len(frozen["conclusions"]), "development conclusions")
        return
    frozen_spec = frozen_sha = None
    if args.heldout_final:
        heldout_guard()
        if not CONCLUSIONS.exists():
            raise SystemExit("freeze the development conclusions first (--freeze-conclusions) and commit them")
        frozen_bytes = CONCLUSIONS.read_bytes()
        frozen_spec, frozen_sha = json.loads(frozen_bytes), hashlib.sha256(frozen_bytes).hexdigest()
        validate_frozen(frozen_spec, (OUT / "results.json").read_bytes(),
                        (ROOT / "evidence" / "assumptions.yaml").read_bytes(), MANIFEST.read_bytes())
        HELDOUT_LOCK.write_bytes((evidence.utc_now() + "\n").encode("utf-8"))
    a = params.load_assumptions()
    draws = params.latin_hypercube(a["sampling"]["parameter_draws"], seed=20261002, assumptions=a)
    seeds = list(range(a["sampling"]["seeds_per_draw"]))
    split = "heldout" if args.heldout_final else "development"
    cases = load_cases(split)
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    git = evidence.git_state(GUARDED_PATHS)
    started = evidence.utc_now()
    data = run(cases, draws, seeds, args.workers)
    # the cache carries what it was computed from, so a later reader can check it belongs to this run
    draw_values = np.array([[getattr(p, k) for k in params.PARAM_NAMES] for p in draws])
    fingerprints = {"assumptions_sha256": hashlib.sha256((ROOT / "evidence" / "assumptions.yaml").read_bytes()).hexdigest(),
                    "heldout_manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                    "data_sha256": evidence.array_sha256(data)}
    np.savez_compressed(RAW / f"e4_{split}.npz", data=data, configs=np.array(CONFIG_LABELS),
                        measures=np.array(MEASURES), cases=np.array([c.name for c in cases]),
                        draw_params=draw_values, param_names=np.array(params.PARAM_NAMES),
                        **{k: np.array(v) for k, v in fingerprints.items()})
    all_idx = list(range(len(cases)))
    result = {
        "split": split, "started_utc": started, "finished_utc": evidence.utc_now(), "versions": git,
        "assumptions_sha256": fingerprints["assumptions_sha256"],
        "heldout_manifest_sha256": fingerprints["heldout_manifest_sha256"],
        "raw_data_sha256": fingerprints["data_sha256"],
        "cases": [c.name for c in cases], "parameter_draws": len(draws), "seeds_per_draw": len(seeds),
        "parameter_draw_values": {k: [round(float(v), 6) for v in draw_values[:, j]]
                                  for j, k in enumerate(params.PARAM_NAMES)},
        "configs": CONFIG_LABELS, "measures": list(MEASURES),
        "summary_pooled": summarise(data, all_idx),
        "comparisons_pooled": comparisons(data, all_idx, draws),
        "dominance_pooled": dominance(data, all_idx),
    }
    if split == "heldout":
        result["frozen_conclusions_sha256"] = frozen_sha
        result["robustness_check"] = evaluate_conclusions(frozen_spec, result["comparisons_pooled"])
    if split == "development":
        result["summary_W0"] = summarise(data, [0])
        result["comparisons_W0"] = comparisons(data, [0], draws)
        figures(result["summary_pooled"], result["comparisons_pooled"], data, all_idx, draws)
        write_traces(cases, git)
    path = HELDOUT_RESULT if split == "heldout" else OUT / "results.json"
    path.write_bytes((json.dumps(result, indent=1) + "\n").encode("utf-8"))
    if split == "heldout":
        HELDOUT_LOCK.unlink()
    print("done", split, result["started_utc"], "->", result["finished_utc"])


if __name__ == "__main__":
    main()
