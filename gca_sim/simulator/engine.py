"""Discrete-event engine for one simulated week of quotations (E4).

A plain event loop over a time-ordered heap. Each
quote is drafted, routed, possibly reviewed (one first-in-first-out server per regional lead and
one for head office) and released. A review occupies the reviewer for its effort; the decision goes
out after a response delay that uses no capacity. Notes written by agents persist through the week
and are read by later drafts: across all regions when context is shared, within the drafting region
when it is isolated.

Hard permissions: with the policy gate on, the system refuses any release
by an agent or a lead whose terms exceed the written limits without head-office authorisation, and
escalates the quote to head office instead. With the gate off (a labelled sensitivity), such releases
go out and are counted as releases beyond authority.

The engine is the only code that reads truth. It builds each role's observation from truth and
calls the decision functions inside `truth_forbidden()`. Events marked `evaluator_only` record sampled
world states for audit; no role ever sees them.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections import deque
from dataclasses import asdict, dataclass, field
from statistics import NormalDist

from . import decisions as D
from .designs import AGENT, HO, LEAD, NONE, RELEASE_RULES, Design
from .observations import DraftObs, NoteChoiceObs, PolicyCheckObs, RecogniseObs, ReviewObs, SelfCheckObs
from .params import Params, evidence_id
from .random_streams import Streams
from .ground_truth import POLICY, REGIONS, Case, Request, is_error, truth_forbidden

_Z = NormalDist().inv_cdf
WEEK_DAYS = 5.0
GATE_RULE = "policy_gate_to_ho"


@dataclass
class Note:
    id: str
    customer: str
    term: str
    value: object
    author: str               # region whose agent wrote it
    t: float
    origin: str               # stale | draft | released
    source_quote: str | None  # the quote whose draft or release wrote it; None for a stale note


@dataclass(frozen=True, slots=True)
class PlainRequest:
    """The engine's own copy of a request. Never passed to a decision function."""

    id: str
    day: int
    region: str
    customer: str
    account_owner: str
    value_eur: int
    kind: str
    term: str
    template_value: object
    true_value: object
    requested_value: object
    cites_agreement_possible: bool


def _plain(r: Request) -> PlainRequest:
    return PlainRequest(r.id, r.day, r.region, r.customer, r.account_owner, r.value_eur, r.kind, r.term,
                        r.template_value, r.true_value, r.requested_value, r.cites_agreement_possible)


@dataclass
class QuoteState:
    req: PlainRequest
    drafted: object = None
    draft_source: str | None = None
    note_used: bool = False
    note_read_id: str | None = None
    value: object = None
    route: str | None = None
    reviewer: str | None = None
    flag: str | None = None
    pending_action: tuple | None = None
    started: bool = False
    released_at: float | None = None
    approver: str | None = None
    approver_id: str | None = None
    rule: str | None = None
    error: bool | None = None
    gate_refusals: int = 0
    visit: int = 0                 # queue visits so far; a bypass timer acts only on its own visit
    enqueued_at: float | None = None


@dataclass
class Server:
    name: str
    busy: bool = False
    queue: deque = field(default_factory=deque)
    busy_time: float = 0.0
    enqueued: int = 0
    started: int = 0
    completed: int = 0
    bypassed: int = 0
    changed: int = 0


@dataclass
class RunResult:
    measures: dict
    quotes: dict
    servers: dict
    log: list
    notes: list


def _lognormal(median: float, sigma: float, u: float) -> float:
    if median <= 0:
        return 0.0
    u = min(max(u, 1e-12), 1 - 1e-12)
    return median * math.exp(sigma * _Z(u))


