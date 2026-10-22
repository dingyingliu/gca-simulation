"""Run one split of the agent pilot (plan section 8).

    .venv/Scripts/python.exe experiments/agent_pilot/run_pilot.py --check-key                 # free: the key's limit and usage
    .venv/Scripts/python.exe experiments/agent_pilot/run_pilot.py --split setup --label 2     # the set-up group
    .venv/Scripts/python.exe experiments/agent_pilot/run_pilot.py --split development         # after the set-up checks pass
    .venv/Scripts/python.exe experiments/agent_pilot/run_pilot.py --split heldout             # once, after development
    .venv/Scripts/python.exe experiments/agent_pilot/run_pilot.py --split setup --fake        # no model, no cost

A model run needs the model, its prices and the spending cap in config.yaml, a clean git tree for the pilot's
code, plan, config and task bank, and the API key in the environment or in the git-ignored .env file. Development
also needs set-up checks that passed with the same experiment inputs and the same scorer. Progress is printed as
counts only: answers are never shown, so the held-out split is not read before its one evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402
from gca_sim.pilot import bank as bank_mod  # noqa: E402
from gca_sim.pilot.client import FakeClient, OpenRouterClient, load_key  # noqa: E402
from gca_sim.pilot.guard import SpendingGuard  # noqa: E402
from gca_sim.pilot.records import (load_config, read_records, request_fingerprint, scoring_fingerprint,  # noqa: E402
                                   split_state)
from gca_sim.pilot.runner import run_split  # noqa: E402

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
CODE_PATHS = ["gca_sim/pilot", "experiments/agent_pilot/config.yaml", "experiments/agent_pilot/task_bank",
              "experiments/agent_pilot/run_pilot.py", "experiments/agent_pilot_plan.md"]
SETUP_CHECKS = ROOT / "reports" / "E5" / "setup_checks.json"


def inputs_fingerprint(config: dict) -> str:
    manifest = hashlib.sha256((HERE / "task_bank" / "manifest.json").read_bytes()).hexdigest()
    return request_fingerprint(config, manifest)


def setup_gate(inputs: str, checks_path: Path = SETUP_CHECKS) -> None:
    """Development needs set-up checks that passed with these experiment inputs and this scorer."""
    checks = json.loads(checks_path.read_text(encoding="utf-8")) if checks_path.exists() else None
    if not checks or not checks.get("all_pass"):
        raise SystemExit("the set-up checks P1 to P3 have not passed (analyse_pilot.py --setup-checks)")
    if checks.get("request_inputs_sha256") != inputs:
        raise SystemExit("the set-up checks were made with other experiment inputs (prompt, schema, task bank or "
                         "request settings); rerun the set-up group under a new label and check it again")
    if checks.get("scoring_inputs_sha256") != scoring_fingerprint():
        raise SystemExit("the scorer or the analysis changed after the set-up checks; apply the checks again")


def launch_gate(split: str, bank: dict, config: dict, inputs: str, runs: Path = RUNS,
                checks_path: Path = SETUP_CHECKS) -> None:
    """Everything a model run of this split needs, checked before a client exists or a request is sent.

    Development needs set-up checks that passed with these inputs and this scorer. The held-out split runs once,
    so it needs the same, a finished development run, and development records that were all made with the
    current inputs: a change of prompt, task bank or request settings after development must be found here, not
    by the analysis after the held-out groups have been used."""
    if split in ("development", "heldout"):
        setup_gate(inputs, checks_path)
    if split == "heldout":
        records = read_records(runs / "development.jsonl")
        other = {r.get("inputs_sha256") for r in records} - {inputs}
        if other:
            raise SystemExit("the development run was made with other experiment inputs than the current ones "
                             "(prompt, schema, task bank or request settings); the held-out split is not started")
        dev = split_state(bank, "development", config["replicates"]["development"], records)
        if not dev["complete"]:
            raise SystemExit("the development run is not finished; the held-out split runs once, at the end")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=("setup", "development", "heldout"))
    ap.add_argument("--fake", action="store_true", help="dry run with the fake agent: no model, no cost")
    ap.add_argument("--label", default="1", help="set-up run label; a rerun after a change of inputs gets a new label")
    ap.add_argument("--check-key", action="store_true", help="print the key's limit and usage; costs nothing")
    args = ap.parse_args()

    config = load_config(HERE / "config.yaml", paid=not args.fake)
    if args.check_key:
        info = OpenRouterClient(load_key(config["key_env"]), config).key_info()
        print(json.dumps({k: info.get(k) for k in ("limit", "limit_remaining", "usage", "is_free_tier",
                                                   "free_model_daily_requests")}))
        return
    if not args.split:
        ap.error("--split is required")
    bank = bank_mod.load_bank(HERE / "task_bank")
    code = evidence.git_state(CODE_PATHS)
    inputs = inputs_fingerprint(config)
    folder = RUNS / "fake" if args.fake else RUNS
    name = f"setup_{args.label}" if args.split == "setup" else args.split
    path = folder / f"{name}.jsonl"

    if args.fake:
        client = FakeClient(config)
        guard = SpendingGuard(1e9, config["input_usd_per_token"], config["output_usd_per_token"])
    else:
        if code["code_dirty"]:
            raise SystemExit("the pilot's code, plan, config or task bank has uncommitted changes; commit them first")
        launch_gate(args.split, bank, config, inputs)
        client = OpenRouterClient(load_key(config["key_env"]), config)
        guard = SpendingGuard(config["cap_usd"], config["input_usd_per_token"], config["output_usd_per_token"],
                              ledger=RUNS / "ledger.jsonl")
        print(f"model {config['model']}, cap ${config['cap_usd']}, spent so far ${guard.spent:.4f}", flush=True)
    run_split(bank, args.split, client=client, guard=guard, path=path, config=config, code=code, run_id=name,
              inputs_sha256=inputs)


if __name__ == "__main__":
    main()
