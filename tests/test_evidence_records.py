"""Every evidence record validates against evidence/schema.json and is stored under its own id."""

import json

import pytest

from gca_sim import evidence

RECORDS = sorted(evidence.RECORDS_DIR.glob("*.json"))


def test_records_exist():
    assert RECORDS, "no evidence records found"


@pytest.mark.parametrize("path", RECORDS, ids=[p.stem for p in RECORDS])
def test_record_valid(path):
    rec = json.loads(path.read_text(encoding="utf-8"))
    evidence.validate(rec)
    assert path.stem == rec["id"]
    if rec["estimable"] in ("partly", "no"):
        assert rec.get("estimable_note"), "partly or not estimable records must say what is missing"
    if rec["source"].get("doi"):
        # Values from a licensed source carry the licence,
        # so they can be filtered out of a release the licence does not allow.
        assert rec["source"].get("licence"), "a record citing a DOI must carry the source's licence"


@pytest.mark.parametrize("path", RECORDS, ids=[p.stem for p in RECORDS])
def test_observed_records_hold_no_fitted_sampler(path):
    """Fitted parameters only ever sit in records marked fitted, and an
    observed record's distribution, if any, is the empirical one."""
    rec = json.loads(path.read_text(encoding="utf-8"))
    value = rec.get("value") or {}
    if value.get("params"):
        assert rec["status"] == "fitted", rec["id"]
    if rec["status"] == "observed":
        assert value.get("distribution") in (None, "empirical"), rec["id"]


@pytest.mark.parametrize("path", RECORDS, ids=[p.stem for p in RECORDS])
def test_observed_records_hold_no_inferred_estimate(path):
    """An estimate inferred from a sample, with a posterior or credible interval, sits
    in a record marked fitted, never in an observed one."""
    rec = json.loads(path.read_text(encoding="utf-8"))
    if rec["status"] == "observed":
        text = json.dumps(rec.get("value") or {}).lower()
        assert not any(w in text for w in ("credible", "posterior", "jeffreys")), rec["id"]


def test_in_context_confirmation_estimate_is_fitted_and_names_its_sample_and_limits():
    rec = evidence.load_all()["confirm_before_write_in_context.taubench_retail"]
    assert rec["status"] == "fitted" and rec["use"] == "reference_only"
    meaning = rec["value"]["interval_95_meaning"]
    assert "Bayesian credible interval" in meaning and "annotation error" in meaning
    assert "reports/E6/confirmation_sample.json" in rec["notes"] and "one annotator" in rec["estimable_note"].lower()
    keyword = evidence.load_all()["confirm_before_write.taubench_retail"]
    assert keyword["status"] == "observed" and "summary" not in keyword["value"]


def test_analogue_records_named_by_assumptions_are_usable():
    """Every record that assumptions.yaml cites as an analogue exists, is not reference-only or inestimable, and
    carries no parametric fit (none has passed an acceptance check)."""
    import yaml

    a = yaml.safe_load((evidence.ROOT / "evidence" / "assumptions.yaml").read_text(encoding="utf-8"))
    records = evidence.load_all()
    cited = [(name, rid) for name, spec in a["parameters"].items()
             for rid in spec.get("analogue_records", []) + spec.get("context_records", [])]
    for name, rid in cited:
        assert rid in records, (name, rid)
        rec = records[rid]
        assert rec.get("use") != "reference_only" and rec["estimable"] != "no", (name, rid)
        assert not (rec.get("value") or {}).get("params"), (name, rid)


SPECS = sorted((evidence.ROOT / "specs").glob("*.json"))


@pytest.mark.parametrize("path", SPECS, ids=[p.stem for p in SPECS])
def test_spec_carries_licence(path):
    spec = json.loads(path.read_text(encoding="utf-8"))
    assert spec["source"].get("licence"), "a workflow spec must carry its source's licence"
