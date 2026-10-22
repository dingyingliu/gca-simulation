"""Write every E4 case to specs/simulated_weeks/ and record the held-out hashes.

Run once, before any comparison. The held-out weeks are then only read by
run_e4.py --heldout-final, which checks these hashes first.
"""

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim.simulator import ground_truth as truth  # noqa: E402

OUT = ROOT / "specs" / "simulated_weeks"
MANIFEST = Path(__file__).resolve().parent / "heldout_manifest.json"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    manifest = {"frozen_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "generator_commit": commit, "development": {}, "heldout": {}}
    for case in truth.development_cases() + truth.heldout_cases():
        fname = case.name.split()[0] + ".json"
        (OUT / fname).write_bytes((case.to_json() + "\n").encode("utf-8"))
        side = "heldout" if case.split == "heldout" else "development"
        manifest[side][fname] = {"name": case.name, "sha256": case.sha256(), "requests": len(case.requests)}
    MANIFEST.write_bytes((json.dumps(manifest, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
