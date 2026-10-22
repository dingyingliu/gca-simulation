# Tables of the agent pilot's estimates

Written by `experiments/agent_pilot/make_tables.py` from the result files in this folder. Counts are observed in the experiment; shares and intervals are fitted from them.

## Development groups

Task runs: 360 planned, 360 valid, 0 missing. Model: qwen/qwen3.8-27b:free. Generated 2026-10-03 13:56 UTC, commit 65525b4.

### Hosts and missing runs by condition

| Condition | Answers by host | Missing runs (Harm, Help, Own, Standard) |
|---|---|---|
| Shared notes, agreement not visible | ModelRun: 90 | 0, 0, 0, 0 |
| Isolated notes, agreement not visible | ModelRun: 90 | 0, 0, 0, 0 |
| Shared notes, agreement visible | ModelRun: 90 | 0, 0, 0, 0 |
| Isolated notes, agreement visible | ModelRun: 90 | 0, 0, 0, 0 |

### 1. Wrong terms released to the customer

Share of task runs (mean over tasks), with the count over valid runs and the 95% interval from the bootstrap over groups.

| Condition | Harm tasks | Help tasks | Own tasks | Standard tasks |
|---|---|---|---|---|
| Shared notes, agreement not visible | 23% (7 of 30; 3% to 47%) | 0% (0 of 15; 0% to 0%) | 13% (2 of 15; 0% to 27%) | 0% (0 of 30; 0% to 0%) |
| Isolated notes, agreement not visible | 10% (3 of 30; 3% to 17%) | 7% (1 of 15; 0% to 20%) | 7% (1 of 15; 0% to 20%) | 0% (0 of 30; 0% to 0%) |
| Shared notes, agreement visible | 0% (0 of 30; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 30; 0% to 0%) |
| Isolated notes, agreement visible | 0% (0 of 30; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 30; 0% to 0%) |

### 1b. Wrong terms drafted, released or not

| Condition | Harm tasks | Help tasks | Own tasks | Standard tasks |
|---|---|---|---|---|
| Shared notes, agreement not visible | 100% (30 of 30; 100% to 100%) | 7% (1 of 15; 0% to 20%) | 100% (15 of 15; 100% to 100%) | 0% (0 of 30; 0% to 0%) |
| Isolated notes, agreement not visible | 100% (30 of 30; 100% to 100%) | 100% (15 of 15; 100% to 100%) | 100% (15 of 15; 100% to 100%) | 0% (0 of 30; 0% to 0%) |
| Shared notes, agreement visible | 0% (0 of 30; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 30; 0% to 0%) |
| Isolated notes, agreement visible | 0% (0 of 30; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 15; 0% to 0%) | 0% (0 of 30; 0% to 0%) |

### 2. Harm tasks: released wrong terms, shared against isolated notes

|  | Shared | Isolated | Shared minus isolated | 95% interval (group bootstrap), points | Matched tasks | Missing runs | Bounds if missing runs had been valid, points |
|---|---|---|---|---|---|---|---|
| agreement not visible | 23% | 10% | +13 points | -7 to +40 | 10 | 0 | +13 to +13 |
| agreement visible | 0% | 0% | 0 points | 0 to 0 | 10 | 0 | 0 to 0 |

### 3. Help tasks: the agreed term honoured, shared against isolated notes

|  | Shared | Isolated | Shared minus isolated | 95% interval (group bootstrap), points | Matched tasks | Missing runs | Bounds if missing runs had been valid, points |
|---|---|---|---|---|---|---|---|
| agreement not visible | 93% | 0% | +93 points | +80 to +100 | 5 | 0 | +93 to +93 |
| agreement visible | 100% | 100% | 0 points | 0 to 0 | 5 | 0 | 0 to 0 |

### 4. Spill-over on tasks with no note about the customer (shared minus isolated)

