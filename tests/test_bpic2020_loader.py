"""The BPIC 2020 loader reads the file we recorded in data/SOURCES.md. Skipped if the raw file is absent."""

import pytest

from gca_sim.process_logs import bpic2020

pytestmark = pytest.mark.skipif(not bpic2020.RAW_PATH.exists(), reason="data/raw is git-ignored; download per SOURCES.md")


def test_counts_match_dataset_description():
    log = bpic2020.load()
    assert log.cases.shape[0] == 10_500
    assert log.events.shape[0] == 56_437


def test_events_are_chronological_within_cases():
    ev = bpic2020.load().events
    gaps = ev.groupby("case_id")["ts_utc"].diff().dropna()
    assert (gaps.dt.total_seconds() >= 0).all()
