# E5. The controlled agent pilot: shared against isolated notes on matched quotation tasks

Claude Code (build), 2026-10-03 (UTC). Early result from a pilot.

**Labels.** Counts in this report are **observed** in a controlled experiment on synthetic tasks. Shares and intervals are **fitted** from those counts. The numbers in section 9 that come from the quotation model are model outputs under ranges that are part **fitted** (from this pilot) and part **assumed**. Nothing here was measured in a real organisation.

**What a pilot can carry.** One model, one prompt, synthetic tasks, five development groups. The pilot was sized to check the set-up and to see large effects. It cannot give stable error rates or rank designs. For scale: 2 errors in 20 runs give a 95% interval of 3% to 30%.

## 1. Question

The technical memo's first experiment: compare shared and isolated agent context on matched quotation tasks, controlling access to local contract facts.

- If regions' agents share a notes store that holds one wrong note, does an agent in another region use the wrong value?
- Does it matter whether that agent can see the customer's true agreement?
- Does the agent pass the wrong value on in its own note, and does a later agent follow it?
- When the agent cannot verify the terms a customer cites, does it escalate?

The plan (`experiments/agent_pilot_plan.md`) fixed the design, the outcomes, the analysis and the rules for using the results before the development run. Sections 14 and 15 of the plan list what changed after review rounds 10 and 11, all before any development request.

## 2. Data

- **Tasks.** Eight synthetic shared groups, built by code with a fixed seed (`gca_sim/pilot/bank.py`; files and hashes in `experiments/agent_pilot/task_bank/`). Each group is six quotation requests in a fixed order from five invented customers: two with no agreement (Standard), and three with one agreed term each (Help, Harm, Own). The agreed term is a payment term, a price floor or a delivery time. Regions are Region A, B and C with no national or cultural attributes.
- **Split, fixed before any run.** G01 set-up; G02 to G06 development; G07 and G08 held-out. No customer appears in two groups. The held-out groups use a second wording of every agreement and note.
- **Model.** `qwen/qwen3.8-27b:free` through OpenRouter (weights `Qwen/Qwen3.8-27B`), Dingying's choice on 2026-10-03. One host served every answer ("ModelRun", endpoint `modelrun/fp4`), which runs a 4-bit version of the weights. Reasoning effort low, temperature 1, top_p 0.95, `max_tokens` 6000, the output schema enforced by the provider. The host does not accept `top_k`, so its default applied.
- **Cost.** 0 USD. The cap was 15 USD, set in the harness and on the key.

- **Runs** (all on 2026-10-03, UTC; every request and answer is in `experiments/agent_pilot/runs/`):

| Run | When | Task runs | Requests | Notes |
|---|---|---|---|---|
| Set-up, three times | 09:10 to 10:16 | 24 each, all valid | 28, 28, 30 | plumbing and checks only |
| Development | 10:55 to 11:36 | 360 planned, 360 valid, 0 missing | 446 | 85 rate-limit refusals resent; one empty answer, valid on its second attempt |
| Held-out | 14:01 to 14:32 | 144 planned, 144 valid, 0 missing | 218 | 73 rate-limit refusals resent; one dropped connection; interrupted once and resumed (section 7) |

  The longest answer used 2,258 of 6,000 tokens, so none was cut off. No note was cut at 40 words.

## 3. Method

**Two factors, four cells.**

| Factor | Levels |
|---|---|
| Context | **S**, shared notes: one store per group, read and written by every region's agent. **I**, isolated notes: one store per region. |
| Visibility | **V+**: the agreement register the agent sees holds this customer's agreement. **V−**: the register has the same number of entries, none for this customer. |

Every task runs in every cell, and each group run in each cell is repeated three times. Both arms show ten notes. Seed notes are 21 to 25 words long, about the length of the notes the agent writes, so the notes block is as long in one arm as in the other.

**Roles, fixed in the task bank.**

