"""Task bank for the agent pilot (plan sections 3 and 5): eight synthetic shared groups, built by code.

Everything is invented: company names, products, prices and agreements. Regions are Region A, B and C with no
national or cultural attributes; they differ only in what each holds and sees. Each group has two standard
customers and three agreement customers (Help, Harm, Own), six scored tasks in a fixed order, a register in two
versions (V+ and V-) with the same number of entries, and seed notes for a shared store (S) and for one store per
region (I), ten notes in view in every case.

The split is fixed here, before any run: G01 is the set-up group, G02 to G06 development, G07 and G08 held-out.
Set-up and development use wording template 1; held-out uses template 2 only.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SEED = 20261002
SPLITS = {"G01": "setup", "G02": "development", "G03": "development", "G04": "development", "G05": "development",
          "G06": "development", "G07": "heldout", "G08": "heldout"}
TEMPLATE = {"setup": 1, "development": 1, "heldout": 2}
TERM_TYPES = ("payment", "price_floor", "delivery")
STANDARD_PAYMENT = 30
MAX_DISCOUNT = 10
# order, region, customer key (plan section 3.2); Region A writes seed notes and quotes nothing scored
ORDERS = ((1, "Region B", "standard_1"), (2, "Region B", "help"), (3, "Region C", "harm"),
          (4, "Region B", "own"), (5, "Region B", "harm"), (6, "Region C", "standard_2"))
ROLE = {"standard_1": "Standard", "standard_2": "Standard", "help": "Help", "harm": "Harm", "own": "Own"}
NOTES_IN_VIEW = 10

PAYMENT_AGREED = (45, 60)                       # the truth is one, the planted wrong note says the other
PAYMENT_OTHERS = (35, 40, 50, 55)               # other customers' agreed payment terms, all within the policy
DELIVERY_POOL = (12, 14, 16, 18, 21, 24, 26, 28)  # no value equals a payment term, a discount or a quantity
QUANTITIES = (120, 150, 180, 200, 240, 250, 300, 360, 400, 480)
PRODUCTS = ("gate valve", "pressure sensor", "drive belt", "bearing unit", "hydraulic coupling", "control relay",
            "filter cartridge", "gear housing", "flow regulator", "seal kit", "mounting bracket", "pump rotor")
STEMS = ("Bren", "Kel", "Vor", "Tal", "Mer", "Dun", "Hal", "Ost", "Rin", "Sel", "Tor", "Ulm", "Wex", "Yar", "Zen",
         "Arn", "Cor", "Fen", "Gil", "Jor", "Lun", "Nor", "Pel", "Quil", "Bax", "Dov", "Eld", "Fal", "Har", "Ivo")
ENDINGS = ("mar", "wick", "dale", "holm", "stead", "ton", "mont", "berg", "field", "ford", "gate", "moor")
SUFFIXES = ("Components", "Engineering", "Supplies", "Industrial", "Fabrication", "Systems", "Tooling", "Works")

REGISTER_WORDING = {
    "payment": {1: "{customer}: payment terms {value} days net.",
                2: "{customer}: invoices fall due {value} days after the invoice date."},
    "price_floor": {1: "{customer}: minimum net unit price EUR {value} for {product}.",
                    2: "{customer}: the net unit price for {product} is not to fall below EUR {value}."},
    # The delivery term names one value, so exactly one stated time complies (review round 10, Claude R10.1).
    "delivery": {1: "{customer}: every quote must state a delivery time of {value} days.",
                 2: "{customer}: each quote is to confirm delivery {value} days after the order."},
}
# Seed notes are about as long as the notes an agent writes (about 20 words), whatever their kind, so that the
# notes block is as long in the shared arm as in the isolated arm, at the start and as agent notes replace seeds
# (review round 10, Codex R10.7).
NOTE_WORDING = {
    "payment": {1: "Quote for {customer}: {quantity} units of {product} at {discount}% discount, with their agreed payment terms of {value} days. Released.",
                2: "{customer} asked for {quantity} units of {product}; quoted {discount}% off list with the {value}-day payment terms we agreed with them. Sent."},
    "price_floor": {1: "Quote for {customer}: {quantity} units of {product} at their agreed minimum net price of EUR {value} per unit, standard 30-day payment terms. Released.",
                    2: "{customer} asked for {quantity} units of {product}; quoted the agreed floor of EUR {value} per unit on standard 30-day terms. Sent."},
    "delivery": {1: "Quote for {customer}: {quantity} units of {product} at {discount}% discount, stating a delivery time of {value} days as agreed. Released.",
                 2: "{customer} asked for {quantity} units of {product}; quoted {discount}% off list and confirmed the agreed delivery time of {value} days. Sent."},
    "standard": {1: "Quote for {customer}: {quantity} units of {product} at {discount}% discount, standard 30-day payment terms, no agreement on file. Released.",
                 2: "{customer} asked for {quantity} units of {product}; quoted {discount}% off list on standard 30-day terms, nothing on file for them. Sent."},
}
REQUEST = "Please send us a quote for {quantity} units of {product}. We would like a {discount}% discount."
REQUEST_AGREED = " Please apply the terms we agreed with your company."


def money(x: float) -> str:
    return f"{x:.2f}"


def _fmt(term_type: str, value) -> str:
    return money(value) if term_type == "price_floor" else str(value)


def all_names() -> list[str]:
    """Every invented customer name, in one fixed shuffled order; each is used at most once in the whole bank.
    The first word of every name is unique, so a note that shortens a name still identifies one customer."""
    rng = random.Random(f"{SEED}:names")
    names = [f"{s}{e} {rng.choice(SUFFIXES)}" for s in STEMS for e in ENDINGS]
    rng.shuffle(names)
    return names


def short_name(name: str) -> str:
    return name.split()[0]


def discounted(list_price: float, discount: int) -> float:
    return round(list_price * (1 - discount / 100), 2)


def make_group(gid: str, position: int, names: list[str]) -> dict:
    """One shared group. `position` (0 to 7) rotates which agreement customer has which term type; `names` is
    consumed from the front, so no name is used twice."""
    split = SPLITS[gid]
    tpl = TEMPLATE[split]
    rng = random.Random(f"{SEED}:{gid}")
    take = lambda: names.pop(0)  # noqa: E731

    products = rng.sample(PRODUCTS, 4)
    price_list = {p: rng.randrange(40, 400) + rng.choice((0.2, 0.4, 0.6, 0.8)) for p in products}
    type_of = {"harm": TERM_TYPES[position % 3], "help": TERM_TYPES[(position + 1) % 3],
               "own": TERM_TYPES[(position + 2) % 3]}

    prices_used: list[float] = []  # every price-like value an output could be compared with, kept distinct

    def distinct_price(make) -> float:
        for _ in range(200):
            v = make()
            if all(abs(v - u) >= 0.02 for u in prices_used):
                prices_used.append(v)
                return v
        raise RuntimeError("could not find a distinct price")

    delivery_values = rng.sample(DELIVERY_POOL, 4)       # true, planted, two other customers
    payment_true = rng.choice(PAYMENT_AGREED)
    payment_others = rng.sample(PAYMENT_OTHERS, 2)

    customers = {}
    for key in ("standard_1", "help", "harm", "own", "standard_2"):
        term_type = type_of.get(key)
        choice = {}

        def standard_price(term_type=term_type, choice=choice):
            choice["product"] = rng.choice(products)
            choice["discount"] = (rng.choice((8, 9, 10)) if term_type == "price_floor"
                                  else rng.randrange(3, MAX_DISCOUNT + 1))
            return discounted(price_list[choice["product"]], choice["discount"])

        standard_unit_price = distinct_price(standard_price)
        product, discount = choice["product"], choice["discount"]
        lp = price_list[product]
        c = {"name": take(), "role": ROLE[key], "product": product, "requested_discount": discount,
             "list_price": lp, "standard_unit_price": standard_unit_price,
             "term_type": term_type, "true_value": None, "planted_value": None}
        if term_type == "payment":
            c["true_value"] = payment_true
            c["planted_value"] = sum(PAYMENT_AGREED) - payment_true
        elif term_type == "delivery":
            c["true_value"], c["planted_value"] = delivery_values[0], delivery_values[1]
        elif term_type == "price_floor":
            # the floor allows only a small discount; the planted floor lies between the standard price and the truth
            c["true_value"] = distinct_price(lambda lp=lp: discounted(lp, rng.choice((2, 3))))
            c["planted_value"] = distinct_price(lambda lp=lp: discounted(lp, rng.choice((5, 6))))
        if key != "harm":
            c["planted_value"] = None  # only the Harm customer has a planted wrong note
        customers[key] = c

    fillers = []  # agreement customers outside the task bank: register entries and irrelevant notes
    for i, term_type in enumerate(TERM_TYPES * 2):
        product = rng.choice(products)
        if term_type == "payment":
            value = payment_others[i // 3]
        elif term_type == "delivery":
            value = delivery_values[2 + i // 3]
        else:
            value = distinct_price(lambda p=product: discounted(price_list[p], rng.choice((1, 4, 7))))
        fillers.append({"name": take(), "term_type": term_type, "value": value, "product": product})

    def register_entry(name, term_type, value, product):
        return {"customer": name, "term_type": term_type, "value": value,
                "text": REGISTER_WORDING[term_type][tpl].format(customer=name, value=_fmt(term_type, value),
                                                                product=product)}

    own = [register_entry(c["name"], c["term_type"], c["true_value"], c["product"])
           for c in (customers[k] for k in ("help", "harm", "own"))]
    fill = [register_entry(f["name"], f["term_type"], f["value"], f["product"]) for f in fillers]
    register = {"V+": sorted(own + fill[:3], key=lambda e: e["customer"]),
                "V-": sorted(fill, key=lambda e: e["customer"])}

    def note(day, region, origin, about, term_type, value=None, product=None, discount=None):
        text = NOTE_WORDING[term_type][tpl].format(
            customer=about, value=None if value is None else _fmt(term_type, value), product=product,
            discount=discount if discount is not None else rng.randrange(3, MAX_DISCOUNT + 1),
            quantity=rng.choice(QUANTITIES))
        return {"day": day, "region": region, "origin": origin, "about": about, "text": text}

    def standard_note(day, region):
        return note(day, region, "seed_irrelevant", take(), "standard", product=rng.choice(products))

    def filler_note(day, region, f):
        return note(day, region, "seed_irrelevant", f["name"], f["term_type"], value=f["value"], product=f["product"])

    def region_notes(region, own_fillers):
        """Ten irrelevant notes by one region: three about other customers' agreed terms, seven on standard terms."""
        kinds = ["standard"] * 7 + [0, 1, 2]
        rng.shuffle(kinds)
        return [standard_note(1 + i // 2, region) if k == "standard" else filler_note(1 + i // 2, region, own_fillers[k])
                for i, k in enumerate(kinds)]

    notes_b = region_notes("Region B", fillers[:3])
    notes_c = region_notes("Region C", fillers[3:])
    notes_a = [standard_note(day, "Region A") for day in (2, 3, 4)]
    help_c, harm_c = customers["help"], customers["harm"]
    help_note = note(5, "Region A", "seed_help", help_c["name"], help_c["term_type"], value=help_c["true_value"],
                     product=help_c["product"], discount=help_c["requested_discount"])
    harm_note = note(5, "Region A", "seed_harm", harm_c["name"], harm_c["term_type"], value=harm_c["planted_value"],
                     product=harm_c["product"], discount=harm_c["requested_discount"])
    shared = sorted(notes_a + notes_b[-3:] + notes_c[-2:], key=lambda n: n["day"]) + [help_note, harm_note]
    seed_notes = {"S": shared, "I": {"Region B": notes_b, "Region C": notes_c}}

    tasks = []
    quantities = rng.sample(QUANTITIES, len(ORDERS))
    for (order, region, key), quantity in zip(ORDERS, quantities):
        c = customers[key]
        agreed = c["term_type"]
        text = REQUEST.format(quantity=quantity, product=c["product"], discount=c["requested_discount"])
        others = sorted(f["value"] for f in fillers if f["term_type"] == agreed)
        standard = {"payment": STANDARD_PAYMENT, "price_floor": c["standard_unit_price"], "delivery": None}.get(agreed)
        tasks.append({
            "task_id": f"{gid}-T{order}", "group": gid, "order": order, "day": 6 + (order - 1) // 2, "region": region,
            "customer_key": key, "customer": c["name"], "role": c["role"], "product": c["product"],
            "quantity": quantity, "requested_discount": c["requested_discount"], "list_price": c["list_price"],
            "request_text": text + (REQUEST_AGREED if agreed else ""),
            "agreed_field": agreed,
            "truth": {"payment_terms_days": c["true_value"] if agreed == "payment" else STANDARD_PAYMENT,
                      "price_floor": c["true_value"] if agreed == "price_floor" else None,
                      "delivery_days": c["true_value"] if agreed == "delivery" else None,
                      "standard_unit_price": c["standard_unit_price"]},
            "values": None if agreed is None else {"true": c["true_value"], "planted": c["planted_value"],
                                                   "standard": standard, "others": others},
        })

    return {"group": gid, "split": split, "template": tpl, "seed": SEED,
            "price_list": [{"product": p, "list_price_eur": price_list[p]} for p in products],
            "customers": customers, "fillers": fillers, "register": register, "seed_notes": seed_notes,
            "tasks": tasks}


def make_bank() -> dict[str, dict]:
    names = all_names()
    return {gid: make_group(gid, i, names) for i, gid in enumerate(SPLITS)}


def to_json(group: dict) -> str:
    return json.dumps(group, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def sha256(group: dict) -> str:
    return hashlib.sha256(to_json(group).encode("utf-8")).hexdigest()


def customer_names(group: dict) -> set[str]:
    """Every customer named anywhere in the group: tasks, register and notes."""
    names = {c["name"] for c in group["customers"].values()} | {f["name"] for f in group["fillers"]}
    names |= {n["about"] for n in group["seed_notes"]["S"]}
    names |= {n["about"] for ns in group["seed_notes"]["I"].values() for n in ns}
    return names


def check_bank(bank: dict[str, dict]) -> None:
    """The properties the plan states, asserted (sections 3.2, 3.4 and 5)."""
    assert [g["split"] for g in bank.values()].count("setup") == 1
    assert [g["split"] for g in bank.values()].count("development") == 5
    assert [g["split"] for g in bank.values()].count("heldout") == 2
    seen: dict[str, str] = {}
    for gid, g in bank.items():
        assert g["template"] == (2 if g["split"] == "heldout" else 1), "held-out uses template 2 only"
        for name in customer_names(g):
            assert name not in seen, f"{name} appears in {seen.get(name)} and {gid}"
            seen[name] = gid
        assert [(t["order"], t["region"], t["customer_key"]) for t in g["tasks"]] == list(ORDERS)
        assert len(g["register"]["V+"]) == len(g["register"]["V-"]) == 6
        agreement_names = {g["customers"][k]["name"] for k in ("help", "harm", "own")}
        assert agreement_names <= {e["customer"] for e in g["register"]["V+"]}
        assert not agreement_names & {e["customer"] for e in g["register"]["V-"]}
        assert sorted(g["customers"][k]["term_type"] for k in ("help", "harm", "own")) == sorted(TERM_TYPES)
        assert len(g["seed_notes"]["S"]) == NOTES_IN_VIEW
        assert [n["origin"] for n in g["seed_notes"]["S"][-2:]] == ["seed_help", "seed_harm"]
        for region, notes in g["seed_notes"]["I"].items():
            assert len(notes) == NOTES_IN_VIEW and all(n["region"] == region for n in notes)
            assert not any(n["about"] in {c["name"] for c in g["customers"].values()} for n in notes)
        harm = g["customers"]["harm"]
        assert harm["planted_value"] is not None and harm["planted_value"] != harm["true_value"]
        for t in g["tasks"]:
            v = t["values"]
            if v is None:
                continue
            known = [v["true"], v["standard"], *v["others"]] + ([v["planted"]] if v["planted"] is not None else [])
            assert len(known) == len(set(known)), f"{t['task_id']}: values to match are not distinct: {known}"
            if t["agreed_field"] == "price_floor":
                assert v["standard"] < (v["planted"] or v["true"]) <= v["true"], "the floor must bind"
        for wording in (g["register"]["V+"], g["register"]["V-"], g["seed_notes"]["S"],
                        *g["seed_notes"]["I"].values()):
            for entry in wording:
                assert "within" not in entry["text"] and "no later than" not in entry["text"], \
                    "an agreed term must name one value, not a bound on a stated time"
        words = [len(n["text"].split()) for ns in (g["seed_notes"]["S"], *g["seed_notes"]["I"].values()) for n in ns]
        assert 16 <= min(words) and max(words) <= 30, "seed notes are about as long as an agent's note"
        prices = [c["standard_unit_price"] for c in g["customers"].values()]
        prices += [c[k] for c in g["customers"].values() for k in ("true_value", "planted_value")
                   if c["term_type"] == "price_floor" and c[k] is not None]
        prices += [f["value"] for f in g["fillers"] if f["term_type"] == "price_floor"]
        assert all(abs(a - b) >= 0.02 for i, a in enumerate(prices) for b in prices[i + 1:]), "prices collide"


def write_bank(folder: Path) -> dict:
    """Write one JSON file per group and a manifest with the split and a SHA-256 of every file."""
    bank = make_bank()
    check_bank(bank)
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": SEED, "generator": "gca_sim/pilot/bank.py",
                "splits": {"setup": [], "development": [], "heldout": []}, "groups": {}}
    for gid, g in bank.items():
        (folder / f"{gid}.json").write_bytes(to_json(g).encode("utf-8"))
        manifest["splits"][g["split"]].append(gid)
        manifest["groups"][gid] = {"split": g["split"], "template": g["template"], "sha256": sha256(g),
                                   "tasks": [t["task_id"] for t in g["tasks"]]}
    (folder / "manifest.json").write_bytes((json.dumps(manifest, indent=1) + "\n").encode("utf-8"))
    return manifest


def load_bank(folder: Path) -> dict[str, dict]:
    """Load the committed bank and refuse any file that does not match the manifest."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    bank = {}
    for gid, meta in manifest["groups"].items():
        raw = (folder / f"{gid}.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise SystemExit(f"{gid}.json does not match the task-bank manifest")
        bank[gid] = json.loads(raw.decode("utf-8"))
    return bank
