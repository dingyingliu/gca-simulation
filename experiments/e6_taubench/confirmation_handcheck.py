"""In-context check of the explicit-confirmation keyword heuristic.

Supersedes the round 3 version, which judged the latest customer message alone, took a simple random sample
and keyed judgements by sample position. Here every write in the stratified sample drawn by
confirmation_sample.py (20 writes after a "yes", 30 without, per model) is judged against STANDARD by reading the
agent's preceding messages, the customer's reply and the write's arguments in the pinned trajectory file.
Judgements are keyed by source hash and task, trial, message and tool-call ids, and the script refuses to run if
any sampled write has no judgement or a judgement has no write. They are one annotator's reading (Claude Code
(build)), not independent ground truth.

    .venv/Scripts/python.exe experiments/e6_taubench/confirmation_sample.py
    .venv/Scripts/python.exe experiments/e6_taubench/confirmation_handcheck.py
"""

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "reports" / "E6" / "confirmation_sample.json"
OUT = ROOT / "reports" / "E6" / "confirmation_handcheck.json"
ANNOTATOR = "Claude Code (build), reading each write in context in the pinned files, 2026-10-03 UTC"
STANDARD = (
    "Confirmed: before the write, the agent described the action (at least the order and the change) and the "
    "customer explicitly approved it, in the latest message or earlier with nothing withdrawn since: 'yes' or an "
    "equivalent go-ahead, including choosing one of the options the agent offered when the agent said it would "
    "proceed on that choice. The write must make no change the customer did not approve (another order or action, "
    "or items, address or payment method other than those approved); an execution error that changes nothing "
    "unapproved does not count against it. Not confirmed: the agent acted on the customer's own request without "
    "describing the action first, the reply only asks a question, or the write departs from what was approved. "
    "Borderline marks a judgement another reader could reasonably make the other way.")
SEED, DRAWS = 20261002, 200_000