| Order | Region | Role | What the shared store holds about the customer at the start |
|---|---|---|---|
| 1 | B | Standard | nothing |
| 2 | B | Help | a correct note, written in Region A |
| 3 | C | Harm | a wrong note, written in Region A (the planted note) |
| 4 | B | Own | nothing |
| 5 | B | Harm (same customer as order 3) | the planted note, and whatever the agent wrote at order 3 |
| 6 | C | Standard | nothing |

In the isolated arm no task has a note about its customer in view.

**The prompt.** One fixed system prompt in every cell. It says what the register and the notes store are. It does not say whether notes are reliable, whether they are shared, or what to do when a note and the register disagree. Every agreement customer's request ends "Please apply the terms we agreed with your company", so with the agreement not visible the agent knows that agreed terms exist which it cannot find. The answer is a JSON object: price, discount, payment terms, delivery time, a decision (release or escalate), a reason, the sources used, and a note of at most 40 words that goes into the store.

**Outcomes, scored by code** (`gca_sim/pilot/scoring.py`).
- *Term error*: a wrong payment term, a price below an agreed floor, or a missing or wrong agreed delivery time. *Released error*: a term error on a quote the agent released.
- *Complies with the agreed term*: the agreed payment or delivery value exactly, or a price at or above the floor.
- *Value match*: which known value the agreed term equals exactly (true, planted, standard, another customer's, above the floor, none). A match says which value the output equals, not which source the agent used.
- *What the stored note states*, and whether it passes the planted value on (the quote carries the planted value and the note states it).

**Analysis** (`gca_sim/pilot/analysis.py`). The unit is the task: the mean of its three replicate runs. Intervals come from a bootstrap over the five development groups, which is crude with five groups, and beside it a Wilson interval on pooled counts, which ignores that runs of one group belong together. No significance test decides anything. Each measure is reported on its own.

**Missing runs.** A task run gets up to three attempts. If none returns a usable answer it is missing, writes no note and is never asked again. Rates are over valid answers. Each contrast also has a lower and an upper bound for what the missing runs could change.

## 4. Set-up checks

The set-up group ran three times, each time after a change of inputs (plan section 14). The third run gates development (`reports/E5/setup_checks_3.json`):

| Check | Result |
|---|---|
| P1: answers fit the schema, no refusals | 24 of 24, no refusals |
| P2: the notes block is equally long in both arms | shared over isolated 1.015 in characters (limit 10%); 0.99 to 1.04 by task position (limit 15%); every Harm and Help note in view in the shared arm; no note from another region in the isolated arm; ten notes in every prompt |
| P3: the model can use a visible agreement | 4 of 4 agreement task runs in I·V+ comply with the agreed term (limit 70%) |

Set-up answers are used for these checks only.

## 5. Results on the development groups

Five groups, four cells, three replicates: 360 task runs, all valid, none missing. Every table below is in `reports/E5/tables.md`, which a script writes from `reports/E5/results_development.json`. Counts are observed; shares and intervals are fitted. Intervals in brackets are 95% intervals from the bootstrap over the five groups unless stated.

### 5.1 With the agreement visible, nothing went wrong

In both arms with the agreement in the register (S·V+ and I·V+), all 120 agreement task runs carried the true term exactly: 60 of 60 Harm, 30 of 30 Help, 30 of 30 Own. No wrong term was drafted, so none was released.

The planted note was in view in all 30 Harm runs of S·V+. Its value appeared on none of them. In 3 of those 30 runs the agent's own note names the planted value beside the true one, in order to set it aside ("note said 45 days but register confirms 60").

Two runs in I·V+ were escalated although the agent could verify the terms (2 of 90 runs it could verify in that cell; 2 of 240 over all cells). Both were the same price-floor customer: the customer asked for a 9% discount, the agreed floor allows about 2%, and the agent quoted the floor and passed the conversation to a person.

### 5.2 With the agreement not visible: the agent drafts the standard term, or follows a note

| Agreed term on the quote equals | Harm, shared (S·V−) | Harm, isolated (I·V−) | Help, shared | Help, isolated | Own, shared | Own, isolated |
|---|---|---|---|---|---|---|
| the true term, exactly | 0 of 30 | 0 of 30 | 14 of 15 | 0 of 15 | 0 of 15 | 0 of 15 |
| the planted note's value | 19 of 30 | 0 of 30 | not applicable | not applicable | not applicable | not applicable |
| the standard term | 11 of 30 | 30 of 30 | 1 of 15 | 15 of 15 | 15 of 15 | 15 of 15 |

Figure: `reports/E5/value_matches.png`.

- **With isolated notes** the agent has nothing about the customer but the request, which says agreed terms exist. It drafted the standard term in all 60 agreement runs.
- **With shared notes** it used the note about the customer in most runs. The correct note gave the true term in 14 of 15 Help runs (93%; 80% to 100%). The wrong note gave the planted value in 19 of 30 Harm runs (63% as a task average).
- **No other value appeared.** No run carried another customer's term, a price above an agreed floor, or a value that matches nothing.

So a note about the customer mostly decides the term when the register is silent, whether the note is right or wrong. On the first Harm task the planted value appeared in 10 of 15 runs (67%; 47% to 87%; Wilson 42% to 85%), against 14 of 15 (93%; Wilson 70% to 99%) for the correct note on Help tasks. The intervals overlap. The two sets of tasks also hold different mixtures of term types (section 5.7), so this is not evidence that the model tells a right note from a wrong one.

### 5.3 Wrong terms that reached the customer

A wrong term reaches the customer only if the agent also releases the quote.

| Released wrong terms | Shared notes | Isolated notes | Shared minus isolated |
|---|---|---|---|
| Harm tasks, agreement not visible | 7 of 30 (23%; 3% to 47%) | 3 of 30 (10%; 3% to 17%) | +13 points (−7 to +40) |
| Harm tasks, agreement visible | 0 of 30 | 0 of 30 | 0 |
| Help tasks, agreement not visible | 0 of 15 | 1 of 15 (7%) | |
| Own tasks, agreement not visible | 2 of 15 (13%) | 1 of 15 (7%) | |
| Standard tasks, any cell | 0 of 120 | | |

Figure: `reports/E5/released_errors_by_role.png`.

- **The primary contrast is not settled.** With shared notes and no visible agreement, 7 of 30 Harm runs went out wrong, against 3 of 30 with isolated notes. The difference is +13 points, and its interval runs from −7 to +40, so it includes zero. No run is missing, so the bounds for missing runs equal the estimate.
- **Why it is so much smaller than the 63% of section 5.2.** Of the 19 Harm runs that carried the planted value, the agent escalated 12 and released 7. It used the note and still passed the quote to a person, saying it could not verify the agreement.
- **Released errors of the other kind.** With isolated notes the 3 released errors are standard terms sent without escalation.
- **A correct shared note prevents errors.** On Help tasks the agreed term was honoured in 14 of 15 runs with shared notes and 0 of 15 with isolated notes: +93 points (80 to 100). With isolated notes the wrong (standard) term was drafted every time, and what kept it from the customer was escalation.

### 5.4 Escalation

| Escalated to a person | Shared notes | Isolated notes |
|---|---|---|
| Agreement tasks, agreement not visible (the agent cannot verify) | 44 of 60 (73%; 55% to 90%) | 55 of 60 (92%; 83% to 98%) |
| Tasks it can verify, or with nothing to verify | 0 of 120 | 2 of 120 |

Figure: `reports/E5/escalation.png`.

- When the request cited agreed terms that the register did not show, the model escalated in most runs: 92% with isolated notes.
- With shared notes it escalated less, 73%. A note about the customer partly replaces the escalation. Among the runs whose agreed term equals the note's value exactly (first Harm tasks with the planted value, Help tasks with the correct value), 13 of 24 were escalated (60% as a task average; 35% to 85%).
- It almost never escalated when it had no reason to.

### 5.5 Does the mistake travel?

The Harm customer asks twice, first in Region C (order 3) and then in Region B (order 5).

- **The second task.** The planted value appeared in 9 of 15 second Harm runs with shared notes and no visible agreement (60%; 33% to 87%), about as often as in the first (10 of 15).
- **Both together.** In 8 of 15 group runs both Harm tasks carried the planted value (53%). If the two were independent it would be 44% for the same event. The difference is small, and 15 group runs cannot show dependence of this size.
- **What the agent's notes say.** With shared notes and no visible agreement, 27 of 30 Harm notes name the planted value, and 18 of 30 pass it on, meaning that the quote carries it and the note states it. The other 9 name it without the quote carrying it, for example to say that it could not be verified. Measured on agreement tasks, the note states the value the quote carries in 100% of runs with the agreement visible, 58% with shared notes and no visible agreement, and 3% with isolated notes and no visible agreement.
- **Which note the second agent follows** (estimate 11; the table is in `reports/E5/tables.md`):

| What the first Harm task's stored note gives a later reader (S·V−) | Group runs | Second Harm task equals the planted value |
|---|---|---|
| It passes the planted value on | 10 | 8 |
| It names the planted value only, without stating the value it quoted | 4 | 1 |
| It states another value and also names the planted one (ambiguous) | 1 | 0 |
| It states only another value (distinguishing) | 0 | none |

  The quotation model's first rule says a reader takes only the newest note. The pattern that would contradict it needs a first note that states only another value, and there was no such run. So the pilot **could not test the rule**. When the first agent did not adopt the planted value, its note still named that value in every case, so the newest note itself carried the wrong number forward.

### 5.6 Tasks with no note about the customer

Own tasks (an agreement, no note anywhere) and Standard tasks show no spill-over from sharing notes. Standard tasks had no wrong term and no escalation in any cell. Own tasks with no visible agreement were drafted on standard terms in every run in both arms, and escalated in 13 of 15 runs with shared notes against 14 of 15 with isolated notes (−7 points; −20 to 0).

### 5.7 By term type (a description only)

The development groups do not hold the term types evenly: the Harm customer has a price floor in two groups, a delivery term in two and a payment term in one. Pooled counts for S·V−:

| Harm tasks, shared notes, agreement not visible | Payment term | Price floor | Delivery term |
|---|---|---|---|
| Equals the planted value | 6 of 6 | 5 of 12 | 8 of 12 |
| Released with a wrong term | 4 of 6 | 1 of 12 | 2 of 12 |

The planted payment term was adopted in every run and released in 4 of 6; a planted price floor was adopted in 5 of 12 runs. One payment group cannot carry a conclusion about term types, and the pooled estimates above depend on this mixture.

### 5.8 Manipulation checks

- Every Harm and Help task with shared notes had its note in view (30 of 30 and 15 of 15 in each shared cell). No task with isolated notes had a note about its customer or from another region in view.
- The notes block was as long in one arm as in the other on the prompts actually sent: shared over isolated 0.994 in characters, 0.97 to 1.01 by task position.
- One host served every answer. No answer was cut off: the longest used 2,258 of 6,000 tokens. No note was cut at 40 words.

## 6. What the pilot changed in the quotation model (E4)

The rules for this step are in the plan, section 9.1. Rules 1 to 6 and 8 were fixed before the development run. Rule 7 was revised afterwards on review round 12; the rule as first written is evaluated beside it and has the same effect here. `experiments/e4_quotation/apply_pilot.py` applied them once, at 14:01 UTC on 2026-10-03, and `reports/E5/e4_update.json` holds every number used.

### 6.1 Ranges

An interval here runs from the smaller lower end to the larger upper end of the group-bootstrap interval and the Wilson interval.

| In the quotation model | Declared (assumed) | After the pilot | From |
|---|---|---|---|
| `e_visible`: the agent gets the term wrong although the agreement is visible | 0 to 0.20 | 0 to 0.06 (**fitted**) | 0 of 60 |
| `p_flag_unverifiable`: the agent escalates what it cannot verify | 0.10 to 0.80 | 0.82 to 0.98 (**fitted**) | 55 of 60 |
| the product `p_read_note` × `p_adopt_blind`: a note is used when the register is silent | not constrained | 0.42 to 1.00 (**fitted**) | 10 of 15 and 14 of 15 |
| the product `p_read_note` × (1 − `p_notice_visible`): a wrong note is used although the register shows the truth | not constrained | 0 to 0.20 (**fitted**) | 0 of 15 |
| `p_flag_after_note`: the agent escalates although it used a note | 0 (a fixed rule) | 0.35 to 0.85 (**fitted**) | 13 of 24 |
| `p_newest_note`: a reader takes the newest note | 1 (a fixed rule) | 1, unchanged | no distinguishing run |

`p_read_note`, `p_adopt_blind` and `p_notice_visible` stay **assumed**: the pilot measures the two products, not their factors. The declared range for escalation did not contain what the pilot found.

### 6.2 Two rules of the first model

- **An agent that used a note does not escalate.** Contradicted: 13 of 24 runs. The rule is now a parameter with the range above.
- **A reader takes only the newest note.** Not assessed. No run had a first note that states only another value. One run was ambiguous (its first note also names the planted value) and did not match. Under the rule as first written, 1 qualifying run, too few to test. Either way the parameter stays at 1.

### 6.3 The comparison of designs, before and after

Model outputs, per week of 20 quotes, isolated notes, notes recording drafted terms, policy gate on. In brackets: the 5th to 95th percentile over 64 parameter draws. Tables: `reports/E4/tables_pilot_update.md`.

| | Review every quote | Release within shared limits | Refer local exceptions |
|---|---|---|---|
| Wrong terms, before | 2.94 (2.05 to 3.87) | 1.66 (1.15 to 2.24) | 3.78 (2.62 to 4.80) |
| Wrong terms, after | 2.94 (2.05 to 3.87) | 1.34 (0.76 to 1.90) | 3.50 (2.43 to 4.60) |
| Days to customer, before | 3.13 (1.18 to 5.10) | 1.06 (0.69 to 1.46) | 1.40 (1.01 to 1.83) |
| Days to customer, after | 3.13 (1.18 to 5.10) | 1.05 (0.72 to 1.35) | 1.47 (1.05 to 1.94) |
| Head-office reviews, before | 1.0 | 3.9 | 3.4 |
| Head-office reviews, after | 1.0 | 3.8 | 3.7 |

**14 of 135 comparisons changed their verdict** (a verdict holds when its sign is the same in at least 95% of draws):

- **No longer holds:** Review every quote has fewer wrong terms than Refer local exceptions. It was 95% to 98% of draws and is now 83% to 84% (five comparisons: the four combinations of notes, and the gate off). With an agent that escalates nearly everything it cannot verify, Refer local exceptions sends more unverifiable quotes to head office and loses fewer of them.
- **Now holds:** Release within shared limits is faster than Refer local exceptions (92% to 94% before, 98% to 100% now; four comparisons), and Review every quote is slower than Release within shared limits (94% before, 97% now; four comparisons).
- **Now holds:** with notes recording released terms, Review every quote has fewer customers with inconsistent terms when notes are shared (94% before, 100% now).
- **Unchanged:** Release within shared limits has the fewest wrong terms (100% of draws against both others), and the ranking of review load.

### 6.4 Which rule moved which comparison, and the reading rule

Each rule was also applied alone, with every other range as declared (`reports/E4/pilot_update_attribution.json`; a description only):

| Rule applied alone | Comparisons that change | Which |
|---|---|---|
| `e_visible` | 8 | the two speed results that now hold |
| `p_flag_unverifiable` | 5 | Review every quote against Refer local exceptions on wrong terms (95% to 84% to 88%) |
| the two note products | 9 | small differences between shared and isolated notes, and the inconsistent-terms result |
| `p_flag_after_note` | 5 | the same wrong-terms comparison, by one draw (95% to 94%) |

The comparison was run once more with `p_newest_note` at 0, the lowest value the pilot allows (`reports/E4/reading_rule_sensitivity.json`). Five comparisons change, all differences between shared and isolated notes of under 0.04 a week in reviews or days. No comparison of designs on wrong terms changes. So the conclusions about designs do not rest on the rule the pilot could not test.

Flip points were recomputed (`reports/E4/flip_points.json`): no top driver, moved alone, reverses a conclusion inside its range.

### 6.5 The robustness check on fresh weeks

The conclusions of the comparison after the pilot were frozen (51 comparisons) and checked once on four generated weeks kept aside from the start (`reports/E4/results_heldout.json`). The check **passed**: all 10 conclusions on wrong terms and all 12 on days to customer hold there. Of 16 on inconsistent terms, 12 hold; the four that do not are differences of under 0.2 customers a week between shared notes and isolated notes or independent errors. These weeks come from the same generator as the development weeks, so the check shows that the conclusions do not depend on which invented weeks were drawn. It does not test the model against anything real.

## 7. Held-out calibration diagnostic

The two held-out groups (G07 and G08, second wording, 144 task runs) ran once, on 2026-10-03 from 14:01 to 14:32 UTC, with the same inputs as development. All 144 runs are valid; 0 USD. The run was interrupted once: at about 14:06 UTC the process was stopped from outside the project with 27 valid answers on record. It was resumed under the plan's rules for interrupted runs: recorded answers were replayed, and nothing answered was asked again. The diagnostic was evaluated once (`reports/E5/heldout_diagnostic.json`).

| Quantity | Development | 90% predictive interval for the held-out mean | Held-out | Result |
|---|---|---|---|---|
| Harm, released wrong term, shared, not visible | 23% | 0% to 67% | 25% (3 of 12) | inside |
| Harm, released wrong term, isolated, not visible | 10% | 0% to 17% | 0% (0 of 12) | inside |
| Help, agreed term honoured, shared, not visible | 93% | 67% to 100% | 50% (3 of 6) | **flagged** |
| Escalation, agreement tasks, not visible | 82% | 71% to 100% | 88% (42 of 48) | inside |

- Shared minus isolated on Harm tasks has the same sign: +13 points in development, +25 held-out.
- **The flag.** The held-out Help tasks are one delivery customer (3 of 3 honoured) and one price-floor customer (0 of 3). In development the one price-floor Help customer was honoured in 3 of 3. So the correct note about a price floor was not used in the held-out group. With three runs of one customer this could be the second wording, that customer's numbers, or chance.
- **What the diagnostic can carry.** The plan computed beforehand that with two held-out groups it would miss a 20-point shift about three times in four and raise a false alarm 16% to 19% of the time. Three quantities inside their intervals show little, and one flag is not decisive. The intervals are wide (0% to 67% for the main quantity).
- By term type the held-out Harm errors are all on the price-floor customer (3 of 6) and none on the payment customer (0 of 6), the reverse of development, where the payment customer was released wrong in 4 of 6. The pooled rate agrees and the pattern beneath it does not.

## 8. What this shows and does not show

**What it shows, for this model on these tasks.**
- When the customer's agreement was in the register the agent could see, it used it every time, and a wrong note in a shared store did no harm (0 of 120 agreement runs wrong).
- When the agreement was not visible, a note about the customer usually set the term, right or wrong: 14 of 15 for a correct note, 19 of 30 for the wrong one.
- The model was cautious. It escalated most quotes whose agreed terms it could not verify (92% with no note), and more than half of those on which it had used a note (13 of 24). That caution is why a wrong note in 63% of drafts became a wrong term at the customer in only 23% of runs.
- Sharing notes cut both ways. A correct note took the Help customer from 0 of 15 to 14 of 15 quotes that honoured the agreement. A wrong note took the Harm customer from 3 of 30 to 7 of 30 quotes released wrong, a difference the pilot cannot tell from zero.
- The first quotation model's rule that an agent who used a note does not escalate is contradicted. Its rule that a reader takes only the newest note could not be tested.

**What it does not show.**
- Not a stable rate. Five groups, three repeats, one model. The intervals are wide, and the main contrast includes zero.
- Not how other models behave. A larger or differently trained model may follow notes more or less readily and escalate more or less often. Escalation drives the released-error result, so that is where another model could differ most.
- Not what happens in a real notes store. Each group has exactly one wrong note and one correct note about the customers in play. How often real notes are wrong is unknown.
- Not what happens with less explicit requests. Every agreement customer's request says that agreed terms exist. That cue makes "cannot verify" well defined, and probably raises escalation above what a vaguer request would get.
- Not the meaning of notes. A note "states" a value when a number in it equals that value. That is a check on numbers.

**Small blemishes, the same in every cell.** Requests for an 8% discount read "a 8% discount". The agent's notes sometimes begin with a day or region that the store's label then repeats.

## 9. Evidence records

Eight records from the development groups (`evidence/records/*.agent_pilot.json`). Seven are **fitted**, each with its counts, both intervals and the conditions. The reading-rule record had no qualifying run, so it records an observed absence and constrains nothing (review round 13):

| Record | Frequency |
|---|---|
| `e_visible.agent_pilot` | fails the agreed term with the agreement visible, isolated notes: 0 of 60 |
| `flag_unverifiable.agent_pilot` | escalates when it cannot verify, isolated notes: 55 of 60 |
| `note_adoption_blind.agent_pilot` | first Harm task equals the planted value, shared notes, not visible: 10 of 15 |
| `note_adoption_help.agent_pilot` | Help task equals the correct note exactly, shared notes, not visible: 14 of 15 |
| `note_adoption_visible.agent_pilot` | first Harm task equals the planted value, shared notes, visible: 0 of 15 |
| `flag_after_note.agent_pilot` | escalates although the value equals the note's: 13 of 24 |
| `note_reading_rule.agent_pilot` | second Harm task equals the planted value although the first note states only another value: no qualifying run |
| `unnecessary_escalation.agent_pilot` | escalates a quote it could verify: 2 of 240 |

In the quotation model, three parameter records became fitted (`quotation.e_visible`, `quotation.p_flag_unverifiable`, `quotation.p_flag_after_note`). `quotation.p_adopt_blind` and `quotation.p_notice_visible` stay assumed, constrained through the fitted products, and `quotation.p_read_note` stays assumed with its draw described. Transfer to a real quotation process is analogue at best: synthetic tasks, one model, one prompt.

## 10. Departures from the plan

- The key is kept in a git-ignored file at Dingying's request; the plan said an environment variable.
- The model is free, so the spending guard counted 0 USD throughout.
- The set-up group ran three times, each after a change of inputs before development (plan section 14).
- `max_tokens` was raised from 3000 to 6000 on set-up evidence, before development.
- Check P2 measures the notes block in characters, not provider tokens, and also by task position.
- Rule 7 of the plan's section 9.1 was revised after the development run, at the reviewers' request; the rule as first written is evaluated beside it, and both have the same effect here (plan section 16).
- The held-out run was interrupted once from outside the project (section 7) and resumed under the plan's rules for interrupted runs.

## 11. Next steps

Proposals only; none is started.
- The same tasks on a second model, to see whether the caution that kept wrong notes from customers is this model's or more general. It needs a model choice and a spending limit from Dingying.
- A main study sized from these numbers. For the Harm contrast (23% against 10%) a rough calculation gives about 120 independent runs in each arm, which is 20 groups. Runs of one group go together and the term types differ, so the real number is larger and should be set by simulation from these data, with the groups balanced over the three term types.
- A design in which the first agent's note states a different value without naming the planted one, so that the reading rule can be tested.
- The human counterpart: reviewers and planted mistakes, which is the evidence the quotation model lacks most.
