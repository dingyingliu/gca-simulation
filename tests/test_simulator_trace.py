"""Trace completeness: from the decision log alone an auditor can recover why
each consequential path happened, which note a draft read and where that note came from, every old and new
value, and the evidence record behind every probability or time that shaped it."""

from dataclasses import replace

from gca_sim import evidence
from gca_sim.simulator import designs, engine, params, random_streams as streams, ground_truth as truth

CASE = truth.walkthrough_case()
ENTS = streams.case_entities(CASE)


def _run(design, context, p, **kw):
    return engine.simulate(CASE, designs.DESIGNS[design], context, p, streams.Streams(0, ENTS), log=True,
                           run_meta={"parameter_draw": "test", "seed": 0}, **kw)


def test_run_manifest_and_world_provenance():
    res = _run("local", "shared", params.central())
    first = res.log[0]
    assert first["action"] == "run_manifest" and first["evaluator_only"]
    assert first["info"]["case_sha256"] == CASE.sha256() and first["info"]["stream_seed"] == 0
    assert {"t_draft", "notes_record", "bypass_after_days"} <= {e.split(".", 1)[1] for e in first["evidence"]}
    actions = [e["action"] for e in res.log]
    assert actions.count("world:lead_knows_policy") == 3
    assert actions.count("world:stale_note_draw") == sum(1 for a in CASE.agreements if a.written)
    cues = [e for e in res.log if e["action"] == "world:request_cue"]
    assert len(cues) == sum(1 for r in CASE.requests if r.cites_agreement_possible)
    assert all(e["evaluator_only"] and e["evidence"] == ["quotation.p_cue"] for e in cues)


def test_both_outcomes_of_routing_checks_are_logged():
    res = _run("local", "isolated", params.central())
    checks = [e for e in res.log if e["action"] in ("policy_check", "recognise_local", "self_check")]
    assert any(e["action"] == "policy_check" and e["info"]["flagged"] is False for e in checks)
    assert any(e["action"] == "recognise_local" and e["info"]["recognised"] is False for e in checks)
    assert any(e["action"] == "self_check" and e["info"]["flag"] is None for e in checks)


def test_missed_check_then_gate_is_visible():
    p = replace(params.central(), p_policy_flag=0.0, p_selfcheck=0.0, p_as_requested=1.0)
    res = _run("limits", "isolated", p)
    q04 = [e for e in res.log if e["quote"] == "Q04"]
    kinds = [e["action"] for e in q04]
    assert "policy_check" in kinds and "self_check" in kinds and "gate_refused" in kinds
    policy = next(e for e in q04 if e["action"] == "policy_check")
    assert policy["info"]["flagged"] is False and "quotation.p_policy_flag" in policy["evidence"]
    check = next(e for e in q04 if e["action"] == "self_check")
    assert check["info"]["flag"] is None and "quotation.p_selfcheck" in check["evidence"]


def test_stale_note_chain_is_linked():
    p = replace(params.central(), p_stale_note=1.0, p_read_note=1.0, p_adopt_blind=1.0)
    res = _run("review", "shared", p)
    writes = {e["info"]["note_id"]: e for e in res.log if e["action"] == "note_write"}
    stale = [nid for nid, e in writes.items() if e["info"]["origin"] == "stale" and e["info"]["customer"] == "Nexa"]
    assert len(stale) == 1 and writes[stale[0]]["evaluator_only"]
    q07 = next(e for e in res.log if e["action"] == "draft" and e["quote"] == "Q07")
    # Q02's own draft note (written later than the stale note) is the newest readable one for Q07
    in_view = q07["info"]["note_in_view"]
    assert in_view in writes and q07["info"]["note_used"] == in_view
    chain_origin = writes[in_view]["info"]["origin"]
    assert chain_origin in ("stale", "draft")
    if chain_origin == "draft":
        assert writes[in_view]["quote"] == "Q02"
        q02 = next(e for e in res.log if e["action"] == "draft" and e["quote"] == "Q02")
        assert q02["info"]["note_used"] == stale[0]  # Q02 read the stale note, and passed its value on


def test_owner_query_records_old_and_new_values_and_its_evidence():
    p = replace(params.central(), p_cue=1.0, p_query=1.0, lambda_workload=0.0)
    res = _run("review", "isolated", p)
    queries = [e for e in res.log if e["action"] == "query_owner"]
    assert queries, "expected the Singapore lead to ask Brazil about Nexa"
    q = next(e for e in queries if e["quote"] == "Q07")
    assert q["info"]["old"] == 30 and q["info"]["new"] == 60
    assert {"quotation.delay_lead", "quotation.effort_lead", "quotation.sigma_review"} <= set(q["evidence"])


def test_corrections_record_old_and_new_values():
    p = replace(params.central(), p_detect_informed=0.95, lambda_workload=0.0)
    res = _run("review", "isolated", p)
    corrections = [e for e in res.log if e["action"] in ("review_done:correct", "review_done:counter")]
    assert corrections and all("old" in e["info"] and "new" in e["info"] for e in corrections)


def test_every_cited_evidence_id_resolves():
    records = evidence.load_all()
    for design in designs.DESIGNS:
        for context in designs.CONTEXTS:
            res = _run(design, context, params.central(), bypass_after=3.0)
            for e in res.log:
                for rid in e["evidence"]:
                    assert rid in records, (design, context, e["action"], rid)
