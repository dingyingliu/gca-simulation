"""Loader for the BPI Challenge 2020 Domestic Declarations log.

Source, licence and checksums: data/SOURCES.md. The raw file stays in data/raw/ (git-ignored).

What the file contains (checked at E3, 2026-10-02 UTC):

- One trace per declaration, with trace attributes id, concept:name, BudgetNumber (a single
  anonymised value for every case, so it carries no information), DeclarationNumber
  ("UNKNOWN" for 452 cases) and Amount (not exact amounts, per the challenge page).
- Events with id, concept:name, time:timestamp, org:resource and org:role. There is no
  lifecycle:transition attribute, so each event has a single timestamp: the moment the
  step was recorded. Start of work is not recorded.
- Timestamps are local Dutch time with the correct CET/CEST offset, second resolution.
- org:resource is only "STAFF MEMBER" or "SYSTEM". Individuals cannot be identified, so
  everything about people is by role.

The loader parses the XES directly (it is flat) so time zones are kept, and returns one
pandas DataFrame of events and one of cases.
"""

from __future__ import annotations

import gzip
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "raw" / "DomesticDeclarations.xes.gz"
RAW_SHA256 = "0bc3312acf0b9ee5ae6f4ebe9df204005ef11665d62f2d21dd04995161d7532b"
LOCAL_TZ = "Europe/Amsterdam"

SOURCE = {
    "name": "BPI Challenge 2020: Domestic Declarations",
    "creator": "Boudewijn van Dongen, Eindhoven University of Technology",
    "doi": "10.4121/uuid:3f422315-ed9d-4882-891f-e180b5b4feb5",
    "url": "https://data.4tu.nl/datasets/6a0a26d2-82d0-4018-b1cd-89afb0e8627f/1",
    "licence": "CC BY-NC 4.0",
    "retrieved_utc": "2026-10-02",
    "file_sha256": RAW_SHA256,
}


@dataclass(frozen=True)
class Bpic2020Log:
    events: pd.DataFrame
    cases: pd.DataFrame


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path = RAW_PATH, verify: bool = True) -> Bpic2020Log:
    if verify:
        sha = sha256_of(path)
        if sha != RAW_SHA256:
            raise ValueError(f"{path} does not match the recorded SHA-256 ({sha})")
    root = ET.parse(gzip.open(path)).getroot()
    ev_rows: list[dict] = []
    case_rows: list[dict] = []
    for trace in root.findall("trace"):
        attrs = {a.get("key"): a.get("value") for a in trace if a.tag != "event"}
        case_id = attrs["concept:name"]
        case_rows.append({
            "case_id": case_id,
            "declaration_number": attrs.get("DeclarationNumber"),
            "budget_number": attrs.get("BudgetNumber"),
            "amount": float(attrs["Amount"]),
        })
        for pos, e in enumerate(trace.findall("event")):
            d = {a.get("key"): a.get("value") for a in e}
            ev_rows.append({
                "case_id": case_id,
                "file_pos": pos,
                "event_id": d.get("id"),
                "activity": d["concept:name"],
                "timestamp_raw": d["time:timestamp"],
                "resource": d.get("org:resource"),
                "role": d.get("org:role"),
            })
    events = pd.DataFrame(ev_rows)
    events["ts_utc"] = pd.to_datetime(events["timestamp_raw"], utc=True)
    events["ts_local"] = events["ts_utc"].dt.tz_convert(LOCAL_TZ)
    events = events.sort_values(["case_id", "ts_utc", "file_pos"], kind="mergesort").reset_index(drop=True)
    events["seq"] = events.groupby("case_id").cumcount()
    cases = pd.DataFrame(case_rows)
    return Bpic2020Log(events=events, cases=cases)


def to_pm4py(events: pd.DataFrame) -> pd.DataFrame:
    """The event table in PM4Py's column convention, timestamps in UTC."""
    df = pd.DataFrame({
        "case:concept:name": events["case_id"],
        "concept:name": events["activity"],
        "time:timestamp": events["ts_utc"],
        "org:role": events["role"],
        "org:resource": events["resource"],
    })
    return df
