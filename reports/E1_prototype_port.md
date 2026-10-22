# E1. The walkthrough model ported to Python as a regression baseline

Claude Code (build), 2026-10-02 (UTC). Early result. Everything in this report is **illustrative**: the case, the quotes, the capacities, the delays and the agent's behaviour were invented for the walkthrough demonstration. Nothing here is evidence about real quotation work.

## Question

Can we reproduce the walkthrough's `simulate(d)` exactly in Python, so that later work has a fixed baseline to regress against, and which of its assumptions must not be carried into the research model?

## Data

The `<script>` block of `One_Week_in_the_Course.html` (SHA-256 9fcd4c02…6bb5), copied byte for byte to `gca_sim/prototype/original/walkthrough_script.js`. Twenty invented quotes (Q01 to Q20) in three invented markets, three named designs (`PRESET`), reviewer capacities, delays, a queue penalty and the bypass rule.

## Method

1. **Golden outputs from the original code.** `tests/golden/make_prototype_golden.py` evaluates, unchanged, the case data and `simulate()` (everything before the UI marker) plus the pure helpers `r1()` and `summary()`, and calls `simulate()` on each preset. Output: `tests/golden/prototype/golden_<preset>.json`, with a manifest of SHA-256 hashes. The files were first generated in V8 through mini-racer, because Node is not installed system-wide. After review round 1 they were regenerated with Node v24.19.0 (the copy bundled with Codex's runtime) and cross-checked against V8: both engines give byte-identical files, unchanged from the first generation.
2. **A labelled variant.** The same code with the single line `const BYPASS=3;` replaced by `const BYPASS=Infinity;` (`variant_nobypass_<preset>.json`). This is not the original. It checks the port's default, bypass off, against the original logic.
3. **The port.** `gca_sim/prototype/case.py` (the case, transcribed) and `gca_sim/prototype/walkthrough.py` (`simulate`, `summary`, and the helpers `canSee`, `agentCanCheck`, JavaScript rounding and number formatting). It keeps the JavaScript field names and returns the same structure, including every trace line, the accountability text and the summary metrics, and even leaves `err` unset where the original leaves it undefined.
4. **Regression test.** `tests/test_prototype_port.py` compares the whole output (all twenty rows with their traces, and the summary metrics and text) for each preset. Eight tests: three against the original, three against the variant, one that the bypass is off by default, one that the golden files match their manifest. A one-character change to a trace line, a renamed market or a 1e-12 change to the average all make the comparison fail.

## Results

All eight tests pass (`.venv/Scripts/python.exe -m pytest`, commit in the lab log).

The regression targets, all **illustrative**:

| Design | Bypass assumption | Wrong quotes at customers | Average days to customer | Quotes sent to the leads (12 slots) | Head-office escalations (3 slots) | No approval recorded |
|---|---|---|---|---|---|---|
| Review every quote | on, 3 days (as published) | 4 (Q07, Q12, Q17, Q18) | 1.7 | 20 | 0 | 5 (Q16 to Q20) |
| Review every quote | off | 2 (Q07, Q12) | 2.1 | 20 | 0 | 0 |
| Release within shared limits | on or off | 2 (Q09, Q14) | 0.8 | 0 | 3 | 0 |
| Refer local exceptions | on or off | 1 (Q09) | 1.0 (0.95 before rounding) | 6 | 3 | 0 |

The published walkthrough's worked example ("five waited past the three-day point … and four were still wrong at the customer") is reproduced exactly.

## The bypass rule is a named assumption, off by default

The walkthrough assumes that after three days in a review queue the sales team sends a quote itself, unreviewed and with no approval recorded. The case memo (01, "Evidence and simulation boundary") says: "Do not assume that staff evade controls when review becomes slower."

In the port this is `PrototypeAssumptions.bypass_after_days`. The default is `None`, meaning a waiting quote is reviewed late rather than sent round the review. Only the golden test passes `WALKTHROUGH_ASSUMPTIONS` (3 days) to reproduce the published page.

It matters for the comparison the walkthrough teaches. With the bypass on, "Review every quote" shows 4 wrong quotes and 5 without approval, and the worked example rejects it for that reason. With the bypass off, the same design shows 2 wrong quotes, the same 2 as "Release within shared limits", and is slower (2.1 days against 0.8). So the walkthrough's case against reviewing everything rests partly on the bypass assumption. The other two designs never reach the threshold and are unchanged. This is a property of an invented model, not a finding about organisations, but it is exactly the kind of assumption the research model must state and vary rather than build in.

## What the port does and does not show

It shows that the Python code reproduces the demonstration exactly, so later changes can be checked against it.

It does not show anything about real quotation work, and it is not research validation. We have not produced design-space tables from it and will not.

Properties of the prototype that the research model (E4) must not inherit. None of these is a defect in a demonstration; each is a reason to keep the port separate.

1. **Routing on the true category.** `route = d[q.kind]` (HTML line 480, port `walkthrough.py`) uses the quote's true kind, so the program already knows which quotes are exceptions. In E4, routing acts only on what a role can observe, and recognising an exception can fail.
2. **Detection is a fixed property of each quote.** Whether a reviewer catches an error is hard-coded per quote (`catch: {regional, ho, other}`), not derived from what the reviewer can see, their expertise or their workload. The technical memo says detection depends on information, expertise and workload.
3. **The agent is deterministic.** Each quote is drafted wrong or right by fixture (`draftWrong`), with one fixed profile. No error rates, no randomness, no shared-context mechanism.
4. **The queue counts position in the week, not time.** A quote's wait is `(position − capacity) × 1.5` days, whatever day it arrives and whenever earlier reviews finish. Capacity is per week. The trace text can therefore read "Quote 6 of 4 this reviewer can take this week".
5. **Accountability text for bypassed quotes** says "three-day practice". The port derives the word from the assumption's value so the text stays true if the value changes.

## Evidence records created

None. The prototype's values are illustrative and are not evidence. The research model's parameters get their own records in E3 and E4.

## Departures from the plan

- Golden outputs come from running the original code, not from extraction by hand: first in V8 (mini-racer), then cross-checked with Node v24.19.0 from Codex's bundled runtime (review round 1, Codex R1.1). Neither engine was installed system-wide.
- Added a labelled variant run with the bypass disabled, so the port's default path is also checked against the original logic.

## Next steps

- E2: the controlled agent pilot plan.
- E4 builds the research model separately and will include a test that it does not import `gca_sim.prototype`.
