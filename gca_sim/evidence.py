"""Evidence records: build, validate, write and load. Every number the simulator uses has a record saying where it
comes from, what it measures and whether it is observed, fitted, assumed or illustrative."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

import jsonschema
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evidence" / "schema.json"
RECORDS_DIR = ROOT / "evidence" / "records"


def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


class GitStateError(RuntimeError):
    pass


def git_state(paths: list[str] | None = None) -> dict:
    """Current commit, and whether the given paths (or the whole tree) have uncommitted changes.

    Raises GitStateError if either git command fails, so a failure can never be recorded as a
    clean tree.
    """
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    commit = rev.stdout.strip()
    if rev.returncode != 0 or not commit:
        raise GitStateError(f"git rev-parse failed ({rev.returncode}): {rev.stderr.strip()}")
    status = subprocess.run(["git", "status", "--porcelain", "--", *(paths or [])], cwd=ROOT, capture_output=True,
                            text=True)
    if status.returncode != 0:
        raise GitStateError(f"git status failed ({status.returncode}): {status.stderr.strip()}")
    return {"code_commit": commit, "code_dirty": bool(status.stdout.strip())}


def array_sha256(data) -> str:
    """Fingerprint of a raw result array: its shape, type and bytes. A saved .npz file is not byte-stable, so a
    cache is checked by this instead."""
    a = np.ascontiguousarray(data)
    return hashlib.sha256(f"{a.shape}|{a.dtype.str}|".encode() + a.tobytes()).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def validate(record: dict) -> None:
    jsonschema.validate(record, schema())


def write(record: dict, directory: Path = RECORDS_DIR) -> Path:
    validate(record)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{record['id']}.json"
    path.write_bytes((json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))  # LF on every OS
    return path


def load_all(directory: Path = RECORDS_DIR) -> dict[str, dict]:
    out = {}
    for p in sorted(directory.glob("*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        out[rec["id"]] = rec
    return out
