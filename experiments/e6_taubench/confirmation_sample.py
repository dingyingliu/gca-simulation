"""Draw the stratified, in-context sample for the confirmation check.

Strata per model: database writes whose latest preceding customer message contains the word "yes" (Y) and
those whose message does not (N). 20 random writes from Y and 30 from N per model, seed 20261002. Each item
keeps the agent's preceding message (the proposal), the customer's reply and the write's arguments, keyed by
the file's SHA-256 and the task, trial, message and tool-call indices.

    .venv/Scripts/python.exe experiments/e6_taubench/confirmation_sample.py
"""

import hashlib
import importlib.util
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "third_party" / "tau-bench" / "historical_trajectories"
OUT = ROOT / "reports" / "E6" / "confirmation_sample.json"
WRITE = {"cancel_pending_order", "modify_pending_order_items", "modify_pending_order_address",
         "modify_pending_order_payment", "return_delivered_order_items", "exchange_delivered_order_items",
         "modify_user_address"}
YES = re.compile(r"\byes\b", re.I)
SIZES = {"Y": 20, "N": 30}
FILES = ("gpt-4o-retail.json", "sonnet-35-new-retail.json")
_spec = importlib.util.spec_from_file_location("check_taubench", Path(__file__).with_name("check_taubench.py"))
_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_check)
EXPECTED_SHA = _check.EXPECTED_SHA  # the pinned hashes in data/SOURCES.md


def writes(fn: str):
    raw = (REPO / fn).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != EXPECTED_SHA[fn]:
        raise SystemExit(f"{fn} sha256 {sha} differs from the pinned {EXPECTED_SHA[fn]}")
    runs = json.loads(raw.decode("utf-8"))
    for r in runs:
        traj = r["traj"]
        for i, m in enumerate(traj):
            if m.get("role") != "assistant" or not m.get("tool_calls"):
                continue
            for j, tc in enumerate(m["tool_calls"]):
                if tc["function"]["name"] not in WRITE:
                    continue
                ui = next((k for k in range(i - 1, -1, -1) if traj[k].get("role") == "user"), None)
                reply = traj[ui]["content"] if ui is not None else ""
                pi = next((k for k in range(ui - 1, -1, -1) if traj[k].get("role") == "assistant"
                           and traj[k].get("content")), None) if ui is not None else None
                yield {"key": f"{sha[:12]}:task{r['task_id']}:trial{r['trial']}:msg{i}:call{j}",
                       "file_sha256": sha, "task": r["task_id"], "trial": r["trial"], "message_index": i,
                       "tool_call_index": j, "write": tc["function"]["name"],
                       "arguments": tc["function"].get("arguments"),
                       "proposal": traj[pi]["content"] if pi is not None else "",
                       "customer_reply": reply or "", "stratum": "Y" if YES.search(reply or "") else "N"}


def main():
    out = {"design": "stratified: writes with and without 'yes' in the latest customer message",
           "sizes": SIZES, "seed": 20261002, "models": {}}
    for fn in FILES:
        items = list(writes(fn))
        rng = random.Random(20261002)
        strata = {s: [it for it in items if it["stratum"] == s] for s in ("Y", "N")}
        sample = {s: rng.sample(strata[s], min(SIZES[s], len(strata[s]))) for s in ("Y", "N")}
        out["models"][fn] = {"population": {s: len(v) for s, v in strata.items()}, "sample": sample}
    OUT.write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    for fn, m in out["models"].items():
        print("=====", fn, m["population"])
        for s in ("Y", "N"):
            for k, it in enumerate(m["sample"][s]):
                prop = it["proposal"].replace("\n", " ")[-260:]
                print(f"[{s}{k:02d}] {it['write']} {str(it['arguments'])[:90]}")
                print(f"   AGENT: ...{prop}")
                print(f"   CUST : {it['customer_reply'][:160]!r}")


if __name__ == "__main__":
    main()
