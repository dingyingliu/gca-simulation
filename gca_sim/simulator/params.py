"""Parameters of the quotation model, loaded from evidence/assumptions.yaml.

Twenty-six parameters are drawn by a Latin hypercube over their declared ranges. Two more describe behaviour the
agent pilot (E5) can measure and the first model fixed by rule: which note a reader takes when several are
readable, and whether an agent escalates after using a note. Their default values reproduce the first model
exactly, and they are drawn from a second, separate hypercube, so adding them leaves the 26 earlier draws
unchanged.

When assumptions.yaml carries a `pilot_constraints` block, the three note parameters are no longer drawn
independently: the pilot measures two products of them, so the products are drawn from the pilot's intervals and
the single parameters follow (experiments/agent_pilot_plan.md, section 9). The same holds for the reading rule
when the pilot constrains it: the pilot measures b = (1 - p_newest_note) x q, so b is drawn from its interval and
p_newest_note follows from b and the q of the same draw. Every draw then agrees with every measured interval.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[2]
ASSUMPTIONS = ROOT / "evidence" / "assumptions.yaml"


@dataclass(frozen=True)
class Params:
    e_std: float
    e_visible: float
    p_as_requested: float
    p_read_note: float
    p_adopt_blind: float
    p_notice_visible: float
    p_stale_note: float
    p_cue: float
    p_rec_visible: float
    p_rec_cue: float
    p_rec_none: float
    p_policy_flag: float
    p_selfcheck: float
    p_selfcheck_request: float
    p_flag_unverifiable: float
    p_detect_informed: float
    p_detect_request: float
    p_query: float
    p_fix_flagged: float
    lambda_workload: float
    p_lead_knows_policy: float
    effort_lead: float
    delay_lead: float
    effort_ho: float
    delay_ho: float
    sigma_review: float
    # Added before the agent pilot's development run (2026-10-03). The defaults are the first model's fixed rules.
    p_newest_note: float = 1.0       # a reader with several readable notes takes the newest one
    p_flag_after_note: float = 0.0   # an agent that used a note does not escalate the quote as unverifiable


PARAM_NAMES = tuple(f.name for f in fields(Params))
EXTRA_DEFAULTS = {"p_newest_note": 1.0, "p_flag_after_note": 0.0}
EXTRA_NAMES = tuple(EXTRA_DEFAULTS)
LHS_NAMES = tuple(n for n in PARAM_NAMES if n not in EXTRA_DEFAULTS)   # the 26 parameters of the first model
PRODUCT_PARAMS = ("p_read_note", "p_adopt_blind", "p_notice_visible")


def load_assumptions(path: Path = ASSUMPTIONS) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def evidence_id(name: str) -> str:
    return f"quotation.{name}"


def ranges(assumptions: dict | None = None) -> dict[str, tuple[float, float]]:
    a = assumptions or load_assumptions()
    declared = a["parameters"]
    missing = set(declared) - set(PARAM_NAMES)
    if missing:
        raise ValueError(f"assumptions.yaml declares parameters the model does not use: {missing}")
    out = {n: tuple(float(x) for x in declared[n]["range"]) for n in LHS_NAMES}
    for n, default in EXTRA_DEFAULTS.items():
        out[n] = tuple(float(x) for x in declared[n]["range"]) if n in declared else (default, default)
    return {n: out[n] for n in PARAM_NAMES}


def product_constraints(assumptions: dict) -> dict | None:
    """The pilot's intervals for q = p_read_note x p_adopt_blind and r = p_read_note x (1 - p_notice_visible),
    and, when the pilot constrains the reading rule, for b = (1 - p_newest_note) x q. None while no pilot result
    has been applied."""
    c = (assumptions.get("pilot_constraints") or {}).get("products")
    if not c:
        return None
    out = {"q": tuple(map(float, c["q_read_x_adopt_blind"])), "r": tuple(map(float, c["r_read_x_not_notice"]))}
    if c.get("b_not_newest_x_q") is not None:
        out["b"] = tuple(map(float, c["b_not_newest_x_q"]))
    for name, (lo, hi) in out.items():
        if not 0.0 <= lo <= hi <= 1.0:
            raise ValueError(f"pilot constraint {name} is not an interval inside [0, 1]: {(lo, hi)}")
    if "b" in out and out["b"][0] > out["q"][0] + 1e-12:
        # b cannot exceed q, so a b interval that starts above the smallest q leaves some draws with no valid value
        raise ValueError("the pilot's intervals for b and q are incompatible: the lower end of b is above the lower "
                         f"end of q ({out['b']} against {out['q']})")
    return out


def from_unit(unit: np.ndarray, assumptions: dict | None = None) -> np.ndarray:
    """Parameter values from points in the unit cube, one column per name in PARAM_NAMES.

    Without pilot constraints every parameter is uniform on its range. With them, the columns of p_adopt_blind
    and p_notice_visible draw the two products q and r from the pilot's intervals; p_read_note is uniform on the
    part of its range that allows both (at least q and r, since the other factor is at most one); then
    p_adopt_blind = q / p_read_note and p_notice_visible = 1 - r / p_read_note. If the pilot also constrains
    b = (1 - p_newest_note) x q, the column of p_newest_note draws b and the parameter follows from b and q."""
    a = assumptions or load_assumptions()
    r = ranges(a)
    lo = np.array([r[k][0] for k in PARAM_NAMES])
    hi = np.array([r[k][1] for k in PARAM_NAMES])
    values = lo + unit * (hi - lo)
    c = product_constraints(a)
    if c is not None:
        i_read, i_adopt, i_notice = (PARAM_NAMES.index(k) for k in PRODUCT_PARAMS)
        q = c["q"][0] + unit[:, i_adopt] * (c["q"][1] - c["q"][0])
        rr = c["r"][0] + unit[:, i_notice] * (c["r"][1] - c["r"][0])
        read_lo, read_hi = r["p_read_note"]
        floor = np.maximum(read_lo, np.maximum(q, rr))
        if np.any(floor > read_hi + 1e-12):
            raise ValueError("the pilot's products need p_read_note above its declared range")
        read = floor + unit[:, i_read] * (read_hi - floor)
        values[:, i_read] = read
        values[:, i_adopt] = np.clip(q / read, 0.0, 1.0)
        values[:, i_notice] = np.clip(1.0 - rr / read, 0.0, 1.0)
        if "b" in c:
            # b is drawn from its interval, capped at this draw's q; p_newest_note follows, so that
            # (1 - p_newest_note) x q lies inside the measured interval in every draw
            i_new = PARAM_NAMES.index("p_newest_note")
            b = c["b"][0] + unit[:, i_new] * (np.minimum(c["b"][1], q) - c["b"][0])
            values[:, i_new] = np.where(q > 0, 1.0 - b / np.where(q > 0, q, 1.0), 1.0)
    return values


def central(assumptions: dict | None = None) -> Params:
    """The middle of every range (and of the pilot's products, when they apply)."""
    a = assumptions or load_assumptions()
    r = ranges(a)
    mid = {n: (lo + hi) / 2 for n, (lo, hi) in r.items()}
    c = product_constraints(a)
    if c is not None:
        q, rr = sum(c["q"]) / 2, sum(c["r"]) / 2
        read = (max(r["p_read_note"][0], q, rr) + r["p_read_note"][1]) / 2
        mid.update(p_read_note=read, p_adopt_blind=min(1.0, q / read), p_notice_visible=max(0.0, 1.0 - rr / read))
        if "b" in c:
            b = (c["b"][0] + min(c["b"][1], q)) / 2
            mid["p_newest_note"] = 1.0 - b / q if q > 0 else 1.0
    return Params(**mid)


def latin_hypercube(n: int, seed: int, assumptions: dict | None = None) -> list[Params]:
    """`n` parameter draws. The 26 parameters of the first model keep the hypercube they always had; the two
    later ones get their own (seed + 1), so their ranges can change without moving any other draw."""
    main = qmc.LatinHypercube(d=len(LHS_NAMES), seed=seed).random(n)
    extra = qmc.LatinHypercube(d=len(EXTRA_NAMES), seed=seed + 1).random(n)
    unit = np.empty((n, len(PARAM_NAMES)))
    for j, name in enumerate(PARAM_NAMES):
        unit[:, j] = (main[:, LHS_NAMES.index(name)] if name in LHS_NAMES else extra[:, EXTRA_NAMES.index(name)])
    values = from_unit(unit, assumptions)
    return [Params(**dict(zip(PARAM_NAMES, map(float, row)))) for row in values]


def structural(assumptions: dict | None = None) -> dict:
    a = assumptions or load_assumptions()
    return a["structural"]
