"""Run one split of the pilot: every group in every cell and replicate, six tasks in order, carrying the notes
store forward, one JSON line per request (plan section 8).

A run can be interrupted and resumed. On a restart, a task run with a valid recorded answer is replayed from its
record so that its note rebuilds the store, a task run whose attempts are used up stays missing and writes no
note, and an unfinished one continues with the attempts it has left. Nothing finished is ever requested again
(review round 10, Codex R10.2).

Every record carries a fingerprint of the experiment's inputs. A run refuses to add to records made with other
inputs (review round 10, Codex R10.8).
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gca_sim.pilot.client import ClientError, RateLimited
from gca_sim.pilot.guard import CapExceeded, SpendingGuard, input_token_upper_bound
from gca_sim.pilot.prompting import SYSTEM_PROMPT, NotesStore, clip_note, exposure, sha256_text, user_message
from gca_sim.pilot.records import group_runs, read_records, split_state, task_states, utc_now
from gca_sim.pilot.scoring import parse_output


class RunStopped(RuntimeError):
    """The run cannot go on now (the spending cap or the provider's rate limit) and can be resumed later."""


class Recorder:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict) -> None:
        with self._lock, open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_group(group: dict, context: str, visibility: str, replicate: int, *, split: str, run_id: str, client,
              guard: SpendingGuard, recorder: Recorder, states: dict, config: dict, code: dict, inputs_sha256: str,
              stop: threading.Event) -> int:
    """One run of one group in one cell. Returns the number of requests sent."""
    store = NotesStore(group, context)
    cell = f"{context}.{visibility}"
    sent = 0
    for task in group["tasks"]:
        view = store.view(task["region"])
        user = user_message(group, task, visibility, view)
        exp = exposure(task, visibility, view)
        key = (group["group"], cell, replicate, task["order"])
        st = states.get(key)
        if st is not None and st["prompts"] != {sha256_text(user)}:
            raise SystemExit(f"{key}: the recorded prompt differs from the one built now; the task bank, the prompt "
                             "or an earlier note has changed since the run started")
        output = None
        if st is not None and st["valid"] is not None:
            output = st["valid"]["parsed"]
        elif st is not None and st["exhausted"]:
            pass  # finished and missing: never requested again, and it writes no note
        else:
            first_attempt = (st["attempts_used"] if st else 0) + 1
            requests = st["requests"] if st else 0
            for attempt in range(first_attempt, config["max_attempts"] + 1):
                resp, waits = None, 0
                while resp is None:
                    if stop.is_set():
                        return sent
                    requests += 1
                    request_key = f"{run_id}|{group['group']}|{cell}|r{replicate}|T{task['order']}|q{requests}"
                    try:
                        guard.reserve(request_key, input_token_upper_bound(SYSTEM_PROMPT, user), config["max_tokens"])
                    except CapExceeded as e:
                        stop.set()
                        raise RunStopped(str(e)) from None
                    record = {
                        "run_id": run_id, "split": split, "fake": not client.paid, "provider": config["provider"],
                        "model_requested": config["model"] if client.paid else "fake-agent",
                        "inputs_sha256": inputs_sha256, "request_key": request_key,
                        "group": group["group"], "cell": cell, "context": context, "visibility": visibility,
                        "replicate": replicate, "order": task["order"], "task_id": task["task_id"],
                        "role": task["role"], "region": task["region"], "exposure": exp, "tools": [],
                        "attempt": attempt, "system_prompt": SYSTEM_PROMPT,
                        "system_sha256": sha256_text(SYSTEM_PROMPT), "user_message": user,
                        "user_sha256": sha256_text(user), "utc_sent": utc_now(),
                        "code_commit": code["code_commit"], "code_dirty": code["code_dirty"]}
                    sent += 1
                    try:
                        resp = client.complete(SYSTEM_PROMPT, user, meta={"task": task, "view": view, "exposure": exp,
                                                                          "request_key": request_key})
                    except RateLimited as e:
                        # nothing ran: wait and send again without using up one of the task's attempts
                        guard.forfeit(request_key)
                        recorder.write({**record, "utc_received": utc_now(), "error": str(e), "rate_limited": True,
                                        "parsed": None, "final": False})
                        if e.daily or waits >= config.get("max_rate_limit_waits", 20):
                            stop.set()
                            raise RunStopped(f"rate limit: {e}") from None
                        waits += 1
                        time.sleep(e.retry_after if e.retry_after is not None
                                   else config.get("rate_limit_wait_seconds", 30))
                    except ClientError as e:
                        guard.forfeit(request_key)
                        recorder.write({**record, "utc_received": utc_now(), "error": str(e), "parsed": None,
                                        "final": attempt == config["max_attempts"]})
                        break
                if resp is None:
                    continue
                usage = resp["usage"]
                if usage.get("prompt_tokens") is None or usage.get("completion_tokens") is None:
                    guard.forfeit(request_key)
                    cost_list = charged = None
                else:
                    cost_list = (usage["prompt_tokens"] * config["input_usd_per_token"]
                                 + usage["completion_tokens"] * config["output_usd_per_token"])
                    charged = max(cost_list, resp["cost_reported_usd"] or 0.0)
                    guard.settle(request_key, charged)
                parsed, problem = parse_output(resp["text"])
                stored, cut = clip_note(parsed["note"]) if parsed is not None else (None, None)
                recorder.write({**record, "utc_received": utc_now(), "error": None,
                                "model_reported": resp["model"], "host": resp.get("host"),
                                "request_parameters": resp["request_parameters"],
                                "request_id": resp["id"], "raw_response": resp["raw"],
                                "finish_reason": resp["finish_reason"], "refusal": resp["refusal"],
                                "usage": usage, "cost_list_usd": cost_list,
                                "cost_reported_usd": resp["cost_reported_usd"], "cost_charged_usd": charged,
                                "parsed": parsed, "parse_problem": problem, "note_stored": stored, "note_cut": cut,
                                "final": parsed is not None or attempt == config["max_attempts"]})
                if parsed is not None:
                    output = parsed
                    break
        if output is not None:
            note, _ = clip_note(output["note"])
            store.append(task["region"], task["day"], note, task["task_id"], task["customer"])
    return sent


