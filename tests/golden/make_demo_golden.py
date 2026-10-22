"""Regenerate the E1 golden outputs by running the original walkthrough JavaScript.

The JavaScript is the verbatim <script> block of One_Week_in_the_Course.html, kept in
gca_sim/demo_replica/original/walkthrough_script.js. The harness takes, unchanged, the case
data and simulate() (everything in the closure before the "---------- UI ----------"
marker) and the two pure helpers r1() and summary() from the UI section, then calls
simulate() for each of the three presets. No DOM is needed for those functions.

Two engines can run it:

- Node, if one is given with --node or the GCA_NODE environment variable, or is on PATH.
  Without Node, mini-racer is used.
- mini-racer (V8, pinned in pyproject.toml) otherwise.

--cross-check runs both and stops with an error unless every output is byte-identical.

Two sets are written:

- golden_<preset>.json: the original code exactly as published (BYPASS=3).
- variant_nobypass_<preset>.json: the same code with the single line
  `const BYPASS=3;` replaced by `const BYPASS=Infinity;`, so no quote is ever sent round
  the review. This is a labelled variant, not the original. It cross-checks the port's
  default (bypass assumption off) against the original logic.

Run from the project root:
    .venv/Scripts/python.exe tests/golden/make_demo_golden.py [--engine auto|node|mini-racer]
        [--node PATH] [--cross-check]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "gca_sim" / "demo_replica" / "original" / "walkthrough_script.js"
OUT = Path(__file__).resolve().parent / "demo_replica"
SCRIPT_SHA256 = "53cca498ebdea69261f20335c25d207477f4db729d860d1e698d195141c4fe3e"
SOURCE_HTML_SHA256 = "9fcd4c02491d0714ba99a3424665899acbec487a9431629c5900d5a9d18c6bb5"
PRESETS = ("review", "limits", "local")
VARIANTS = (("golden", None), ("variant_nobypass", "Infinity"))


def build_harness(src: str, bypass_override: str | None) -> str:
    body_start = src.index("(function(){") + len("(function(){")
    ui_marker = src.index("// ---------- UI ----------")
    core = src[body_start:ui_marker]
    r1 = re.search(r"^[ \t]*function r1\(x\)\{.*\}[ \t]*$", src, re.M).group(0)
    summary = src[src.index("  function summary(o){") : src.index("  function deltaText(o){")]
    if bypass_override is not None:
        old = "const BYPASS=3;"
        if core.count(old) != 1:
            raise SystemExit("expected exactly one BYPASS declaration")
        core = core.replace(old, f"const BYPASS={bypass_override};")
    run = (
        "  globalThis.__run=function(k){const o=simulate(PRESET[k]);"
        "return JSON.stringify({preset:k,name:PNAME[k],design:PRESET[k],result:o,summary:summary(o)});};\n"
    )
    return "(function(){\n" + core + "\n" + r1 + "\n" + summary + run + "})();\n"


def find_node(explicit: str | None) -> str | None:
    for candidate in (explicit, os.environ.get("GCA_NODE"), shutil.which("node")):
        if candidate and Path(candidate).exists():
            return candidate
    return None


def run_node(node: str, harness: str) -> dict[str, str]:
    js = harness + "".join(f"process.stdout.write(__run({json.dumps(k)})+'\\n');\n" for k in PRESETS)
    proc = subprocess.run([node, "-"], input=js.encode("utf-8"), capture_output=True, check=True)
    lines = proc.stdout.decode("utf-8").splitlines()
    if len(lines) != len(PRESETS):
        raise RuntimeError(f"node returned {len(lines)} lines, expected {len(PRESETS)}")
    return dict(zip(PRESETS, lines))


def run_mini_racer(harness: str) -> dict[str, str]:
    from py_mini_racer import MiniRacer

    with MiniRacer() as ctx:  # closing the context lets the interpreter exit normally
        ctx.eval(harness)
        return {k: ctx.eval(f"__run({json.dumps(k)})") for k in PRESETS}


def engine_version(engine: str, node: str | None) -> str:
    if engine == "node":
        v = subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip()
        return f"Node {v}"
    return f"V8 via mini-racer {importlib.metadata.version('mini-racer')}"


def render(raw: dict[str, str], override: str | None) -> dict[str, bytes]:
    out = {}
    for k, line in raw.items():
        payload = json.loads(line)
        payload["source"] = "original" if override is None else "variant: const BYPASS=Infinity"
        out[k] = (json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    return out


def generate(engine: str, node: str | None, src: str) -> dict[str, bytes]:
    files = {}
    for label, override in VARIANTS:
        harness = build_harness(src, override)
        raw = run_node(node, harness) if engine == "node" else run_mini_racer(harness)
        for k, data in render(raw, override).items():
            files[f"{label}_{k}.json"] = data
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["auto", "node", "mini-racer"], default="auto")
    ap.add_argument("--node", help="path to a Node executable (or set GCA_NODE)")
    ap.add_argument("--cross-check", action="store_true", help="run both engines and require identical outputs")
    args = ap.parse_args()

    raw = SCRIPT.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != SCRIPT_SHA256:
        raise SystemExit(f"walkthrough_script.js changed: sha256 {sha}")
    src = raw.decode("utf-8")

    node = find_node(args.node)
    engine = args.engine
    if engine == "auto":
        engine = "node" if node else "mini-racer"
    if engine == "node" and not node:
        raise SystemExit("no Node executable found; pass --node or set GCA_NODE")

    files = generate(engine, node, src)
    engines = [engine_version(engine, node)]
    cross = None
    if args.cross_check:
        other = "mini-racer" if engine == "node" else "node"
        if other == "node" and not node:
            raise SystemExit("--cross-check needs a Node executable; pass --node or set GCA_NODE")
        other_files = generate(other, node, src)
        differing = sorted(n for n in files if files[n] != other_files[n])
        if differing:
            raise SystemExit(f"engines disagree on: {', '.join(differing)}")
        engines.append(engine_version(other, node))
        cross = "byte-identical outputs from both engines"

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "engine": engines[0],
        "cross_check": {"engines": engines, "result": cross} if cross else None,
        "script": "gca_sim/demo_replica/original/walkthrough_script.js",
        "script_sha256": SCRIPT_SHA256,
        "source_html": "One_Week_in_the_Course.html",
        "source_html_sha256": SOURCE_HTML_SHA256,
        "files": {},
    }
    for name, data in files.items():
        (OUT / name).write_bytes(data)
        manifest["files"][name] = hashlib.sha256(data).hexdigest()
        print(name, json.loads(data)["summary"])
    (OUT / "MANIFEST.json").write_bytes((json.dumps(manifest, indent=1) + "\n").encode("utf-8"))
    if cross:
        print(cross, "|", " and ".join(engines))


if __name__ == "__main__":
    main()