def simulate(case: Case, design: Design, context: str, params: Params, streams: Streams, *,
             notes_record: str = "draft", bypass_after: float | None = None, t_draft: float = 0.5,
             enforce_policy_gate: bool = True, log: bool = False, baseline: dict | None = None,
             run_meta: dict | None = None) -> RunResult:
    """Run one week. `baseline` (quote id -> [(cumulative probability, value, source, note_used)])
    replaces drafting by independent draws and switches notes off (the independent-errors model)."""
    if context not in ("shared", "isolated"):
        raise ValueError(context)
    if notes_record not in ("draft", "released"):
        raise ValueError(notes_record)
    p = params
    events: list = []
    heap: list = []
    seq = itertools.count()
    note_ids = itertools.count(1)

    def push(t: float, kind: str, qid: str, visit: int | None = None) -> None:
        heapq.heappush(heap, (t, next(seq), kind, qid, visit))

    def emit(t: float, qid: str | None, actor: str, action: str, rule: str | None, info: dict, used=(),
             evaluator_only: bool = False) -> None:
        if log:
            e = {"t": round(t, 6), "quote": qid, "actor": actor, "action": action, "rule": rule,
                 "info": info, "evidence": [evidence_id(n) for n in used]}
            if evaluator_only:
                e["evaluator_only"] = True
            events.append(e)

    if log:
        emit(0.0, None, "simulator", "run_manifest", None, {
            **(run_meta or {}), "case": case.name, "case_sha256": case.sha256(), "design": design.key,
            "context": context, "notes_record": notes_record, "bypass_after": bypass_after,
            "policy_gate": enforce_policy_gate, "t_draft": t_draft, "baseline": baseline is not None,
            "stream_seed": streams.seed, "params": {k: v for k, v in asdict(p).items()}},
             ("t_draft", "notes_record", "bypass_after_days"), evaluator_only=True)

    # ---- world state built from truth (outside any decision) ------------------------------------
    registers = {r: {} for r in REGIONS}
    private = {r: {} for r in REGIONS}
    notes: list[Note] = []

    def write_note(customer, term, value, author, t, origin, source_quote) -> Note:
        n = Note(f"N{next(note_ids)}", customer, term, value, author, t, origin, source_quote)
        notes.append(n)
        emit(t, source_quote, f"agent:{author}" if origin != "stale" else "world", "note_write", None,
             {"note_id": n.id, "customer": customer, "term": term, "value": value, "author": author,
              "origin": origin}, evaluator_only=(origin == "stale"))
        return n

    for a in case.agreements:
        customer, term, value, holder, written, stale = (a.customer, a.term, a.value, a.holder, a.written,
                                                         a.stale_value)
        (registers if written else private)[holder][(customer, term)] = value
        if written and stale is not None and baseline is None:
            created = streams.u(f"customer:{customer}", "stale_note") < p.p_stale_note
            emit(0.0, None, "world", "world:stale_note_draw", None,
                 {"customer": customer, "term": term, "created": created, "author": holder},
                 ("p_stale_note",), evaluator_only=True)
            if created:
                write_note(customer, term, stale, holder, 0.0, "stale", None)
    knows_policy = {}
    for r in REGIONS:
        knows_policy[r] = streams.u(f"region:{r}", "knows_policy") < p.p_lead_knows_policy
        emit(0.0, None, "world", "world:lead_knows_policy", None, {"region": r, "knows": knows_policy[r]},
             ("p_lead_knows_policy",), evaluator_only=True)
    plain = [_plain(r) for r in case.requests]
    cites = {}
    for r in plain:
        cites[r.id] = r.cites_agreement_possible and streams.u(r.id, "cites_agreement") < p.p_cue
        if r.cites_agreement_possible:
            emit(0.0, r.id, "world", "world:request_cue", None, {"cites_agreement": cites[r.id]}, ("p_cue",),
                 evaluator_only=True)
    all_registers = {}
    for r in REGIONS:
        all_registers.update(registers[r])

    def lead_knows(region: str, key) -> object:
        if design.share_agreements and key in all_registers:
            return all_registers[key]
        if key in registers[region]:
            return registers[region][key]
        return private[region].get(key)

    def agent_sees(key) -> object:
        return all_registers.get(key) if design.share_agreements else None

    quotes = {r.id: QuoteState(r) for r in plain}
    servers = {f"lead:{r}": Server(f"lead:{r}") for r in REGIONS}
    servers["ho"] = Server("ho")

    for r in plain:
        push(float(r.day), "arrive", r.id)

    # ---- helpers -------------------------------------------------------------------------------
    def release(q: QuoteState, t: float, kind: str, actor_id: str | None, rule: str) -> None:
        r = q.req
        if (enforce_policy_gate and kind in (AGENT, LEAD)
                and POLICY.exceeds(r.term, q.value, r.value_eur)):
            q.gate_refusals += 1
            emit(t, r.id, "release gate", "gate_refused", GATE_RULE,
                 {"attempted_by": actor_id, "attempted_rule": rule, "value": q.value,
                  "reason": "terms exceed the written limits; head-office authorisation required"},
                 ("policy_gate",))
            q.route, q.flag = HO, "policy_gate"
            enqueue(q, "ho", t)
            return
        q.released_at, q.approver, q.approver_id, q.rule = t, kind, actor_id, rule
        q.error = is_error(r, q.value, kind)
        emit(t, r.id, actor_id or "sales team", "release", rule,
             {"value": q.value, "approver": kind, "route": q.route,
              "beyond_written_limits": POLICY.exceeds(r.term, q.value, r.value_eur)})
        if notes_record == "released" and baseline is None and r.term != "content":
            write_note(r.customer, r.term, q.value, r.region, t, "released", r.id)

    def enqueue(q: QuoteState, server_name: str, t: float) -> None:
        s = servers[server_name]
        s.enqueued += 1
        q.reviewer = server_name
        q.started = False
        q.visit += 1
        q.enqueued_at = t
        emit(t, q.req.id, server_name, "enqueue", None,
             {"queue_length": len(s.queue), "busy": s.busy, "visit": q.visit})
        if s.busy:
            s.queue.append(q.req.id)
        else:
            start(q, t)
        if bypass_after is not None:
            push(t + bypass_after, "bypass", q.req.id, q.visit)

    def start(q: QuoteState, t: float) -> None:
        r = q.req
        s = servers[q.reviewer]
        s.busy = True
        s.started += 1
        q.started = True
        role = HO if q.reviewer == "ho" else LEAD
        region = None if role == HO else q.reviewer.split(":")[1]
        key = (r.customer, r.term)
        known = (all_registers.get(key) if design.share_agreements else None) if role == HO else lead_knows(region, key)
        knows = True if role == HO else knows_policy[region]
        obs = ReviewObs(
            role=role, term=r.term, drafted=q.value, requested_value=r.requested_value, known_value=known,
            knows_policy=knows,
            draft_exceeds_policy=(POLICY.exceeds(r.term, q.value, r.value_eur) if knows else None),
            counter_value=POLICY.counter(r.term), cites_agreement=cites[r.id],
            can_query_owner=(role == HO) or (r.account_owner != region), backlog=len(s.queue), flag=q.flag)
        u = streams.for_entity(r.id, ("detect", "query"))
        with truth_forbidden():
            action, value, used = D.review(obs, u, p)
        effort_name, delay_name = ("effort_ho", "delay_ho") if role == HO else ("effort_lead", "delay_lead")
        effort = _lognormal(getattr(p, effort_name), p.sigma_review,
                            streams.u(r.id, "service_ho" if role == HO else "service_lead"))
        s.busy_time += effort
        q.pending_action = (action, value, role)
        emit(t, r.id, q.reviewer, f"review_start:{action}", None,
             {"observation": asdict(obs), "effort_days": round(effort, 6)} if log else None,
             used + (effort_name, "sigma_review"))
        push(t + effort, "review_done", r.id)

    # ---- event loop ----------------------------------------------------------------------------
    while heap:
        t, _, kind, qid, visit = heapq.heappop(heap)
        q = quotes[qid]
        r = q.req
        if kind == "arrive":
            emit(t, qid, "customer", "request", None,
                 {"region": r.region, "customer": r.customer, "value_eur": r.value_eur,
                  "cites_agreement": cites[qid]} if log else None)
            push(t + t_draft, "drafted", qid)

        elif kind == "drafted":
            key = (r.customer, r.term)
            register_value = agent_sees(key)
            if baseline is None:
                readable = [n for n in notes if n.customer == r.customer and n.term == r.term and n.t <= t
                            and (context == "shared" or n.author == r.region)] if r.term != "content" else []
                with truth_forbidden():
                    pick, pick_used = D.agent_pick_note(NoteChoiceObs(len(readable)),
                                                        streams.for_entity(qid, ("note_choice", "note_pick")), p)
                note = None if pick is None else readable[pick]
                obs = DraftObs(term=r.term, template_value=r.template_value, requested_value=r.requested_value,
                               requested_exceeds_policy=POLICY.exceeds(r.term, r.requested_value, r.value_eur),
                               counter_value=POLICY.counter(r.term), register_value=register_value,
                               note_value=None if note is None else note.value,
                               note_author=None if note is None else note.author)
                u = streams.for_entity(qid, ("read_note", "note_judgement", "slip", "as_requested"))
                with truth_forbidden():
                    value, source, note_used, used = D.agent_draft(obs, u, p)
                used = tuple(pick_used) + tuple(used)
                q.note_read_id = note.id if (note is not None and note_used) else None
                info = ({"observation": asdict(obs), "source": source, "readable_notes": len(readable),
                         "note_in_view": None if note is None else note.id,
                         "note_in_view_origin": None if note is None else note.origin,
                         "note_used": q.note_read_id} if log else None)
            else:
                ub = streams.u(qid, "baseline_draft")
                value, source, note_used = next((v, s_, n_) for c, v, s_, n_ in baseline[qid] if ub < c)
                used, info = (), {"baseline_draw": True, "source": source}
            q.drafted = q.value = value
            q.draft_source, q.note_used = source, note_used
            if log:
                emit(t, qid, f"agent:{r.region}", "draft", None, {**info, "value": value}, used)
            if notes_record == "draft" and baseline is None and r.term != "content":
                write_note(r.customer, r.term, value, r.region, t, "draft", qid)

            # routing, on observable features only; both outcomes of each check are logged
            if design.review_every_quote:
                q.route = LEAD
                emit(t, qid, "routing rule", f"route:lead:{r.region}", "review_every_quote", {})
                enqueue(q, f"lead:{r.region}", t)
                continue
            if design.policy_breach_to_ho:
                pobs = PolicyCheckObs(POLICY.exceeds(r.term, r.requested_value, r.value_eur))
                u = streams.for_entity(qid, ("policy_flag",))
                with truth_forbidden():
                    flagged, used = D.system_policy_check(pobs, u, p)
                emit(t, qid, "routing rule", "policy_check", "policy_breach_to_ho",
                     {**asdict(pobs), "flagged": flagged} if log else None, used)
                if flagged:
                    q.route, q.flag = HO, "policy_route"
                    enqueue(q, "ho", t)
                    continue
            if design.refer_cross_market and r.account_owner != r.region:
                q.route = LEAD
                emit(t, qid, "routing rule", f"route:lead:{r.account_owner}", "cross_market_referral",
                     {"account_owner": r.account_owner, "drafting_region": r.region})
                enqueue(q, f"lead:{r.account_owner}", t)
                continue
            if design.refer_recognised_local:
                robs = RecogniseObs(cites_agreement=cites[qid], register_visible=register_value is not None)
                u = streams.for_entity(qid, ("recognise",))
                with truth_forbidden():
                    recognised, used = D.agent_recognise_local(robs, u, p)
                emit(t, qid, f"agent:{r.region}", "recognise_local", "refer_recognised_local",
                     {**asdict(robs), "recognised": recognised} if log else None, used)
                if recognised:
                    q.route = LEAD
                    enqueue(q, f"lead:{r.region}", t)
                    continue
            if design.agent_may_release:
                sobs = SelfCheckObs(term=r.term, drafted=q.value, requested_value=r.requested_value,
                                    draft_exceeds_policy=POLICY.exceeds(r.term, q.value, r.value_eur),
                                    register_value=register_value, note_used=q.note_used,
                                    cites_agreement=cites[qid])
                u = streams.for_entity(qid, ("self_check", "unverifiable"))
                with truth_forbidden():
                    flag, used = D.agent_self_check(sobs, u, p)
                emit(t, qid, f"agent:{r.region}", "self_check", "agent_flag_to_ho",
                     {**asdict(sobs), "flag": flag} if log else None, used)
                if flag is not None and design.agent_flags_to_ho:
                    q.route, q.flag = HO, flag
                    enqueue(q, "ho", t)
                    continue
                q.route = AGENT
                release(q, t, AGENT, f"agent:{r.region}", RELEASE_RULES[AGENT])
                continue
            raise RuntimeError(f"design {design.key} left quote {qid} without a route")

        elif kind == "review_done":
            s = servers[q.reviewer]
            s.completed += 1
            s.busy = False
            action, value, role = q.pending_action
            delay_name = "delay_ho" if role == HO else "delay_lead"
            delay = _lognormal(getattr(p, delay_name), p.sigma_review, streams.u(qid, "response_delay"))
            if action in ("correct", "counter") and value != q.value:
                s.changed += 1
                emit(t, qid, q.reviewer, f"review_done:{action}", None, {"old": q.value, "new": value})
                q.value = value
            elif action == "query":
                owner_value = lead_knows(r.account_owner, (r.customer, r.term))
                qdelay = _lognormal(p.delay_lead + p.effort_lead, p.sigma_review, streams.u(qid, "query_delay"))
                new = owner_value if owner_value is not None else q.value
                emit(t, qid, q.reviewer, "query_owner", None,
                     {"owner": f"lead:{r.account_owner}", "answer_delay_days": round(qdelay, 6),
                      "old": q.value, "new": new}, ("delay_lead", "effort_lead", "sigma_review"))
                if new != q.value:
                    s.changed += 1
                    q.value = new
                delay += qdelay
            else:
                emit(t, qid, q.reviewer, f"review_done:{action}", None, {"value": q.value})
            push(t + delay, "respond", qid)
            if delay > 0:
                emit(t, qid, q.reviewer, "response_delay", None, {"days": round(delay, 6)}, (delay_name, "sigma_review"))
            if s.queue:
                start(quotes[s.queue.popleft()], t)

        elif kind == "respond":
            role = q.pending_action[2]
            release(q, t, role, q.reviewer, RELEASE_RULES[role])

        elif kind == "bypass":
            # a timer from an earlier queue visit never acts on a later one
            if visit != q.visit:
                continue
            s = servers[q.reviewer]
            if not q.started and q.released_at is None and qid in s.queue:
                s.queue.remove(qid)
                s.bypassed += 1
                q.route = NONE
                emit(t, qid, "sales team", "bypass", "company_practice_bypass",
                     {"waited_days": round(t - q.enqueued_at, 6), "queue": q.reviewer, "visit": visit},
                     ("bypass_after_days",))
                release(q, t, NONE, None, "company_practice_bypass")

    return RunResult(_measures(case, quotes, servers), quotes, servers, events, notes)