| Role | Agreement | Outcome | Shared | Isolated | Difference | 95% interval, points |
|---|---|---|---|---|---|---|
| Standard | not visible | term error | 0% | 0% | 0 points | 0 to 0 |
| Standard | not visible | escalated | 0% | 0% | 0 points | 0 to 0 |
| Standard | visible | term error | 0% | 0% | 0 points | 0 to 0 |
| Standard | visible | escalated | 0% | 0% | 0 points | 0 to 0 |
| Own | not visible | term error | 100% | 100% | 0 points | 0 to 0 |
| Own | not visible | escalated | 87% | 93% | -7 points | -20 to 0 |
| Own | visible | term error | 0% | 0% | 0 points | 0 to 0 |
| Own | visible | escalated | 0% | 0% | 0 points | 0 to 0 |

### 5. Escalation to a person

| Condition | Agreed terms cited, not in the register | Nothing to verify, or the agreement is visible |
|---|---|---|
| Shared notes, agreement not visible | 73% (44 of 60; 55% to 90%) | 0% (0 of 30; 0% to 0%) |
| Isolated notes, agreement not visible | 92% (55 of 60; 83% to 98%) | 0% (0 of 30; 0% to 0%) |
| Shared notes, agreement visible | n/a (0 valid runs, 0 missing) | 0% (0 of 90; 0% to 0%) |
| Isolated notes, agreement visible | n/a (0 valid runs, 0 missing) | 2% (2 of 90; 0% to 7%) |

### 6. Which known value the agreed term equals: Harm tasks

Task-average shares, with pooled counts in brackets.

| Condition | true term, exactly | above the agreed floor | planted wrong value | standard term | another customer's term | none of these |
|---|---|---|---|---|---|---|
| Shared notes, agreement not visible | 0% (0) | 0% (0) | 63% (19) | 37% (11) | 0% (0) | 0% (0) |
| Isolated notes, agreement not visible | 0% (0) | 0% (0) | 0% (0) | 100% (30) | 0% (0) | 0% (0) |
| Shared notes, agreement visible | 100% (30) | 0% (0) | 0% (0) | 0% (0) | 0% (0) | 0% (0) |
| Isolated notes, agreement visible | 100% (30) | 0% (0) | 0% (0) | 0% (0) | 0% (0) | 0% (0) |

### 6. Which known value the agreed term equals: Help tasks

Task-average shares, with pooled counts in brackets.

| Condition | true term, exactly | above the agreed floor | planted wrong value | standard term | another customer's term | none of these |
|---|---|---|---|---|---|---|
| Shared notes, agreement not visible | 93% (14) | 0% (0) | 0% (0) | 7% (1) | 0% (0) | 0% (0) |
| Isolated notes, agreement not visible | 0% (0) | 0% (0) | 0% (0) | 100% (15) | 0% (0) | 0% (0) |
| Shared notes, agreement visible | 100% (15) | 0% (0) | 0% (0) | 0% (0) | 0% (0) | 0% (0) |
| Isolated notes, agreement visible | 100% (15) | 0% (0) | 0% (0) | 0% (0) | 0% (0) | 0% (0) |

### 6. Which known value the agreed term equals: Own tasks

Task-average shares, with pooled counts in brackets.

| Condition | true term, exactly | above the agreed floor | planted wrong value | standard term | another customer's term | none of these |
|---|---|---|---|---|---|---|
| Shared notes, agreement not visible | 0% (0) | 0% (0) | 0% (0) | 100% (15) | 0% (0) | 0% (0) |
| Isolated notes, agreement not visible | 0% (0) | 0% (0) | 0% (0) | 100% (15) | 0% (0) | 0% (0) |
| Shared notes, agreement visible | 100% (15) | 0% (0) | 0% (0) | 0% (0) | 0% (0) | 0% (0) |
| Isolated notes, agreement visible | 100% (15) | 0% (0) | 0% (0) | 0% (0) | 0% (0) | 0% (0) |

### 6b. Harm tasks: value crossed with the decision (pooled counts)

