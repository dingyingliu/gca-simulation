"""Hard-constraint tests for the quotation engine.

A failed hard-constraint test blocks release of any result. Checked over every design, context and
notes assumption, on every development week, at the central parameter values and at the corners
of the declared ranges, with several seeds:

- every quote is released exactly once;
- no release beyond granted authority: the releasing actor holds release authority for the
  quote's route under the design, and no agent or lead releases terms beyond the written limits
  (head office alone may authorise those);
- every release has a recorded approver or authorising rule (and, with the bypass assumption off,
  an approver);
- queue accounting conserves items;
- event times never go backwards;
- the same seed gives identical output.
"""

import json
from dataclasses import replace

import pytest

from gca_sim.simulator import designs, engine, params, random_streams as streams, ground_truth as truth
from gca_sim.simulator.ground_truth import POLICY

CASES = truth.development_cases()


def _param_sets():
    r = params.ranges()
    lo = params.Params(**{k: v[0] for k, v in r.items()})
    hi = params.Params(**{k: v[1] for k, v in r.items()})
    return {"central": params.central(), "low": lo, "high": hi}


PARAM_SETS = _param_sets()


def _runs(bypass_after=None):
    for pname, p in PARAM_SETS.items():
        for case in CASES:
            ents = streams.case_entities(case)
            for seed in range(4):
                s = streams.Streams(seed, ents)
                for dkey, d in designs.DESIGNS.items():
                    for ctx in designs.CONTEXTS:
                        for nr in ("draft", "released"):
                            res = engine.simulate(case, d, ctx, p, s, notes_record=nr, log=True,
                                                  bypass_after=bypass_after)
                            yield (pname, case.name, seed, dkey, ctx, nr), d, res


@pytest.fixture(scope="module")
def runs():
    return list(_runs())


def test_every_quote_released_once(runs):
    for label, d, res in runs:
        releases = [e for e in res.log if e["action"] == "release"]
        assert len(releases) == len(res.quotes), label
        assert len({e["quote"] for e in releases}) == len(res.quotes), label
        assert all(q.released_at is not None for q in res.quotes.values()), label


def test_no_release_beyond_granted_authority(runs):
    for label, d, res in runs:
        allowed = d.release_authority()
        for q in res.quotes.values():
            assert (q.approver, q.route) in allowed, (label, q.req.id, q.approver, q.route)


def test_no_release_beyond_the_written_limits_without_head_office(runs):
    """The actual policy predicate, not just the route."""
    for label, d, res in runs:
        for q in res.quotes.values():
            if POLICY.exceeds(q.req.term, q.value, q.req.value_eur):
                assert q.approver == designs.HO, (label, q.req.id, q.approver, q.value)
        assert res.measures["releases_beyond_authority"] == 0, label


def test_every_release_has_approver_and_rule(runs):
    for label, d, res in runs:
        for q in res.quotes.values():
            assert q.rule, (label, q.req.id)
            assert q.approver in (designs.AGENT, designs.LEAD, designs.HO), (label, q.req.id)
            assert q.approver_id, (label, q.req.id)
        assert res.measures["no_approval"] == 0, label


def test_queue_accounting_conserves_items(runs):
    for label, d, res in runs:
        for name, s in res.servers.items():
            assert s.started == s.completed, (label, name)
            assert s.enqueued == s.completed + s.bypassed, (label, name)
            assert not s.queue and not s.busy, (label, name)
        enqueues = [e for e in res.log if e["action"] == "enqueue"]
        assert len(enqueues) == sum(s.enqueued for s in res.servers.values()), label
        for q in res.quotes.values():
            n = sum(1 for e in enqueues if e["quote"] == q.req.id)
            assert n >= q.gate_refusals, (label, q.req.id)
            if q.gate_refusals:
                assert q.approver == designs.HO and q.route == designs.HO, (label, q.req.id)


def test_event_times_never_go_backwards(runs):
    for label, d, res in runs:
        times = [e["t"] for e in res.log]
        assert times == sorted(times), label
        for q in res.quotes.values():
            assert q.released_at >= q.req.day, (label, q.req.id)


def test_same_seed_identical_output():
    case = CASES[1]
    ents = streams.case_entities(case)
    p = PARAM_SETS["central"]
    for d in designs.DESIGNS.values():
        a = engine.simulate(case, d, "shared", p, streams.Streams(7, ents), log=True)
        b = engine.simulate(case, d, "shared", p, streams.Streams(7, ents), log=True)
        assert json.dumps(a.log, default=str) == json.dumps(b.log, default=str)
        assert a.measures == b.measures