def _measures(case: Case, quotes: dict, servers: dict) -> dict:
    qs = list(quotes.values())
    days = [q.released_at - q.req.day for q in qs]
    by_kind = {}
    for q in qs:
        by_kind[q.req.kind] = by_kind.get(q.req.kind, 0) + int(q.error)
    groups = {}
    for q in qs:
        if q.req.kind in ("agreement", "verbal"):
            groups.setdefault((q.req.customer, q.req.term), []).append(q)
    repeat = [g for g in groups.values() if len(g) > 1]
    leads = [s for n, s in servers.items() if n.startswith("lead:")]
    lead_reviews = sum(s.completed for s in leads)
    return {
        "errors": sum(int(q.error) for q in qs),
        "wrong_terms": sum(int(q.error) for q in qs if q.req.kind != "beyond_policy"),
        "days_mean": sum(days) / len(days),
        "days_max": max(days),
        "lead_reviews": lead_reviews,
        "ho_reviews": servers["ho"].completed,
        "lead_util_max": max(s.busy_time for s in leads) / WEEK_DAYS,
        "ho_util": servers["ho"].busy_time / WEEK_DAYS,
        "no_approval": sum(1 for q in qs if q.approver == NONE),
        "agent_releases": sum(1 for q in qs if q.approver == AGENT),
        "gate_escalations": sum(q.gate_refusals for q in qs),
        "releases_beyond_authority": sum(1 for q in qs if q.approver != HO
                                         and POLICY.exceeds(q.req.term, q.value, q.req.value_eur)),
        "inconsistent_customers": sum(1 for g in repeat if len({repr(q.value) for q in g}) > 1),
        "repeat_all_wrong": sum(1 for g in repeat if all(q.error for q in g)),
        "repeat_customers": len(repeat),
        "lead_changed": sum(s.changed for s in leads),
        "errors_standard": by_kind.get("standard", 0),
        "errors_agreement": by_kind.get("agreement", 0),
        "errors_verbal": by_kind.get("verbal", 0),
        "errors_beyond_policy": by_kind.get("beyond_policy", 0),
    }