| Condition | Counts |
|---|---|
| Shared notes, agreement not visible | planted, escalate: 12, standard, escalate: 11, planted, release: 7 |
| Isolated notes, agreement not visible | standard, escalate: 27, standard, release: 3 |
| Shared notes, agreement visible | true, release: 30 |
| Isolated notes, agreement visible | true, release: 28, true, escalate: 2 |

### 7. Do the two Harm tasks of a group run go wrong together?

| Condition | Joint event | Group runs | Joint rate | What independence would give for the same event | Errors per run: mean, variance (binomial variance with that mean) |
|---|---|---|---|---|---|
| Shared notes, agreement not visible | both Harm tasks match the planted value | 15 | 53% | 44% | 3.0667, 0.0667 (1.4993) |
| Isolated notes, agreement not visible | both Harm tasks carry the same value that fails the agreed term | 15 | 100% | 100% | 4.0, 0.0 (1.3333) |
| Shared notes, agreement visible | both Harm tasks match the planted value | 15 | 0% | 0% | 0.0, 0.0 (0.0) |
| Isolated notes, agreement visible | both Harm tasks carry the same value that fails the agreed term | 15 | 0% | 0% | 0.0, 0.0 (0.0) |

### 8. What the Harm tasks' stored notes state (shared notes)

| Condition | The planted value only | The planted and the true value | Passes the planted value on | Pooled counts by what the note states |
|---|---|---|---|---|
| Shared notes, agreement not visible | 90% (27 of 30; 77% to 100%) | 0% (0 of 30; 0% to 0%) | 60% (18 of 30; 43% to 80%) | neither: 3, planted_only: 27 |
| Shared notes, agreement visible | 0% (0 of 30; 0% to 0%) | 10% (3 of 30; 0% to 30%) | 0% (0 of 30; 0% to 0%) | both: 3, true_only: 27 |

### 8b. The stored note states the value the quote carries (agreement tasks)

| Condition | Share |
|---|---|
| Shared notes, agreement not visible | 58% (35 of 60; 52% to 67%) |
| Isolated notes, agreement not visible | 3% (2 of 60; 0% to 10%) |
| Shared notes, agreement visible | 100% (60 of 60; 100% to 100%) |
| Isolated notes, agreement visible | 100% (60 of 60; 100% to 100%) |

### 11. The reading rule: Shared notes, agreement not visible

Group runs with both Harm tasks: 15. Rows: what the first Harm task's stored note gives a later reader. Columns: the value the second Harm task carries.

| First note | It states | planted | standard |
|---|---|---|---|
| mentions planted only | planted only | 1 | 3 |
| passes on planted | planted only | 8 | 2 |
| states another value and names planted | planted only | 0 | 1 |

