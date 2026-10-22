"""Matched random streams and the shared-notes mechanism behave as specified."""

from dataclasses import replace

import numpy as np

from gca_sim.simulator import designs, engine, params, random_streams as streams, ground_truth as truth
from gca_sim.simulator.decisions import agent_draft
from gca_sim.simulator.observations import DraftObs


def test_same_key_same_draw_and_seeds_differ():
    a = streams.Streams(3, ["Q01", "Q02"])
    b = streams.Streams(3, ["Q02", "Q01"])
    c = streams.Streams(4, ["Q01"])
    for purpose in streams.PURPOSES:
        assert a.u("Q01", purpose) == b.u("Q01", purpose)
    assert a.u("Q01", "slip") != c.u("Q01", "slip")
    assert a.u("Q01", "slip") != a.u("Q02", "slip")


def test_draws_follow_seedsequence_by_entity_and_purpose_position():
    """PURPOSES is append-only: each draw depends on the seed, the entity and the purpose's position."""
    s = streams.Streams(11, ["Q05"])
    ss = np.random.SeedSequence(entropy=11, spawn_key=(streams.entity_key("Q05"),))
    raw = np.random.default_rng(ss).random(len(streams.PURPOSES) + 5)
    for i, purpose in enumerate(streams.PURPOSES):
        assert s.u("Q05", purpose) == raw[i]


def test_design_does_not_change_the_world_draws():
    case = truth.walkthrough_case()
    ents = streams.case_entities(case)
    p = params.central()
    worlds = []
    for d in designs.DESIGNS.values():
        res = engine.simulate(case, d, "shared", p, streams.Streams(5, ents), log=True)
        cites = {e["quote"]: e["info"]["cites_agreement"] for e in res.log if e["action"] == "request"}
        stale = sorted((n.customer, n.value) for n in res.notes if n.origin == "stale")
        worlds.append((cites, stale))
    assert all(w == worlds[0] for w in worlds)


def test_note_reading_rules():
    base = dict(term="payment_days", template_value=30, requested_value=None, requested_exceeds_policy=False,
                counter_value=60, note_author="BR")
    p = replace(params.central(), p_read_note=1.0, p_notice_visible=1.0, p_adopt_blind=1.0, e_visible=0.0)
    u = {"read_note": 0.5, "note_judgement": 0.5, "slip": 0.5, "as_requested": 0.5}
    # register visible, wrong note: noticed, register used
    v, src, used_note, _ = agent_draft(DraftObs(**base, register_value=60, note_value=45), u, p)
    assert (v, src) == (60, "register_after_conflict")
    # register not visible: the note is adopted, right or wrong
    v, src, used_note, _ = agent_draft(DraftObs(**base, register_value=None, note_value=45), u, p)
    assert (v, src, used_note) == (45, "note", True)
    # nothing to go on: the template
    v, src, used_note, _ = agent_draft(DraftObs(**base, register_value=None, note_value=None), u, p)
    assert (v, src) == (30, "template")
    # register visible but the agent never notices conflicts: the wrong note wins
    p2 = replace(p, p_notice_visible=0.0)
    v, src, _, _ = agent_draft(DraftObs(**base, register_value=60, note_value=45), u, p2)
    assert (v, src) == (45, "note")


def test_shared_context_carries_a_wrong_note_across_regions_isolated_does_not():
    """W0: Nexa's agreement is held in Brazil; Q07 is drafted in Singapore. With a stale Brazilian
    note on file, shared notes expose Q07 to it and isolated notes do not."""
    case = truth.walkthrough_case()
    ents = streams.case_entities(case)
    p = replace(params.central(), p_stale_note=1.0, p_read_note=1.0, p_adopt_blind=1.0)
    d = designs.DESIGNS["review"]  # registers not shared, so the agent cannot check the note
    shared = engine.simulate(case, d, "shared", p, streams.Streams(0, ents), log=True)
    isolated = engine.simulate(case, d, "isolated", p, streams.Streams(0, ents), log=True)
    assert shared.quotes["Q07"].drafted == 45 and shared.quotes["Q07"].draft_source == "note"
    assert isolated.quotes["Q07"].drafted == 30 and isolated.quotes["Q07"].draft_source == "template"
    # Q02 is drafted in Brazil, the stale note's own region, so both contexts expose it
    assert shared.quotes["Q02"].drafted == 45 and isolated.quotes["Q02"].drafted == 45


def test_released_notes_carry_review_corrections_forward():
    """When notes record released terms, a lead's correction reaches a later draft for the same customer."""
    case = truth.generate_week(4, "development", "G4 development week")
    ents = streams.case_entities(case)
    p = replace(params.central(), p_stale_note=0.0, p_read_note=1.0, p_adopt_blind=1.0,
                p_detect_informed=0.95, lambda_workload=0.0, effort_lead=0.2, delay_lead=0.0, sigma_review=0.25)
    d = designs.DESIGNS["review"]
    found = False
    for seed in range(40):
        res = engine.simulate(case, d, "shared", p, streams.Streams(seed, ents), notes_record="released")
        released_notes = [n for n in res.notes if n.origin == "released"]
        for q in res.quotes.values():
            if q.draft_source == "note":
                src = [n for n in released_notes if n.customer == q.req.customer and n.t <= q.req.day + 0.5]
                assert src, q.req.id
                found = found or src[-1].value == q.req.true_value
    assert found
