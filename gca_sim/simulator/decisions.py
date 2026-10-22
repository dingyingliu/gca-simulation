"""Decision functions. Each takes only an observation, matched uniform draws and parameters.

This module must not import `truth` (tests/test_quotation_access.py checks imports), and the engine
calls every function here inside `truth_forbidden()`.

Each function returns its choice and the names of the parameters it actually used, so the
decision log can cite the evidence record behind every probability that shaped the outcome.
"""

from __future__ import annotations

from .observations import DraftObs, NoteChoiceObs, PolicyCheckObs, RecogniseObs, ReviewObs, SelfCheckObs

WORKLOAD_REFERENCE_BACKLOG = 5  # backlog at which the workload penalty reaches its full size (assumed)


def agent_pick_note(o: NoteChoiceObs, u: dict, p) -> tuple[int | None, tuple]:
    """Which readable note about the customer's term the agent takes: its index, oldest first, or None.

    With probability p_newest_note the newest one; otherwise one of the older ones, each equally likely. At the
    default of 1 this is the first model's rule (always the newest). The agent pilot measures how often a reader
    follows an older note when a newer one disagrees (experiments/agent_pilot_plan.md, section 9)."""
    if o.readable_notes == 0:
        return None, ()
    if o.readable_notes == 1:
        return 0, ()
    if u["note_choice"] < p.p_newest_note:
        return o.readable_notes - 1, ("p_newest_note",)
    older = o.readable_notes - 1
    return min(int(u["note_pick"] * older), older - 1), ("p_newest_note",)


def agent_draft(o: DraftObs, u: dict, p) -> tuple[object, str, bool, tuple]:
    """Draft the term at stake. Returns (value, source, note_used, params used)."""
    used = []
    note = None
    if o.note_value is not None:
        used.append("p_read_note")
        if u["read_note"] < p.p_read_note:
            note = o.note_value
    if o.register_value is not None:
        if note is not None and note != o.register_value:
            used.append("p_notice_visible")
            if u["note_judgement"] < p.p_notice_visible:
                value, source = o.register_value, "register_after_conflict"
            else:
                return note, "note", True, tuple(used)
        else:
            value, source = o.register_value, "register"
        used.append("e_visible")
        if u["slip"] < p.e_visible:
            return o.template_value, "template_slip", False, tuple(used)
        return value, source, note is not None, tuple(used)
    if note is not None:
        used.append("p_adopt_blind")
        if u["note_judgement"] < p.p_adopt_blind:
            return note, "note", True, tuple(used)
    if o.term == "content":
        used.append("e_std")
        if u["slip"] < p.e_std:
            return "misread", "slip", False, tuple(used)
        return o.requested_value, "request", False, tuple(used)
    if o.requested_value is not None:
        if o.requested_exceeds_policy:
            used.append("p_as_requested")
            if u["as_requested"] < p.p_as_requested:
                return o.requested_value, "request", False, tuple(used)
            return o.counter_value, "counter_offer", False, tuple(used)
        return o.requested_value, "request", False, tuple(used)
    return o.template_value, "template", False, tuple(used)


def agent_recognise_local(o: RecogniseObs, u: dict, p) -> tuple[bool, tuple]:
    """Does the agent treat this quote as a local exception? Recognition can fail either way."""
    if o.register_visible:
        name = "p_rec_visible"
    elif o.cites_agreement:
        name = "p_rec_cue"
    else:
        name = "p_rec_none"
    return u["recognise"] < getattr(p, name), (name,)


def system_policy_check(o: PolicyCheckObs, u: dict, p) -> tuple[bool, tuple]:
    """Does the routing rule spot a request beyond the written limits?"""
    if not o.requested_exceeds_policy:
        return False, ()
    return u["policy_flag"] < p.p_policy_flag, ("p_policy_flag",)


def agent_self_check(o: SelfCheckObs, u: dict, p) -> tuple[str | None, tuple]:
    """Before releasing, the agent checks its draft against what it can read."""
    if o.draft_exceeds_policy:
        return ("policy" if u["self_check"] < p.p_selfcheck else None), ("p_selfcheck",)
    if o.register_value is not None and o.drafted != o.register_value:
        return ("register_conflict" if u["self_check"] < p.p_selfcheck else None), ("p_selfcheck",)
    if o.term == "content" and o.drafted != o.requested_value:
        return ("content" if u["self_check"] < p.p_selfcheck_request else None), ("p_selfcheck_request",)
    if o.cites_agreement and o.register_value is None:
        # an agent that used a note escalates with p_flag_after_note; its default of 0 is the first model's rule
        name = "p_flag_after_note" if o.note_used else "p_flag_unverifiable"
        return ("unverifiable" if u["unverifiable"] < getattr(p, name) else None), (name,)
    return None, ()


def review(o: ReviewObs, u: dict, p) -> tuple[str, object, tuple]:
    """A lead or head office reviews a draft. Returns (action, value, params used).

    Actions: pass, correct (to a known value), counter (bring within the written limits),
    authorise (head office approves a beyond-policy exception), query (ask the owning market's lead).
    """
    if o.role == "ho" and o.draft_exceeds_policy:
        return "authorise", o.drafted, ()  # head office holds authority for exceptions
    if o.role == "ho" and o.flag is not None:
        if o.flag == "register_conflict" and o.known_value is not None:
            if u["detect"] < p.p_fix_flagged:
                return "correct", o.known_value, ("p_fix_flagged",)
            return "pass", o.drafted, ("p_fix_flagged",)
        if o.flag == "content":
            if u["detect"] < p.p_fix_flagged:
                return "correct", o.requested_value, ("p_fix_flagged",)
            return "pass", o.drafted, ("p_fix_flagged",)
        if o.flag in ("unverifiable", "register_conflict") and o.known_value is None and o.can_query_owner:
            if u["detect"] < p.p_fix_flagged:
                return "query", o.drafted, ("p_fix_flagged",)
            return "pass", o.drafted, ("p_fix_flagged",)
    workload = 1.0 - p.lambda_workload * min(1.0, o.backlog / WORKLOAD_REFERENCE_BACKLOG)
    if o.known_value is not None and o.drafted != o.known_value:
        used = ("p_detect_informed", "lambda_workload")
        if u["detect"] < p.p_detect_informed * workload:
            return "correct", o.known_value, used
        return "pass", o.drafted, used
    if o.draft_exceeds_policy:  # only set when the reviewer knows the written limits
        used = ("p_detect_informed", "lambda_workload")
        if u["detect"] < p.p_detect_informed * workload:
            return "counter", o.counter_value, used
        return "pass", o.drafted, used
    if o.term == "content" and o.drafted != o.requested_value:
        used = ("p_detect_request", "lambda_workload")
        if u["detect"] < p.p_detect_request * workload:
            return "correct", o.requested_value, used
        return "pass", o.drafted, used
    if o.cites_agreement and o.known_value is None and o.can_query_owner:
        used = ("p_query", "lambda_workload")
        if u["query"] < p.p_query * workload:
            return "query", o.drafted, used
        return "pass", o.drafted, used
    return "pass", o.drafted, ()
