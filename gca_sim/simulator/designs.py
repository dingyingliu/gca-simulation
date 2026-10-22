"""The team's design: who may see what, who may release what, and where work is routed.

The three designs follow the walkthrough's presets, re-expressed so that routing acts only on
what the routing rule can observe (a written limit exceeded, the agent's own recognition of a
local exception, the customer record's owning market), never on a quote's true category.
Context (shared or isolated agent notes) is a separate factor.
"""

from __future__ import annotations

from dataclasses import dataclass

AGENT, LEAD, HO, NONE = "agent", "lead", "ho", "none"


@dataclass(frozen=True)
class Design:
    key: str
    name: str
    share_agreements: bool          # regional registers readable by agents, head office and every lead
    agent_may_release: bool
    review_every_quote: bool        # every quote goes to the drafting market's lead
    refer_recognised_local: bool    # quotes the agent recognises as local exceptions go to a lead
    refer_cross_market: bool        # accounts owned by another market go to that market's lead
    policy_breach_to_ho: bool       # requests beyond the written limits go to head office
    agent_flags_to_ho: bool         # drafts the agent's own check flags go to head office

    def release_authority(self) -> frozenset:
        """(actor kind, route) pairs allowed to release. Checked by the hard-constraint tests.

        Head office holds authority for exceptions to the written limits in every design, so a quote the
        policy gate escalates is released by head office on the head-office route."""
        pairs = {(HO, HO)}
        if self.agent_may_release:
            pairs.add((AGENT, AGENT))
        if self.review_every_quote or self.refer_recognised_local or self.refer_cross_market:
            pairs.add((LEAD, LEAD))
        return frozenset(pairs)


DESIGNS = {
    "review": Design("review", "Review every quote", share_agreements=False, agent_may_release=False,
                     review_every_quote=True, refer_recognised_local=False, refer_cross_market=False,
                     policy_breach_to_ho=False, agent_flags_to_ho=False),
    "limits": Design("limits", "Release within shared limits", share_agreements=True, agent_may_release=True,
                     review_every_quote=False, refer_recognised_local=False, refer_cross_market=False,
                     policy_breach_to_ho=True, agent_flags_to_ho=True),
    "local": Design("local", "Refer local exceptions", share_agreements=False, agent_may_release=True,
                    review_every_quote=False, refer_recognised_local=True, refer_cross_market=True,
                    policy_breach_to_ho=True, agent_flags_to_ho=True),
}

CONTEXTS = ("isolated", "shared")
RELEASE_RULES = {
    AGENT: "agent_release_under_team_rule",
    LEAD: "lead_approval",
    HO: "head_office_approval",
}
