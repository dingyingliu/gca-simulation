"""Two-driver sweep for the E4 speed conclusions.

The one-at-a-time flip points sweep only each conclusion's top two drivers, so head-office review effort never
appeared, although the speed reversals need a slow head office as well as quick lead reviews. This sweeps
`effort_lead` against `effort_ho` over their declared ranges, every other parameter at its central value, in the
main configuration (isolated notes, notes record drafted terms, policy gate on), development weeks pooled, 64
seeds. It reports days to customer and head-office utilisation for each design, and the difference in days for
each pair of designs. The 64 parameter draws of the development run are overlaid, marked by the sign of their own
difference, when `data/derived/e4_development.npz` is present.

Two slices: the lead's response delay (`delay_lead`) at its central value, and at 0.1 days. The first run showed
that with the central delay no point of the plane reverses a speed conclusion involving Review every quote,
while the draws that do reverse one all have short lead response delays (0.04 to 0.33 days).

    .venv/Scripts/python.exe experiments/e4_quotation/two_driver_sweep.py
"""

from __future__ import annotations

import hashlib
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

OUT = ROOT / "reports" / "E4"
CASES_DIR = ROOT / "specs" / "simulated_weeks"
MANIFEST = Path(__file__).resolve().parent / "heldout_manifest.json"
RAW = ROOT / "data" / "derived" / "e4_development.npz"
RESULTS = OUT / "results.json"
ASSUMPTIONS = ROOT / "evidence" / "assumptions.yaml"
PROVENANCE = ["gca_sim/simulator", "experiments/e4_quotation", "evidence/assumptions.yaml", "specs/simulated_weeks"]
GRID = 16
SEEDS = list(range(64))
PAIRS = [("review", "local"), ("review", "limits"), ("limits", "local")]
SLICES = {"delay_lead central": None, "delay_lead 0.1": 0.1}
_cases = None


def development_cases() -> list[truth.Case]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = []
    for fname, meta in manifest["development"].items():
        case = truth.Case.from_json((CASES_DIR / fname).read_text(encoding="utf-8"))
        if case.sha256() != meta["sha256"]:
            raise SystemExit(f"{fname} does not match the frozen manifest")
        cases.append(case)
    return cases


def point(task: tuple) -> tuple:
    """Mean days, head-office utilisation and the largest lead utilisation per design at one grid point."""
    global _cases
    if _cases is None:
        _cases = development_cases()
    name, i, j, lead, ho, delay_lead = task
    p = replace(params.central(), effort_lead=lead, effort_ho=ho)
    if delay_lead is not None:
        p = replace(p, delay_lead=delay_lead)
    out = {d: {"days_mean": [], "ho_util": [], "lead_util_max": []} for d in designs.DESIGNS}
    for case in _cases:
        ents = streams.case_entities(case)
        for seed in SEEDS:
            s = streams.Streams(seed, ents)
            for d in designs.DESIGNS:
                m = engine.simulate(case, designs.DESIGNS[d], "isolated", p, s).measures
                for k in out[d]:
                    out[d][k].append(float(m[k]))
    return name, i, j, {d: {k: float(np.mean(v)) for k, v in ms.items()} for d, ms in out.items()}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def development_draws(raw: Path = RAW, results: Path = RESULTS, assumptions: Path = ASSUMPTIONS,
                      manifest: Path = MANIFEST) -> dict:
    """The development run's own draws, for the overlay: effort values and each pair's days difference.

    Used only when the local cache belongs to the committed development run and to the current ranges and weeks:
    its data fingerprint matches the one in reports/E4/results.json, its assumptions and manifest hashes match the
    current files, and it carries its own draw coordinates, which are used instead of regenerating them. Otherwise the overlay is omitted, with the reason."""
    if not raw.exists():
        return {"omitted": f"no development cache at {raw.name}"}
    with np.load(raw) as z:
        needed = ("data", "configs", "measures", "draw_params", "param_names", "assumptions_sha256",
                  "heldout_manifest_sha256", "data_sha256")
        missing = [k for k in needed if k not in z.files]
        if missing:
            return {"omitted": f"the development cache predates its fingerprints (missing {', '.join(missing)})"}
        data, labels, measures = z["data"], list(z["configs"]), list(z["measures"])
        draw_params, names = z["draw_params"], list(z["param_names"])
        stored = {k: str(z[k]) for k in ("assumptions_sha256", "heldout_manifest_sha256", "data_sha256")}
    committed = json.loads(results.read_text(encoding="utf-8")).get("raw_data_sha256") if results.exists() else None
    if evidence.array_sha256(data) != stored["data_sha256"] or stored["data_sha256"] != committed:
        return {"omitted": "the development cache is not the committed development run's"}
    if stored["assumptions_sha256"] != _sha(assumptions.read_bytes()):
        return {"omitted": "the declared ranges changed after the development run"}
    if stored["heldout_manifest_sha256"] != _sha(manifest.read_bytes()):
        return {"omitted": "the case manifest changed after the development run"}
    m = measures.index("days_mean")
    out = {"source": "the development run in reports/E4/results.json (fingerprints checked)",
           "effort_lead": [round(float(v), 4) for v in draw_params[:, names.index("effort_lead")]],
           "effort_ho": [round(float(v), 4) for v in draw_params[:, names.index("effort_ho")]]}
    for x, y in PAIRS:
        ia, ib = labels.index(f"full|{x}|isolated|draft"), labels.index(f"full|{y}|isolated|draft")
        out[f"{x}-{y}"] = [round(float(v), 4) for v in (data[:, :, ia, :, m] - data[:, :, ib, :, m]).mean(axis=(0, 2))]
    return out


