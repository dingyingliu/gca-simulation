"""E3: extract what the BPIC 2020 Domestic Declarations log supports.

Follows the estimand table in reports/E3_real_log.md (committed before this script ran).
Writes:
  reports/E3/results.json             every number quoted in the E3 report
  reports/E3/*.png                    figures
  reports/E3/*.pnml, *.txt            discovered process models
  specs/bpic2020_declarations.workflow.json
  evidence/records/*.bpic2020.json    one evidence record per extracted quantity

Run from the project root:
    .venv/Scripts/python.exe experiments/e3_bpic2020/run_e3.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402
from gca_sim.process_logs import bpic2020  # noqa: E402

warnings.filterwarnings("ignore")
OUT = ROOT / "reports" / "E3"
SPEC = ROOT / "specs" / "bpic2020_declarations.workflow.json"
ANALYSIS = "experiments/e3_bpic2020/run_e3.py"
RNG = np.random.default_rng(20261002)
N_BOOT = 2000

SUB = "Declaration SUBMITTED by EMPLOYEE"
SAVED = "Declaration SAVED by EMPLOYEE"
RET = "Declaration REJECTED by EMPLOYEE"
REQ = "Request Payment"
PAID = "Payment Handled"
APPROVE = {
    "ADMINISTRATION": "Declaration APPROVED by ADMINISTRATION",
    "PRE_APPROVER": "Declaration APPROVED by PRE_APPROVER",
    "BUDGET OWNER": "Declaration APPROVED by BUDGET OWNER",
    "SUPERVISOR": "Declaration FINAL_APPROVED by SUPERVISOR",
}
REJECT = {
    "ADMINISTRATION": "Declaration REJECTED by ADMINISTRATION",
    "PRE_APPROVER": "Declaration REJECTED by PRE_APPROVER",
    "BUDGET OWNER": "Declaration REJECTED by BUDGET OWNER",
    "SUPERVISOR": "Declaration REJECTED by SUPERVISOR",
    "MISSING": "Declaration REJECTED by MISSING",
}
REVIEW_ROLES = ["ADMINISTRATION", "PRE_APPROVER", "BUDGET OWNER", "SUPERVISOR"]
# (record key, preceding activity, deciding role, estimable as review latency)
STEPS = [
    ("administration_after_submission", SUB, "ADMINISTRATION", "no"),
    ("pre_approver_after_submission", SUB, "PRE_APPROVER", "no"),
    ("supervisor_after_submission", SUB, "SUPERVISOR", "no"),
    ("budget_owner_after_administration", APPROVE["ADMINISTRATION"], "BUDGET OWNER", "partly"),
    ("supervisor_after_administration", APPROVE["ADMINISTRATION"], "SUPERVISOR", "partly"),
    ("supervisor_after_budget_owner", APPROVE["BUDGET OWNER"], "SUPERVISOR", "partly"),
    ("supervisor_after_pre_approver", APPROVE["PRE_APPROVER"], "SUPERVISOR", "partly"),
]
ROLE_SHORT = {"ADMINISTRATION": "ADM", "PRE_APPROVER": "PRE", "BUDGET OWNER": "BO", "SUPERVISOR": "SUP"}


def label(a: str) -> str:
    if a.startswith("Declaration "):
        outcome, role = a[len("Declaration "):].split(" by ")
        return f"{role.title()} {outcome.lower().replace('_', ' ')}"
    return a


# ---------------------------------------------------------------- helpers

def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(float(centre - half), 4), round(float(centre + half), 4)]


def boot_median_ci(x: np.ndarray) -> list[float]:
    idx = RNG.integers(0, len(x), size=(N_BOOT, len(x)))
    meds = np.median(x[idx], axis=1)
    return [round(float(np.quantile(meds, 0.025)), 3), round(float(np.quantile(meds, 0.975)), 3)]


def spans_weekend(start: pd.Series, end: pd.Series) -> np.ndarray:
    s = start.dt.tz_convert(bpic2020.LOCAL_TZ).dt.normalize().dt.tz_localize(None).values.astype("datetime64[D]")
    e = end.dt.tz_convert(bpic2020.LOCAL_TZ).dt.normalize().dt.tz_localize(None).values.astype("datetime64[D]")
    business = np.busday_count(s, e + 1)  # weekdays in [s, e]
    calendar = (e - s).astype(int) + 1
    return calendar > business


def gap_summary(gaps_days: np.ndarray, weekend: np.ndarray | None = None) -> dict:
    x = np.asarray(gaps_days, dtype=float)
    q = np.quantile(x, [0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975])
    out = {
        "n": int(len(x)),
        "mean_days": round(float(x.mean()), 3),
        "median_days": round(float(q[3]), 3),
        "median_days_95ci_bootstrap": boot_median_ci(x),
        "p2_5_days": round(float(q[0]), 3), "p10_days": round(float(q[1]), 3),
        "p25_days": round(float(q[2]), 3), "p75_days": round(float(q[4]), 3),
        "p90_days": round(float(q[5]), 3), "p97_5_days": round(float(q[6]), 3),
        "share_under_1_hour": round(float((x < 1 / 24).mean()), 4),
        "share_over_7_days": round(float((x > 7).mean()), 4),
    }
    if weekend is not None:
        out["share_spanning_a_weekend_day"] = round(float(np.mean(weekend)), 4)
    return out


def lognormal_reference_fit(gaps_days: np.ndarray) -> dict | None:
    """A lognormal fitted to the positive gaps, for reference only. Reported with what it implies against what was observed; never a sampler."""
    x = np.asarray(gaps_days, dtype=float)
    pos = x[x > 0]
    if len(pos) < 30:
        return None
    shape, loc, scale = stats.lognorm.fit(pos, floc=0)
    ks = stats.kstest(pos, "lognorm", args=(shape, loc, scale)).statistic
    mu, sigma = float(np.log(scale)), float(shape)
    return {"mu": round(mu, 4), "sigma": round(sigma, 4), "ks_statistic": round(float(ks), 4),
            "n_positive": int(len(pos)), "share_zero_gaps": round(float((x <= 0).mean()), 4),
            "implied_mean_days": round(float(np.exp(mu + sigma ** 2 / 2)), 3),
            "implied_p99_days": round(float(stats.lognorm.ppf(0.99, shape, 0, scale)), 3),
            "observed_mean_days": round(float(x.mean()), 3),
            "observed_p99_days": round(float(np.quantile(x, 0.99)), 3)}


# ---------------------------------------------------------------- analysis

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    git = evidence.git_state([ANALYSIS, "gca_sim/logs/bpic2020.py", "gca_sim/evidence.py"])
    import pm4py  # imported late: it prints a licence banner

    log = bpic2020.load()
    ev, cs = log.events.copy(), log.cases.copy()
    ev["prev_activity"] = ev.groupby("case_id")["activity"].shift(1)
    ev["prev_ts"] = ev.groupby("case_id")["ts_utc"].shift(1)
    ev["gap_days"] = (ev["ts_utc"] - ev["prev_ts"]).dt.total_seconds() / 86400
    ev["start_year"] = ev.groupby("case_id")["ts_utc"].transform("min").dt.year
    paid_cases = set(ev.loc[ev.activity == PAID, "case_id"])
    cs["paid"] = cs["case_id"].isin(paid_cases)
    R: dict = {"generated_utc": evidence.utc_now(), "versions": {
        **git, "pm4py": pm4py.__version__, "pandas": pd.__version__, "numpy": np.__version__}}

    # 1. counts -----------------------------------------------------------
    per_case = ev.groupby("case_id").size()
    R["counts"] = {
        "cases": int(cs.shape[0]), "events": int(ev.shape[0]), "activities": int(ev.activity.nunique()),
        "first_event_utc": str(ev.ts_utc.min()), "last_event_utc": str(ev.ts_utc.max()),
        "cases_by_start_year": {int(k): int(v) for k, v in
                                ev.groupby("case_id")["start_year"].first().value_counts().sort_index().items()},
        "events_per_case": {"min": int(per_case.min()), "median": float(per_case.median()),
                            "max": int(per_case.max()), "mean": round(float(per_case.mean()), 3)},
        "activity_counts": {a: int(c) for a, c in ev.activity.value_counts().items()},
        "role_counts": {r: int(c) for r, c in ev.role.value_counts().items()},
    }

    # 2. variants ---------------------------------------------------------
    var = ev.groupby("case_id")["activity"].agg(tuple).value_counts()
    cum = var.cumsum() / var.sum()
    R["variants"] = {
        "n_variants": int(len(var)),
        "variants_to_cover": {f"{int(p * 100)}%": int((cum < p).sum() + 1) for p in (0.5, 0.8, 0.9, 0.95, 0.99)},
        "top10": [{"rank": i + 1, "cases": int(c), "share": round(float(c / var.sum()), 4),
                   "cumulative_share": round(float(cum.iloc[i]), 4), "sequence": [label(a) for a in v]}
                  for i, (v, c) in enumerate(var.head(10).items())],
    }

    # 3. directly-follows graph -------------------------------------------
    df4 = bpic2020.to_pm4py(ev)
    dfg, starts, ends = pm4py.discover_dfg(df4)
    R["dfg"] = {
        "edges": sorted([{"from": a, "to": b, "count": int(c)} for (a, b), c in dfg.items()],
                        key=lambda e: -e["count"]),
        "start_activities": {a: int(c) for a, c in starts.items()},
        "end_activities": {a: int(c) for a, c in ends.items()},
    }
    draw_dfg(dfg, starts, ends, OUT / "dfg.png")

    # 4. inductive miner and replay fitness --------------------------------
    R["inductive_miner"] = {}
    for name, noise in (("im_noise_0.0", 0.0), ("im_noise_0.2", 0.2)):
        net, im, fm = pm4py.discover_petri_net_inductive(df4, noise_threshold=noise)
        tree = pm4py.discover_process_tree_inductive(df4, noise_threshold=noise)
        fit = pm4py.fitness_token_based_replay(df4, net, im, fm)
        prec = pm4py.precision_token_based_replay(df4, net, im, fm)
        pm4py.write_pnml(net, im, fm, str(OUT / f"{name}.pnml"))
        (OUT / f"{name}_tree.txt").write_bytes((str(tree) + "\n").encode("utf-8"))
        R["inductive_miner"][name] = {
            "noise_threshold": noise,
            "token_replay_log_fitness": round(float(fit["log_fitness"]), 4),
            "token_replay_share_fitting_traces": round(float(fit["perc_fit_traces"]) / 100, 4),
            "token_replay_average_trace_fitness": round(float(fit["average_trace_fitness"]), 4),
            "token_replay_precision": round(float(prec), 4),
            "places": len(net.places), "transitions": len(net.transitions),
            "process_tree": str(tree),
        }
    try:
        net, im, fm = pm4py.discover_petri_net_inductive(df4, noise_threshold=0.2)
        al = pm4py.fitness_alignments(df4, net, im, fm)
        R["inductive_miner"]["im_noise_0.2"]["alignment_log_fitness"] = round(float(al["log_fitness"]), 4)
        R["inductive_miner"]["im_noise_0.2"]["alignment_share_fitting_traces"] = round(
            float(al["percFitTraces"]) / 100, 4)
    except Exception as exc:  # alignments are optional; record why they are missing
        R["inductive_miner"]["im_noise_0.2"]["alignment_error"] = repr(exc)
    # transfer: discover on the 2017 cases (two departments), replay the 2018 cases (whole university)
    case_year = ev.groupby("case_id")["start_year"].first()
    d17 = df4[df4["case:concept:name"].isin(case_year[case_year == 2017].index)]
    d18 = df4[df4["case:concept:name"].isin(case_year[case_year == 2018].index)]
    R["inductive_miner"]["transfer_2017_to_2018"] = {}
    for name, noise in (("im_noise_0.0", 0.0), ("im_noise_0.2", 0.2)):
        net, im, fm = pm4py.discover_petri_net_inductive(d17, noise_threshold=noise)
        f_in = pm4py.fitness_token_based_replay(d17, net, im, fm)
        f_out = pm4py.fitness_token_based_replay(d18, net, im, fm)
        p_in = pm4py.precision_token_based_replay(d17, net, im, fm)
        p_out = pm4py.precision_token_based_replay(d18, net, im, fm)
        R["inductive_miner"]["transfer_2017_to_2018"][name] = {
            "cases_2017": int(d17["case:concept:name"].nunique()),
            "cases_2018": int(d18["case:concept:name"].nunique()),
            "fitness_on_2017": round(float(f_in["log_fitness"]), 4),
            "fitness_on_2018": round(float(f_out["log_fitness"]), 4),
            "share_2018_traces_fitting": round(float(f_out["perc_fit_traces"]) / 100, 4),
            "precision_on_2017": round(float(p_in), 4),
            "precision_on_2018": round(float(p_out), 4),
        }

    # 5. handover network by role -----------------------------------------
    ev["next_role"] = ev.groupby("case_id")["role"].shift(-1)
    pairs = ev.dropna(subset=["next_role"]).groupby(["role", "next_role"]).size()
    hand = pairs[[a != b for a, b in pairs.index]]
    R["handover_by_role"] = {
        "note": "Consecutive events in a case whose roles differ. SYSTEM events have role UNDEFINED.",
        "edges": sorted([{"from": a, "to": b, "count": int(c)} for (a, b), c in hand.items()],
                        key=lambda e: -e["count"]),
        "same_role_consecutive": {a: int(c) for (a, b), c in pairs.items() if a == b},
    }
    try:
        sna = pm4py.discover_handover_of_work_network(df4, resource_key="org:role")
        R["handover_by_role"]["pm4py_crosscheck_edges"] = int(len(sna.connections))
    except Exception as exc:
        R["handover_by_role"]["pm4py_crosscheck_error"] = repr(exc)
    draw_handover(hand, OUT / "handover_by_role.png")

    # 6. outcomes at each approval step ------------------------------------
    steps = {}
    for role in REVIEW_ROLES + ["MISSING"]:
        a = int((ev.activity == APPROVE[role]).sum()) if role in APPROVE else 0
        r = int((ev.activity == REJECT[role]).sum())
        n = a + r
        steps[role] = {"decisions": n, "approved": a, "rejected": r,
                       "rejection_share": round(r / n, 4) if n else None,
                       "rejection_share_95ci_wilson": wilson(r, n) if n else None}
    for role in REVIEW_ROLES:
        by_year = {}
        for year in (2017, 2018):
            g = ev[ev.start_year == year]
            a = int((g.activity == APPROVE[role]).sum())
            r = int((g.activity == REJECT[role]).sum())
            by_year[year] = {"decisions": a + r, "rejected": r,
                             "rejection_share": round(r / (a + r), 4) if a + r else None}
        steps[role]["by_start_year"] = by_year
    # later reviewer rejects after an earlier approval
    after_adm = ev[ev.prev_activity == APPROVE["ADMINISTRATION"]]
    later = {}
    for role in ("BUDGET OWNER", "SUPERVISOR"):
        sub = after_adm[after_adm.activity.isin([APPROVE[role], REJECT[role]])]
        k = int((sub.activity == REJECT[role]).sum())
        later[f"{role} after ADMINISTRATION approval"] = {
            "decisions": int(len(sub)), "rejected": k, "share": round(k / len(sub), 4),
            "share_95ci_wilson": wilson(k, len(sub))}
    sub = ev[ev.prev_activity == APPROVE["BUDGET OWNER"]]
    sub = sub[sub.activity.isin([APPROVE["SUPERVISOR"], REJECT["SUPERVISOR"]])]
    k = int((sub.activity == REJECT["SUPERVISOR"]).sum())
    later["SUPERVISOR after BUDGET OWNER approval"] = {
        "decisions": int(len(sub)), "rejected": k, "share": round(k / len(sub), 4),
        "share_95ci_wilson": wilson(k, len(sub))}
    # rework
    returned = ev[ev.activity == RET].copy()
    returned["next_activity"] = ev.groupby("case_id")["activity"].shift(-1).loc[returned.index]
    resub = returned[returned.next_activity == SUB]
    resub_gap = (ev.loc[resub.index + 1, "ts_utc"].values - resub["ts_utc"].values) / np.timedelta64(1, "D")
    n_sub = ev[ev.activity == SUB].groupby("case_id").size().reindex(cs.case_id, fill_value=0)
    last_act = ev.groupby("case_id")["activity"].last()
    R["outcomes"] = {
        "per_step": steps,
        "note": "Counted per decision event. A resubmitted declaration can be decided more than once by the same role.",
        "later_reviewer_rejects_after_earlier_approval": later,
        "case_outcomes": {
            "paid": int(cs.paid.sum()),
            "ended_unpaid": int((~cs.paid).sum()),
            "unpaid_last_activity": {label(a): int(c) for a, c in last_act[~last_act.index.isin(paid_cases)]
                                     .value_counts().items()},
        },
        "rework": {
            "returned_to_employee": int(len(returned)),
            "resubmitted_next": int(len(resub)),
            "resubmission_share": round(len(resub) / len(returned), 4),
            "resubmission_share_95ci_wilson": wilson(len(resub), len(returned)),
            "time_to_resubmit": gap_summary(resub_gap),
            "submissions_per_case": {int(k): int(v) for k, v in n_sub.value_counts().sort_index().items()},
            "cases_with_more_than_one_submission": int((n_sub > 1).sum()),
        },
    }

    # 7. time between steps -------------------------------------------------
    timing = {}
    pairs_of_interest = [
        (SUB, APPROVE["ADMINISTRATION"]), (SUB, REJECT["ADMINISTRATION"]),
        (SUB, APPROVE["PRE_APPROVER"]), (SUB, APPROVE["SUPERVISOR"]),
        (APPROVE["ADMINISTRATION"], APPROVE["BUDGET OWNER"]), (APPROVE["ADMINISTRATION"], APPROVE["SUPERVISOR"]),
        (APPROVE["ADMINISTRATION"], REJECT["SUPERVISOR"]),
        (APPROVE["BUDGET OWNER"], APPROVE["SUPERVISOR"]), (APPROVE["PRE_APPROVER"], APPROVE["SUPERVISOR"]),
        (APPROVE["SUPERVISOR"], REQ), (REQ, PAID), (RET, SUB),
    ]
    for a, b in pairs_of_interest:
        m = ev[(ev.prev_activity == a) & (ev.activity == b)]
        if len(m) < 30:
            continue
        wk = spans_weekend(m["prev_ts"], m["ts_utc"])
        timing[f"{label(a)} -> {label(b)}"] = {"from": a, "to": b, **gap_summary(m["gap_days"].values, wk)}
    # time to a role's decision (approve or reject), whatever came before: descriptive only
    to_decision = {}
    for role in REVIEW_ROLES:
        acts = [APPROVE[role], REJECT[role]]
        m = ev[ev.activity.isin(acts) & ev.prev_ts.notna()]
        wk = spans_weekend(m["prev_ts"], m["ts_utc"])
        to_decision[role] = gap_summary(m["gap_days"].values, wk)
    # the same, split by the step that handed the declaration to the role
    step_timing, fits = {}, {}
    for key, prev, role, estimable in STEPS:
        m = ev[(ev.prev_activity == prev) & ev.activity.isin([APPROVE[role], REJECT[role]])]
        wk = spans_weekend(m["prev_ts"], m["ts_utc"])
        summ = gap_summary(m["gap_days"].values, wk)
        by_year = {}
        for year in (2017, 2018):
            x = m.loc[m.start_year == year, "gap_days"].values
            if len(x) >= 30:
                q = np.quantile(x, [0.25, 0.5, 0.75, 0.9])
                by_year[year] = {"n": int(len(x)), "median_days": round(float(q[1]), 3),
                                 "p25_days": round(float(q[0]), 3), "p75_days": round(float(q[2]), 3),
                                 "p90_days": round(float(q[3]), 3)}
        step_timing[key] = {"from": prev, "role": role, "estimable_as_review_latency": estimable,
                            **summ, "by_start_year": by_year}
        fits[key] = lognormal_reference_fit(m["gap_days"].values)
    # whole case: first submission to payment, paid cases
    first_sub = ev[ev.activity == SUB].groupby("case_id")["ts_utc"].min()
    paid_ts = ev[ev.activity == PAID].groupby("case_id")["ts_utc"].min()
    tp = ((paid_ts - first_sub.reindex(paid_ts.index)).dt.total_seconds() / 86400).dropna()
    first_appr = ev[ev.activity == APPROVE["SUPERVISOR"]].groupby("case_id")["ts_utc"].max()
    tf = ((first_appr - first_sub.reindex(first_appr.index)).dt.total_seconds() / 86400).dropna()
    R["timing"] = {
        "note": ("Elapsed calendar time between two recorded events. Includes queueing, nights, weekends "
                 "and waiting for information. Not review time."),
        "between_activities": timing,
        "to_role_decision_pooled_descriptive": to_decision,
        "to_role_decision_by_preceding_step": step_timing,
        "lognormal_reference_fits": fits,
        "submission_to_final_supervisor_approval": gap_summary(tf.values),
        "submission_to_payment": gap_summary(tp.values),
    }
    draw_gaps(step_timing, ev, OUT / "time_to_decision_by_step.png")

    # working calendar
    dec = ev[ev.activity.isin(list(APPROVE.values()) + list(REJECT.values()))].copy()
    dec["hour"] = dec.ts_local.dt.hour
    dec["weekday"] = dec.ts_local.dt.dayofweek
    cal = {}
    for role, g in dec.groupby("role"):
        cal[role] = {
            "decisions": int(len(g)),
            "share_weekday_08_18": round(float(((g.weekday < 5) & g.hour.between(8, 17)).mean()), 4),
            "share_weekend": round(float((g.weekday >= 5).mean()), 4),
            "share_22_to_06": round(float(((g.hour >= 22) | (g.hour < 6)).mean()), 4),
            "by_hour": {int(h): int(c) for h, c in g.hour.value_counts().sort_index().items()},
        }
    R["working_calendar"] = cal
    paid_ev = ev[ev.activity == PAID]
    R["payment_batch"] = {
        "events": int(len(paid_ev)),
        "share_17_30_to_17_32": round(float(paid_ev.ts_local.dt.strftime("%H:%M").isin(
            ["17:30", "17:31", "17:32"]).mean()), 4),
        "by_weekday": {int(k): int(v) for k, v in paid_ev.ts_local.dt.dayofweek.value_counts().sort_index().items()},
    }
    weekly = ev[ev.activity == SUB].set_index("ts_local").resample("W-MON").size()
    weekly_2018 = weekly[(weekly.index.year == 2018)]
    R["arrivals"] = {"submissions_per_week_2018": {
        "weeks": int(len(weekly_2018)), "median": float(weekly_2018.median()),
        "p10": float(weekly_2018.quantile(0.1)), "p90": float(weekly_2018.quantile(0.9))}}
    draw_calendar(cal, OUT / "decisions_by_hour.png")

    # 8. approval chain against amount ---------------------------------------
    rows = []
    for cid, g in ev[ev.case_id.isin(paid_cases)].groupby("case_id", sort=False):
        acts = list(g.activity)
        last_sub = max(i for i, a in enumerate(acts) if a == SUB) if SUB in acts else 0
        chain = [r for a in acts[last_sub:] for r, aa in APPROVE.items() if a == aa]
        rows.append({"case_id": cid, "chain": ">".join(ROLE_SHORT[r] for r in chain), "length": len(chain)})
    ch = pd.DataFrame(rows).merge(cs[["case_id", "amount"]], on="case_id")
    ch = ch[ch.amount > 0]
    bins = [0, 25, 50, 100, 250, 500, np.inf]
    labels_b = ["0-25", "25-50", "50-100", "100-250", "250-500", "500+"]
    ch["amount_bin"] = pd.cut(ch.amount, bins=bins, labels=labels_b, right=False)
    tab = pd.crosstab(ch.amount_bin, ch.chain)
    keep = [c for c in tab.columns if tab[c].sum() >= 20]
    bo = ch.groupby("amount_bin", observed=False).apply(lambda g: (g.chain.str.contains("BO").sum(), len(g)))
    rho = stats.spearmanr(ch.amount, ch.length)
    R["chain_vs_amount"] = {
        "note": ("Paid cases with a positive amount; approval roles in the submission round that led to payment. "
                 "Amounts are not exact (challenge page) and their currency is not stated."),
        "cases": int(len(ch)),
        "chain_counts": {k: int(v) for k, v in ch.chain.value_counts().items()},
        "length_counts": {int(k): int(v) for k, v in ch.length.value_counts().sort_index().items()},
        "by_amount_bin": {str(b): {c: int(tab.loc[b, c]) for c in keep} for b in tab.index},
        "share_with_budget_owner_step": {str(b): {"cases": int(n), "with_BO": int(k),
                                                  "share": round(k / n, 4) if n else None,
                                                  "share_95ci_wilson": wilson(int(k), int(n)) if n else None}
                                         for b, (k, n) in bo.items()},
        "spearman_amount_vs_length": {"rho": round(float(rho.statistic), 4), "p_value": float(rho.pvalue)},
        "median_amount_by_length": {int(k): round(float(v), 2) for k, v in ch.groupby("length").amount.median().items()},
    }
    draw_chain(R["chain_vs_amount"], OUT / "budget_owner_share_by_amount.png")

    # 9. 2017 (two departments) against 2018 (whole university)
    chy = pd.DataFrame(rows)
    chy["start_year"] = chy.case_id.map(case_year)
    route_by_year = {}
    for year, g in chy.groupby("start_year"):
        vc = g.chain.value_counts(normalize=True)
        route_by_year[int(year)] = {k: round(float(v), 4) for k, v in vc.items() if k}
    R["year_comparison"] = {
        "note": ("2017 covers two departments and 2018 the whole university, so differences mix organisational "
                 "scope with time."),
        "paid_cases": {int(y): int(n) for y, n in chy.start_year.value_counts().sort_index().items()},
        "route_shares_paid_round": route_by_year,
        "rejection_share_by_role": {role: R["outcomes"]["per_step"][role]["by_start_year"] for role in REVIEW_ROLES},
        "time_to_decision_median_by_step": {
            k: {int(y): v["median_days"] for y, v in t["by_start_year"].items()}
            for k, t in R["timing"]["to_role_decision_by_preceding_step"].items()},
        "transfer_2017_model_on_2018": R["inductive_miner"]["transfer_2017_to_2018"],
    }

    (OUT / "results.json").write_bytes((json.dumps(R, indent=2, ensure_ascii=False, default=str) + "\n")
                                       .encode("utf-8"))
    write_spec(R, git)
    write_records(R, git)
    print("E3 done:", OUT / "results.json")


# ---------------------------------------------------------------- figures

POS = {  # hand layout: stages left to right, rejections below
    "Declaration SAVED by EMPLOYEE": (0, 1.2), SUB: (0, 0),
    APPROVE["ADMINISTRATION"]: (1, 0.6), APPROVE["PRE_APPROVER"]: (1, -0.6),
    APPROVE["BUDGET OWNER"]: (2, 0.9), APPROVE["SUPERVISOR"]: (3, 0),
    REQ: (4, 0), PAID: (5, 0),
    REJECT["ADMINISTRATION"]: (1, -1.8), REJECT["PRE_APPROVER"]: (1.5, -2.6),
    REJECT["BUDGET OWNER"]: (2, -1.8), REJECT["SUPERVISOR"]: (3, -1.8), REJECT["MISSING"]: (4, -1.4),
    RET: (0.6, -3.2),
    "Declaration FOR_APPROVAL by SUPERVISOR": (5, -2.6), "Declaration FOR_APPROVAL by PRE_APPROVER": (5, -3.0),
    "Declaration FOR_APPROVAL by ADMINISTRATION": (5, -3.4),
}


def draw_dfg(dfg, starts, ends, path: Path, min_count: int = 20) -> None:
    g = nx.DiGraph()
    for (a, b), c in dfg.items():
        if c >= min_count:
            g.add_edge(a, b, count=c)
    fig, ax = plt.subplots(figsize=(13, 7.5))
    pos = {n: POS.get(n, (5, -3.8)) for n in g.nodes}
    widths = [0.4 + 4 * np.log10(g[u][v]["count"]) / np.log10(12000) for u, v in g.edges]
    nx.draw_networkx_edges(g, pos, ax=ax, width=widths, edge_color="#7a8699", arrowsize=12,
                           connectionstyle="arc3,rad=0.12", min_source_margin=18, min_target_margin=18)
    nx.draw_networkx_edge_labels(g, pos, ax=ax, edge_labels={(u, v): f"{g[u][v]['count']:,}" for u, v in g.edges},
                                 font_size=7, label_pos=0.45, connectionstyle="arc3,rad=0.12")
    for n, (x, y) in pos.items():
        colour = "#f4d6d2" if "REJECTED" in n else ("#dfe8f7" if n in (REQ, PAID) else "#e8f0e3")
        ax.text(x, y, label(n).replace(" ", "\n", 1), ha="center", va="center", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.35", fc=colour, ec="#555555", lw=0.6))
    ax.set_title(f"BPIC 2020 Domestic Declarations: directly-follows graph (edges with at least {min_count} "
                 f"occurrences; counts observed)", fontsize=10)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def draw_handover(hand: pd.Series, path: Path) -> None:
    g = nx.DiGraph()
    for (a, b), c in hand.items():
        if c >= 20:
            g.add_edge(a, b, count=c)
    pos = {"EMPLOYEE": (0, 0), "ADMINISTRATION": (1, 0.8), "PRE_APPROVER": (1, -0.8), "BUDGET OWNER": (2, 1.0),
           "SUPERVISOR": (3, 0), "UNDEFINED": (4, 0), "MISSING": (3.5, -1.2)}
    pos = {n: pos.get(n, (4, -1)) for n in g.nodes}
    fig, ax = plt.subplots(figsize=(10, 5.5))
    widths = [0.4 + 4 * np.log10(g[u][v]["count"]) / np.log10(12000) for u, v in g.edges]
    nx.draw_networkx_edges(g, pos, ax=ax, width=widths, edge_color="#7a8699", arrowsize=12,
                           connectionstyle="arc3,rad=0.15", min_source_margin=22, min_target_margin=22)
    nx.draw_networkx_edge_labels(g, pos, ax=ax, edge_labels={(u, v): f"{g[u][v]['count']:,}" for u, v in g.edges},
                                 font_size=7, connectionstyle="arc3,rad=0.15")
    for n, (x, y) in pos.items():
        ax.text(x, y, "SYSTEM" if n == "UNDEFINED" else n.title(), ha="center", va="center", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.4", fc="#eef2f7", ec="#555555", lw=0.6))
    ax.set_title("Handover of work between roles (consecutive events, different roles; at least 20; observed)",
                 fontsize=10)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def draw_gaps(step_timing: dict, ev: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.2))
    bins = np.logspace(np.log10(1 / 1440), np.log10(200), 60)
    for key, prev, role, estimable in STEPS:
        m = ev[(ev.prev_activity == prev) & ev.activity.isin([APPROVE[role], REJECT[role]])]
        x = m.gap_days.clip(lower=1 / 1440)
        ax.hist(x, bins=bins, histtype="step", lw=1.5, ls="-" if estimable == "partly" else ":",
                label=f"{key.replace('_', ' ')} (n={len(x):,}, median {step_timing[key]['median_days']:.2f} d)")
    for d, t in ((1 / 24, "1 hour"), (1, "1 day"), (7, "1 week"), (30, "30 days")):
        ax.axvline(d, color="#bbbbbb", lw=0.8, ls="--")
        ax.text(d, ax.get_ylim()[1] * 0.97, t, fontsize=7, color="#777777", ha="center", va="top")
    ax.set_xscale("log")
    ax.set_xlabel("Days from the previous event in the case to the role's decision (log scale)")
    ax.set_ylabel("Decisions")
    ax.set_title("Time to a decision by the step before it (observed). Solid: later steps, partly informative as an "
                 "upper envelope; dotted: straight after submission, not review time", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def draw_calendar(cal: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for role in REVIEW_ROLES:
        h = cal[role]["by_hour"]
        n = cal[role]["decisions"]
        ax.plot(range(24), [h.get(i, 0) / n for i in range(24)], marker="o", ms=3, lw=1.4, label=role.title())
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Hour of decision, local time")
    ax.set_ylabel("Share of the role's decisions")
    ax.set_title("When decisions are recorded, by role (observed)", fontsize=10)
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def draw_chain(c: dict, path: Path) -> None:
    rows = [(b, v["share"], v["share_95ci_wilson"], v["cases"]) for b, v in c["share_with_budget_owner_step"].items()]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(rows))
    y = np.array([r[1] for r in rows])
    lo = np.array([r[2][0] for r in rows])
    hi = np.array([r[2][1] for r in rows])
    ax.errorbar(x, y, yerr=[y - lo, hi - y], fmt="o", color="#3b6fb6", capsize=4)
    for i, r in enumerate(rows):
        ax.text(i, hi[i] + 0.01, f"n={r[3]:,}", ha="center", fontsize=8, color="#555555")
    ax.set_xticks(x, [r[0] for r in rows])
    ax.set_xlabel("Declared amount (inexact, currency not stated)")
    ax.set_ylabel("Share of paid cases with a budget-owner step")
    ax.set_title("Budget-owner step by declared amount, with 95% Wilson intervals (observed)", fontsize=10)
    ax.set_ylim(0, max(hi) + 0.08)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- spec and records

def rid(name: str) -> str:
    return f"{name}.bpic2020"


def write_spec(R: dict, git: dict) -> None:
    acts = R["counts"]["activity_counts"]

    def kind(a: str) -> str:
        if a in (SUB, SAVED):
            return "submission"
        if a == RET:
            return "returned_to_employee"
        if "APPROVED" in a:
            return "approval"
        if "REJECTED" in a:
            return "rejection"
        if "FOR_APPROVAL" in a:
            return "rare_status"
        return "system_payment"

    spec = {
        "spec_version": "0.1",
        "name": "BPIC 2020 Domestic Declarations, observed workflow",
        "status": "observed",
        "status_note": ("Everything here is what the log shows. The formal rules and permissions behind the paths "
                        "are not in the log and are not inferred."),
        "source": bpic2020.SOURCE,
        "generated_utc": R["generated_utc"],
        "versions": {**git, "analysis": ANALYSIS},
        "case_notion": "one travel expense declaration (trace)",
        "timestamp_semantics": ("single timestamp per event: when the step was recorded; local Dutch time with "
                                "UTC offset; whole seconds; no start-of-work events"),
        "roles": sorted(R["counts"]["role_counts"]),
        "role_note": ("Individuals are anonymised (resource is STAFF MEMBER or SYSTEM). UNDEFINED is the SYSTEM "
                      "role. MISSING is a role the log does not name. No director appears."),
        "activities": [{"name": a, "label": label(a), "kind": kind(a), "count": c} for a, c in acts.items()],
        "start_activities": R["dfg"]["start_activities"],
        "end_activities": R["dfg"]["end_activities"],
        "transitions": R["dfg"]["edges"],
        "variants": {"n_variants": R["variants"]["n_variants"],
                     "variants_to_cover": R["variants"]["variants_to_cover"],
                     "top10": R["variants"]["top10"]},
        "review_steps": [
            {"role": role, "approve_activity": APPROVE[role], "reject_activity": REJECT[role],
             "outcomes": R["outcomes"]["per_step"][role],
             "time_to_decision_by_preceding_step": {
                 key: {k: R["timing"]["to_role_decision_by_preceding_step"][key][k]
                       for k in ("n", "median_days", "p25_days", "p75_days", "p90_days",
                                 "estimable_as_review_latency")}
                 for key, prev, rl, est in STEPS if rl == role},
             "evidence_ids": [rid(f"rejection_share.{role.lower().replace(' ', '_')}")]
                             + [rid(f"time_to_decision.{key}") for key, prev, rl, est in STEPS if rl == role]}
            for role in REVIEW_ROLES],
        "observed_routes_in_paid_round": R["chain_vs_amount"]["chain_counts"],
        "rework_loop": {"from": RET, "to": SUB, "resubmission_share": R["outcomes"]["rework"]["resubmission_share"],
                        "evidence_ids": [rid("resubmission")]},
        "release": {"activities": [REQ, PAID], "note": "Payment runs as a batch on Mondays and Thursdays at about 17:30.",
                    "evidence_ids": [rid("payment_batch_schedule")]},
        "discovered_models": {k: {kk: v[kk] for kk in ("noise_threshold", "token_replay_log_fitness",
                                                        "token_replay_precision", "process_tree")}
                              for k, v in R["inductive_miner"].items() if k.startswith("im_")},
        "not_in_log": [
            "formal approval rules and permissions (for example when the budget-owner step is skipped)",
            "who the individual reviewers are, and how many people hold each role",
            "start of work on a declaration, review effort, queue position",
            "reasons for rejection, and whether a declaration was actually wrong",
            "anything about errors reaching payment",
        ],
    }
    SPEC.parent.mkdir(parents=True, exist_ok=True)
    SPEC.write_bytes((json.dumps(spec, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def write_records(R: dict, git: dict) -> None:
    for old in evidence.RECORDS_DIR.glob("*.bpic2020.json"):  # this script owns every *.bpic2020 record
        old.unlink()
    created = R["generated_utc"]
    versions = {**git, "analysis": ANALYSIS, "model": None}
    common = {"source": bpic2020.SOURCE, "versions": versions, "disagreements": [], "tests": [],
              "created_utc": created}
    conditions = ("Eindhoven University of Technology travel expense declarations (domestic), 2017 two departments, "
                  "2018 whole university; staff anonymised to roles")
    recs = []

    recs.append({"id": rid("log_size_and_variants"),
                 "mechanism": "How many declarations, events and distinct paths the process produced",
                 "measures": "Counts of traces, events, activities and distinct activity sequences in the file",
                 "simulator_parameter": None, "estimable": "yes",
                 "value": {"summary": {"cases": R["counts"]["cases"], "events": R["counts"]["events"],
                                       "activities": R["counts"]["activities"],
                                       "variants": R["variants"]["n_variants"],
                                       "variants_to_cover": R["variants"]["variants_to_cover"]}},
                 "status": "observed", "conditions": conditions,
                 "transfer": "None. Descriptive of this log.", **common})

    recs.append({"id": rid("directly_follows_graph"),
                 "mechanism": "Which step follows which in practice",
                 "measures": "Counts of directly-follows pairs of activities within cases",
                 "simulator_parameter": None, "estimable": "yes",
                 "value": {"table": R["dfg"]["edges"]},
                 "status": "observed", "conditions": conditions,
                 "transfer": "None directly. The observed paths are not the formal rules.", **common})

    im = R["inductive_miner"]
    recs.append({"id": rid("inductive_miner_fitness"),
                 "mechanism": "How well a discovered process model describes the observed paths",
                 "measures": ("Token-replay fitness and precision of inductive-miner models discovered from this "
                              "same log (noise 0.0 fits by construction), plus fitness and precision of a model "
                              "discovered on 2017 cases when replaying 2018 cases"),
                 "simulator_parameter": None, "estimable": "yes",
                 "value": {"summary": im},
                 "status": "fitted", "conditions": conditions,
                 "transfer": "None. Describes the declarations process only.", **common})

    recs.append({"id": rid("handover_by_role"),
                 "mechanism": "Which role hands work to which",
                 "measures": "Counts of consecutive events in a case whose roles differ",
                 "simulator_parameter": None, "estimable": "yes",
                 "value": {"table": R["handover_by_role"]["edges"]},
                 "status": "observed", "conditions": conditions,
                 "transfer": "None directly. Shows a sequential approval chain with a return loop to the submitter.",
                 **common})

    for role in REVIEW_ROLES:
        s = R["outcomes"]["per_step"][role]
        key = role.lower().replace(" ", "_")
        recs.append({
            "id": rid(f"rejection_share.{key}"),
            "mechanism": f"How often the {role.title()} step returns a declaration rather than approving it",
            "measures": ("Share of this role's decision events that are rejections. Reasons are not recorded, nor "
                         "whether the declaration was wrong. Mixes caught errors, missing paperwork and policy "
                         "refusals, and misses errors nobody caught."),
            "simulator_parameter": "share of items returned at a review step (not detection probability)",
            "estimable": "yes",
            "estimable_note": "Estimable as an observed return rate. Not estimable as the chance of catching an error.",
            "value": {"unit": "share of decisions", "n": s["decisions"], "point": s["rejection_share"],
                      "interval_95": s["rejection_share_95ci_wilson"],
                      "interval_95_meaning": ("Wilson interval treating decisions as independent. Decisions "
                                              "cluster within cases and within reviewers the log cannot identify, "
                                              "so it understates uncertainty; the 2017 and 2018 shares in the "
                                              "summary show the spread across organisational scope."),
                      "summary": {"by_start_year": s["by_start_year"]}},
            "status": "observed", "conditions": conditions + f"; {role.title()} step",
            "transfer": ("Analogue plausibility range for how often a quotation review returns a quote. Must not be "
                         "used as a detection rate."), **common})

    for key, prev, role, est in STEPS:
        t = R["timing"]["to_role_decision_by_preceding_step"][key]
        informative = est == "partly"
        recs.append({
            "id": rid(f"time_to_decision.{key}"),
            "mechanism": f"Time from '{label(prev)}' to the {role.title()} decision that follows it",
            "measures": ("Elapsed calendar time between the two recorded events. Includes queueing, nights, weekends, "
                         "notification delay and waiting for information. Not review time."),
            "simulator_parameter": ("review latency range for a quotation reviewer (upper envelope)" if informative
                                    else None),
            "estimable": est,
            "estimable_note": (
                "No start-of-work events and no queue position, so work time cannot be separated out; usable only "
                "as an upper envelope." if informative else
                f"Not review latency: {t['share_under_1_hour']:.0%} of these gaps are under an hour, so the two "
                "events are recorded together or the step is near-instant; the log cannot tell which."),
            "value": {"unit": "days", "n": t["n"], "distribution": "empirical", "summary": t,
                      "interval_95": [t["p2_5_days"], t["p97_5_days"]],
                      "interval_95_meaning": "central 95% of observed gaps (2.5th to 97.5th percentile), not a CI"},
            "use": "range_only" if informative else "descriptive",
            "status": "observed", "conditions": conditions + f"; {label(prev)} then {role.title()}",
            "transfer": ("Analogue range for how long a quotation reviewer takes to respond at a comparable load, as "
                         "an upper envelope (it includes queueing). Use the empirical quantiles; no fitted "
                         "distribution is endorsed." if informative else "None as review latency."),
            **common})

    fits = R["timing"]["lognormal_reference_fits"]
    recs.append({"id": rid("lognormal_fits"),
                 "mechanism": "Candidate parametric forms for the elapsed gaps between steps",
                 "measures": ("A lognormal fitted by maximum likelihood to the positive gaps of each step, with its "
                              "Kolmogorov-Smirnov statistic and the mean and 99th percentile it implies, next to the "
                              "observed ones"),
                 "simulator_parameter": None, "estimable": "no",
                 "estimable_note": ("Reference only, not a sampler. The fits are poor (KS well above what n supports) "
                                    "and imply far longer tails than observed, for example a 67-day mean against an "
                                    "observed 2-day mean for the pooled supervisor gaps before this split."),
                 "value": {"table": fits}, "use": "reference_only",
                 "status": "fitted", "conditions": conditions,
                 "transfer": "None. Not selected for simulation.", **common})

    rw = R["outcomes"]["rework"]
    recs.append({"id": rid("resubmission"),
                 "mechanism": "A returned declaration is corrected and resubmitted, or abandoned",
                 "measures": ("Share of 'returned to employee' events followed directly by a new submission, and "
                              "the elapsed time between them"),
                 "simulator_parameter": "correction loop: chance a returned item is resubmitted, and time to resubmit",
                 "estimable": "yes",
                 "value": {"unit": "share; days", "n": rw["returned_to_employee"], "point": rw["resubmission_share"],
                           "interval_95": rw["resubmission_share_95ci_wilson"],
                           "interval_95_meaning": "Wilson interval for the resubmission share",
                           "summary": {"time_to_resubmit": rw["time_to_resubmit"]}},
                 "use": "range_only",
                 "status": "observed", "conditions": conditions,
                 "transfer": "Analogue range for a quote returned to its drafter. Elapsed time includes other work.",
                 **common})

    recs.append({"id": rid("year_comparison"),
                 "mechanism": "Whether routes, return shares and step times differ between 2017 and 2018",
                 "measures": ("Route shares in the paid round, rejection shares per role, median time to decision per "
                              "step, and the 2017-discovered model's fitness and precision on 2018, by the case's "
                              "start year"),
                 "simulator_parameter": None, "estimable": "yes",
                 "value": {"summary": R["year_comparison"]}, "use": "descriptive",
                 "status": "observed", "conditions": conditions,
                 "transfer": ("The spread between the two years is a better guide to how much these quantities vary "
                              "than the Wilson intervals, which assume independent decisions."), **common})

    later = R["outcomes"]["later_reviewer_rejects_after_earlier_approval"]
    recs.append({"id": rid("later_reviewer_rejection_after_approval"),
                 "mechanism": "A later reviewer returns a declaration that an earlier reviewer approved",
                 "measures": "Share of later-step decisions that are rejections when the previous event was an approval",
                 "simulator_parameter": None, "estimable": "yes",
                 "estimable_note": "Observed disagreement rate between sequential steps. Says nothing about who was right.",
                 "value": {"table": later},
                 "status": "observed", "conditions": conditions,
                 "transfer": "Weak. Shows sequential reviewers disagree at a low observed rate.", **common})

    recs.append({"id": rid("working_calendar"),
                 "mechanism": "When review decisions are made",
                 "measures": "Hour and weekday of decision events by role, local time",
                 "simulator_parameter": "working calendar for reviewers",
                 "estimable": "yes",
                 "value": {"table": {r: {k: v for k, v in c.items() if k != "by_hour"}
                                     for r, c in R["working_calendar"].items()}},
                 "status": "observed", "conditions": conditions,
                 "transfer": "Analogue: office reviewers decide mostly in weekday working hours.", **common})

    recs.append({"id": rid("payment_batch_schedule"),
                 "mechanism": "Payment of approved declarations",
                 "measures": "Time of day and weekday of 'Payment Handled' events",
                 "simulator_parameter": None, "estimable": "yes",
                 "value": {"summary": R["payment_batch"]},
                 "status": "observed", "conditions": conditions,
                 "transfer": "None. A payment batch schedule, not processing.", **common})

    recs.append({"id": rid("arrivals"),
                 "mechanism": "Submission of declarations",
                 "measures": "Submissions per week, 2018 (whole university)",
                 "simulator_parameter": None, "estimable": "yes",
                 "value": {"summary": R["arrivals"]},
                 "status": "observed", "conditions": conditions,
                 "transfer": "None. Quotation arrivals are a different process.", **common})

    c = R["chain_vs_amount"]
    recs.append({"id": rid("approval_chain_vs_amount"),
                 "mechanism": "Whether larger declarations pass more approvers",
                 "measures": ("Approval roles in the paid submission round against the declared amount (inexact), "
                              "for paid cases with a positive amount"),
                 "simulator_parameter": "value-based escalation (example of association, not a threshold)",
                 "estimable": "partly",
                 "estimable_note": ("Association only. Amounts are perturbed, and whether the budget owner is also the "
                                    "supervisor changes the path but is not recorded."),
                 "value": {"n": c["cases"], "table": c["share_with_budget_owner_step"],
                           "summary": {"spearman_amount_vs_length": c["spearman_amount_vs_length"],
                                       "chain_counts": c["chain_counts"]}},
                 "status": "observed", "conditions": conditions,
                 "transfer": "Example only. No threshold transfers to quotations.", **common})

    for r in recs:
        evidence.write(r)


if __name__ == "__main__":
    main()