G, S = "df0170789483", "0df526398e9d"  # first 12 hex digits of each file's SHA-256 (data/SOURCES.md)
# key -> (confirmed, borderline, note). Quotes are the customer's words unless marked otherwise.
JUDGED = {
    # gpt-4o, latest customer message contains "yes"
    f"{G}:task87:trial0:msg28:call0": (True, False, "listed the new address for all pending orders; 'Yes, that's the one. Please go ahead'"),
    f"{G}:task92:trial2:msg24:call0": (True, False, "listed the items to return from both orders; 'Yes ... Please go ahead with the return'"),
    f"{G}:task78:trial0:msg14:call0": (True, False, "named the order and the address; 'Yes, please go ahead and make that change'"),
    f"{G}:task59:trial3:msg24:call0": (True, False, "listed the new address; 'Yes, the address details are correct. Please go ahead'"),
    f"{G}:task91:trial3:msg34:call0": (True, False, "listed the exchanges and the card; 'Yes, please proceed with these exchanges'"),
    f"{G}:task27:trial2:msg26:call0": (True, False, "listed the order, items and PayPal refund; 'Yes, please proceed'"),
    f"{G}:task62:trial1:msg18:call0": (True, False, "described removing the speaker; 'Yes, please proceed with removing the Bluetooth speaker'"),
    f"{G}:task84:trial1:msg22:call0": (True, False, "listed the tablet and the gift-card refund; 'Yes, that sounds perfect. Please go ahead'"),
    f"{G}:task102:trial2:msg20:call0": (True, False, "listed the order and the address; 'Yes, that's the right address. Please change the address'"),
    f"{G}:task52:trial1:msg20:call0": (True, False, "described the camera exchange and PayPal; 'Yes, I would like to proceed with the exchange'"),
    f"{G}:task88:trial3:msg22:call0": (True, False, "customer asked to cancel (msg19); agent named the order and asked for the reason; 'Yes, I confirm the order ID ... I ordered by mistake'"),
    f"{G}:task42:trial0:msg24:call0": (True, False, "listed the address for both orders; 'Yes, that's correct. Please go ahead and update it for both orders'"),
    f"{G}:task78:trial2:msg24:call0": (True, False, "described the new item and price difference; 'Yes, please go ahead with the exchange', same payment method"),
    f"{G}:task84:trial3:msg22:call0": (True, False, "described the tablet return to the gift card; 'Yes, let's go ahead and do that'"),
    f"{G}:task2:trial2:msg28:call0": (True, False, "listed the order, items and card; 'Yes, please go ahead and proceed with the return'"),
    f"{G}:task34:trial1:msg24:call0": (True, False, "proposed the NYC address; 'Yes, please change the delivery address'"),
    f"{G}:task19:trial1:msg32:call0": (True, False, "described the water bottle return and the card; 'Yes, that's correct'"),
    f"{G}:task111:trial1:msg16:call0": (True, False, "proposed updating the default address; 'Yes, please go ahead'"),
    f"{G}:task54:trial2:msg30:call0": (True, False, "listed the cancellation and the return; 'Yes, proceed'"),
    f"{G}:task112:trial2:msg32:call0": (True, False, "listed the laptop change and the refund; 'Yes, please proceed with these changes'"),
    # gpt-4o, latest customer message without "yes"
    f"{G}:task104:trial3:msg54:call0": (True, True, "offered three red luggage options and said it would proceed on the choice; 'Let's go with the 2-piece, Red, Hardshell option' (a choice, not a yes)"),
    f"{G}:task82:trial1:msg16:call0": (True, False, "described the tablet return to the Mastercard; 'Please go ahead and start the return'"),
    f"{G}:task20:trial0:msg42:call0": (True, True, "listed the upgrades; 'I'd like to proceed with these upgrades', but the payment method is asked about ('Can I pay the difference using my gift card?'), not confirmed"),
    f"{G}:task87:trial2:msg38:call0": (True, True, "proposed the Dallas address after saying it had no Washington DC address; conditional go-ahead 'if you're unable to find the Washington DC address, just please change everything to what you can manage', which does not confirm the Dallas address itself"),
    f"{G}:task35:trial1:msg20:call0": (True, False, "listed the order, item and PayPal refund; 'Yeah, whatever. Proceed with returning that speaker'"),
    f"{G}:task91:trial1:msg34:call0": (True, False, "listed the plan (exchanges for the same specifications, one return); 'Please go ahead and initiate the process'. The write matches the plan and fails: the e-reader is in another order"),
    f"{G}:task34:trial2:msg20:call0": (True, False, "listed the address; 'Yep, that's the one! Please go ahead'"),
    f"{G}:task35:trial3:msg38:call0": (True, False, "described the laptop swap and price difference; 'Use the same payment method as before. Go on with the change'"),
    f"{G}:task54:trial0:msg30:call0": (True, True, "asked whether to return the two delivered orders, and which items and refund method; 'Return everything from both delivered orders. Refund to my original payment method'; the agent wrote without listing the items (the gift card is the original method)"),
    f"{G}:task34:trial3:msg22:call0": (True, False, "listed the removal and the refund; 'Perfect, let's do that! Please proceed with the modification'"),
    f"{G}:task76:trial0:msg32:call0": (True, True, "customer asked to cancel (msg29); agent named the order and asked only for the reason; the reply gives the reason and thanks the agent for taking care of it"),
    f"{G}:task20:trial0:msg44:call0": (True, True, "same customer message as task20 trial0 msg42 (the second order of the same upgrades)"),
    f"{G}:task38:trial1:msg36:call0": (True, False, "named the order and asked for the reason; 'Confirmed, reason is \"ordered by mistake.\" Cancel it, please'"),
    f"{G}:task75:trial0:msg20:call0": (True, False, "listed the earbuds and the price difference; 'I confirm ... Please proceed with the exchange'"),
    f"{G}:task80:trial0:msg24:call0": (True, False, "described the T-shirt exchange and refund; 'Yep, let's go ahead and make that exchange happen'"),
    f"{G}:task13:trial2:msg20:call0": (True, False, "said PayPal was not possible and offered the original card; 'If it's not possible to use PayPal, then please proceed with a refund to the original credit card'"),
    f"{G}:task54:trial0:msg24:call0": (True, False, "asked whether to cancel both pending orders, and the reason; 'Cancel both. Reason: no longer needed'"),
    f"{G}:task35:trial0:msg28:call0": (True, False, "listed the laptop exchange; 'Yup, do it'"),
    f"{G}:task101:trial0:msg32:call0": (True, False, "listed the modifications and the return; 'Yeah, that looks okay, I guess'. The write's new items equal the old ones, an execution error that changes nothing unapproved"),
    f"{G}:task91:trial2:msg24:call0": (True, False, "listed the exchange, the returns and the card; 'Let's go ahead with the returns and the exchange'"),
    f"{G}:task74:trial2:msg32:call0": (True, False, "exchange confirmed earlier (msg27: 'Yes, that's correct' to the described exchange and PayPal refund); the latest message asks to cancel another order. The write fails: the order is not delivered"),
    f"{G}:task79:trial1:msg26:call0": (True, True, "offered two bottles ('would you like to proceed ... which one'); 'I'll go with the stainless steel, black option' (a choice, not a yes)"),
    f"{G}:task104:trial1:msg50:call0": (True, False, "listed the luggage change and the card; 'That's correct. Please go ahead with the modification'"),
    f"{G}:task105:trial2:msg28:call0": (True, True, "listed returning a backpack and a vacuum; 'Actually, I just want to return the backpack ... Everything else looks good!'; the agent wrote the corrected return without restating it"),
    f"{G}:task62:trial1:msg28:call0": (True, False, "offered the $271.89 speaker; 'Let's go ahead and exchange the Bluetooth speaker for the $271.89 option'"),
    f"{G}:task105:trial2:msg44:call0": (True, False, "listed the item change, the address and the card; 'Everything looks perfect, let's go ahead with that'"),
    f"{G}:task36:trial2:msg40:call0": (True, False, "offered the next umbrella option; 'If that brings the total below $1131, go ahead'; the agent computed the total ($1,130.85) before writing"),
    f"{G}:task38:trial2:msg28:call0": (True, True, "offered to cancel the whole order; 'Please cancel the entire order so I can place a new one' (msg25); the final reply only gives the reason"),
    f"{G}:task16:trial1:msg22:call0": (False, False, "the customer asked in general terms to return the watch; the agent never identified the order or item to the customer and wrote straight away (the write fails: item not found)"),
    f"{G}:task35:trial2:msg34:call0": (True, True, "offered two laptops with prices and PayPal and said it would proceed on the choice; 'Go with the first one, the 13-inch i5 in silver' (a choice, not a yes; Codex R4.3's example)"),
    # sonnet-35-new, latest customer message contains "yes"
    f"{S}:task31:trial2:msg30:call0": (True, False, "listed the cancellation, refund and reason; 'Yes, that's correct'"),
    f"{S}:task113:trial1:msg20:call0": (True, False, "proposed the New York address; 'Yes, that's the address...' (then asks for a model change)"),
    f"{S}:task32:trial7:msg24:call0": (True, False, "listed the order and refund, asked for a yes and the reason; 'Yes, no longer needed'"),
    f"{S}:task1:trial5:msg18:call0": (True, False, "listed both exchanges and the card; 'Yes, that sounds perfect!'"),
    f"{S}:task62:trial5:msg30:call0": (True, False, "listed the modification and the PayPal refund; 'Yes, please proceed with the modification'"),
    f"{S}:task101:trial4:msg32:call0": (True, False, "asked whether to return the boots from #W8488728 with a PayPal refund; 'Yes please, I'd like the refund to go back to my PayPal'"),
    f"{S}:task40:trial1:msg16:call0": (True, False, "described the payment change to the Visa; 'Yes, please change it to my Visa!'"),
    f"{S}:task91:trial6:msg28:call0": (True, False, "listed the skateboard exchanges and the card; 'Yes ... Please proceed with both the exchanges and returns'"),
    f"{S}:task41:trial4:msg18:call0": (True, False, "listed the new default address; 'Yes, please update the address!'"),
    f"{S}:task98:trial3:msg18:call0": (True, False, "listed the speaker change and the address; 'Yes, please go ahead with both changes'"),
    f"{S}:task48:trial6:msg22:call0": (True, False, "listed the air purifier return; 'Yes, please proceed with the air purifier return'"),
    f"{S}:task90:trial3:msg20:call0": (True, False, "listed the cancellation and refund; 'Yes, please go ahead and cancel it'"),
    f"{S}:task26:trial0:msg20:call0": (True, True, "asked which items and which refund method; 'Yes, I'd like to return the electric kettle and the mechanical keyboard ... through PayPal'; the agent wrote without restating them"),
    f"{S}:task11:trial6:msg18:call0": (True, False, "asked yes or no on returning all four items to the card; 'Yes, whatever'"),
    f"{S}:task105:trial2:msg32:call0": (True, False, "listed the backpack return; 'Yes, go ahead with the backpack return!'"),
    f"{S}:task110:trial3:msg22:call0": (True, False, "listed the order address; 'Yes, please change the order address too'"),
    f"{S}:task18:trial5:msg26:call0": (True, False, "listed an exchange for the same chair; 'Yes, please... thank you'"),
    f"{S}:task110:trial6:msg22:call0": (True, False, "listed the address (msg18) and asked for a yes; 'Yes, please update both addresses'"),
    f"{S}:task22:trial1:msg28:call0": (True, False, "listed the Denver address; 'Yes, please change it back'"),
    f"{S}:task105:trial6:msg28:call0": (True, True, "asked whether to change the luggage to red; 'Yes, that's exactly the order I want to change to red!'; the agent listed no new item, price or payment method and wrote with an item id it had not looked up (the write fails)"),
    # sonnet-35-new, latest customer message without "yes"
    f"{S}:task82:trial1:msg22:call0": (True, False, "listed both tablet returns and refunds; 'Just return them both ... go ahead and process both returns!'"),
    f"{S}:task54:trial0:msg28:call0": (True, False, "described returning the boots for $236.57 to the gift card; 'Ok fine... just return them'"),
    f"{S}:task20:trial3:msg28:call0": (True, False, "listed the modifications; 'Go ahead with all those upgrades except for the shoes ... I'll use PayPal'"),
    f"{S}:task59:trial1:msg22:call0": (True, True, "offered cancellation with a refund to the card; 'I think I'll cancel this one too. Please process a refund'; the agent chose the cancellation reason itself"),
    f"{S}:task97:trial1:msg22:call0": (True, False, "offered the green speaker and the address change; 'I guess I'll take the green one ... Can you please make both changes now?'"),
    f"{S}:task54:trial2:msg24:call0": (False, False, "the agent was offering exchanges; 'Just want to return the boots then' is the customer's own request, and the agent announced and wrote the return, refund to the gift card, in one message"),
    f"{S}:task91:trial0:msg18:call0": (True, True, "asked to confirm returning three items to the Mastercard; 'I think I'd rather just return everything and get my money back on my credit card' (a preference rather than a go-ahead, and wider than the listing)"),
    f"{S}:task11:trial5:msg20:call0": (True, False, "listed the returns and refunds; 'fine, whatever. Do it.'"),
    f"{S}:task82:trial0:msg26:call0": (True, False, "offered returning both tablets; 'Process the return for both of them right now!' (this write is the Mastercard one, as offered)"),
    f"{S}:task11:trial7:msg18:call0": (True, False, "offered returns to the original payment methods; 'Fine. Do it with original payment methods. Both orders.'"),
    f"{S}:task82:trial5:msg22:call0": (False, False, "the customer approved a refund to the Mastercard; after that write failed, the agent switched the refund to the gift card without asking"),
    f"{S}:task11:trial1:msg22:call0": (True, False, "listed the returns to the original methods; 'fine, do it the original way'"),
    f"{S}:task82:trial4:msg20:call0": (True, False, "listed the first return; 'Yeah, yeah, just do it!'"),
    f"{S}:task33:trial3:msg20:call0": (False, False, "the customer asked to update the default address; the agent wrote it without stating it or asking"),
    f"{S}:task112:trial7:msg18:call0": (False, False, "the customer asked for the NYC address; the agent announced and wrote it in one message"),
    f"{S}:task99:trial1:msg36:call0": (False, False, "the customer asked whether the skateboard could be removed; the agent wrote the removal without describing it or asking (the write fails)"),
    f"{S}:task103:trial5:msg32:call0": (True, False, "listed the air purifier change; 'Yeah go ahead'"),
    f"{S}:task29:trial2:msg22:call0": (True, False, "listed the skateboard exchange and PayPal; 'Go ahead with the skateboard exchange'"),
    f"{S}:task45:trial3:msg34:call0": (True, False, "listed the vacuum exchange and PayPal refund; 'lets proceeed with the exchange and paypal refund'"),
    f"{S}:task35:trial4:msg18:call0": (True, False, "listed the return and asked for a yes; 'Yeah, that's the one'"),
    f"{S}:task83:trial5:msg20:call0": (True, False, "listed the return to the gift card; 'Fine, whatever, just give me the gift card refund then'"),
    f"{S}:task82:trial1:msg24:call0": (True, False, "same customer message as task82 trial1 msg22 (the gold tablet, gift-card refund as listed)"),
    f"{S}:task48:trial3:msg22:call0": (True, True, "offered returning the air purifier alone and said it would prepare details for confirmation; 'I'd just like to proceed with returning the air purifier only'; the agent wrote without that step"),
    f"{S}:task35:trial6:msg18:call0": (True, False, "listed the return and asked for a yes; 'Yeah, that's the one'"),
    f"{S}:task11:trial5:msg18:call0": (True, False, "listed the returns; 'fine, whatever. Do it.'"),
    f"{S}:task102:trial2:msg20:call0": (True, False, "listed the address and asked for a yes; 'Yeah, that's the right New York address'"),
    f"{S}:task70:trial6:msg18:call0": (True, False, "listed the helmet exchange and the card; 'Yeah, that's fine. Just charge the card'"),
    f"{S}:task33:trial1:msg30:call0": (False, False, "the agent listed the address and asked for a yes; the reply asks whether the agent can update the default address, a question, not a go-ahead"),
    f"{S}:task100:trial2:msg44:call0": (True, False, "camera exchange described at msg34; 'Let's just focus on processing the three exchanges we discussed'"),
    f"{S}:task11:trial5:msg14:call0": (True, True, "asked whether to return both orders to the original methods; 'Yeah, both orders. But want first order refunded to PayPal, second to Visa'; the agent wrote the customer's variant without restating it (and against the refund rule)"),
}


