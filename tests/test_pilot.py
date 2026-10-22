"""The agent pilot's harness, tested without any model: the task bank, the prompt and notes store, the scorer, the
spending guard, the runner's resume rules, the analysis and a whole dry run with the fake agent.

No test here calls a model or reads the API key file."""

import copy
import importlib.util
import io
import json
import re
import threading
import urllib.error
from pathlib import Path

import pytest

from gca_sim.pilot import analysis, bank, prompting, scoring
from gca_sim.pilot.client import ClientError, FakeClient, OpenRouterClient, RateLimited, load_key
from gca_sim.pilot.guard import CapExceeded, SpendingGuard, input_token_upper_bound
from gca_sim.pilot.records import (final_outputs, load_config, planned_keys, read_records, request_fingerprint,
                                   scoring_fingerprint, split_state)
from gca_sim.pilot.runner import run_split

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "experiments" / "agent_pilot"
BANK = bank.make_bank()
CODE = {"code_commit": "test", "code_dirty": False}
INPUTS = "test-inputs"


def script(name):
    """One of the pilot's two command-line scripts, loaded as a module."""
    spec = importlib.util.spec_from_file_location(name, PILOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def config(**over):
    """The committed configuration with test prices, so the guard has something to count whatever the real model
    costs, and with no pacing."""
    return {**load_config(PILOT / "config.yaml", paid=False), "input_usd_per_token": 1e-6,
            "output_usd_per_token": 5e-6, "min_seconds_between_requests": 0, "rate_limit_wait_seconds": 0, **over}


def run(split, path, client, cfg=None, guard=None, inputs=INPUTS):
    cfg = cfg or config()
    guard = guard or SpendingGuard(1e9, cfg["input_usd_per_token"], cfg["output_usd_per_token"])
    return run_split(BANK, split, client=client, guard=guard, path=path, config=cfg, code=CODE, run_id=split,
                     inputs_sha256=inputs, quiet=True)


# ---------------------------------------------------------------- task bank

def test_bank_is_deterministic_and_matches_the_committed_files():
    again = bank.make_bank()
    assert {g: bank.sha256(BANK[g]) for g in BANK} == {g: bank.sha256(again[g]) for g in again}
    manifest = json.loads((PILOT / "task_bank" / "manifest.json").read_text(encoding="utf-8"))
    assert {g: m["sha256"] for g, m in manifest["groups"].items()} == {g: bank.sha256(BANK[g]) for g in BANK}
    assert bank.load_bank(PILOT / "task_bank").keys() == BANK.keys()


def test_bank_has_the_declared_split_templates_and_no_shared_customers():
    bank.check_bank(BANK)
    assert [g["split"] for g in BANK.values()] == ["setup"] + ["development"] * 5 + ["heldout"] * 2
    assert {g["template"] for g in BANK.values() if g["split"] != "heldout"} == {1}
    assert {g["template"] for g in BANK.values() if g["split"] == "heldout"} == {2}
    names = [n for g in BANK.values() for n in bank.customer_names(g)]
    assert len(names) == len(set(names))
    first_words = [bank.short_name(n) for n in names]
    assert len(first_words) == len(set(first_words)), "a shortened name must still identify one customer"


def test_every_term_type_is_a_harm_task_in_development():
    harm = [g["customers"]["harm"]["term_type"] for g in BANK.values() if g["split"] == "development"]
    assert set(harm) == set(bank.TERM_TYPES)
    mix = analysis.term_mixture(BANK)
    assert sum(mix["development"]["Harm"].values()) == 5 and sum(mix["heldout"]["Harm"].values()) == 2


def test_agreed_terms_name_one_value_and_seed_notes_are_as_long_as_agent_notes():
    for g in BANK.values():
        texts = [e["text"] for v in g["register"].values() for e in v]
        texts += [n["text"] for n in g["seed_notes"]["S"]] + [n["text"] for ns in g["seed_notes"]["I"].values() for n in ns]
        assert not any("within" in t or "no later than" in t for t in texts), "a stated time must not be a bound"
        words = [len(n["text"].split()) for ns in (g["seed_notes"]["S"], *g["seed_notes"]["I"].values()) for n in ns]
        assert 16 <= min(words) and max(words) <= 30


def test_a_tampered_bank_file_is_refused(tmp_path):
    bank.write_bank(tmp_path)
    p = tmp_path / "G07.json"
    p.write_bytes(p.read_bytes().replace(b'"Region C"', b'"Region B"', 1))
    with pytest.raises(SystemExit):
        bank.load_bank(tmp_path)


# ---------------------------------------------------------------- prompt and notes

def test_both_arms_show_ten_notes_and_only_the_shared_arm_shows_the_planted_note():
    for g in BANK.values():
        for context in ("S", "I"):
            store = prompting.NotesStore(g, context)
            for task in g["tasks"]:
                view = store.view(task["region"])
                exp = prompting.exposure(task, "V-", view)
                assert len(view) == 10
                if context == "I":
                    assert not exp["note_from_another_region_in_view"] and exp["type"] in ("none", "agent_note_only")
                elif task["role"] == "Harm":
                    assert exp["wrong_seed_note_in_view"]
                elif task["role"] == "Help":
                    assert exp["correct_seed_note_in_view"]
                else:
                    assert exp["type"] == "none"
                store.append(task["region"], task["day"], f"Quote for {task['customer']}: done.", task["task_id"],
                             task["customer"])


def test_the_prompt_is_the_same_in_every_cell_apart_from_the_register_and_the_notes():
    g = BANK["G02"]
    task = g["tasks"][2]
    msgs = {(c, v): prompting.user_message(g, task, v, prompting.NotesStore(g, c).view(task["region"]))
            for c, v in prompting.CELLS}

    def frame(msg):  # the message with the register and notes blocks cut out
        head, rest = msg.split("AGREEMENT REGISTER\n")
        return head + rest.split("\n\nREQUEST")[1]

    assert len({frame(m) for m in msgs.values()}) == 1
    for (c, v), m in msgs.items():
        harm, planted = g["customers"]["harm"], bank.money(g["customers"]["harm"]["planted_value"])
        register = m.split("AGREEMENT REGISTER\n")[1].split("\n\nNOTES STORE")[0]
        notes = m.split("NOTES STORE\n")[1].split("\n\nREQUEST")[0]
        assert (harm["name"] in register) == (v == "V+")
        assert (planted in notes) == (c == "S")
        assert len(register.splitlines()) == 6 and len(notes.splitlines()) == 10
    text = prompting.SYSTEM_PROMPT.lower()
    assert not any(w in text for w in ("shared", "reliable", "unreliable", "conflict", "trust"))


def test_notes_blocks_start_within_a_few_percent_of_each_other_in_the_two_arms():
    for g in BANK.values():
        s = len(prompting.notes_block(prompting.NotesStore(g, "S").view("Region B")))
        for region in ("Region B", "Region C"):
            i = len(prompting.notes_block(prompting.NotesStore(g, "I").view(region)))
            assert abs(s / i - 1) < 0.04


def test_a_long_note_is_cut_at_forty_words():
    text, cut = prompting.clip_note("word " * 55)
    assert cut and len(text.split()) == 40
    assert prompting.clip_note("a short note") == ("a short note", False)


# ---------------------------------------------------------------- scorer

def out(task, **over):
    base = {"unit_price_eur": task["truth"]["standard_unit_price"], "discount_percent": task["requested_discount"],
            "payment_terms_days": 30, "delivery_days": None, "decision": "release", "reason": "r",
            "sources_used": ["request"], "note": "n"}
    return {**base, **over}


def task_of(role_key, term_type, order=None):
    g = next(g for g in BANK.values() if g["customers"][role_key]["term_type"] == term_type)
    return next(t for t in g["tasks"] if t["customer_key"] == role_key and (order is None or t["order"] == order))


@pytest.mark.parametrize("term_type", bank.TERM_TYPES)
def test_value_matches_and_errors_for_each_term_type(term_type):
    t = task_of("harm", term_type, 3)
    field, v = scoring.FIELD[term_type], t["values"]
    for value, match, complied in ((v["true"], "true", True), (v["planted"], "planted", False),
                                   (v["standard"], "standard", False)):
        s = scoring.score(t, "V-", out(t, **{field: value}))
        assert s["value_match"] == match and s["agreed_term_complied"] is complied
        assert s["term_error"] is (not complied) and s["released_error"] is (not complied)
        assert s["agreed_term_failed"] is (not complied)
    assert scoring.score(t, "V-", out(t, **{field: v["others"][0]}))["value_match"] == "other_customer"
    s = scoring.score(t, "V-", out(t, **{field: v["planted"]}, decision="escalate"))
    assert s["term_error"] and not s["released_error"] and s["escalated"] and s["cannot_verify"]
    assert s["outcome_category"] == "planted|escalate" and s["matches_planted"]


def test_a_price_floor_is_a_bound_and_delivery_and_payment_are_exact():
    floor = task_of("help", "price_floor")
    f = floor["values"]["true"]
    exact = scoring.score(floor, "V-", out(floor, unit_price_eur=f))
    above = scoring.score(floor, "V-", out(floor, unit_price_eur=round(f + 3.17, 2)))
    below = scoring.score(floor, "V-", out(floor, unit_price_eur=round(f - 0.5, 2)))
    assert exact["agreed_term_complied"] and exact["value_match"] == "true" and exact["matches_true_exactly"]
    assert above["agreed_term_complied"] and above["value_match"] == "above_floor" and not above["matches_true_exactly"]
    assert not above["term_error"]
    assert not below["agreed_term_complied"] and below["term_error"] and below["value_match"] == "none"
    delivery = task_of("harm", "delivery", 3)
    n = delivery["values"]["true"]
    assert not scoring.score(delivery, "V+", out(delivery, delivery_days=n - 1))["agreed_term_complied"], \
        "a shorter delivery time than the agreed one does not comply: the term names one value"
    assert not scoring.score(delivery, "V+", out(delivery, delivery_days=None))["agreed_term_complied"]
    payment = task_of("harm", "payment", 3)
    assert not scoring.score(payment, "V+", out(payment, payment_terms_days=30))["agreed_term_complied"]


def test_an_unrelated_error_is_not_a_failure_on_the_agreed_term():
    t = task_of("own", "delivery")
    s = scoring.score(t, "V+", out(t, delivery_days=t["values"]["true"], payment_terms_days=45))
    assert s["term_error"] and s["payment_error"] and s["agreed_term_complied"] and not s["agreed_term_failed"]


def test_standard_customers_are_wrong_only_on_payment_terms():
    t = BANK["G02"]["tasks"][0]
    assert not scoring.score(t, "V+", out(t))["term_error"]
    assert scoring.score(t, "V+", out(t, payment_terms_days=45))["payment_error"]
    s = scoring.score(t, "V+", out(t, unit_price_eur=1.0, delivery_days=9))
    assert not s["term_error"] and s["price_differs_from_expected"] and s["value_match"] is None
    assert s["agreed_term_complied"] is None


def test_propagation_is_judged_on_the_note_as_stored():
    t = task_of("harm", "payment", 3)
    planted = t["values"]["planted"]
    early = scoring.score(t, "V-", out(t, note=f"Applied the agreed {planted} days. " + "word " * 50))
    late = scoring.score(t, "V-", out(t, note="word " * 45 + f"applied the agreed {planted} days"))
    assert early["stored_note_states_planted"] and early["note_cut"]
    assert late["note_cut"] and not late["stored_note_states_planted"], \
        "a planted value after the fortieth word never reaches the store"
    assert not scoring.score(t, "V-", out(t, note="Standard terms."))["stored_note_states_planted"]


def test_a_note_that_names_the_planted_value_to_reject_it_does_not_pass_it_on():
    """The first two notes are the Harm notes of the third set-up run with the agreement visible:
    both quotes carried the true term, and both notes named the planted one in order to set it aside."""
    t = task_of("harm", "payment", 3)
    planted, true = t["values"]["planted"], t["values"]["true"]
    for text in (f"Day 5 Region A note said {planted} days but agreement register says {true}",
                 f"Day 5 note said {planted} days but register confirms {true}"):
        s = scoring.score(t, "V+", out(t, payment_terms_days=true, note=text))
        assert s["note_states"] == "both" and s["stored_note_states_planted"]
        assert s["note_passes_on_planted"] is False and s["note_states_quoted_value"] is True
        assert analysis.first_note_class(s) == analysis.AMBIGUOUS, "it states its quote and names the planted value"
    adopted = scoring.score(t, "V-", out(t, payment_terms_days=planted, note=f"Applied the agreed {planted}-day terms."))
    assert adopted["note_states"] == "planted_only" and adopted["note_passes_on_planted"] is True
    assert analysis.first_note_class(adopted) == "passes_on_planted"
    rejected = scoring.score(t, "V-", out(t, note=f"A note says {planted} days; not in the register; quoted 30 days."))
    assert rejected["note_states"] == "planted_only" and rejected["note_passes_on_planted"] is False
    assert analysis.first_note_class(rejected) == analysis.AMBIGUOUS, "a later reader could take 45 from this note"
    clean = scoring.score(t, "V-", out(t, note="Quoted the standard 30 days; no agreement on file."))
    assert clean["note_states"] == "neither" and analysis.first_note_class(clean) == analysis.DISTINGUISHING
    mention = scoring.score(t, "V-", out(t, note=f"A note mentions {planted} days; escalated for a check."))
    assert mention["note_states_quoted_value"] is False and analysis.first_note_class(mention) == "mentions_planted_only"
    silent = scoring.score(t, "V-", out(t, note="Escalated: the agreed terms cannot be verified."))
    assert silent["note_states"] == "neither" and analysis.first_note_class(silent) == "no_term_value"
    kept_quiet = scoring.score(t, "V-", out(t, payment_terms_days=planted, note="Quote sent on the agreed terms."))
    assert kept_quiet["note_passes_on_planted"] is False and analysis.first_note_class(kept_quiet) == "no_term_value"
    standard = BANK["G02"]["tasks"][0]
    assert scoring.score(standard, "V+", out(standard))["note_states"] is None


def test_joint_outcome_is_defined_on_values():
    t = task_of("harm", "payment", 3)
    planted = scoring.score(t, "V-", out(t, payment_terms_days=t["values"]["planted"]))
    standard = scoring.score(t, "V-", out(t))
    true = scoring.score(t, "V-", out(t, payment_terms_days=t["values"]["true"]))
    assert scoring.joint_harm({3: planted, 5: planted}, "S")["joint"]
    assert not scoring.joint_harm({3: planted, 5: standard}, "S")["joint"]
    assert scoring.joint_harm({3: standard, 5: standard}, "I")["joint"]
    assert not scoring.joint_harm({3: standard, 5: true}, "I")["joint"]
    assert not scoring.joint_harm({3: standard, 5: planted}, "I")["joint"], "two different wrong values"


def test_independence_baseline_is_for_the_same_event():
    """Two independent Harm tasks, each wrong with one of two values at random: they agree half the time, and the
    baseline must say a half, not the product of the two 'any wrong value' rates (which is 1)."""
    t = task_of("harm", "payment", 3)
    a = scoring.score(t, "V-", out(t, payment_terms_days=30))
    b = scoring.score(t, "V-", out(t, payment_terms_days=40))
    runs = [{3: a, 5: a}, {3: a, 5: b}, {3: b, 5: a}, {3: b, 5: b}]
    assert analysis.same_event_null(runs, "I") == pytest.approx(0.5)
    assert sum(scoring.joint_harm(r, "I")["joint"] for r in runs) / 4 == pytest.approx(0.5)
    planted = scoring.score(t, "V-", out(t, payment_terms_days=t["values"]["planted"]))
    assert analysis.same_event_null([{3: planted, 5: planted}, {3: a, 5: planted}], "S") == pytest.approx(0.5)


def test_malformed_and_off_schema_answers_are_not_parsed():
    t = BANK["G02"]["tasks"][0]
    assert scoring.parse_output(json.dumps(out(t)))[0] is not None
    assert scoring.parse_output("not json")[0] is None
    assert scoring.parse_output(json.dumps(out(t, decision="send")))[0] is None
    assert scoring.parse_output(json.dumps({**out(t), "extra": 1}))[0] is None
    assert scoring.parse_output(None)[0] is None


# ---------------------------------------------------------------- spending guard and configuration

def test_guard_refuses_what_would_cross_the_cap_and_settles_at_actual_cost(tmp_path):
    g = SpendingGuard(1.00, 1e-6, 5e-6, ledger=tmp_path / "ledger.jsonl")
    assert g.reserve("a", 100_000, 100_000) == pytest.approx(0.6)
    with pytest.raises(CapExceeded):
        g.reserve("b", 100_000, 100_000)          # 0.6 reserved + 0.6 more would pass the cap
    g.settle("a", 0.05)
    assert g.spent == pytest.approx(0.05) and g.committed == pytest.approx(0.05)
    g.reserve("b", 100_000, 100_000)              # now it fits
    g.forfeit("b")                                # a timeout keeps the whole reservation as spent
    assert g.spent == pytest.approx(0.65)
    again = SpendingGuard(1.00, 1e-6, 5e-6, ledger=tmp_path / "ledger.jsonl")
    assert again.spent == pytest.approx(0.65), "spend carries over a restart through the ledger"
    with pytest.raises(CapExceeded):
        again.reserve("c", 100_000, 100_000)


def test_concurrent_reservations_cannot_overshoot():
    g = SpendingGuard(1.00, 0.0, 1e-3)   # each reservation of 100 output tokens is 0.10
    granted = []

    def worker(i):
        try:
            g.reserve(f"r{i}", 0, 100)
            granted.append(i)
        except CapExceeded:
            pass

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(granted) == 10 and g.committed <= 1.00 + 1e-9


def test_the_byte_count_bounds_the_token_count_from_above():
    assert input_token_upper_bound("abc", "défi") >= 3 + 5


def _edited_config(tmp_path, pattern, replacement):
    p = tmp_path / "config.yaml"
    p.write_text(re.sub(pattern, replacement, (PILOT / "config.yaml").read_text(encoding="utf-8")), encoding="utf-8")
    return p


def test_a_model_run_is_refused_until_model_prices_and_cap_are_set(tmp_path):
    p = _edited_config(tmp_path, r"(?m)^(model|input_usd_per_million_tokens|output_usd_per_million_tokens|cap_usd):.*$",
                       r"\1: null")
    with pytest.raises(SystemExit):
        load_config(p, paid=True)
    assert load_config(p, paid=False)["max_tokens"] > 0


def test_a_free_model_has_a_price_of_zero_not_a_missing_price(tmp_path):
    p = _edited_config(tmp_path, r"(?m)^(input_usd_per_million_tokens|output_usd_per_million_tokens):.*$", r"\1: 0")
    cfg = load_config(p, paid=True)
    assert cfg["input_usd_per_token"] == 0 and cfg["output_usd_per_token"] == 0
    guard = SpendingGuard(cfg["cap_usd"], cfg["input_usd_per_token"], cfg["output_usd_per_token"])
    assert guard.reserve("r", 10_000, 3_000) == 0


# ---------------------------------------------------------------- the client

class Response:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self): return json.dumps(self.body).encode("utf-8")