def run_split(bank: dict, split: str, *, client, guard: SpendingGuard, path: Path, config: dict, code: dict,
              run_id: str, inputs_sha256: str, quiet: bool = False) -> dict:
    """Run, or finish, every group run of the split. Prints progress as counts only, never answers."""
    replicates = config["replicates"][split]
    records = read_records(path)
    other = {r.get("inputs_sha256") for r in records} - {inputs_sha256}
    if other:
        raise SystemExit(f"{path.name} holds records made with other experiment inputs (prompt, schema, task bank or "
                         "request settings); start a run under a new name")
    before = split_state(bank, split, replicates, records)
    states = task_states(records)
    recorder, stop = Recorder(path), threading.Event()
    runs = group_runs(bank, split, replicates)
    if not quiet:
        print(f"{split}: {len(runs)} group runs, {before['planned']} task runs planned, {len(before['valid'])} valid "
              f"and {len(before['missing'])} missing already recorded", flush=True)
    sent, failure = 0, None

    def one(run):
        gid, context, visibility, rep = run
        return run_group(bank[gid], context, visibility, rep, split=split, run_id=run_id, client=client, guard=guard,
                         recorder=recorder, states=states, config=config, code=code, inputs_sha256=inputs_sha256,
                         stop=stop)

    with ThreadPoolExecutor(max_workers=config.get("workers", 4)) as pool:
        futures = [pool.submit(one, r) for r in runs]
        for f in futures:
            try:
                sent += f.result()
            except RunStopped as e:
                failure = failure or str(e)
    after = split_state(bank, split, replicates, read_records(path))
    summary = {"split": split, "planned_task_runs": after["planned"], "valid_task_runs": len(after["valid"]),
               "missing_task_runs": len(after["missing"]), "unfinished_task_runs": len(after["unfinished"]),
               "complete": after["complete"], "requests_sent": sent, "spent_usd": round(guard.spent, 4),
               "cap_usd": guard.cap, "stopped": failure}
    if not quiet:
        print(json.dumps(summary), flush=True)
    return summary