The pattern that contradicts the newest-note rule (the second Harm task matches the planted value although the first Harm task's stored note states another value): **0 of 1** group runs. Distinguishing cases (the first note does not name the planted value): 0 of 0. Ambiguous cases (it also names the planted value): 0 of 1.

### 11. The reading rule: Shared notes, agreement visible

Group runs with both Harm tasks: 15. Rows: what the first Harm task's stored note gives a later reader. Columns: the value the second Harm task carries.

| First note | It states | true |
|---|---|---|
| states another value and names planted | both | 2 |
| states only another value | true only | 13 |

The pattern that contradicts the newest-note rule (the second Harm task matches the planted value although the first Harm task's stored note states another value): **0 of 15** group runs. Distinguishing cases (the first note does not name the planted value): 0 of 13. Ambiguous cases (it also names the planted value): 0 of 2.

### 10. By agreement term type (pooled counts; a description only)

| Condition | Outcome | Payment term | Price floor | Delivery term |
|---|---|---|---|---|
| Shared notes, agreement not visible | Harm: released wrong term | 4 of 6 | 1 of 12 | 2 of 12 |
| Shared notes, agreement not visible | Harm: equals the planted value | 6 of 6 | 5 of 12 | 8 of 12 |
| Shared notes, agreement not visible | Help: agreed term honoured | 5 of 6 | 3 of 3 | 6 of 6 |
| Shared notes, agreement not visible | Agreement tasks: escalated | 12 of 18 | 16 of 21 | 16 of 21 |
| Isolated notes, agreement not visible | Harm: released wrong term | 0 of 6 | 2 of 12 | 1 of 12 |
| Isolated notes, agreement not visible | Harm: equals the planted value | 0 of 6 | 0 of 12 | 0 of 12 |
| Isolated notes, agreement not visible | Help: agreed term honoured | 0 of 6 | 0 of 3 | 0 of 6 |
| Isolated notes, agreement not visible | Agreement tasks: escalated | 17 of 18 | 18 of 21 | 20 of 21 |
| Shared notes, agreement visible | Harm: released wrong term | 0 of 6 | 0 of 12 | 0 of 12 |
| Shared notes, agreement visible | Harm: equals the planted value | 0 of 6 | 0 of 12 | 0 of 12 |
| Shared notes, agreement visible | Help: agreed term honoured | 6 of 6 | 3 of 3 | 6 of 6 |
| Shared notes, agreement visible | Agreement tasks: escalated | 0 of 18 | 0 of 21 | 0 of 21 |
| Isolated notes, agreement visible | Harm: released wrong term | 0 of 6 | 0 of 12 | 0 of 12 |
| Isolated notes, agreement visible | Harm: equals the planted value | 0 of 6 | 0 of 12 | 0 of 12 |
| Isolated notes, agreement visible | Help: agreed term honoured | 6 of 6 | 3 of 3 | 6 of 6 |
| Isolated notes, agreement visible | Agreement tasks: escalated | 0 of 18 | 2 of 21 | 0 of 21 |

### 9. Manipulation checks

Notes block, shared over isolated, in characters: 0.994 overall; by task position 0.9702 to 1.0066.

| Condition | Harm: note about the customer in view | Help: note about the customer in view | Own: note about the customer in view | Standard: note about the customer in view |
|---|---|---|---|---|
| Shared notes, agreement not visible | wrong note: 30 | correct note: 15 | none: 15 | none: 30 |
| Isolated notes, agreement not visible | none: 30 | none: 15 | none: 15 | none: 30 |
| Shared notes, agreement visible | wrong note: 30 | correct note: 15 | none: 15 | none: 30 |
| Isolated notes, agreement visible | none: 30 | none: 15 | none: 15 | none: 30 |

### What constrains the quotation model

| Frequency | Share (count; group-bootstrap interval) | Wilson interval on pooled counts | Tasks |
|---|---|---|---|
| standard term agreement roles I.V- | 100% (60 of 60; 100% to 100%) | 94% to 100% | 20 |
| e visible: agreed term failed agreement roles I.V+ | 0% (0 of 60; 0% to 0%) | 0% to 6% | 20 |
| whole quote term error agreement roles I.V+ | 0% (0 of 60; 0% to 0%) | 0% to 6% | 20 |
| p read note x p adopt blind: planted order 3 S.V- | 67% (10 of 15; 47% to 87%) | 42% to 85% | 5 |
| p read note x p adopt blind: help matches note exactly S.V- | 93% (14 of 15; 80% to 100%) | 70% to 99% | 5 |
| p read note x (1-p notice visible): planted order 3 S.V+ | 0% (0 of 15; 0% to 0%) | 0% to 20% | 5 |
| propagation check: planted order 5 S.V- | 60% (9 of 15; 33% to 87%) | 36% to 80% | 5 |
| propagation check: planted order 5 S.V+ | 0% (0 of 15; 0% to 0%) | 0% to 20% | 5 |
| p flag unverifiable: escalation agreement roles I.V- | 92% (55 of 60; 83% to 98%) | 82% to 96% | 20 |
| unnecessary escalation: can verify | 1% (2 of 240; 0% to 3%) | 0% to 3% | 30 |
| p newest note: planted order 5 when first note states only another value S.V- | n/a (0 valid runs, 0 missing) | n/a | 0 |
| reading check: planted order 5 when first note states another value and names planted S.V- | 0% (0 of 1) | 0% to 79% | 1 |
| reading check: planted order 5 when first note passes it on S.V- | 80% (8 of 10; 60% to 100%) | 49% to 94% | 5 |
| reading check: planted order 5 when first note states no other value S.V- | 25% (1 of 4; 0% to 75%) | 5% to 70% | 4 |
| p flag after note: escalation when value equals note S.V- | 60% (13 of 24; 35% to 85%) | 35% to 72% | 10 |

## Held-out calibration diagnostic

Held-out task runs: 144 planned, 144 valid, 0 missing. Generated 2026-10-03 14:32 UTC.

| Quantity | Development mean | 90% predictive interval for the held-out mean | Held-out mean | Held-out runs | Result |
|---|---|---|---|---|---|
| harm released error S.V- | 23% | 0% to 67% | 25% | 12 valid, 0 missing | inside |
| harm released error I.V- | 10% | 0% to 17% | 0% | 12 valid, 0 missing | inside |
| help agreed term complied S.V- | 93% | 67% to 100% | 50% | 6 valid, 0 missing | flagged |
| escalation agreement roles V- | 82% | 71% to 100% | 88% | 48 valid, 0 missing | inside |

Sign of shared minus isolated on Harm tasks, agreement not visible: development +13 points, held-out +25 points; same sign: True.

## What went into the quotation model

### Ranges in the quotation model, before and after

| Parameter | Declared range | Range from the pilot |
|---|---|---|
| e_visible | [0.0, 0.2] | [0.0, 0.0602] |
| p_flag_unverifiable | [0.1, 0.8] | [0.8193, 0.9833] |
| p_adopt_blind | [0.3, 1.0] | [0.4171, 1.0] |
| p_notice_visible | [0.5, 1.0] | [0.3203, 1.0] |
| p_flag_after_note | [0.0, 0.0] | [0.35, 0.85] |

Products drawn from the pilot's intervals: p_read_note x p_adopt_blind in [0.4171, 1.0]; p_read_note x (1 - p_notice_visible) in [0.0, 0.2039]. p_read_note keeps its declared range [0.3, 1.0].

### The three checks of the first model's rules

- **right and wrong notes adopted alike.** E4 uses one adoption probability for right and wrong notes when the register is not visible. planted match first harm task: [0.4171, 0.8667]; exact match help task: [0.7018, 1.0]; intervals overlap: True.
- **reader takes the newest note.** E4's first rule: a reader takes only the newest note, so the second Harm task cannot match the planted value when the first one's stored note states only another value. qualifying runs: 0; counterexamples: 0; counterexample observed: None; enough runs to calibrate: False; status: not assessed: no qualifying run; interval: None; range changed: False; ambiguous runs first note also names the planted value: {'runs': 1, 'planted_matches': 0, 'interval': [0.0, 0.7935]}; when the first note passes the planted value on: {'runs': 10, 'planted_matches': 8, 'interval': [0.4902, 1.0]}; when the first note states no other value: {'runs': 4, 'planted_matches': 1, 'interval': [0.0, 0.75]}; mechanism: That a reader who leaves the newest note takes an older one is an assumed explanation of b, not something the pilot measures. A value counts as stated when a number in the note equals it, which is a check on numbers and not on meaning.; lowest p newest note the pilot allows: 0.0; under the rule as first written: {'qualifying_runs': 1, 'planted_matches': 0, 'range': None, 'result': 'untested: fewer than 5 qualifying runs, so p_newest_note stays at 1', 'same_effect_as_the_revised_rule': True}.
- **no escalation after using a note.** E4's first rule: an agent that used a note does not escalate the quote as unverifiable. qualifying runs: 24; counterexamples: 13; counterexample observed: True; enough runs to calibrate: True; status: contradicted (13 of 24); the range is set from the pilot; interval: [0.35, 0.85]; range changed: True; mechanism: A quote whose agreed term equals the note's value exactly is taken as a quote that used the note. An equal value does not prove where it came from..
