"""E6 in-context confirmation check: every sampled write has exactly one recorded judgement, keyed to the pinned
files, and the saved counts follow from the judgements.

Reads the committed sample and output only; does not need the third_party checkout."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E6 = ROOT / "experiments" / "e6_taubench"


def load(name):
    spec = importlib.util.spec_from_file_location(name, E6 / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hc, ct = load("confirmation_handcheck"), load("check_taubench")
SAMPLE = json.loads((ROOT / "reports" / "E6" / "confirmation_sample.json").read_text(encoding="utf-8"))
OUT = json.loads((ROOT / "reports" / "E6" / "confirmation_handcheck.json").read_text(encoding="utf-8"))


def sampled(fn):
    return [it for s in ("Y", "N") for it in SAMPLE["models"][fn]["sample"][s]]


def test_every_sampled_write_has_exactly_one_judgement():
    keys = [it["key"] for fn in SAMPLE["models"] for it in sampled(fn)]
    assert len(keys) == len(set(keys)) == 100
    assert set(keys) == set(hc.JUDGED)
    for confirmed, borderline, note in hc.JUDGED.values():
        assert isinstance(confirmed, bool) and isinstance(borderline, bool) and note.strip()


def test_keys_name_the_pinned_files_and_strata_follow_the_keyword():
    for fn, m in SAMPLE["models"].items():
        for s in ("Y", "N"):
            for it in m["sample"][s]:
                assert it["file_sha256"] == ct.EXPECTED_SHA[fn] and it["key"].startswith(ct.EXPECTED_SHA[fn][:12])
                assert it["key"].endswith(f"msg{it['message_index']}:call{it['tool_call_index']}")
                assert bool(ct.YES.search(it["customer_reply"])) == (s == "Y")


def test_saved_counts_follow_from_the_judgements():
    for fn, r in OUT["models"].items():
        for s in ("Y", "N"):
            items = SAMPLE["models"][fn]["sample"][s]
            assert r["strata"][s]["confirmed"] == sum(hc.JUDGED[it["key"]][0] for it in items)
            assert r["strata"][s]["borderline"] == sum(hc.JUDGED[it["key"]][1] for it in items)
        lo, hi = r["estimated_share_if_borderline_flipped"]
        assert lo <= r["estimated_share_confirmed"] <= hi
        assert r["estimated_share_credible_95"][0] <= r["estimated_share_confirmed"] <= 1
    assert OUT["judged_by"].startswith("Claude Code (build)")
