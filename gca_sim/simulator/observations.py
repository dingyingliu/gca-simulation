"""What each role can see when it decides. Built by the engine; nothing here refers to truth.

Every field is a plain copy of information the role has under the design: the request as written,
the template, the public policy, register entries the role may read, notes it may read, its own
private knowledge, its own queue. Fields that only truth holds (the true category, the correct
value when the role cannot see it) never appear; tests/test_quotation_access.py checks the names.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DraftObs:
    """The drafting agent, when it drafts a quote."""

    term: str
    template_value: object
    requested_value: object        # a value the customer asked for, or None
    requested_exceeds_policy: bool  # the asked-for value is beyond the written limits
    counter_value: object           # nearest value within the written limits
    register_value: object          # this customer's register entry for the term, if the agent may read it
    note_value: object              # the note about this customer and term that the agent took, or None
    note_author: str | None


@dataclass(frozen=True, slots=True)
class NoteChoiceObs:
    """The drafting agent, before it drafts: the notes about this customer and term that it may read."""

    readable_notes: int         # how many there are; they are ordered oldest first


@dataclass(frozen=True, slots=True)
class RecogniseObs:
    """The drafting agent, deciding whether the quote looks like a local exception."""

    cites_agreement: bool       # the request mentions agreed or promised terms
    register_visible: bool      # the agent can see a register entry for this customer


@dataclass(frozen=True, slots=True)
class PolicyCheckObs:
    """The routing rule, checking the request against the written limits."""

    requested_exceeds_policy: bool


@dataclass(frozen=True, slots=True)
class SelfCheckObs:
    """The drafting agent, checking its own draft before releasing it."""

    term: str
    drafted: object
    requested_value: object
    draft_exceeds_policy: bool
    register_value: object
    note_used: bool
    cites_agreement: bool


@dataclass(frozen=True, slots=True)
class ReviewObs:
    """A regional lead or head office, reviewing a draft."""

    role: str                   # lead | ho
    term: str
    drafted: object
    requested_value: object
    known_value: object         # the correct value as this reviewer knows it (own register, shared
                                # registers, private knowledge), or None if it knows nothing about it
    knows_policy: bool
    draft_exceeds_policy: bool | None   # None if the reviewer does not know the written limits
    counter_value: object
    cites_agreement: bool
    can_query_owner: bool       # the account belongs to another market, whose lead could be asked
    backlog: int                # quotes waiting behind this one in the reviewer's queue
    flag: str | None            # why the quote was escalated, for head office


OBSERVATION_TYPES = (DraftObs, NoteChoiceObs, RecogniseObs, PolicyCheckObs, SelfCheckObs, ReviewObs)