def test_bypass_assumption_records_no_approval_and_conserves_items():
    """With the walkthrough's bypass switched on, unreviewed releases are counted, never hidden."""
    p = replace(PARAM_SETS["central"], effort_lead=1.25)
    for label, d, res in _runs(bypass_after=3.0):
        for q in res.quotes.values():
            if q.approver == designs.NONE:
                assert q.rule == "company_practice_bypass" and q.approver_id is None, label
        assert res.measures["no_approval"] == sum(1 for q in res.quotes.values() if q.approver == designs.NONE)
        for name, s in res.servers.items():
            assert s.enqueued == s.completed + s.bypassed, (label, name)
    # and it does happen when review every quote overloads the leads
    case = CASES[0]
    s = streams.Streams(0, streams.case_entities(case))
    res = engine.simulate(case, designs.DESIGNS["review"], "isolated", p, s, bypass_after=3.0)
    assert res.measures["no_approval"] > 0


def test_q18_counterexample_is_escalated_not_released_by_the_lead():
    """In the saved W0 trace (review every quote) Q18, free shipping on a
    EUR 12,800 order, went out through lead:BR. With the gate on, the lead's release is refused and head
    office authorises instead, whatever the lead knows."""
    case = CASES[0]
    p = replace(PARAM_SETS["central"], p_lead_knows_policy=0.0, p_as_requested=1.0)  # no lead knows the limits
    s = streams.Streams(0, streams.case_entities(case))
    res = engine.simulate(case, designs.DESIGNS["review"], "isolated", p, s, log=True)
    q18 = res.quotes["Q18"]
    assert q18.gate_refusals == 1 and q18.approver == designs.HO and q18.route == designs.HO
    assert not q18.error
    assert any(e["action"] == "gate_refused" and e["quote"] == "Q18" and e["info"]["attempted_by"] == "lead:BR"
               for e in res.log)


def test_missed_agent_policy_check_is_caught_by_the_gate():
    """An agent that drafts beyond the limits and whose own check misses it cannot release."""
    case = CASES[0]
    p = replace(PARAM_SETS["central"], p_policy_flag=0.0, p_selfcheck=0.0, p_as_requested=1.0)
    s = streams.Streams(0, streams.case_entities(case))
    res = engine.simulate(case, designs.DESIGNS["limits"], "isolated", p, s, log=True)
    for qid in ("Q04", "Q12", "Q18"):  # the three beyond-policy requests
        q = res.quotes[qid]
        assert q.gate_refusals == 1 and q.approver == designs.HO, qid
        assert any(e["action"] == "gate_refused" and e["quote"] == qid and e["info"]["attempted_by"].startswith("agent:")
                   for e in res.log)


def test_gate_off_sensitivity_counts_releases_beyond_authority():
    """With the gate off (labelled sensitivity), the same breaches go out and are counted, never hidden."""
    case = CASES[0]
    p = replace(PARAM_SETS["central"], p_lead_knows_policy=0.0, p_as_requested=1.0)
    s = streams.Streams(0, streams.case_entities(case))
    res = engine.simulate(case, designs.DESIGNS["review"], "isolated", p, s, enforce_policy_gate=False)
    assert res.measures["releases_beyond_authority"] >= 1
    assert res.measures["gate_escalations"] == 0
    assert res.quotes["Q18"].approver == designs.LEAD and res.quotes["Q18"].error


def test_bypass_acts_only_on_the_current_queue_visit():
    """After a policy-gate escalation a quote is queued again at head office; a
    bypass timer from its earlier lead queue must not release it. Every bypass must follow at least the full
    bypass delay of waiting since the quote's latest enqueue."""
    case = CASES[0]
    p = replace(PARAM_SETS["central"], p_lead_knows_policy=0.0, p_as_requested=1.0, effort_lead=0.1,
                delay_lead=1.0, effort_ho=1.67, delay_ho=0.25)
    found_escalated_bypass_candidates = 0
    for seed in range(40):
        s = streams.Streams(seed, streams.case_entities(case))
        res = engine.simulate(case, designs.DESIGNS["review"], "isolated", p, s, bypass_after=2.0, log=True)
        for e in res.log:
            if e["action"] != "bypass":
                continue
            enq = [x["t"] for x in res.log if x["action"] == "enqueue" and x["quote"] == e["quote"] and x["t"] <= e["t"]]
            assert e["t"] - enq[-1] >= 2.0 - 1e-9, (seed, e["quote"], e["t"], enq)
        found_escalated_bypass_candidates += sum(q.gate_refusals for q in res.quotes.values())
    assert found_escalated_bypass_candidates > 0  # the scenario (escalation after a lead queue) does occur
