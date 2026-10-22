"""E4 comparison statistics: the run-to-run standard error is computed at seed level,
and a reversing draw lists every parameter value and both configurations' utilisation.

Fabricated arrays only."""

import importlib.util
from dataclasses import replace
from pathlib import Path

import numpy as np

from gca_sim.simulator import params

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_e4", ROOT / "experiments" / "e4_quotation" / "run_e4.py")
run_e4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_e4)


def test_a_duplicated_perfectly_correlated_week_does_not_lower_the_se():
    one = np.random.default_rng(1).normal(size=(1, 3, 64))  # [week, draw, seed]
    two = np.concatenate([one, one], axis=0)
    assert np.allclose(run_e4.seed_level_se(one), run_e4.seed_level_se(two))


def test_fixed_offsets_between_deterministic_weeks_are_not_run_noise():
    diff = np.zeros((5, 3, 64)) + np.arange(5.0)[:, None, None]  # each week its own constant, no seed variation
    assert np.allclose(run_e4.seed_level_se(diff), 0.0)


def test_one_week_gives_the_usual_standard_error():
    d = np.random.default_rng(2).normal(size=(1, 2, 50))
    assert np.allclose(run_e4.seed_level_se(d), d[0].std(axis=1, ddof=1) / np.sqrt(50))


def test_a_reversing_draw_lists_every_parameter_and_both_utilisations():
    n_draws, n_seeds = 20, 4
    data = np.zeros((2, n_draws, len(run_e4.CONFIGS), n_seeds, len(run_e4.MEASURES)))
    a, b, m = 0, 1, run_e4.MEASURES.index("wrong_terms")
    data[:, :, b, :, m] = 1.0          # a lower than b in every draw ...
    data[:, 7, a, :, m] = 2.0          # ... except draw 7: holds in 95% of draws, with one reversal
    data[:, :, a, :, run_e4.MEASURES.index("ho_util")] = 0.5
    data[:, :, b, :, run_e4.MEASURES.index("ho_util")] = 1.2
    draws = [replace(params.central(), effort_ho=round(0.1 + 0.01 * i, 2)) for i in range(n_draws)]
    row = run_e4.compare(data, [0, 1], a, b, "wrong_terms", draws)
    assert row["robust_sign"] == -1 and [r["draw"] for r in row["reversals"]] == [7]
    rev = row["reversals"][0]
    assert set(rev["parameters"]) == set(params.PARAM_NAMES) and rev["parameters"]["effort_ho"] == 0.17
    assert rev["utilisation"]["ho_util"] == {"a": 0.5, "b": 1.2}
    assert rev["run_se"] == 0.0 and rev["beyond_two_run_se"] is True
