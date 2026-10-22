"""Power of the E5 pilot's held-out calibration diagnostic, computed before any run.

Version 2. Version 1 drew held-out tasks independently from a pooled task set,
which loses the within-group dependence the pilot is designed to create. This version:

  - simulates each group with a group-level rate around the true rate (Beta, concentration KAPPA_GROUP; no
    group effect when KAPPA_GROUP is None) and tasks within the group around the group's rate (Beta,
    concentration 6), each task's outcome the mean of 3 replicates;
  - forms the 90% predictive interval for the held-out mean by a two-level bootstrap over whole groups:
    resample the 5 development groups with replacement, then draw the H held-out groups from that resample,
    and average over all their tasks; 5th and 95th percentiles of 10,000 such draws;
  - flags a quantity when the observed held-out mean (over all tasks of the H held-out groups) falls outside.

    .venv/Scripts/python.exe experiments/agent_pilot_heldout_power.py
"""

import json

import numpy as np

RNG = np.random.default_rng(20261002)
REPLICATES = 3
GROUPS_DEV = 5
B = 10000
SIMS = 1000
KAPPA_TASK = 6.0


def beta_around(mean, kappa, size):
    a, b = max(mean * kappa, 1e-3), max((1 - mean) * kappa, 1e-3)
    return RNG.beta(a, b, size)


def groups(rate, n_groups, tasks_per_group, kappa_group):
    """Array [groups, tasks] of task outcomes (mean of replicates)."""
    g_rate = np.full(n_groups, rate) if kappa_group is None else beta_around(rate, kappa_group, n_groups)
    p = np.stack([beta_around(gr, KAPPA_TASK, tasks_per_group) for gr in g_rate])
    return RNG.binomial(REPLICATES, p) / REPLICATES


def interval(dev, h):
    g = dev.shape[0]
    outer = RNG.integers(0, g, size=(B, g))                 # resample development groups
    inner = RNG.integers(0, g, size=(B, h))                 # draw held-out groups from the resample
    picked = np.take_along_axis(outer, inner, axis=1)       # [B, h] indices into dev groups
    means = dev[picked].reshape(B, -1).mean(axis=1)
    return np.quantile(means, [0.05, 0.95])


def flag_rate(dev_rate, held_rate, tasks_per_group, h, kappa_group):
    flags = 0
    for _ in range(SIMS):
        lo, hi = interval(groups(dev_rate, GROUPS_DEV, tasks_per_group, kappa_group), h)
        z = groups(held_rate, h, tasks_per_group, kappa_group).mean()
        flags += (z < lo) or (z > hi)
    return round(flags / SIMS, 3)


def main():
    out = {"version": 2, "settings": {"replicates": REPLICATES, "development_groups": GROUPS_DEV, "bootstrap": B,
                                       "simulated_pilots": SIMS, "task_concentration": KAPPA_TASK, "seed": 20261002},
           "flag_rates": {}}
    quantities = {"harm role, S.V- released error (2 tasks per group)": 2,
                  "help role, S.V- correct term (1 task per group)": 1}
    for name, per_group in quantities.items():
        for dep_label, kappa in (("no group effect", None), ("group effect, concentration 4", 4.0)):
            for h in (2, 6):
                row = {}
                for dev_rate, held_rate in ((0.5, 0.5), (0.5, 0.3), (0.5, 0.2), (0.3, 0.6)):
                    row[f"dev {dev_rate} -> held-out {held_rate}"] = flag_rate(dev_rate, held_rate, per_group, h, kappa)
                key = f"{name}; {dep_label}; {h} held-out groups"
                out["flag_rates"][key] = row
                print(key, row, flush=True)
    with open("experiments/agent_pilot_heldout_power.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