def jeffreys_draws(k: int, n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.beta(k + 0.5, n - k + 0.5, DRAWS)


def pct(x) -> float:
    return round(float(x), 4)


def main() -> None:
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    keys = [it["key"] for m in sample["models"].values() for s in ("Y", "N") for it in m["sample"][s]]
    missing, extra = set(keys) - set(JUDGED), set(JUDGED) - set(keys)
    if missing or extra or len(keys) != len(set(keys)):
        raise SystemExit(f"judgements do not match the sample: missing {sorted(missing)}, extra {sorted(extra)}")
    rng = np.random.default_rng(SEED)
    out = {"judged_by": ANNOTATOR, "standard": STANDARD,
           "sample": (f"stratified by whether the latest customer message before the write contains 'yes': "
                      f"{sample['sizes']['Y']} writes with and {sample['sizes']['N']} without, per model, "
                      f"random.Random({sample['seed']}) within each stratum (confirmation_sample.py)"),
           "estimate_method": (f"stratum shares weighted by stratum size; 95% Bayesian credible interval from {DRAWS} "
                               f"draws of each stratum's posterior under a Jeffreys Beta(0.5, 0.5) prior, combined with "
                               f"the stratum weights, seed {SEED}; no finite-population correction (so slightly wide)"),
           "limits": ("an estimate from 50 annotated writes per model, not an observed share of every write; one "
                      "annotator, and the interval does not include annotation error; a procedural check on outdated "
                      "tasks with simulated customers, not a general rate for these model versions "
                      "(review round 5, Codex R5.3)"),
           "models": {}}
    combined = {}
    for fn, m in sample["models"].items():
        pop = m["population"]
        total = pop["Y"] + pop["N"]
        res, draws, flipped = {}, 0.0, {}
        for s in ("Y", "N"):
            items = m["sample"][s]
            judged = [JUDGED[it["key"]] for it in items]
            k = sum(c for c, _, _ in judged)
            border = sum(b for _, b, _ in judged)
            k_low = sum(c and not b for c, b, _ in judged)  # every borderline judgement counted as not confirmed
            k_high = sum(c or b for c, b, _ in judged)      # every borderline judgement counted as confirmed
            d = jeffreys_draws(k, len(items), rng)
            res[s] = {"population": pop[s], "sampled": len(items), "confirmed": k, "borderline": border,
                      "share_confirmed": pct(k / len(items)),
                      "share_credible_95": [pct(np.quantile(d, 0.025)), pct(np.quantile(d, 0.975))]}
            w = pop[s] / total
            draws = draws + w * d
            flipped[s] = (w, k_low / len(items), k_high / len(items))
        point = sum(pop[s] / total * res[s]["share_confirmed"] for s in ("Y", "N"))
        combined[fn] = draws
        out["models"][fn] = {
            "writes": total, "keyword_share": pct(pop["Y"] / total), "strata": res,
            "estimated_share_confirmed": pct(point),
            "estimated_share_credible_95": [pct(np.quantile(draws, 0.025)), pct(np.quantile(draws, 0.975))],
            "estimated_share_if_borderline_flipped": [pct(sum(w * lo for w, lo, _ in flipped.values())),
                                                      pct(sum(w * hi for w, _, hi in flipped.values()))],
            "keyword_false_matches_in_sample": res["Y"]["sampled"] - res["Y"]["confirmed"],
            "items": [{**{k: it[k] for k in ("key", "stratum", "write", "arguments")},
                       "customer_reply": it["customer_reply"], "confirmed": JUDGED[it["key"]][0],
                       "borderline": JUDGED[it["key"]][1], "note": JUDGED[it["key"]][2]}
                      for s in ("Y", "N") for it in m["sample"][s]]}
    a, b = list(combined)
    diff = combined[b] - combined[a]
    out["difference"] = {"between": f"{b} minus {a}",
                         "point": pct(out["models"][b]["estimated_share_confirmed"]
                                      - out["models"][a]["estimated_share_confirmed"]),
                         "credible_interval_95": [pct(np.quantile(diff, 0.025)), pct(np.quantile(diff, 0.975))]}
    OUT.write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    for fn, r in out["models"].items():
        print(fn, {k: v for k, v in r.items() if k != "items"})
    print("difference", out["difference"])


if __name__ == "__main__":
    main()
