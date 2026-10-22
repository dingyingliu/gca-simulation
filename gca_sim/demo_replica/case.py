"""The walkthrough's fixed case, transcribed from the original JavaScript.

Source: gca_sim/demo_replica/original/walkthrough_script.js, lines 3 to 41 (the `MK`, `LEAD`,
`Q`, `CAP`, `DELAY`, `QUEUE_PER_OVER`, `KIND`, `ACTION`, `ACCT`, `PRESET` and `PNAME`
constants). Every value here is invented for the demonstration and is illustrative.
Keys keep the JavaScript names so outputs compare directly with the golden files.

`BYPASS` is deliberately not here. It is an assumption about staff behaviour, not a case
fact, and lives in `walkthrough.PrototypeAssumptions`.
"""

from __future__ import annotations

MK = {"BR": "Brazil", "TR": "Türkiye", "SG": "Singapore"}
LEAD = {"BR": "Ana", "TR": "Deniz", "SG": "Mei"}

# checkable: what written rule, if any, the agent could test this draft against.
#   'policy'  = the written policy limits, always available to the agent
#   'records' = the regional agreements, available only if shared
#   'none'    = nothing written to check against
Q = [
    {"id": "Q01", "mk": "BR", "cust": "Aster", "kind": "std", "day": 1, "val": 2400,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q02", "mk": "BR", "cust": "Nexa", "kind": "loc", "day": 1, "val": 8200,
     "record": "Nexa distributor agreement, 60-day payment terms, negotiated by Ana.",
     "draftWrong": "30-day terms instead of the agreed 60", "fixedByRecords": True, "checkable": "records",
     "catch": {"regional": True, "ho": "records", "other": "records"}},
    {"id": "Q03", "mk": "TR", "cust": "Linden", "kind": "std", "day": 1, "val": 4400,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q04", "mk": "TR", "cust": "Orion", "kind": "pol", "day": 1, "val": 14500,
     "record": "Orion asked for 18 per cent. The written limit is 10.",
     "draftWrong": "18 per cent discount, written limit is 10", "checkable": "policy",
     "catch": {"regional": True, "ho": True}},
    {"id": "Q05", "mk": "TR", "cust": "Deren", "kind": "loc", "day": 2, "val": 3200,
     "record": "Deren's contract requires the delivery term stated on every quote. Deren rejects quotes without it.",
     "draftWrong": "no delivery term stated", "fixedByRecords": True, "checkable": "records",
     "catch": {"regional": True, "ho": False, "other": False}},
    {"id": "Q06", "mk": "SG", "cust": "Vela", "kind": "std", "day": 2, "val": 17000,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q07", "mk": "SG", "cust": "Nexa", "kind": "loc", "day": 2, "val": 8200,
     "record": "Same Nexa agreement as Q02, held by Ana in Brazil. Singapore's template does not have it.",
     "draftWrong": "30-day terms instead of the agreed 60", "fixedByRecords": True, "checkable": "records",
     "cross": "BR", "catch": {"regional": "records", "ho": "records", "other": True}},
    {"id": "Q08", "mk": "BR", "cust": "Pine", "kind": "std", "day": 2, "val": 2900,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q09", "mk": "SG", "cust": "Sol", "kind": "std", "day": 3, "val": 6800,
     "record": "Standard catalogue. The request said 40 units.",
     "draftWrong": "quoted for 4 units, not 40", "fixedByRecords": False, "checkable": "none",
     "missReason": "quantity", "catch": {"regional": True, "ho": True, "other": True}},
    {"id": "Q10", "mk": "BR", "cust": "Cedar", "kind": "loc", "day": 3, "val": 5100,
     "record": "Cedar distributor agreement, minimum unit price €105.",
     "draftWrong": "€99 per unit, below the €105 floor", "fixedByRecords": True, "checkable": "records",
     "catch": {"regional": True, "ho": "records", "other": "records"}},
    {"id": "Q11", "mk": "TR", "cust": "Tern", "kind": "std", "day": 3, "val": 4100,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q12", "mk": "SG", "cust": "Vega", "kind": "pol", "day": 3, "val": 9900,
     "record": "Vega asked for 90-day terms. The written limit is 60. Mei does not know the limit.",
     "draftWrong": "90-day terms, written limit is 60", "checkable": "policy",
     "catch": {"regional": False, "ho": True}},
    {"id": "Q13", "mk": "BR", "cust": "Iris", "kind": "std", "day": 4, "val": 3300,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q14", "mk": "SG", "cust": "Lotus", "kind": "loc", "day": 4, "val": 7600,
     "record": "Lotus was promised tax-inclusive pricing in a meeting. Written nowhere.",
     "draftWrong": "price quoted before tax", "fixedByRecords": False, "checkable": "none",
     "missReason": "verbal", "catch": {"regional": True, "ho": False, "other": False}},
    {"id": "Q15", "mk": "TR", "cust": "Birch", "kind": "std", "day": 4, "val": 2100,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q16", "mk": "SG", "cust": "Elm", "kind": "std", "day": 4, "val": 5400,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q17", "mk": "TR", "cust": "Barut", "kind": "loc", "day": 5, "val": 6100,
     "record": "Barut agreed minimum price €88, from last year's negotiation.",
     "draftWrong": "€84 per unit, below the agreed €88", "fixedByRecords": True, "checkable": "records",
     "catch": {"regional": True, "ho": "records", "other": "records"}},
    {"id": "Q18", "mk": "BR", "cust": "Onda", "kind": "pol", "day": 5, "val": 12800,
     "record": "Onda asked for free shipping on a €12,800 order. The written limit allows it above €20,000.",
     "draftWrong": "free shipping below the written threshold", "checkable": "policy",
     "catch": {"regional": True, "ho": True}},
    {"id": "Q19", "mk": "BR", "cust": "Ravi", "kind": "std", "day": 5, "val": 1900,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
    {"id": "Q20", "mk": "TR", "cust": "Sana", "kind": "std", "day": 5, "val": 2600,
     "record": "Standard catalogue, 30-day terms.", "draftWrong": None, "checkable": "none"},
]

CAP = {"regional": 4, "ho": 3}
DELAY = {"agent": 0.5, "regional": 1, "ho": 2.5}
QUEUE_PER_OVER = 1.5  # days of wait added by each quote beyond a reviewer's capacity
KIND = {"std": "Standard", "loc": "Local knowledge", "pol": "Beyond policy"}
ACTION = {"agent": "Agent checks and sends", "regional": "Regional review", "ho": "Head-office review"}
ACCT = {"team": "the team, through its rule", "regional": "the regional lead", "ho": "head office",
        "nobody": "no approval recorded"}
PRESET = {
    "review": {"std": "regional", "loc": "regional", "pol": "regional", "share": False, "cross": False,
               "owner": "regional"},
    "limits": {"std": "agent", "loc": "agent", "pol": "ho", "share": True, "cross": False, "owner": "ho"},
    "local": {"std": "agent", "loc": "regional", "pol": "ho", "share": False, "cross": True, "owner": "regional"},
}
PNAME = {"review": "Review every quote", "limits": "Release within shared limits", "local": "Refer local exceptions"}