def figure(res: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lead, ho = np.array(res["effort_lead"]), np.array(res["effort_ho"])
    fig, grid_axes = plt.subplots(len(SLICES), 3, figsize=(16, 4.6 * len(SLICES)), sharex=True, sharey=True)
    lim = max(float(np.abs(np.array(sl["pairs"][f"{x}-{y}"]["days_difference"])).max())
              for sl in res["slices"].values() for x, y in PAIRS) or 1.0
    for row, (name, sl) in zip(grid_axes, res["slices"].items()):
        _panels(fig, row, name, sl, lead, ho, lim, res.get("development_draws"))
    for ax in grid_axes[:, 0]:
        ax.set_ylabel("effort per head-office review (days)")
    for ax in grid_axes[-1]:
        ax.set_xlabel("effort per lead review (days)")
    dev = res.get("development_draws") or {}
    if "omitted" not in dev:
        for ax in grid_axes[0]:  # each column names its own first design
            ax.legend(fontsize=7, frameon=True, loc="upper right")
    marks = ("Marks: the 64 development draws, which vary every parameter." if "omitted" not in dev
             else f"Development draws not shown: {dev['omitted']}.")
    fig.suptitle("Speed conclusions across lead and head-office review effort, at two lead response delays (others at "
                 f"central values; black line: no difference). {marks} Assumed parameters.", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "two_driver_days.png", dpi=150)
    plt.close(fig)


def _panels(fig, axes, name, sl, lead, ho, lim, dev) -> None:
    from matplotlib.colors import TwoSlopeNorm

    for ax, (x, y) in zip(axes, PAIRS):
        z = np.array(sl["pairs"][f"{x}-{y}"]["days_difference"])  # [effort_ho, effort_lead]
        mesh = ax.pcolormesh(lead, ho, z, cmap="RdBu_r", norm=TwoSlopeNorm(0.0, -lim, lim), shading="nearest")
        if z.min() < 0 < z.max():
            ax.contour(lead, ho, z, levels=[0.0], colors="black", linewidths=1.2)
        if dev and "omitted" not in dev:
            dd = np.array(dev[f"{x}-{y}"])
            el, eh = np.array(dev["effort_lead"]), np.array(dev["effort_ho"])
            first_slower = dd > 0
            ax.scatter(el[first_slower], eh[first_slower], s=14, facecolors="none", edgecolors="#333333", lw=0.8,
                       label=f"draw: {designs.DESIGNS[x].name} slower")
            ax.scatter(el[~first_slower], eh[~first_slower], s=40, marker="x", color="#000000", lw=1.4,
                       label=f"draw: {designs.DESIGNS[x].name} faster or equal")
        ax.set_title(f"{designs.DESIGNS[x].name} minus {designs.DESIGNS[y].name}\ndays to customer ({name})",
                     fontsize=9)
        fig.colorbar(mesh, ax=ax, fraction=0.046, pad=0.02)


def main() -> None:
    ranges = params.ranges()
    lead = np.linspace(*ranges["effort_lead"], GRID)
    ho = np.linspace(*ranges["effort_ho"], GRID)
    tasks = [(name, i, j, float(lead[j]), float(ho[i]), dl) for name, dl in SLICES.items()
             for i in range(GRID) for j in range(GRID)]
    grid = {}
    with ProcessPoolExecutor(max_workers=16) as ex:
        for name, i, j, vals in ex.map(point, tasks, chunksize=4):
            grid[(name, i, j)] = vals
    res = {"generated_utc": evidence.utc_now(),
           "versions": evidence.git_state(PROVENANCE),
           "method": (f"{GRID} x {GRID} grid over the declared ranges of effort_lead and effort_ho, at two values of "
                      "delay_lead (its central value and 0.1 days), every other parameter at its central value; "
                      "isolated notes, notes record drafted terms, policy gate on; development weeks pooled, 64 seeds. "
                      "Matrices are indexed [effort_ho][effort_lead]."),
           "effort_lead": [round(float(v), 4) for v in lead], "effort_ho": [round(float(v), 4) for v in ho],
           "slices": {}}
    for name, dl in SLICES.items():
        sl = {"delay_lead": round(params.central().delay_lead if dl is None else dl, 4), "designs": {}, "pairs": {}}
        for d in designs.DESIGNS:
            sl["designs"][d] = {k: [[round(grid[(name, i, j)][d][k], 4) for j in range(GRID)] for i in range(GRID)]
                                for k in ("days_mean", "ho_util", "lead_util_max")}
        for x, y in PAIRS:
            z = [[round(grid[(name, i, j)][x]["days_mean"] - grid[(name, i, j)][y]["days_mean"], 4)
                  for j in range(GRID)] for i in range(GRID)]
            flat = np.array(z)
            sl["pairs"][f"{x}-{y}"] = {
                "days_difference": z,
                "share_of_grid_where_first_is_faster": round(float((flat < 0).mean()), 4),
                "first_faster_at": [{"effort_lead": res["effort_lead"][j], "effort_ho": res["effort_ho"][i],
                                     "difference": z[i][j],
                                     "ho_util": {x: sl["designs"][x]["ho_util"][i][j],
                                                 y: sl["designs"][y]["ho_util"][i][j]}}
                                    for i in range(GRID) for j in range(GRID) if z[i][j] < 0]}
        res["slices"][name] = sl
    res["development_draws"] = development_draws()
    (OUT / "two_driver_sweep.json").write_bytes((json.dumps(res, indent=1) + "\n").encode("utf-8"))
    figure(res)
    for name, sl in res["slices"].items():
        for k, v in sl["pairs"].items():
            print(name, k, "first faster on", v["share_of_grid_where_first_is_faster"], "of the grid")


if __name__ == "__main__":
    main()
