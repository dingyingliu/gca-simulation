# Old names and new names

The code was developed in a private repository and given clearer names for this public release. The recorded results (reports, evidence records, run records, result files) were produced before the renames and keep the old names exactly as they were written. This list lets anyone match the two.

Nothing that the results depend on changed: the frozen data files are byte for byte the same, with the SHA-256 fingerprints the results record, and the renamed code produces the same simulation output (checked by fingerprint of the raw result array).

## Code

| Old name (in recorded results) | New name |
|---|---|
| `gca_sim/quotation/` | `gca_sim/simulator/` |
| `gca_sim/quotation/truth.py` | `gca_sim/simulator/ground_truth.py` |
| `gca_sim/quotation/streams.py` | `gca_sim/simulator/random_streams.py` |
| `gca_sim/quotation/baseline.py` | `gca_sim/simulator/independent_errors.py` |
| `gca_sim/quotation/decisions.py`, `designs.py`, `engine.py`, `observations.py`, `params.py` | the same file names, in `gca_sim/simulator/` |
| `gca_sim/prototype/` | `gca_sim/demo_replica/` |
| `gca_sim/logs/` | `gca_sim/process_logs/` |
| `gca_sim/evidence.py` | unchanged |

## Data

| Old name | New name |
|---|---|
| `specs/quotation_cases/` | `specs/simulated_weeks/` (the nine files inside keep their names: `W0` is the demonstration's week, `G1` to `G4` the development weeks, `H1` to `H4` the held-out weeks) |
| `specs/bpic2020_declarations.workflow.json` | unchanged |
| `evidence/schema.json`, `evidence/assumptions.yaml` | unchanged |

## Tests

| Old name | New name |
|---|---|
| `tests/test_quotation_access.py` | `tests/test_simulator_access.py` |
| `tests/test_quotation_constraints.py` | `tests/test_simulator_constraints.py` |
| `tests/test_quotation_streams.py` | `tests/test_simulator_random_streams.py` |
| `tests/test_quotation_trace.py` | `tests/test_simulator_trace.py` |
| `tests/test_prototype_port.py` | `tests/test_demo_replica.py` |
| `tests/golden/make_prototype_golden.py` | `tests/golden/make_demo_golden.py` |
| `tests/golden/prototype/` | `tests/golden/demo_replica/` (the golden files are unchanged; the manifest's script path names the new folder) |

## What was deliberately not renamed

- **`gca_sim/pilot/`, the agent experiment.** The experiment's run records and its estimates are bound to four of its files (`prompting.py`, `scoring.py`, `analysis.py`, `records.py`) by SHA-256 fingerprints of their contents. Renaming the folder or editing those files would change the fingerprints, and the analysis would then refuse to re-analyse the published records. So the whole package is published byte for byte as it was run, including its original comments.
- **`evidence/assumptions.yaml`.** The simulator's results and its frozen conclusions record this file's fingerprint, so it is published unchanged.
- **The experiment folders** (`experiments/agent_pilot/`, `experiments/e3_bpic2020/`, `experiments/e4_quotation/`, `experiments/e6_taubench/`). The recorded results and the agent experiment's code refer to these paths. Four kinds of file in them are published byte for byte as they were used, because the results are bound to them or because they were fixed before the runs: the experiment plan (`experiments/agent_pilot_plan.md`), the experiment's settings (`experiments/agent_pilot/config.yaml`), the task bank (`experiments/agent_pilot/task_bank/`) and the held-out weeks' fingerprints (`experiments/e4_quotation/heldout_manifest.json`).
- **The evidence record identifiers** such as `quotation.e_visible`. They are names of records, not of code, and the results cite them.
