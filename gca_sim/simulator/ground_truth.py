"""World truth for the quotation research model (E4).

Truth is what is actually the case: each request's true category and correct terms, who holds
which agreement, which promises were made only verbally. No decision function may read it.

The engine builds each role's observation from truth, copying only what that role can see, and
calls every decision function inside `truth_forbidden()`. Inside that block any attribute access
on a truth object raises TruthAccessError (tests/test_quotation_access.py).

The written policy is public and is not truth in this sense, so it is a plain object.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np

_FORBID = contextvars.ContextVar("gca_truth_forbidden", default=False)

REGIONS = ("BR", "TR", "SG")  # invented settings from the walkthrough; no national or cultural traits attached
KINDS = ("standard", "agreement", "verbal", "beyond_policy")


class TruthAccessError(RuntimeError):
    pass


class _TruthForbidden:
    """Context manager: inside it, reading any truth object raises TruthAccessError."""

    __slots__ = ("_tokens",)

    def __init__(self):
        self._tokens = []

    def __enter__(self):
        self._tokens.append(_FORBID.set(True))
        return self

    def __exit__(self, *exc):
        _FORBID.reset(self._tokens.pop())
        return False


_GUARD = _TruthForbidden()


def truth_forbidden() -> _TruthForbidden:
    return _GUARD


class Truth:
    """Base for truth objects. Reading any field while decisions run raises TruthAccessError."""

    __slots__ = ()

    def __getattribute__(self, name):
        if _FORBID.get() and not (name.startswith("__") and name.endswith("__")):
            raise TruthAccessError(f"ground truth read inside a decision: {type(self).__name__}.{name}")
        return object.__getattribute__(self, name)


# ---------------------------------------------------------------- public policy

@dataclass(frozen=True)
class Policy:
    """The written policy limits. Public: every agent and head office can read them."""

    discount_max: float = 10.0
    payment_days_max: int = 60
    free_shipping_min_eur: int = 20_000

    def exceeds(self, term: str, value, order_value_eur: int) -> bool:
        if term == "discount_pct":
            return value is not None and value > self.discount_max
        if term == "payment_days":
            return value is not None and value > self.payment_days_max
        if term == "free_shipping":
            return bool(value) and order_value_eur < self.free_shipping_min_eur
        return False

    def counter(self, term: str):
        """The nearest value within the written limits."""
        return {"discount_pct": self.discount_max, "payment_days": self.payment_days_max,
                "free_shipping": False}.get(term)


POLICY = Policy()


# ---------------------------------------------------------------- truth objects

@dataclass(frozen=True, slots=True)
class Request(Truth):
    id: str
    day: int
    region: str               # market whose agent drafts the quote
    customer: str
    account_owner: str        # region that owns the customer account (visible in the customer record)
    value_eur: int
    kind: str                 # truth: standard | agreement | verbal | beyond_policy
    term: str                 # the term at stake: content | payment_days | unit_price | delivery_stated |
                              # tax_inclusive | discount_pct | free_shipping
    template_value: object    # what the standard template gives
    true_value: object        # the correct value (None for beyond_policy, where only authority matters)
    requested_value: object   # a specific value the customer asked for, or None
    cites_agreement_possible: bool  # the request may mention agreed or promised terms (agreement, verbal)


@dataclass(frozen=True, slots=True)
class Agreement(Truth):
    customer: str
    term: str
    value: object
    holder: str               # region whose lead holds it (negotiated it, or was in the room)
    written: bool             # in the holder's register (True) or verbal only (False)
    stale_value: object       # value of an out-of-date note, if one exists at the start of the week


@dataclass(frozen=True)
class Case:
    name: str
    requests: tuple
    agreements: tuple
    split: str                # walkthrough | development | heldout

    def to_json(self) -> str:
        return json.dumps({"name": self.name, "split": self.split,
                           "requests": [asdict(r) for r in self.requests],
                           "agreements": [asdict(a) for a in self.agreements]}, indent=1, sort_keys=True)

    @staticmethod
    def from_json(text: str) -> "Case":
        d = json.loads(text)
        return Case(d["name"], tuple(Request(**r) for r in d["requests"]),
                    tuple(Agreement(**a) for a in d["agreements"]), d["split"])

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def is_error(req: Request, released_value, approver: str | None, policy: Policy = POLICY) -> bool:
    """Whether the released quote is wrong at the customer."""
    if req.kind == "beyond_policy":
        return policy.exceeds(req.term, released_value, req.value_eur) and approver != "ho"
    return released_value != req.true_value


# ---------------------------------------------------------------- the walkthrough week

def walkthrough_case() -> Case:
    """The walkthrough's twenty quotes as world truth only.

    Taken from the facts in One_Week_in_the_Course.html (Q01 to Q20). The walkthrough's
    behaviour fixtures are not carried over: which drafts go wrong (`draftWrong`), who catches
    what (`catch`) and the routing by true kind. In this model those are behaviour, drawn from
    declared parameters. Q09's "4 units, not 40" was such a fixture; here Q09 is an ordinary
    standard quote whose content can be misread with the standard-quote error rate.
    """

    def std(i, day, region, cust, val):
        return Request(f"Q{i:02d}", day, region, cust, region, val, "standard", "content", "as requested",
                       "as requested", "as requested", False)

    def agr(i, day, region, cust, owner, val, term, template, true):
        return Request(f"Q{i:02d}", day, region, cust, owner, val, "agreement", term, template, true, None, True)

    def pol(i, day, region, cust, val, term, requested):
        return Request(f"Q{i:02d}", day, region, cust, region, val, "beyond_policy", term,
                       POLICY.counter(term), None, requested, False)

    reqs = (
        std(1, 1, "BR", "Aster", 2400),
        agr(2, 1, "BR", "Nexa", "BR", 8200, "payment_days", 30, 60),
        std(3, 1, "TR", "Linden", 4400),
        pol(4, 1, "TR", "Orion", 14500, "discount_pct", 18),
        agr(5, 2, "TR", "Deren", "TR", 3200, "delivery_stated", False, True),
        std(6, 2, "SG", "Vela", 17000),
        agr(7, 2, "SG", "Nexa", "BR", 8200, "payment_days", 30, 60),
        std(8, 2, "BR", "Pine", 2900),
        std(9, 3, "SG", "Sol", 6800),
        agr(10, 3, "BR", "Cedar", "BR", 5100, "unit_price", 99, 105),
        std(11, 3, "TR", "Tern", 4100),
        pol(12, 3, "SG", "Vega", 9900, "payment_days", 90),
        std(13, 4, "BR", "Iris", 3300),
        Request("Q14", 4, "SG", "Lotus", "SG", 7600, "verbal", "tax_inclusive", False, True, None, True),
        std(15, 4, "TR", "Birch", 2100),
        std(16, 4, "SG", "Elm", 5400),
        agr(17, 5, "TR", "Barut", "TR", 6100, "unit_price", 84, 88),
        pol(18, 5, "BR", "Onda", 12800, "free_shipping", True),
        std(19, 5, "BR", "Ravi", 1900),
        std(20, 5, "TR", "Sana", 2600),
    )
    agreements = (
        Agreement("Nexa", "payment_days", 60, "BR", True, 45),
        Agreement("Deren", "delivery_stated", True, "TR", True, False),
        Agreement("Cedar", "unit_price", 105, "BR", True, 100),
        Agreement("Barut", "unit_price", 88, "TR", True, 84),  # walkthrough: agreed in last year's negotiation
        Agreement("Lotus", "tax_inclusive", True, "SG", False, None),
    )
    return Case("W0 walkthrough week", reqs, agreements, "walkthrough")


# ---------------------------------------------------------------- generated weeks

_NAMES = (
    "Alder", "Basalt", "Cobalt", "Delta", "Ember", "Fjord", "Garnet", "Harbor", "Indigo", "Juniper",
    "Kestrel", "Lumen", "Marble", "Nimbus", "Onyx", "Pebble", "Quartz", "Rowan", "Sable", "Tundra",
    "Umber", "Vireo", "Willow", "Xenon", "Yarrow", "Zephyr", "Acorn", "Birchwood", "Cirrus", "Dahlia",
    "Elmstead", "Fennel", "Granite", "Hazel", "Iris Bay", "Jasper", "Kelp", "Larch", "Meadow", "Nettle",
    "Oakmont", "Pine Ridge", "Quill", "Reed", "Sorrel", "Thistle", "Upland", "Vale", "Wren", "Yew",
    "Amber", "Bramble", "Clover", "Drift", "Echo", "Flint", "Glade", "Heron", "Ivy", "Jade",
    "Kite", "Lark", "Moss", "Nook", "Orchid", "Plover", "Quarry", "Ridge", "Slate", "Teal",
    "Ultra", "Vista", "Wharf", "Yonder", "Zinc", "Aspen", "Brook", "Cove", "Dell", "Elm Row",
)
# Development weeks draw customer names from the first half, held-out weeks from the second half,
# so no customer appears on both sides of the split.
_NAME_POOLS = {"development": _NAMES[: len(_NAMES) // 2], "heldout": _NAMES[len(_NAMES) // 2:]}


def generate_week(seed: int, split: str, name: str) -> Case:
    """A synthetic week with the walkthrough's composition plus more cross-market repeat customers.

    20 requests over five days, three markets: 11 standard (two from cross-market accounts with no
    agreement), 3 beyond policy, 6 needing local knowledge: two agreement customers quoted twice each
    (once by the owning market, once by another), one agreement customer quoted once, one verbal promise.
    """
    if split not in _NAME_POOLS:
        raise ValueError(split)
    rng = np.random.default_rng(seed)
    names = [str(n) for n in rng.permutation(_NAME_POOLS[split])[:18]]
    regions = list(REGIONS)
    days = sorted(int(d) for d in rng.permutation(np.repeat(np.arange(1, 6), 4)))
    slots = list(rng.permutation(20))  # which day slot each request takes
    reqs, agreements = [], []

    def value(lo=1500, hi=18000):
        return int(rng.integers(lo, hi) // 100 * 100)

    def agreement_terms():
        term = str(rng.choice(["payment_days", "unit_price", "delivery_stated"]))
        if term == "payment_days":
            true, template, stale = int(rng.choice([45, 60])), 30, None
            stale = 45 if true == 60 else 60
        elif term == "unit_price":
            true = int(rng.integers(85, 120))
            template = true - int(rng.integers(4, 10))
            stale = true - int(rng.integers(1, true - template))
        else:
            true, template, stale = True, False, False
        return term, template, true, stale

    specs = []  # (kind, region, customer, owner, extra)
    for k in range(2):  # repeat agreement customers
        owner, other = [str(r) for r in rng.permutation(regions)[:2]]
        cust = names.pop()
        term, template, true, stale = agreement_terms()
        agreements.append(Agreement(cust, term, true, owner, True, stale))
        order = [owner, other] if rng.random() < 0.5 else [other, owner]
        for reg in order:
            specs.append(("agreement", reg, cust, owner, (term, template, true)))
    cust = names.pop()
    owner = str(rng.choice(regions))
    term, template, true, stale = agreement_terms()
    agreements.append(Agreement(cust, term, true, owner, True, stale))
    specs.append(("agreement", owner, cust, owner, (term, template, true)))
    cust = names.pop()
    owner = str(rng.choice(regions))
    agreements.append(Agreement(cust, "tax_inclusive", True, owner, False, None))
    specs.append(("verbal", owner, cust, owner, ("tax_inclusive", False, True)))
    for _ in range(3):
        cust = names.pop()
        reg = str(rng.choice(regions))
        term = str(rng.choice(["discount_pct", "payment_days", "free_shipping"]))
        requested = {"discount_pct": int(rng.integers(12, 25)), "payment_days": int(rng.choice([75, 90, 120])),
                     "free_shipping": True}[term]
        specs.append(("beyond_policy", reg, cust, reg, (term, requested)))
    for k in range(11):
        cust = names.pop()
        reg = str(rng.choice(regions))
        owner = reg
        if k < 2:  # cross-market account without any agreement
            owner = str(rng.choice([r for r in regions if r != reg]))
        specs.append(("standard", reg, cust, owner, None))

    # keep the two quotes of each repeat customer in their drawn order: assign sorted day slots
    order_idx = list(range(len(specs)))
    day_of = {}
    shuffled = [int(s) for s in slots]
    for i in order_idx:
        day_of[i] = days[shuffled[i]]
    for c in {s[2] for s in specs if s[0] == "agreement"}:
        idx = [i for i, s in enumerate(specs) if s[2] == c]
        if len(idx) == 2:
            a, b = sorted(day_of[i] for i in idx)
            day_of[idx[0]], day_of[idx[1]] = a, b
    ordered = sorted(range(len(specs)), key=lambda i: (day_of[i], i))
    for n, i in enumerate(ordered, start=1):
        kind, reg, cust, owner, extra = specs[i]
        qid = f"{name[:2]}Q{n:02d}"
        val = value()
        if kind == "standard":
            reqs.append(Request(qid, day_of[i], reg, cust, owner, val, kind, "content", "as requested",
                                "as requested", "as requested", False))
        elif kind == "agreement":
            term, template, true = extra
            reqs.append(Request(qid, day_of[i], reg, cust, owner, val, kind, term, template, true, None, True))
        elif kind == "verbal":
            term, template, true = extra
            reqs.append(Request(qid, day_of[i], reg, cust, owner, val, kind, term, template, true, None, True))
        else:
            term, requested = extra
            if term == "free_shipping":
                val = value(1500, 19000)
            reqs.append(Request(qid, day_of[i], reg, cust, owner, val, kind, term, POLICY.counter(term), None,
                                requested, False))
    return Case(name, tuple(reqs), tuple(agreements), split)


def development_cases() -> list[Case]:
    return [walkthrough_case()] + [generate_week(s, "development", f"G{s} development week") for s in (1, 2, 3, 4)]


def heldout_cases() -> list[Case]:
    return [generate_week(s, "heldout", f"H{s - 100} held-out week") for s in (101, 102, 103, 104)]
