"""Access test: no decision reads ground truth.

Three layers. Statically, the decision module never imports the truth module, and no observation
type has a field that only truth holds. Dynamically, every decision runs inside truth_forbidden(),
where reading any truth object raises; the full model runs cleanly under it, and a deliberately
bad decision that reaches for truth is caught.
"""

import ast
import inspect
from pathlib import Path

import pytest

from gca_sim.simulator import decisions, designs, engine, observations, params, random_streams as streams, ground_truth as truth

ROOT = Path(__file__).resolve().parents[1]
TRUTH_ONLY_FIELDS = {"kind", "true_value", "true_kind", "category", "stale_value", "written", "holder",
                     "cites_agreement_possible", "error"}


def test_decision_module_does_not_import_truth():
    tree = ast.parse((ROOT / "gca_sim" / "simulator" / "decisions.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
    assert not any("truth" in name or "engine" in name for name in imported), imported


def test_observations_hold_no_truth_only_fields():
    for cls in observations.OBSERVATION_TYPES:
        names = set(cls.__dataclass_fields__)
        assert not names & TRUTH_ONLY_FIELDS, (cls.__name__, names & TRUTH_ONLY_FIELDS)


def test_decision_functions_take_an_observation_first():
    for fn in (decisions.agent_draft, decisions.agent_pick_note, decisions.agent_recognise_local,
               decisions.system_policy_check, decisions.agent_self_check, decisions.review):
        first = next(iter(inspect.signature(fn).parameters.values()))
        assert first.annotation in {c.__name__ for c in observations.OBSERVATION_TYPES}, fn.__name__


def test_guard_blocks_truth_reads():
    req = truth.walkthrough_case().requests[0]
    assert req.kind == "standard"  # readable outside the guard
    with truth.truth_forbidden():
        with pytest.raises(truth.TruthAccessError):
            _ = req.kind
        with pytest.raises(truth.TruthAccessError):
            _ = req.true_value
    assert req.true_value == "as requested"


@pytest.mark.parametrize("design", list(designs.DESIGNS))
@pytest.mark.parametrize("context", designs.CONTEXTS)
def test_full_model_runs_under_the_guard(design, context):
    p = params.central()
    for case in truth.development_cases():
        ents = streams.case_entities(case)
        for seed in range(5):
            for notes_record in ("draft", "released"):
                engine.simulate(case, designs.DESIGNS[design], context, p, streams.Streams(seed, ents),
                                notes_record=notes_record)


def test_a_decision_that_reads_truth_is_caught(monkeypatch):
    case = truth.walkthrough_case()
    smuggled = case.requests[1]  # Q02, an agreement quote

    def cheating_draft(o, u, p):
        if smuggled.kind == "agreement":  # reads the true category
            return smuggled.true_value, "cheat", False, ()
        return o.template_value, "template", False, ()

    monkeypatch.setattr(decisions, "agent_draft", cheating_draft)
    with pytest.raises(truth.TruthAccessError):
        engine.simulate(case, designs.DESIGNS["review"], "shared", params.central(),
                        streams.Streams(0, streams.case_entities(case)))
