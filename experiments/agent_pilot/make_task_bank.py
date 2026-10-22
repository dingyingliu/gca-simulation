"""Generate the pilot's task bank and its manifest (plan sections 3 and 5). Run once, before any model run.

    .venv/Scripts/python.exe experiments/agent_pilot/make_task_bank.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim.pilot import bank  # noqa: E402

if __name__ == "__main__":
    manifest = bank.write_bank(Path(__file__).resolve().parent / "task_bank")
    for split, groups in manifest["splits"].items():
        print(split, groups)
