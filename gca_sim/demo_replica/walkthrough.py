"""Faithful Python port of `simulate(d)` from the walkthrough (One_Week_in_the_Course.html).

This is a regression baseline that reproduces a demonstration. It is not a research model
and its outputs are illustrative.

Two properties of the original are kept on purpose, because the port must match it, and
must not be carried into the research model in `gca_sim/`:

1. Routing reads the quote's true category (`route = d[q["kind"]]`, line 480 of the HTML).
   The program therefore already knows which quotes are exceptions. In the research model,
   routing acts only on what a role can observe, and recognising an exception can fail.
2. The bypass rule. The walkthrough assumes that after three days in a review queue the
   sales team sends the quote itself, unreviewed. It is a named assumption here,
   `PrototypeAssumptions.bypass_after_days`, and is off unless a caller turns it on.

Comments give the line numbers of the matching JavaScript in walkthrough_script.js.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .case import ACCT, ACTION, CAP, DELAY, LEAD, MK, Q, QUEUE_PER_OVER


@dataclass(frozen=True)
class PrototypeAssumptions:
    """Assumptions of the walkthrough model that are not facts of the case.

    bypass_after_days: days a quote may wait for review before the sales team sends it
        itself, unreviewed and with no approval recorded. The walkthrough uses 3
        (`const BYPASS=3`). The course's case notes say not to assume that staff evade
        controls when review becomes slower, so the default is None (off): a waiting quote is
        reviewed late instead. Only the golden regression test turns it on, to reproduce
        the published walkthrough.
    """

    bypass_after_days: float | None = None


# The value the published walkthrough uses. For the golden regression test only.
WALKTHROUGH_ASSUMPTIONS = PrototypeAssumptions(bypass_after_days=3)


def js_round(x: float) -> int:
    """JavaScript Math.round: nearest integer, ties toward +infinity."""
    f = math.floor(x)
    return f + 1 if x - f >= 0.5 else f


def r1(x: float) -> str:
    """JavaScript `(Math.round(x*10)/10).toFixed(1)`."""
    return f"{js_round(x * 10) / 10:.1f}"


def js_num(x: float) -> str:
    """JavaScript default number-to-string for the values this model produces."""
    x = float(x)
    return str(int(x)) if x.is_integer() else repr(x)


def _plural_day(n: float) -> str:
    return "day" if n == 1 else "days"


def _number_word(n: float) -> str:
    return {3: "three"}.get(n, js_num(n))


def can_see(q: dict, who: str, d: dict) -> bool:
    """`canSee` (lines 43 to 48)."""
    if not q["draftWrong"]:
        return False
    v = (q.get("catch") or {}).get(who)
    if v == "records":
        return bool(d["share"])
    return bool(v)


def agent_can_check(q: dict, d: dict) -> bool:
    """`agentCanCheck` (lines 50 to 54)."""
    if q["checkable"] == "policy":
        return True
    if q["checkable"] == "records":
        return bool(d["share"])
    return False


def simulate(d: dict, assumptions: PrototypeAssumptions = PrototypeAssumptions()) -> dict:
    """`simulate(d)` (lines 56 to 136). Returns the same structure as the JavaScript."""
    bypass = assumptions.bypass_after_days
    queues: dict[str, list[str]] = {"BR": [], "TR": [], "SG": [], "HO": []}
    rows = []
    for q in Q:
        t: list[dict] = []
        r = dict(q)
        r["trace"] = t
        wrong = q["draftWrong"]
        # the agent drafts from what it can reach
        if wrong and d["share"] and q.get("fixedByRecords"):
            wrong = None
        t.append({"cls": "", "k": "The request",
                  "v": f"{q['cust']}, {MK[q['mk']]}, €{q['val']:,}, day {q['day']}. {q['record']}"})
        if wrong:
            drafted = f"From the standard template: {wrong}."
        elif q["draftWrong"]:
            drafted = ("Correctly. The regional agreement was available to it, and the standard "
                       "template alone would have got this wrong.")
        else:
            drafted = "Correctly."
        t.append({"cls": "agent", "k": "The agent drafts", "v": drafted})

        # Line 65 (line 480 of the HTML): routing on the TRUE category. Demonstration only; not for research use.
        route = d[q["kind"]]
        reviewer_mk = q["mk"]
        if q.get("cross") and d["cross"] and route != "agent":
            route = "regional"
            reviewer_mk = q["cross"]
        r["route"] = route

        if route == "agent":
            flagged = bool(wrong) and agent_can_check(q, d)
            if not flagged:
                if wrong:
                    given = "it has been given" if d["share"] else "it has not been given"
                    if q["checkable"] != "none":
                        tail = "The agreement that would have caught it sits with a lead."
                    elif q.get("missReason") == "quantity":
                        tail = ("The quantity was in the original request, but this agent’s check does "
                                "not compare quantities against the request.")
                    else:
                        tail = "What this quote turns on was agreed verbally and written nowhere."
                    checks = (f"Against the written limits, and against the regional agreements {given}. "
                              f"Nothing it can read contradicts this draft, so it passes. {tail}")
                else:
                    checks = "Against the written limits. Nothing to correct."
                t.append({"cls": "", "k": "The agent checks", "v": checks})
                t.append({"cls": "", "k": "Released",
                          "v": "Sent without human approval, under the rule the team wrote. "
                               "Accountability sits with the team."})
                r["out"] = q["day"] + DELAY["agent"]
                r["acct"] = "team"
                r["err"] = wrong
            else:
                t.append({"cls": "okdot", "k": "The agent checks",
                          "v": "It can read the rule this draft breaks, so it does not send. "
                               "Held and escalated to head office."})
                qu = queues["HO"]
                qu.append(q["id"])
                pos = len(qu)
                if pos <= CAP["ho"]:
                    t.append({"cls": "", "k": "Head office",
                              "v": f"Reviews the flagged draft and corrects it. {js_num(DELAY['ho'])} days added. "
                                   f"Escalation {pos} of {CAP['ho']} head office can take this week."})
                    r["out"] = q["day"] + DELAY["agent"] + DELAY["ho"]
                    r["acct"] = "ho"
                    r["err"] = None
                    r["fixed"] = True
                    r["escalated"] = True
                else:
                    wait = (pos - CAP["ho"]) * QUEUE_PER_OVER
                    if bypass is not None and wait >= bypass:
                        t.append({"cls": "gapdot", "k": "The queue",
                                  "v": f"Head office already had {CAP['ho']} escalations. This one would have "
                                       f"waited {r1(wait)} days. After {js_num(bypass)} days the sales team sends "
                                       f"the draft itself, so it went out on day {js_num(q['day'] + bypass)}, "
                                       f"unreviewed and with no approval recorded."})
                        r["out"] = q["day"] + bypass
                        r["acct"] = "nobody"
                        r["err"] = wrong
                        r["bypass"] = True
                    else:
                        t.append({"cls": "", "k": "Head office",
                                  "v": f"Waited {r1(wait)} days behind other escalations, then corrected. "
                                       f"{js_num(DELAY['ho'])} days of review added."})
                        r["out"] = q["day"] + DELAY["agent"] + DELAY["ho"] + wait
                        r["acct"] = "ho"
                        r["err"] = None
                        r["fixed"] = True
                        r["escalated"] = True
        else:
            key = "HO" if route == "ho" else reviewer_mk
            qu = queues[key]
            qu.append(q["id"])
            pos = len(qu)
            cap = CAP["ho"] if route == "ho" else CAP["regional"]
            who = "Head office" if route == "ho" else f"{LEAD[reviewer_mk]}, {MK[reviewer_mk]} lead"
            base = DELAY["ho"] if route == "ho" else DELAY["regional"]
            wait = (pos - cap) * QUEUE_PER_OVER if pos > cap else 0
            lead_in = (f"Referred to {who}, who holds the Nexa agreement." if q.get("cross") and d["cross"]
                       else f"{ACTION[route]}: {who}.")
            t.append({"cls": "", "k": "The route",
                      "v": f"{lead_in} Quote {pos} of {cap} this reviewer can take this week."})
            if bypass is not None and wait >= bypass:
                t.append({"cls": "gapdot", "k": "The queue",
                          "v": f"{who} already had {cap} quotes. This one would have waited {r1(wait)} days for "
                               f"review. After {js_num(bypass)} days this company's sales team sends the quote "
                               f"itself, so it went out on day {js_num(q['day'] + bypass)}, unreviewed and with "
                               f"no approval recorded."})
                r["out"] = q["day"] + bypass
                r["acct"] = "nobody"
                r["err"] = wrong
                r["bypass"] = True
            else:
                if route == "ho":
                    sees = can_see(q, "ho", d)
                elif reviewer_mk == q["mk"]:
                    sees = can_see(q, "regional", d)
                else:
                    sees = can_see(q, "other", d)
                waited = f"Waited {r1(wait)} days in the queue. " if wait > 0 else ""
                if wrong and sees:
                    r["err"] = None
                    r["fixed"] = True
                    t.append({"cls": "okdot", "k": "The review",
                              "v": f"{waited}{who} sees it and corrects it. {js_num(base)} {_plural_day(base)} added."})
                elif wrong:
                    r["err"] = wrong
                    if route == "ho":
                        why = "Head office does not hold the regional agreement."
                    elif reviewer_mk != q["mk"]:
                        why = "The agreement sits with another market's lead."
                    else:
                        why = "Not visible from what this lead knows."
                    t.append({"cls": "", "k": "The review",
                              "v": f"{waited}{who} reads it and passes it. {why} {js_num(base)} "
                                   f"{_plural_day(base)} added."})
                else:
                    # As in the original, `err` is left unset here (undefined in JavaScript).
                    t.append({"cls": "", "k": "The review",
                              "v": f"{waited}{who} reads it and passes it. Nothing to correct. {js_num(base)} "
                                   f"{_plural_day(base)} of review time spent."})
                r["out"] = q["day"] + base + wait
                r["acct"] = route

        r["days"] = js_round((r["out"] - q["day"]) * 10) / 10
        err = r.get("err")
        t.append({"cls": "gapdot" if err else "okdot", "k": "The customer",
                  "v": f"Receives it on day {r1(r['out'])}, {r1(r['days'])} {_plural_day(r['days'])} after asking."
                       + (f" It is wrong: {err}." if err else " It is right.")})
        if d["owner"] == "regional":
            owner_txt = f"{LEAD[q['mk']]} calls {q['cust']}."
        elif d["owner"] == "ho":
            owner_txt = f"The head of sales calls {q['cust']}."
        else:
            owner_txt = f"Nobody is named to call {q['cust']}. The rules left this open."
        if r["acct"] == "nobody":
            practice = _number_word(bypass) if bypass is not None else "bypass"
            acct_txt = (f"No approval was recorded. The quote left under the company's {practice}-day practice, "
                        f"which the team's rules did not authorise. The team remains accountable for the rule "
                        f"that created the queue.")
        else:
            acct_txt = f"Approved by: {ACCT[r['acct']]}."
        t.append({"cls": "gapdot" if (err and d["owner"] == "none") else "", "k": "Accountability",
                  "v": acct_txt + (" " + owner_txt if err else "")})
        rows.append(r)

    n = len(rows)
    time = sum(r["days"] for r in rows) / n
    load = {k: len(queues[k]) for k in ("BR", "TR", "SG", "HO")}
    errs = [r for r in rows if r.get("err")]
    acct = {"team": 0, "regional": 0, "ho": 0, "nobody": 0}
    for r in rows:  # over ALL twenty quotes
        acct[r["acct"]] += 1
    unsigned = sum(1 for r in rows if r["acct"] == "nobody")
    unowned_errs = len(errs) if d["owner"] == "none" else 0
    return {"rows": rows, "time": time, "load": load, "errs": errs, "acct": acct, "unsigned": unsigned,
            "unownedErrs": unowned_errs, "regUsed": load["BR"] + load["TR"] + load["SG"], "hoUsed": load["HO"]}


def summary(o: dict) -> str:
    """`summary(o)` from the walkthrough UI (lines 151 to 159)."""
    p = [f"{len(o['errs'])} wrong {'quote' if len(o['errs']) == 1 else 'quotes'} reached customers",
         f"{r1(o['time'])} days average to the customer",
         f"the leads were sent {o['regUsed']} quotes for {CAP['regional'] * 3} review slots"]
    if o["unsigned"]:
        p.append(f"{o['unsigned']} went out with no approval recorded")
    if o["unownedErrs"]:
        p.append(f"no follow-up owner named for the {o['unownedErrs']} wrong "
                 f"{'quote' if o['unownedErrs'] == 1 else 'quotes'}")
    return ", ".join(p) + "."
