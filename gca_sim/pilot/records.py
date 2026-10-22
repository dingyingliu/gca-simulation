"""Run records of the pilot: the configuration, the planned task runs, what the records say about each of them,
and the fingerprints that bind records and checks to the experiment's inputs.

Every planned task run ends in one of two finished states: **valid** (a recorded answer that fits the schema) or
**missing** (all its attempts used without one). Anything else is unfinished (review round 10, Codex R10.2 and
R10.3).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import yaml

from gca_sim.pilot import prompting
from gca_sim.pilot.prompting import CELLS, OUTPUT_SCHEMA, SYSTEM_PROMPT, sha256_text

HERE = Path(__file__).resolve().parent
REQUIRED_FOR_PAID = ("model", "input_usd_per_million_tokens", "output_usd_per_million_tokens", "cap_usd")
# the settings that decide what is asked of the model and how many times
REQUEST_KEYS = ("provider", "base_url", "model", "max_tokens", "reasoning_effort", "temperature", "top_p",
                "structured_outputs", "provider_order", "max_attempts", "replicates")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_config(path: Path, paid: bool) -> dict:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    if paid:
        missing = [k for k in REQUIRED_FOR_PAID if cfg.get(k) is None]
        if missing:
            raise SystemExit(f"{path.name} is not complete: {', '.join(missing)} must be set by Dingying before any "
                             "paid run")
    # a price of 0 is a real price (a free model); only a missing price falls back, and only for dry runs
    price_in, price_out = cfg.get("input_usd_per_million_tokens"), cfg.get("output_usd_per_million_tokens")
    cfg["input_usd_per_token"] = (1.0 if price_in is None else price_in) / 1e6
    cfg["output_usd_per_token"] = (5.0 if price_out is None else price_out) / 1e6
    return cfg


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def request_inputs(config: dict, bank_manifest_sha256: str) -> dict:
    """Everything that decides what the model is asked: the prompt-building code, the system prompt, the output
    schema, the task bank and the request settings (review round 10, Codex R10.8)."""
    return {"prompting_code_sha256": _file_sha(Path(prompting.__file__)),
            "system_prompt_sha256": sha256_text(SYSTEM_PROMPT), "output_schema_sha256": _sha(OUTPUT_SCHEMA),
            "bank_manifest_sha256": bank_manifest_sha256,
            "request_settings": {k: config.get(k) for k in REQUEST_KEYS}}


def request_fingerprint(config: dict, bank_manifest_sha256: str) -> str:
    return _sha(request_inputs(config, bank_manifest_sha256))


def scoring_fingerprint() -> str:
    """The scorer and the analysis, as code."""
    return _sha({name: _file_sha(HERE / name) for name in ("scoring.py", "analysis.py", "records.py")})


def estimates_gate(estimates: dict | None, inputs: str, run_sha256: str) -> None:
    """Refuse estimates that were not made by the current scorer, from the current inputs and from this run file.
    Used before the held-out diagnostic (review round 11, Claude R11.3) and before the estimates are put into the
    quotation model (review round 12, Codex R12.5). A mismatch needs the existing records analysed again, never a
    new model run."""
    if estimates is None:
        raise SystemExit("the development estimates do not exist; run analyse_pilot.py --development first")
    if estimates.get("scoring_inputs_sha256") != scoring_fingerprint():
        raise SystemExit("the scorer or the analysis changed after the development estimates were written; "
                         "run analyse_pilot.py --development again first")
    if estimates.get("request_inputs_sha256") != inputs:
        raise SystemExit("the development estimates were made with other experiment inputs than the current ones")
    if estimates.get("run_sha256") != run_sha256:
        raise SystemExit("the development run file is not the one the development estimates were computed from")


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def task_key(r: dict) -> tuple:
    return (r["group"], r["cell"], r["replicate"], r["order"])


def task_states(records: list[dict]) -> dict[tuple, dict]:
    """What the records say about each task run: its valid answer if any, whether its attempts are used up, how
    many attempts and requests it has had, and the prompts it was sent."""
    states: dict[tuple, dict] = {}
    for r in records:
        st = states.setdefault(task_key(r), {"valid": None, "exhausted": False, "attempts_used": 0, "requests": 0,
                                             "prompts": set()})
        st["requests"] += 1
        st["prompts"].add(r["user_sha256"])
        if r.get("parsed") is not None:
            if st["valid"] is not None:
                raise SystemExit(f"{task_key(r)} has two valid answers on record")
            st["valid"] = r
        elif not r.get("rate_limited"):
            st["attempts_used"] = max(st["attempts_used"], r["attempt"])
            st["exhausted"] = st["exhausted"] or bool(r.get("final"))
    return states


def final_outputs(records: list[dict]) -> dict[tuple, dict]:
    """The valid recorded answer of each task run that has one."""
    return {k: st["valid"] for k, st in task_states(records).items() if st["valid"] is not None}


def group_runs(bank: dict, split: str, replicates: int) -> list[tuple]:
    return [(gid, context, visibility, rep) for gid, g in bank.items() if g["split"] == split
            for context, visibility in CELLS for rep in range(1, replicates + 1)]


def planned_keys(bank: dict, split: str, replicates: int) -> list[tuple]:
    """Every task run the plan calls for in a split."""
    return [(gid, f"{context}.{visibility}", rep, task["order"])
            for gid, context, visibility, rep in group_runs(bank, split, replicates) for task in bank[gid]["tasks"]]


def split_state(bank: dict, split: str, replicates: int, records: list[dict]) -> dict:
    """Planned task runs sorted into valid, missing (attempts used up) and unfinished; anything else is refused."""
    planned = planned_keys(bank, split, replicates)
    states = task_states(records)
    unexpected = sorted(set(states) - set(planned))
    if unexpected:
        raise SystemExit(f"records hold task runs the plan does not: {unexpected[:5]}")
    valid = [k for k in planned if k in states and states[k]["valid"] is not None]
    missing = [k for k in planned if k in states and states[k]["valid"] is None and states[k]["exhausted"]]
    finished = set(valid) | set(missing)
    unfinished = [k for k in planned if k not in finished]
    return {"planned": len(planned), "valid": valid, "missing": missing, "unfinished": unfinished,
            "complete": not unfinished}