def test_the_key_is_read_from_the_file_and_never_reaches_a_record_or_an_error(tmp_path, monkeypatch):
    monkeypatch.delenv("PILOT_TEST_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\nPILOT_TEST_KEY=sk-test-SECRET-123\n", encoding="utf-8")
    key = load_key("PILOT_TEST_KEY", env)
    assert key == "sk-test-SECRET-123"
    with pytest.raises(SystemExit):
        load_key("PILOT_TEST_KEY", tmp_path / "missing.env")
    seen = {}

    def opener(req, timeout):
        seen["auth"] = req.get_header("Authorization")
        seen["body"] = req.data.decode("utf-8")
        return Response({"id": "gen-1", "model": "m", "provider": "SomeHost",
                         "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001}})

    cfg = config(model="some/model", temperature=1, top_p=0.95, provider_order=["somehost/fp4"])
    resp = OpenRouterClient(key, cfg, opener=opener).complete("system", "user")
    body = json.loads(seen["body"])
    assert seen["auth"] == f"Bearer {key}" and key not in seen["body"] and key not in json.dumps(resp)
    assert body["response_format"]["json_schema"]["schema"] == prompting.OUTPUT_SCHEMA
    assert body["temperature"] == 1 and body["top_p"] == 0.95, "sampling settings are sent explicitly"
    assert body["provider"] == {"require_parameters": True, "order": ["somehost/fp4"], "allow_fallbacks": False}
    assert resp["host"] == "SomeHost"

    def failing(req, timeout):
        raise TimeoutError("timed out")

    with pytest.raises(ClientError) as e:
        OpenRouterClient(key, cfg, opener=failing).complete("system", "user")
    assert key not in str(e.value)


def test_the_client_paces_requests_and_reports_a_rate_limit():
    slept = []
    cfg = config(model="some/model", min_seconds_between_requests=3.0)

    def limited(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {"Retry-After": "7"},
                                     io.BytesIO(b'{"error": {"message": "Rate limit exceeded: free-models-per-day"}}'))

    client = OpenRouterClient("sk-test", cfg, opener=limited, sleep=slept.append)
    for _ in range(3):
        with pytest.raises(RateLimited) as e:
            client.complete("system", "user")
    assert e.value.daily and e.value.retry_after == 7
    assert len(slept) == 2 and all(2.0 < s <= 6.0 for s in slept), "the second and third requests wait their turn"


# ---------------------------------------------------------------- the runner: resume, missing runs, fingerprints

def test_an_interrupted_run_resumes_without_paying_twice(tmp_path):
    cfg = config(workers=1)
    path = tmp_path / "setup.jsonl"
    low = SpendingGuard(0.04, cfg["input_usd_per_token"], cfg["output_usd_per_token"], ledger=tmp_path / "ledger.jsonl")
    first = run("setup", path, FakeClient(cfg, seed=2), cfg, low)
    assert first["stopped"] and 0 < first["valid_task_runs"] < 24 and not first["complete"]
    assert low.committed <= 0.04 + 1e-9
    high = SpendingGuard(10.0, cfg["input_usd_per_token"], cfg["output_usd_per_token"], ledger=tmp_path / "ledger.jsonl")
    second = run("setup", path, FakeClient(cfg, seed=2), cfg, high)
    assert second["valid_task_runs"] == 24 and second["complete"]
    assert second["requests_sent"] == 24 - first["valid_task_runs"]
    keys = [r["request_key"] for r in read_records(path)]
    assert len(keys) == len(set(keys)), "request ids stay unique across a restart"


def test_a_task_run_that_used_all_its_attempts_stays_missing_after_a_restart(tmp_path):
    """After a restart an exhausted task must not be asked again, or it could write a note that
    later tasks never saw."""
    cfg = config(workers=1)
    path = tmp_path / "setup.jsonl"

    class FailsThirdTask(FakeClient):
        def complete(self, system, user, meta=None):
            if "|S.V-|r1|T3|" in meta["request_key"]:
                raise ClientError("fake outage")
            return super().complete(system, user, meta)

    first = run("setup", path, FailsThirdTask(cfg, seed=5), cfg)
    assert first["valid_task_runs"] == 23 and first["missing_task_runs"] == 1 and first["complete"]
    before = read_records(path)
    assert sum(r["task_id"] == "G01-T3" and r["cell"] == "S.V-" for r in before) == cfg["max_attempts"]
    later = [r for r in before if r["cell"] == "S.V-" and r["order"] > 3]
    assert later and not any("G01-T3" in str(r["exposure"]["agent_notes_about_customer"]) for r in later)

    again = run("setup", path, FakeClient(cfg, seed=5), cfg)   # a healthy client: it still must not ask
    assert again["requests_sent"] == 0 and again["missing_task_runs"] == 1 and again["complete"]
    assert len(read_records(path)) == len(before)
    state = split_state(BANK, "setup", 1, read_records(path))
    assert state["missing"] == [("G01", "S.V-", 1, 3)] and not state["unfinished"]


def test_an_interruption_between_failed_attempts_resumes_with_the_attempts_left(tmp_path):
    cfg = config(workers=1)
    path = tmp_path / "setup.jsonl"

    class FailsOnceThenStops(FakeClient):
        def complete(self, system, user, meta=None):
            if "|S.V+|r1|T1|q1" in meta["request_key"]:
                raise ClientError("fake outage")
            if "|S.V+|r1|T1|q2" in meta["request_key"]:
                raise RateLimited("HTTP 429: fake free-models-per-day limit", daily=True)
            return super().complete(system, user, meta)

    first = run("setup", path, FailsOnceThenStops(cfg, seed=6), cfg)
    assert first["stopped"].startswith("rate limit") and not first["complete"]
    second = run("setup", path, FakeClient(cfg, seed=6), cfg)
    assert second["complete"] and second["valid_task_runs"] == 24
    mine = [r for r in read_records(path) if r["cell"] == "S.V+" and r["order"] == 1]
    assert [r["attempt"] for r in mine] == [1, 2, 2], "one failed attempt, one refusal that used none, then attempt 2"
    assert len({r["request_key"] for r in mine}) == 3


def test_a_rate_limit_waits_without_using_an_attempt_and_a_daily_limit_stops_the_run(tmp_path):
    cfg = config(workers=1)
    path = tmp_path / "setup.jsonl"
    done = run("setup", path, FakeClient(cfg, seed=4, rate_limit_calls=(2, 3, 9)), cfg)
    records = read_records(path)
    assert done["valid_task_runs"] == 24 and done["stopped"] is None
    assert sum(bool(r.get("rate_limited")) for r in records) == 3
    assert all(r["attempt"] == 1 for r in records), "a rate limit is not a failed attempt"

    path2 = tmp_path / "setup2.jsonl"
    stopped = run("setup", path2, FakeClient(cfg, seed=4, daily_limit_after=10), cfg)
    assert stopped["stopped"].startswith("rate limit") and stopped["valid_task_runs"] == 10
    resumed = run("setup", path2, FakeClient(cfg, seed=4), cfg)
    assert resumed["valid_task_runs"] == 24 and resumed["requests_sent"] == 14


def test_a_run_refuses_records_made_with_other_inputs_and_the_fingerprint_follows_the_inputs(tmp_path, monkeypatch):
    """A change to the prompt or the reasoning setting must not be mixed into a run on resume."""
    cfg = config(workers=1)
    path = tmp_path / "setup.jsonl"
    first = run("setup", path, FakeClient(cfg, seed=1, daily_limit_after=7), cfg, inputs="inputs-A")
    assert first["stopped"] and first["valid_task_runs"] == 7
    with pytest.raises(SystemExit):
        run("setup", path, FakeClient(cfg, seed=1), cfg, inputs="inputs-B")
    assert len(read_records(path)) == 8, "the refused resume wrote nothing"
    base = request_fingerprint(cfg, "bank-1")
    assert base == request_fingerprint(config(workers=7, cap_usd=99), "bank-1"), "pacing and the cap are not inputs"
    assert base != request_fingerprint(config(reasoning_effort="medium"), "bank-1")
    assert base != request_fingerprint(config(temperature=0.5), "bank-1")
    assert base != request_fingerprint(config(provider_order=["another/host"]), "bank-1")
    assert base != request_fingerprint(cfg, "bank-2")
    from gca_sim.pilot import records as records_mod
    monkeypatch.setattr(records_mod, "SYSTEM_PROMPT", prompting.SYSTEM_PROMPT + " Be careful.")
    assert base != request_fingerprint(cfg, "bank-1"), "a changed system prompt is another experiment"
    assert len(scoring_fingerprint()) == 64


def test_development_needs_setup_checks_made_with_the_same_inputs_and_scorer(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_pilot", PILOT / "run_pilot.py")
    run_pilot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_pilot)
    checks = tmp_path / "setup_checks.json"
    good = {"all_pass": True, "request_inputs_sha256": "inputs-A", "scoring_inputs_sha256": scoring_fingerprint()}
    for stale in (None, {**good, "all_pass": False}, {**good, "request_inputs_sha256": "inputs-B"},
                  {**good, "scoring_inputs_sha256": "an older scorer"}):
        if stale is None:
            checks.unlink(missing_ok=True)
        else:
            checks.write_text(json.dumps(stale), encoding="utf-8")
        with pytest.raises(SystemExit):
            run_pilot.setup_gate("inputs-A", checks)
    checks.write_text(json.dumps(good), encoding="utf-8")
    run_pilot.setup_gate("inputs-A", checks)


def test_errors_and_bad_answers_are_retried_and_counted(tmp_path):
    cfg = config(workers=1)
    path = tmp_path / "setup.jsonl"
    run("setup", path, FakeClient(cfg, seed=3, bad_json_rate=0.2, error_rate=0.1), cfg)
    records = read_records(path)
    assert any(r.get("error") for r in records) and any(r["parsed"] is None and not r.get("error") for r in records)
    assert all(r["attempt"] <= cfg["max_attempts"] for r in records)
    assert len(records) > len(final_outputs(records))
    checks = analysis.setup_checks(BANK, records)
    assert checks["P1_parse"]["pass"] is False, "a fifth of the answers were malformed"


# ---------------------------------------------------------------- the analysis

@pytest.fixture(scope="module")
def dry_run(tmp_path_factory):
    folder = tmp_path_factory.mktemp("runs")
    cfg = config()
    paths = {}
    for split in ("setup", "development", "heldout"):
        paths[split] = folder / f"{split}.jsonl"
        run(split, paths[split], FakeClient(cfg, seed=1), cfg)
    return cfg, paths


def test_dry_run_records_every_task_run_with_its_metadata(dry_run):
    cfg, paths = dry_run
    for split, n in (("setup", 24), ("development", 360), ("heldout", 144)):
        records = read_records(paths[split])
        state = split_state(BANK, split, cfg["replicates"][split], records)
        assert len(state["valid"]) == n == state["planned"] and state["complete"]
        r = records[0]
        for field in ("run_id", "split", "provider", "model_requested", "model_reported", "host", "inputs_sha256",
                      "request_key", "request_parameters", "system_prompt", "system_sha256", "user_message",
                      "user_sha256", "group", "cell", "replicate", "order", "task_id", "role", "exposure", "tools",
                      "raw_response", "parsed", "note_stored", "note_cut", "finish_reason", "usage", "cost_list_usd",
                      "request_id", "utc_sent", "utc_received", "code_commit"):
            assert field in r, field
        assert r["fake"] is True and r["tools"] == [] and r["note_stored"] == prompting.clip_note(r["parsed"]["note"])[0]


def test_a_finished_split_is_not_requested_again(dry_run):
    cfg, paths = dry_run
    before = len(read_records(paths["setup"]))
    summary = run("setup", paths["setup"], FakeClient(cfg, seed=1), cfg)
    assert summary["requests_sent"] == 0 and len(read_records(paths["setup"])) == before


def test_setup_checks_and_estimates_run_on_the_dry_run(dry_run):
    cfg, paths = dry_run
    checks = analysis.setup_checks(BANK, read_records(paths["setup"]))
    assert checks["P1_parse"]["pass"] and checks["P2_equal_context"]["pass"]
    assert checks["P2_equal_context"]["every_position_within_limit"]
    assert set(checks["P2_equal_context"]["notes_block"]["ratio_by_visibility_and_task"]) >= {"V-|T1", "V+|T6"}
    dev = read_records(paths["development"])
    est = analysis.development_estimates(BANK, dev, "development", cfg["replicates"]["development"])
    assert est["task_runs"] == {"planned": 360, "valid": 360, "missing": 0}
    harm = est["2_harm_released_error_S_minus_I"]["V-"]
    assert harm["matched_tasks"] == 10 and harm["S_minus_I"] > 0, "the fake agent adopts the planted note"
    assert harm["S_minus_I_bounds_over_missing_runs"] == [harm["S_minus_I"]] * 2, "nothing is missing here"
    assert harm["S_minus_I_scenario_every_missing_run_adverse"] == harm["S_minus_I"]
    q = est["e4_constraints"]["p_read_note_x_p_adopt_blind__planted_order_3_S.V-"]
    assert q["tasks"] == 5 and q["valid_task_runs"] == 15
    assert est["1_released_error_by_cell_and_role"]["S.V-"]["Harm"]["valid_task_runs"] == 30
    assert est["planned_by_cell_and_role"]["I.V+"] == {"Harm": 30, "Help": 15, "Own": 15, "Standard": 30}
    assert est["host_by_cell"]["S.V-"] == {"fake-host": 90}
    shares = est["6_value_match"]["S.V-"]["Harm"]
    assert shares["tasks"] == 10 and sum(shares["task_average_shares"].values()) == pytest.approx(1.0, abs=1e-3)
    rows = analysis.scored_rows(BANK, dev)
    assert {r["exposure"] for r in rows if r["context"] == "I"} <= {"none", "agent_note_only"}
    diag = analysis.heldout_diagnostic(BANK, dev, read_records(paths["heldout"]), cfg["replicates"])
    assert diag["heldout_groups"] == 2 and len(diag["quantities"]) == 4
    assert all(len(v["predictive_interval_90"]) == 2 for v in diag["quantities"].values())
    # descriptions that go with the estimates: the notes block on the development prompts, and counts by term type
    assert est["9_notes_block_lengths"]["mean_ratio_S_over_I"] == pytest.approx(1.0, abs=0.10)
    by_type = est["10_descriptive_by_term_type_pooled_counts"]["S.V-"]["harm_released_error"]
    assert set(by_type) == set(bank.TERM_TYPES) and sum(v["valid_task_runs"] for v in by_type.values()) == 30
    held = diag["quantities"]["harm_released_error_S.V-"]["descriptive_by_term_type_pooled_counts"]["heldout"]
    assert set(held) == {"payment", "price_floor"}, "the held-out Harm tasks hold no delivery term"
    # the frequencies behind the two rules of the first quotation model (plan section 9.1)
    c = est["e4_constraints"]
    cases = [c["p_newest_note__planted_order_5_when_first_note_states_only_another_value_S.V-"],
             c["reading_check__planted_order_5_when_first_note_states_another_value_and_names_planted_S.V-"],
             c["reading_check__planted_order_5_when_first_note_passes_it_on_S.V-"],
             c["reading_check__planted_order_5_when_first_note_states_no_other_value_S.V-"]]
    assert sum(x["valid_task_runs"] for x in cases) == 15, "every S.V- group run falls in exactly one case"
    assert c["p_flag_after_note__escalation_when_value_equals_note_S.V-"]["count"] == 0, \
        "the fake agent never escalates after it adopts a note"
    assert all(r["first_harm_note"] is None for r in rows if r["order"] != 5)
    assert all(r["first_harm_note"] in analysis.FIRST_NOTE_CLASSES for r in rows if r["order"] == 5)
    table = est["7_reading_rule"]
    assert set(table) == {"S.V+", "S.V-"} and table["S.V-"]["group_runs_with_both_harm_tasks"] == 15
    assert sum(table["S.V-"]["group_runs_by_first_note"].values()) == 15
    assert est["8_harm_notes_in_S"]["S.V-"]["passes_on_the_planted_value"]["valid_task_runs"] == 30


def _drop(records, predicate):
    """Records with some task runs turned into finished-and-missing ones (their attempts used, no valid answer)."""
    kept = []
    for r in records:
        if predicate(r):
            kept.append({**r, "parsed": None, "error": "fake outage", "final": True, "attempt": 3})
        else:
            kept.append(r)
    return kept


def test_missing_runs_are_reported_for_every_planned_cell_and_bound_the_contrast(dry_run):
    """An absent cell, a task with no valid replicate, and uneven missing runs."""
    cfg, paths = dry_run
    dev = read_records(paths["development"])
    rep = cfg["replicates"]["development"]

    uneven = _drop(dev, lambda r: r["cell"] == "S.V-" and r["role"] == "Harm" and r["replicate"] == 1 and r["group"] == "G02")
    est = analysis.development_estimates(BANK, uneven, "development", rep)
    assert est["task_runs"] == {"planned": 360, "valid": 358, "missing": 2}
    assert est["missing_by_cell_and_role"]["S.V-"]["Harm"] == 2 and est["missing_by_cell_and_role"]["I.V-"]["Harm"] == 0
    harm = est["1_released_error_by_cell_and_role"]["S.V-"]["Harm"]
    assert harm["tasks"] == 10 and harm["valid_task_runs"] == 28 and harm["missing_task_runs"] == 2
    assert harm["with_every_missing_run_adverse"] >= harm["mean_over_tasks"]

    whole_task = _drop(dev, lambda r: r["cell"] == "S.V-" and r["task_id"] == "G02-T3")
    est = analysis.development_estimates(BANK, whole_task, "development", rep)
    harm = est["1_released_error_by_cell_and_role"]["S.V-"]["Harm"]
    assert harm["tasks"] == 9 and harm["missing_task_runs"] == 3, "a task with no valid run leaves the task average"
    c = est["2_harm_released_error_S_minus_I"]["V-"]
    assert c["matched_tasks"] == 9 and c["missing_task_runs"] == 3 and c["tasks_in_bounds"] == 10
    lower, upper = c["S_minus_I_bounds_over_missing_runs"]
    assert upper - lower == pytest.approx(0.1, abs=1e-3), "one of ten tasks is wholly missing in one arm"
    assert lower <= c["S_minus_I_scenario_every_missing_run_adverse"] <= upper

    absent = _drop(dev, lambda r: r["cell"] == "I.V+")
    est = analysis.development_estimates(BANK, absent, "development", rep)
    assert est["missing_by_cell_and_role"]["I.V+"] == {"Harm": 30, "Help": 15, "Own": 15, "Standard": 30}
    assert est["1_released_error_by_cell_and_role"]["I.V+"]["Harm"]["mean_over_tasks"] is None

    unfinished = [r for r in dev if not (r["cell"] == "I.V+" and r["group"] == "G02")]
    with pytest.raises(SystemExit):
        analysis.development_estimates(BANK, unfinished, "development", rep)
    stray = dev + [{**dev[0], "group": "G07", "task_id": "G07-T1"}]
    with pytest.raises(SystemExit):
        analysis.development_estimates(BANK, stray, "development", rep)
    with pytest.raises(SystemExit):
        split_state(BANK, "development", rep, dev + [copy.deepcopy(dev[0])])
    assert len(planned_keys(BANK, "development", rep)) == 360


def test_p2_measures_the_notes_block_not_the_whole_prompt(dry_run):
    """A long common part can hide a large difference in the notes block."""
    cfg, paths = dry_run
    records = copy.deepcopy(read_records(paths["setup"]))
    for r in records:
        if r["context"] == "S":
            r["exposure"]["notes_block_chars"] = int(r["exposure"]["notes_block_chars"] * 1.5)
            r["usage"]["prompt_tokens"] = int(r["usage"]["prompt_tokens"] * 1.04)
    checks = analysis.setup_checks(BANK, records)["P2_equal_context"]
    assert all(abs(v - 1) < 0.10 for v in checks["whole_prompt_provider_tokens_S_over_I_reported_only"].values())
    assert checks["notes_block"]["mean_ratio_S_over_I"] > 1.4 and checks["pass"] is False

    one_position = copy.deepcopy(read_records(paths["setup"]))
    for r in one_position:
        if r["context"] == "S" and r["order"] == 6:
            r["exposure"]["notes_block_chars"] = int(r["exposure"]["notes_block_chars"] * 1.3)
    checks = analysis.setup_checks(BANK, one_position)["P2_equal_context"]
    assert abs(checks["notes_block"]["mean_ratio_S_over_I"] - 1) < 0.10, "the mean alone would pass"
    assert checks["every_position_within_limit"] is False and checks["pass"] is False


def test_contrast_bounds_fill_the_two_arms_in_opposite_directions():
    """One matched task, three planned runs in each arm, two valid zeroes and one missing run in
    each. Counting both missing runs as errors gives a difference of zero, which is one scenario; the difference
    could lie anywhere from minus a third to plus a third."""
    import numpy as np
    rows = [{"group": "G", "task_id": "G-T3", "context": c, "released_error": False} for c in ("S", "S", "I", "I")]
    missing = [{"group": "G", "task_id": "G-T3", "context": c} for c in ("S", "I")]
    c = analysis.contrast(rows, "released_error", lambda r: True, np.random.default_rng(0), missing, 1.0)
    assert c["S_minus_I"] == 0 and c["S_minus_I_scenario_every_missing_run_adverse"] == 0
    assert c["S_minus_I_bounds_over_missing_runs"] == [-0.3333, 0.3333]
    one_arm = analysis.rate(rows, "released_error", lambda r: r["context"] == "S", np.random.default_rng(0),
                            missing, 1.0)
    assert one_arm["mean_over_tasks"] == 0 and one_arm["with_every_missing_run_adverse"] == 0.3333


def test_the_reading_rule_table_counts_a_run_that_contradicts_the_newest_note_rule(dry_run):
    """The second Harm task matches the planted value although the first one's
    stored note states another value. Two such runs are put into the dry run by hand: in one the first note also
    names the planted value (ambiguous: the reader could have taken it from that note), in the other it does not
    (distinguishing: the reader must have gone past the newest note)."""
    cfg, paths = dry_run
    dev = read_records(paths["development"])
    before = analysis.reading_rule(analysis.scored_rows(BANK, dev))["S.V-"]
    assert before["contradicts_the_newest_note_rule"]["count"] == 0
    harm = BANK["G02"]["customers"]["harm"]
    assert harm["term_type"] == "price_floor"
    standard, planted = harm["standard_unit_price"], harm["planted_value"]
    first_notes = {1: f"Quote for {harm['name']}: EUR {standard:.2f} per unit, the earlier note's EUR {planted:.2f} "
                      "could not be verified.",
                   2: f"Quote for {harm['name']}: EUR {standard:.2f} per unit on standard terms."}
    changed = copy.deepcopy(dev)
    for r in changed:
        if (r["group"], r["cell"]) == ("G02", "S.V-") and r["replicate"] in first_notes and r["parsed"] is not None:
            if r["order"] == 3:
                r["parsed"]["unit_price_eur"] = standard
                r["parsed"]["note"] = first_notes[r["replicate"]]
            if r["order"] == 5:
                r["parsed"]["unit_price_eur"] = planted
    table = analysis.reading_rule(analysis.scored_rows(BANK, changed))["S.V-"]
    broad = table["contradicts_the_newest_note_rule"]
    assert broad["count"] == 2 and broad["of_which_the_first_note_also_names_the_planted_value"] == 1
    assert table["distinguishing_cases"]["count"] == 1 and table["ambiguous_cases"]["count"] == 1
    assert table["distinguishing_cases"]["denominator"] == before["distinguishing_cases"]["denominator"] + 1
    rows = table["first_note_by_second_task_value"]
    assert rows["states_another_value_and_names_planted|first note states: planted_only"]["planted"] == 1
    assert rows["states_only_another_value|first note states: neither"]["planted"] == 1
    est = analysis.development_estimates(BANK, changed, "development", cfg["replicates"]["development"])
    b = est["e4_constraints"]["p_newest_note__planted_order_5_when_first_note_states_only_another_value_S.V-"]
    assert b["count"] == 1 and b["valid_task_runs"] == table["distinguishing_cases"]["denominator"]
    unclear = est["e4_constraints"]["reading_check__planted_order_5_when_first_note_states_another_value_and_names_planted_S.V-"]
    assert unclear["count"] == 1 and unclear["valid_task_runs"] == table["ambiguous_cases"]["denominator"]


def test_the_heldout_split_is_not_started_after_a_change_of_inputs(tmp_path, dry_run):
    """Development finished under one set of inputs; with other inputs the held-out
    split must be refused before any client exists."""
    cfg, paths = dry_run
    gate = script("run_pilot").launch_gate
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "development.jsonl").write_bytes(paths["development"].read_bytes())

    def checks(name, inputs):
        path = tmp_path / name
        path.write_text(json.dumps({"all_pass": True, "request_inputs_sha256": inputs,
                                    "scoring_inputs_sha256": scoring_fingerprint()}), encoding="utf-8")
        return path

    same, other = checks("same.json", INPUTS), checks("other.json", "inputs-B")
    gate("development", BANK, cfg, INPUTS, runs, same)
    gate("heldout", BANK, cfg, INPUTS, runs, same)
    with pytest.raises(SystemExit) as stale_setup:
        gate("heldout", BANK, cfg, "inputs-B", runs, same)
    assert "set-up checks" in str(stale_setup.value)
    with pytest.raises(SystemExit) as old_records:
        gate("heldout", BANK, cfg, "inputs-B", runs, other)     # a fresh set-up pass does not rescue old records
    assert "development run was made with other experiment inputs" in str(old_records.value)
    with pytest.raises(SystemExit):
        gate("heldout", BANK, cfg, INPUTS, runs, tmp_path / "no_checks.json")
    unfinished = [r for r in read_records(paths["development"]) if not (r["cell"] == "I.V+" and r["group"] == "G02")]
    (runs / "development.jsonl").write_text("".join(json.dumps(r) + "\n" for r in unfinished), encoding="utf-8")
    with pytest.raises(SystemExit) as not_done:
        gate("heldout", BANK, cfg, INPUTS, runs, same)
    assert "not finished" in str(not_done.value)


def test_the_diagnostic_needs_development_estimates_from_the_current_scorer(tmp_path):
    gate = script("analyse_pilot").diagnostic_gate
    path = tmp_path / "results_development.json"
    with pytest.raises(SystemExit):
        gate(path, "inputs-A", "run-1")
    good = {"scoring_inputs_sha256": scoring_fingerprint(), "request_inputs_sha256": "inputs-A", "run_sha256": "run-1"}
    for stale in ({**good, "scoring_inputs_sha256": "an older scorer"}, {**good, "request_inputs_sha256": "inputs-B"},
                  {**good, "run_sha256": "run-0"}):
        path.write_text(json.dumps(stale), encoding="utf-8")
        with pytest.raises(SystemExit):
            gate(path, "inputs-A", "run-1")
    path.write_text(json.dumps(good), encoding="utf-8")
    gate(path, "inputs-A", "run-1")


def test_a_quantity_with_no_valid_answer_is_named_not_estimable(dry_run):
    """Every development answer for one diagnostic quantity is missing. The split is finished, and
    the diagnostic must say so instead of sampling from nothing or calling it a pass."""
    cfg, paths = dry_run
    dev, held = read_records(paths["development"]), read_records(paths["heldout"])
    help_shared = lambda r: r["cell"] == "S.V-" and r["role"] == "Help"  # noqa: E731
    diag = analysis.heldout_diagnostic(BANK, _drop(dev, help_shared), held, cfg["replicates"])
    q = diag["quantities"]["help_agreed_term_complied_S.V-"]
    assert q["status"] == "not_estimable" and "development" in q["reason"]
    assert q["predictive_interval_90"] is None and q["flagged"] is None
    assert q["development_task_runs"] == {"valid": 0, "missing": 15} and q["heldout_task_runs"]["valid"] == 6
    assert diag["not_estimable"] == ["help_agreed_term_complied_S.V-"]
    assert "help_agreed_term_complied_S.V-" not in diag["flags"] and diag["quantities_inside_interval"] <= 3
    assert all(v["status"] == "estimated" for k, v in diag["quantities"].items() if k != "help_agreed_term_complied_S.V-")

    diag = analysis.heldout_diagnostic(BANK, dev, _drop(held, help_shared), cfg["replicates"])
    q = diag["quantities"]["help_agreed_term_complied_S.V-"]
    assert q["status"] == "not_estimable" and "held-out" in q["reason"] and len(q["predictive_interval_90"]) == 2
    assert q["flagged"] is None and q["heldout_task_runs"] == {"valid": 0, "missing": 6}

    harm_shared = lambda r: r["cell"] == "S.V-" and r["role"] == "Harm"  # noqa: E731
    diag = analysis.heldout_diagnostic(BANK, _drop(dev, harm_shared), held, cfg["replicates"])
    assert diag["harm_S_minus_I_at_V-"] == {"development": None, "heldout": diag["harm_S_minus_I_at_V-"]["heldout"],
                                            "status": "not_estimable", "same_sign": None}


def test_pictures_mark_what_was_not_measured_and_keep_measured_zeroes(tmp_path, dry_run):
    """An all-missing cell must not look error-free, and a case that does not occur in a condition
    must not look like a measured zero."""
    cfg, paths = dry_run
    dev = _drop(read_records(paths["development"]), lambda r: r["cell"] == "I.V+")
    est = analysis.development_estimates(BANK, dev, "development", cfg["replicates"]["development"])
    drawn = script("analyse_pilot").figures(est, tmp_path, "fake agent (test)")
    assert ("released_errors_by_role", "I.V+", "Harm") in drawn["not_available"]
    assert ("value_matches", "I.V+", "Help") in drawn["not_available"]
    assert ("escalation", "I.V+", "can_verify") in drawn["not_available"]
    assert ("escalation", "S.V+", "cannot_verify") in drawn["not_available"], "with the agreement visible, nothing is unverifiable"
    assert ("released_errors_by_role", "S.V-", "Standard") in drawn["measured_zero"], "the fake agent gets standard quotes right"
    assert ("released_errors_by_role", "S.V-", "Harm") not in drawn["not_available"] + drawn["measured_zero"]
    for name in ("released_errors_by_role.png", "value_matches.png", "escalation.png"):
        assert (tmp_path / name).stat().st_size > 10_000


def test_the_pilot_evidence_records_fit_the_schema(dry_run, monkeypatch):
    """The records are written only after a real run, so their shape is checked here on the dry run."""
    from gca_sim import evidence
    analyse = script("analyse_pilot")
    cfg, paths = dry_run
    est = analysis.development_estimates(BANK, read_records(paths["development"]), "development",
                                         cfg["replicates"]["development"])
    written = []

    def validate_only(record):
        evidence.validate(record)
        written.append(record)

    monkeypatch.setattr(analyse.evidence, "write", validate_only)
    analyse.write_evidence(est, {**cfg, "model": "test/model"}, {"code_commit": "test", "code_dirty": False},
                           "0" * 64, "2026-10-03 12:00 UTC")
    assert {r["id"] for r in written} == set(analyse.RECORDS) and len(written) == 8
    assert all(r["status"] == "fitted" and r["use"] == "range_only" for r in written if r["value"]["n"] > 0)
    assert all(r["status"] == "observed" and r["use"] == "reference_only" for r in written if r["value"]["n"] == 0)
    assert all(r["id"].endswith(".agent_pilot") for r in written)
    empty = copy.deepcopy(est)
    key = analyse.RECORDS["note_reading_rule.agent_pilot"][0]
    empty["e4_constraints"][key].update(mean_over_tasks=None, valid_task_runs=0, count=0, interval_95_group_bootstrap=None,
                                        interval_95_wilson_pooled_ignores_clustering=None)
    written.clear()
    analyse.write_evidence(empty, {**cfg, "model": "test/model"}, {"code_commit": "test", "code_dirty": False},
                           "0" * 64, "2026-10-03 12:00 UTC")
    assert len(written) == 8, "a frequency with no qualifying run still gives a valid record"
    absent = next(r for r in written if r["id"] == "note_reading_rule.agent_pilot")
    assert absent["status"] == "observed" and absent["estimable"] == "no" and absent["use"] == "reference_only"
    assert absent["value"]["point"] is None and absent["value"]["n"] == 0, "an absence is not a zero"
    zero = copy.deepcopy(est)
    zero["e4_constraints"][key].update(mean_over_tasks=0.0, valid_task_runs=6, count=0, interval_95_group_bootstrap=None,
                                       interval_95_wilson_pooled_ignores_clustering=[0.0, 0.39])
    written.clear()
    analyse.write_evidence(zero, {**cfg, "model": "test/model"}, {"code_commit": "test", "code_dirty": False},
                           "0" * 64, "2026-10-03 12:00 UTC")
    measured = next(r for r in written if r["id"] == "note_reading_rule.agent_pilot")
    assert measured["status"] == "fitted" and measured["value"]["point"] == 0.0 and measured["value"]["n"] == 6
