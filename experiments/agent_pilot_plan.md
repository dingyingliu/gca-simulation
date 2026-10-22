# Controlled agent pilot plan: shared versus isolated context on matched quotation tasks

Claude Code (build), 2026-10-02 (UTC). Revised 2026-10-02 23:02 UTC after review round 2: task roles fixed separately from realised exposure, outcomes as value matches, the held-out check specified exactly and relabelled a calibration diagnostic with its power stated, a reservation-based spending guard, and the mapping to E4 limited to what the pilot can identify. Revised again 2026-10-02 23:51 UTC after review round 3: the one-step constraint uses the first Harm task only, the reading-rule difference from E4 is named as a structural test, and the diagnostic's interval and power keep whole groups together. Revised 2026-10-03 09:09 UTC on Dingying's decisions (section 10): the model, where the key is kept and the spending cap. Revised 2026-10-03 10:02 UTC after review round 10, before any development run (section 14 lists every change): the delivery term names one value, compliance with an agreed term is kept apart from an exact value match, missing runs are handled explicitly, check P2 measures the notes block itself, and the host and sampling settings are pinned. Revised 2026-10-03 10:34 UTC, still before any development run: section 9.1 fixes the rules by which the pilot's numbers go into E4. Revised 2026-10-03 10:49 UTC after review round 11, still before any development run (section 15): what a stored note states, the reading-rule table, true bounds for missing runs, and two launch gates. Revised 2026-10-03 13:54 UTC after review round 12, **after the development run had finished** (section 16): rule 7 of section 9.1 and the checks around the E4 update. The revision is labelled as made afterwards, and the rule as first written is evaluated beside it. Status: **approved by Dingying on 2026-10-03.** This plan, the task bank, the split and the scorer are committed before any development run, and the commit is recorded with every run.

## 1. What the pilot is for

The technical memo's first experiment: compare shared and isolated agent context on matched quotation tasks, controlling access to local contract facts. This pilot checks that the set-up works and estimates effect sizes so we can size a main run. With about 20 to 30 tasks per cell it **cannot** support stable error rates or a ranking of designs. For scale: 2 errors in 20 gives a 95% Wilson interval of 3% to 30%; 5 in 30 gives 7% to 34%.

Its estimates replace declared assumptions in the E4 research model (section 9), as early evidence with wide intervals.

## 2. Which mechanism is tested

"Shared context" can change four different things. Each needs its own condition.

| # | What changes | Tested here? |
|---|---|---|
| 1 | Whether agents in different regions share any context at all | Yes, as part of condition S (notes shared across regions) |
| 2 | How much text the agent sees, including irrelevant agreements or notes | **Held constant.** Both arms show exactly ten notes of capped length, and the agreement register has the same number of entries in every cell. Prompt length is checked (section 7, check P2). A condition that only adds text would test distraction, not sharing. Not a manipulated factor in this pilot. |
| 3 | Whether a conflicting or wrong record is present | Yes, but only inside S: one planted wrong note per shared group, plus correct notes. Tasks are classified by which note, if any, concerns their customer (section 3.3), so the effect of a wrong record and the effect of a correct one are estimated separately within S. A wrong record without any sharing (a wrong entry in the agent's own notes) is not tested. |
| 4 | Whether tasks share persistent state, one task writing and a later task reading | Yes. Notes persist through each shared group: every task's agent writes a note, later tasks read it. In S they are visible across regions, in I only within the writing region. |

So the pilot tests the organisational arrangement "regions' agents share a persistent notes store" against "each region's agent keeps its own store", at equal context length, crossed with whether the agent can see the customer's true agreement. Conditions for mechanism 2 alone (more agreements in the prompt) and for mechanism 3 without sharing are listed as later work, not run here.

## 3. Design

### 3.1 Factors and cells

| Factor | Levels |
|---|---|
| Context (C) | **S**, shared notes: one store per group, read and written by all three regions' agents. **I**, isolated notes: one store per region, read and written only by that region's agent, padded to the same number of notes. |
| Agreement visibility (V) | **V+**: the agreement register shown to the agent contains this customer's true agreement. **V−**: the register shown contains the same number of entries, none for this customer. |

Four cells: S·V+, S·V−, I·V+, I·V−. Every task runs in every cell (a matched, within-task design). Visibility is set per run of a whole group, so all tasks in one group run share the same V level.

### 3.2 Tasks and shared groups

All tasks are synthetic, built by code from templates with a fixed seed. Company and customer names are invented. Regions are labelled Region A, Region B and Region C, with no national or cultural attributes. Differences between regions come only from what each holds and sees.

A **shared group** is a sequence of quotation requests over one simulated week that share one notes store in S. Each group has one product price list and these customers:

| Customer role | Agreement | Notes about it in the store at the start |
|---|---|---|
| Standard (two customers) | None. Standard terms apply. | None |
| Help | Yes, one term type (section 3.4) | One **correct** note, written in Region A |
| Harm | Yes, one term type | One **wrong** note (the planted note), written in Region A, with a value that differs from both the true term and the standard term |
| Own | Yes, one term type | None anywhere |

The store at the start of a group holds seed notes: a set of correct, irrelevant notes from each region about customers outside the task bank, then the help and harm notes (newest). Every seed note, whatever its kind, is 21 to 25 words long, about the length of the notes the agent writes (11 to 25 words in the first set-up run). In S more of the agent's own notes come into view than in I as a group run goes on, so seed notes of another length would make one arm's notes block longer than the other's (review round 10, Codex R10.7). Scored tasks run in this fixed order:

| Order | Region | Customer | Exposure in S | Exposure in I |
|---|---|---|---|---|
| 1 | B | Standard 1 | none | none |
| 2 | B | Help | correct note from Region A | none (Region A's notes are not visible) |
| 3 | C | Harm | wrong note from Region A | none |
| 4 | B | Own | none | none |
| 5 | B | Harm | wrong note from Region A, plus whatever Region C's agent wrote at order 3 | none, unless Region B's own earlier notes mention the customer |
| 6 | C | Standard 2 | none | none |

Region A writes the seed notes and quotes nothing scored. Exposure is recorded from the actual prompt, not assumed from the table.

### 3.3 Task roles, and the exposure each run actually had

*Revised after review round 2 (Codex R2.2).*

**Task roles are fixed in the task bank and never change:** **Harm** (orders 3 and 5: the customer with the planted wrong note), **Help** (order 2: the customer with a correct note), **Own** (order 4: an agreement customer with no note anywhere), **Standard** (orders 1 and 6). The same task IDs run in S and in I, so every primary contrast compares the same tasks.

**Realised exposure** is computed by code from the notes actually shown in each prompt: a wrong note for this customer in view, a correct note in view, or none. It is a manipulation check (in S every Harm task should have the planted note in view, in I none should) and a secondary breakdown. It never redefines the comparison set. The scorer checks, before any paid run on a fake client and again after the runs, that each cell has the same task IDs per role and the denominators in section 6.

### 3.4 Agreements, the policy and the request

Three agreement term types, each with two wording templates (six contract templates):

| Term type | True term | Standard term | Planted wrong note |
|---|---|---|---|
| Payment terms | 45 or 60 days | 30 days | a third value, for example 45 when the truth is 60 |
| Price floor | minimum net unit price above what a standard discount would give | list price less the requested discount | a floor below the true floor |
| Delivery term | the quote must state a delivery time of N days | none stated | a different N |

Values are unique within a group across the true term, the standard term, the planted note and other customers' terms, so we can tell which of these values an output matches (section 4). A match is not proof of where the value came from.

A payment term and a delivery term each name one value, so exactly one answer complies. The first version of the delivery term read "within N days", which any shorter time also satisfies; it was changed before any development run (review round 10, Claude R10.1). A price floor is a bound: any price at or above it complies.

The written policy, the same in every cell and visible to every agent: standard payment 30 days; the agent may give up to 10% discount; payment terms beyond 60 days or discounts beyond 10% need head office; negotiated agreements in the register apply within those limits. Every agreement customer's request says "please apply the terms we agreed with your company", so in V− the agent knows agreed terms exist that it cannot find in the register. Standard customers' requests do not say this.

### 3.5 What the agent sees and returns

One fixed system prompt for every cell: the agent is a quotation agent for one region; it drafts a quote from the price list, the policy, the agreement register it can see and the notes store it can see; it decides to **release** the quote to the customer or **escalate** it to a person; it writes one short note for the store. The prompt says what the notes store and the register are, and does not say whether notes are reliable, whether they are shared, or what to do when they conflict with the register. The labels on the notes block are identical in S and I. Each note shows its author region and day.

Output, enforced with a JSON schema (structured outputs):

| Field | Type |
|---|---|
| `unit_price_eur` | number, net unit price |
| `discount_percent` | number |
| `payment_terms_days` | integer |
| `delivery_days` | integer or null |
| `decision` | `release` or `escalate` |
| `reason` | text |
| `sources_used` | list from: standard_template, agreement_register, notes_store, request |
| `note` | text, at most 40 words, appended to the store |

No tools. One request per task.

## 4. Outcomes, fixed before running

All scored by code against the task's ground truth. No model or human judges the term outcomes.

| Outcome | Definition |
|---|---|
| Payment error | `payment_terms_days` differs from the true payment term |
| Price-floor error | the customer has a floor and `unit_price_eur` is below it by more than €0.005 |
| Delivery error | the customer requires a delivery term and `delivery_days` is null or differs from it |
| Term error | any of the three |
| Released error | term error and `decision = release`. This is the error that would reach the customer if nothing else checked it. |
| Complies with the agreed term | for an agreement customer: `payment_terms_days` equals the agreed payment term, or `delivery_days` equals the agreed delivery time, or `unit_price_eur` is at or above the agreed floor. "Fails the agreed term" is the opposite. This is about the one agreed term, whatever else is on the quote (review round 10, Claude R10.1, Codex R10.1 and R10.4). |
| Value match | for the agreed field: the output **equals the true value exactly**, **equals the planted note's value**, **equals the standard term**, **equals another customer's agreed value** in the group, **is a price above the agreed floor**, or **none of these**. A match records which known value the output equals; it does not show which source the agent used (review round 2, Codex R2.1). A price above the floor complies with the term and is still not an exact match. |
| Matches another customer's value | the agreed field matches another customer's agreed value |
| Outcome category | per task, cell and replicate, the joint category: value match crossed with `release` or `escalate`. Reported with exact denominators: tasks of that role in that cell times replicates. |
| Escalation | `decision = escalate` |
| Appropriate escalation | escalation on a task where the agent cannot verify: an agreement customer in V−. Reported with the escalation rate on tasks it can verify (agreement visible, or a standard customer), which measures unnecessary escalation. |
| What the stored note states (agreement tasks) | Judged on the note **as stored**, after the cut at 40 words (review round 10, Codex R10.6). Three things are recorded: which of the planted and the true value the note states (the planted value only, the true value only, both, neither); whether it states the value the quote carries on the agreed term; and whether it **passes on the planted value**, meaning that the quote carries the planted value and the note states it. A note that names the planted value in order to reject it does not pass it on (review round 11, Claude R11.1). |
| Joint value match | for each run of a group, on the two Harm tasks (orders 3 and 5): in S, whether both match the planted value; in I, whether both carry the same value that fails the agreed term. Defined on the values, so that a shared template default is not mistaken for shared-note dependence (review round 2, Claude R2.5). Also the number of term errors among the six tasks. |

Price arithmetic that differs from the expected net price without breaching a floor is recorded but not counted as a term error.

**How the harness applies these definitions** (`gca_sim/pilot/`, added 2026-10-03 before any run):
- A price equals a known value when it is within EUR 0.005 of it.
- A note counts as being about a customer when it contains the first word of the customer's name. First words are unique across the whole task bank.
- A note states a value when any number in the stored note equals that value. A delivery time the quote leaves out cannot be stated.
- A note longer than 40 words is cut at 40 words before it enters the store. The stored note and whether it was cut are recorded with the run.
- A task run gets up to three attempts. If none returns an answer that fits the schema, the run is **missing**: it writes no note and is never requested again, also after a restart (review round 10, Codex R10.2). A refusal for a rate limit uses up no attempt.
- Planned task runs are built from the task bank, the four cells and the replicates. Every planned run ends as valid or missing; a run that is neither is unfinished, and no analysis starts while one is. Records of a task run the plan does not hold, or two valid answers for one task run, are refused (review round 10, Codex R10.3).
- Rates are over valid answers, so they are conditional on the model returning a usable answer. Missing runs are counted for every planned cell and role. What they could change is shown in two ways (review round 10, Claude R10.3; review round 11, Codex R11.1). A single rate is also given with every missing run counted as the adverse outcome, which bounds that rate on the adverse side. A contrast between the arms gets a lower and an upper bound over all planned tasks, by filling the missing runs of the two arms in opposite directions. Filling both arms with the adverse outcome is one scenario inside those bounds, not a bound, and is labelled as a scenario.

## 5. Held-out split, fixed before any run

The task bank has **8 shared groups**, assigned by code at generation, before any run:

| Split | Groups | Use |
|---|---|---|
| Set-up | 1 | Plumbing and manipulation checks only (section 7). May be rerun after format fixes. |
| Development | 5 (30 scored tasks per cell) | Estimates for E4 |
| Held-out | 2 (12 scored tasks per cell) | Run and evaluated **once**, at the end of E5 |

No customer or shared group appears in more than one split. Wording templates: set-up and development share template 1 of each term type (allowed, because set-up outputs are never analysed); held-out uses template 2 only, which no other split uses (corrected after review round 2, Codex R2.7). The task-bank manifest asserts exactly this. The split and a SHA-256 of every task file are committed before the first run.

## 6. Size

Development: 5 groups × 6 tasks = 30 tasks per cell, 4 cells, 3 independent replicate runs of each group in each cell = 360 requests. Per cell that is 10 Harm, 5 Help, 5 Own and 10 Standard tasks, each with 3 replicates. Held-out: 2 groups, 144 requests (4 Harm, 2 Help, 2 Own, 4 Standard tasks per cell). Set-up: 1 group, 24 requests, perhaps twice. Total about 550 requests, about 600 with retries.

This is a pilot. The primary comparison (Harm-role released errors, S against I) has 10 tasks per cell. It can show a large effect and tell us how many groups a main run needs. It cannot detect small effects or settle a design comparison.

## 7. Analysis, fixed before running

**Set-up checks on the set-up group, before development runs.** If one fails we fix wording or format on the set-up group only, log the change, and rerun the set-up group. Development and held-out outputs are never used to change the prompt.

| Check | Pass |
|---|---|
| P1 | At least 98% of responses parse against the schema, refusals under 2% |
| P2 | The notes block in S and in I is of equal length: its mean length in S is within 10% of its mean length in I, and within 15% at every task position at each visibility level. And by code: every Harm- and Help-role task in S has its note in view, no task in I has a note from another region in view, and every prompt shows ten notes. |
| P3 | In I·V+, agreement tasks comply with the agreed term in at least 70% of runs. If not, the agent cannot use a visible agreement in this format and the pilot cannot test the mechanism, so the task wording is revised. |

How P2 is measured (revised after review round 10, Codex R10.7). The length is that of the notes block itself, in characters, counted by code on the prompts actually sent. No tokeniser for this model is available offline, so characters stand in for tokens. The limit at single positions is wider because in the set-up group each position is one prompt per cell. The ratio of whole-prompt tokens counted by the provider is reported beside it under its own name and decides nothing: the price list, policy and register are the same in both arms and can hide a large difference in the notes. In the first set-up run whole prompts differed by 4% to 5% while the notes block differed by 12% (28% at the sixth task). The same lengths are reported for the development prompts, as a description.

**Estimates on development data**, each with a 95% interval. The unit is the task (mean over its 3 replicates). Intervals by bootstrap over shared groups, which is crude with 5 groups and is labelled so; Wilson intervals on pooled counts are reported beside them and also labelled as ignoring clustering.

All contrasts are on task roles (section 3.3): the same task IDs in S and I.

1. Outcome categories (value match × release or escalate) and released-error rates, by cell and role, with exact denominators.
2. Harm: S minus I in released errors on Harm-role tasks, separately at V− and V+.
3. Help: S minus I in compliance with the agreed term on Help-role tasks, at V− and at V+.
4. Spill-over: S minus I in term errors and escalations on Standard- and Own-role tasks.
5. Escalation: rate when the agent cannot verify (agreement roles in V−), and when it can, by cell.
6. Value-match shares (the true value exactly, a price above the floor, planted, standard, another customer's, none) by role and cell. The unit is the task: each task's shares over its valid runs, averaged over tasks. Pooled counts are given beside them.
7. Dependence, on values: in each run of a group, whether both Harm tasks match the planted value (S) or carry the same value that fails the agreed term (I), against what independence would give **for the same event**, computed within each group and averaged over groups. In S that is the product of the two tasks' planted-match rates. In I it is the chance that two independent draws, one from each task's distribution of wrong values, are equal (two values count as equal within EUR 0.005). The spread of per-run error counts beside a binomial with the same mean is a description only, because tasks that differ in risk also widen the spread (review round 10, Codex R10.5).
8. What the stored notes state. For Harm tasks in S: the share stating the planted value only, the share stating both the planted and the true value, and the share that pass the planted value on. For agreement tasks in every cell: the share whose note states the value the quote carries.
9. Realised exposure against role, and the notes-block lengths in S and I, as manipulation checks.
10. Pooled counts of the main outcomes by agreement term type, as a description only (review round 10, Codex R10.9; see section 12).
11. The reading-rule table (review round 11, Claude R11.2), for S·V− and S·V+: group runs counted by what the first Harm task's stored note gives a later reader against the value the second Harm task carries. The first note is one of four kinds: it passes on the planted value; it states another value (the value its quote carries, which is not the planted one), with or without also naming the planted one; it names the planted value only, without stating the value quoted; or it states neither. The second task's value is one of the value-match categories, with one more for a value equal to the first task's when that is none of the known values. **The pattern that contradicts E4's newest-note rule** is the second Harm task matching the planted value although the first one's stored note states another value. Its count is reported over its denominator for each cell, with how many of those first notes also name the planted value.

Estimates 1 to 3 also show what missing runs could change: each rate with every missing run counted as the adverse outcome (a released error, a term error, or a failure to comply), and each S-minus-I contrast with its lower and upper bound over all planned tasks. Contrasts on valid answers use the tasks that have a valid answer in both arms.

No significance tests decide anything. Each measure is reported separately; no combined score.

**Held-out calibration diagnostic, once, at the end of E5.** *Revised after review round 2 (Claude R2.4, Codex R2.6). This is a diagnostic, not a test of transfer.*

- **Quantities.** Released-error rate on Harm-role tasks in S·V−; the same in I·V−; the rate of compliance with the agreed term on Help-role tasks in S·V−; escalation rate on agreement-role tasks in V−, pooled over S and I. Both splits must be finished first: every planned task run valid or missing. The diagnostic scores the development run again, so it runs only if the development estimates on file were made by the current scorer, from the same run file and inputs (review round 11, Claude R11.3). A quantity with no valid answer on the development side or the held-out side is reported as not estimable, with its counts of valid and missing runs. It is neither inside its interval nor flagged, and no interval is drawn from nothing (review round 11, Codex R11.3). The same holds for the sign condition.
- **Unit.** The task: the mean of its 3 replicates. The held-out mean is taken over all tasks of the role in the held-out groups.
- **Interval** (revised after review round 3, Codex R3.7, to keep whole groups together). For each quantity, a 90% predictive interval for the held-out mean, by a two-level bootstrap over whole groups. Draw 10,000 times: resample the 5 development groups with replacement, then draw as many groups as there are held-out groups from that resample, and average over all their tasks of the role. The interval runs from the 5th to the 95th percentile of those means. Seed 20261002. Tasks of one group stay together, so the within-group dependence the pilot creates (order 5 reads what order 3 wrote) is kept.
- **Flag.** A quantity is flagged when its observed held-out mean falls outside its interval. The sign condition compares the S-minus-I Harm difference at V− in development and held-out. A difference of exactly zero on either side counts as a sign mismatch.
- **Reading.** We report each quantity's interval, observed value and flag. We do not tune anything in response.

**Power, computed before any run** (`experiments/agent_pilot_heldout_power.py`, version 2). Groups are simulated with no group effect, or with a group effect (each group's rate drawn around the true rate, Beta concentration 4). Tasks vary within a group (concentration 6), with 3 replicates. The interval is the whole-group bootstrap above. The version 1 numbers, from a model that drew tasks independently, are superseded.

| Quantity | Group effect | Held-out groups | False alarm (no shift) | Flags 0.5 → 0.3 | Flags 0.5 → 0.2 | Flags 0.3 → 0.6 |
|---|---|---|---|---|---|---|
| Harm role, S·V− released error | none | 2 | 19% | 31% | 52% | 56% |
| | none | 6 | 23% | 53% | 77% | 78% |
| | yes | 2 | 16% | 23% | 33% | 39% |
| | yes | 6 | 21% | 38% | 58% | 59% |
| Help role, S·V− correct term | none | 2 | 15% | 20% | 27% | 32% |
| | none | 6 | 20% | 34% | 49% | 56% |
| | yes | 2 | 13% | 18% | 19% | 28% |
| | yes | 6 | 16% | 29% | 45% | 49% |

With 2 held-out groups and realistic dependence, the diagnostic would miss a 20-point shift in the main quantity about 3 times in 4 (it flags 23% to 31%), while raising false alarms 16% to 19% of the time. Passing it would show little, and failing it would not be decisive either. The false alarms run above the nominal 10% because 5 development groups give a narrow interval. Option for Dingying: 6 held-out groups instead of 2, adding about 290 requests (about $11 at the Opus 5.5 estimate in section 10). That raises detection of a 20-point shift to 38% to 53%. Even then this stays a diagnostic.

## 8. Procedure and records

1. Generate the task bank and split, commit them with this plan and the scorer.
2. Run the set-up group in all four cells, apply checks P1 to P3.
3. Run development: for each group, cell and replicate, the six tasks in order, carrying the notes store forward.
4. Score, estimate, write evidence records, update E4 and rerun its comparison.
5. Run and evaluate the held-out groups once.

**Recorded with every request**, one JSON line per request in `experiments/agent_pilot/runs/<run_id>.jsonl`: provider, requested model ID, the model string and the host the response reports, every request parameter (effort, max tokens, sampling settings, host order), the full system prompt and user message and their SHA-256, the scenario (group, cell, replicate, order, task id, split, exposure type as computed), tools (none), the raw response, the parsed output, the note as stored and whether it was cut, stop reason, token usage, cost at list price, request id, UTC timestamps, the fingerprint of the experiment's inputs (below), and the git commit of the code. The API key is read from an environment variable or, at Dingying's request on 2026-10-03, from a git-ignored `.env` file that she fills in herself. The harness sends it only in the request's authorisation header, and never prints it or writes it to a record.

**Interrupted runs** (revised after review round 10, Codex R10.2). A run can stop (a rate limit, the cap, a lost connection) and be resumed. On a restart:

- a task run with a valid recorded answer is replayed from the record, so its note rebuilds the store and nothing is sent twice;
- a task run that has used all its attempts stays missing. It is not requested again and writes no note, so the tasks after it keep the prompts they had;
- a task run that was interrupted continues with the attempts it has left, under new request ids;
- if a replayed prompt differs from the recorded one, the run refuses to continue.

A split is finished when every planned task run is valid or missing. A finished split is never requested again.

**Before the held-out split starts** (review round 11, Codex R11.2 and Claude R11.3). The held-out groups run once, so everything is checked before a request is sent: the set-up checks passed with the current inputs and scorer, the development run is finished, and every development record carries the current input fingerprint. A change of prompt, task bank or request settings after development is found here, and the held-out split is not started.

**Input fingerprints** (review round 10, Codex R10.8). Every record carries one SHA-256 over the experiment's inputs: the prompt-building code, the system prompt, the output schema, the task-bank manifest and the request settings (model, reasoning effort, sampling settings, host order, `max_tokens`, attempts and replicates). Pacing, the number of workers and the cap are not inputs. A resumed run refuses records with another fingerprint before it sends anything, and so does every analysis. The set-up checks store this fingerprint and a second one over the scorer and analysis code. Development starts only if both match the current ones, so a pass obtained with other inputs or another scorer does not count. A set-up rerun after a change of inputs gets a new label (`setup_2`), and the earlier run stays on file.

Each record is also converted to the event format (case = task run; events = prompt assembled, draft returned, decision, note written) so it can be process-mined with the other logs.

**Spending guard** (revised after review round 2, Codex R2.4). Reported usage arrives only after a request, so the guard reserves before it sends:

- The model, its list prices, `max_tokens` (which caps thinking and output together) and the effort level are fixed in a committed config before the first run.
- Before each request, the harness reserves an upper bound on its cost: an upper bound on the input tokens at the input price plus `max_tokens` at the output price. The bound on input tokens is the byte length of the prompt, since no tokeniser produces more tokens than bytes.
- A request is sent only if actual spend so far, plus all outstanding reservations, plus this reservation, stays within the cap.
- After the response, the reservation is replaced by the cost of the reported usage.
- Retries and set-up reruns count like any other request. A request that times out or errors without a usage report keeps its full reservation as spent.
- Before any paid call, the guard is tested with a fake client: requests that would cross the cap are refused; timeouts keep their reservation; concurrent requests cannot overshoot.

## 9. What the pilot feeds into E4

*Revised after review round 2 (Codex R2.1).* The pilot measures observable outcome frequencies, not the latent steps behind them. Reading a note, noticing a conflict and correcting it are not separately identified. An output that matches neither the planted value nor the truth, for example the standard term, has neither adopted the note nor corrected the quote. So each observable frequency below constrains a combination of E4 parameters. Those combinations are recorded as **fitted**; the individual parameters stay **assumed**, but constrained to agree with the fitted combination.

| Observable frequency (exact denominator: role × cell × replicates) | What it constrains in E4 |
|---|---|
| Matches the standard term, agreement roles, I·V− | Not a behaviour parameter: drafting from the template when nothing else is visible. Checks the model's structure. |
| Fails the agreed term, agreement roles, I·V+ | `e_visible`, directly. In E4 `e_visible` is a slip on the registered term being drafted, so only failure on that term constrains it. An unrelated error on the same quote (for example a wrong payment term on a quote that honours the agreed floor) is reported as an outcome and is not used here (review round 10, Codex R10.4). |
| Matches the planted value, **first Harm task only (order 3)**, S·V− (denominator: 5 tasks × 3 replicates) | the product `p_read_note` × `p_adopt_blind` |
| Equals the correct note's value **exactly**, Help role, S·V− | the same product, `p_read_note` × `p_adopt_blind`. The model says the agent cannot tell a right note from a wrong one when it cannot see the register, so the two should agree. If they do not, that model assumption is wrong. An exact match is used, not compliance: a price above the floor complies without showing that the note was used (review round 10, Codex R10.1). |
| Matches the planted value, first Harm task only (order 3), S·V+ | `p_read_note` × (1 − `p_notice_visible`) |
| Matches the planted value, second Harm task (order 5), S | **not** the one-step product: order 5 can also read the note order 3 wrote. Under E4's own rules (a reader reads the newest note), with q = `p_read_note` × `p_adopt_blind`, order 5 matches the planted value with probability about q² overall: order 3's agent must adopt the planted value and write it, and order 5's agent must then adopt order 3's note. If order 3's agent wrote a different value, order 5 cannot reach the planted value through the notes (an earlier version had this backwards; review round 4, Claude R4.6). Pooling orders 3 and 5 would give (q + q²)/2, not q (review round 3, Codex R3.5). Used only to check propagation against the sequence the model predicts. |
| Escalation, agreement roles, I·V− (request cites agreed terms, no register, no note) | `p_flag_unverifiable` |
| Escalation on tasks the agent can verify | unnecessary escalation, a model check |
| Joint value match on Harm tasks, S against I | error dependence within a shared group |
| The stored note states the value the quote carries, agreement roles | the endogenous note mechanism: E4 assumes that a note records the drafted term. Reported by cell; not a parameter. |

**A structural difference to test, not to estimate away.** The pilot's prompt shows the ten most recent readable notes, so order 5 can see both the planted note and order 3's note. E4 reads only the newest note about the customer's term. If agents in the pilot use older notes, or weigh conflicting notes, E4's reading rule is wrong for this setting and must change before the pilot's numbers are put into it. The value matches on order 5 (planted value, order 3's value, the truth, the template) show which reading rule the agents follow. Section 9.1, rule 7, says how the reading rule is tested and what replaces it.

The task roles stay fixed in the S-against-I comparison, which uses both Harm tasks on matched task IDs. Only the mapping to E4's one-step parameters is restricted to order 3.

Each becomes an evidence record with status "fitted", the conditions above, the model and version, and the interval. Transfer to the classroom quotation episode is analogue: synthetic tasks, one model, one prompt.

### 9.1 The rules for putting the pilot's numbers into E4

*Written on 2026-10-03 at 10:34 UTC, after the set-up runs and before any development request. The rules are code (`experiments/e4_quotation/apply_pilot.py`, tested on made-up frequencies), committed before the development run, so that no range is chosen after an outcome is seen.*

1. **The interval of a frequency.** It runs from the smaller lower end to the larger upper end of two 95% intervals: the bootstrap over the five development groups, and the Wilson interval on the pooled counts. The bootstrap is crude with five groups and the Wilson interval ignores that runs of one group belong together, so neither is trusted alone. If fewer than two groups have data, the Wilson interval is used alone.
2. **`e_visible`.** Its range becomes the interval of "fails the agreed term" on agreement-role tasks in I·V+.
3. **`p_flag_unverifiable`.** Its range becomes the interval of escalation on agreement-role tasks in I·V−.
4. **The product q = `p_read_note` × `p_adopt_blind`.** Its range covers two intervals: the planted-value match on the first Harm task in S·V−, and the exact match with the correct note on the Help task in S·V−. E4 has one adoption probability for right and wrong notes, so its range must cover both. Whether the two intervals overlap is reported as a check of that assumption.
5. **The product r = `p_read_note` × (1 − `p_notice_visible`).** Its range is the interval of the planted-value match on the first Harm task in S·V+.
6. **Drawing the three note parameters.** q and r are drawn from their ranges. `p_read_note` is drawn from its declared range (0.3 to 1.0), cut from below at the larger of q and r, since neither product can exceed it. Then `p_adopt_blind` = q / `p_read_note` and `p_notice_visible` = 1 − r / `p_read_note`. The pilot cannot separate reading a note from adopting it, so `p_read_note` stays an assumption.
7. **The reading rule.** E4's first model says a reader takes only the newest note about the customer. Then the second Harm task cannot match the planted value when the first Harm task's stored note states another value. The pilot shows this directly (estimate 11 in section 7): among second Harm tasks in S·V− whose first Harm task's stored note states another value, the share b that still match the planted value. The rule predicts zero. Runs in which the first note passes the planted value on, or states no other value, cannot tell the rules apart and are reported beside it.
   - E4 now has a parameter `p_newest_note`: the chance that a reader takes the newest readable note, and otherwise one of the older ones. At 1 it is the first rule. Then b = (1 − `p_newest_note`) × q.
   - Its range becomes 1 − (upper end of b) / (lower end of q) to 1 − (lower end of b) / (upper end of q), kept within 0 to 1.
   - With fewer than 5 qualifying runs the rule stays as it was and is reported as untested.
   - *Revised after review round 11 (Claude R11.1 and R11.2), before any development run.* The first version took the qualifying runs to be those whose first note did not contain the planted number. A note can name that number in order to reject it, so the runs are now sorted by what the note states.
   - *Revised on 2026-10-03 13:54 UTC after review round 12 (Claude R12.1; Codex R12.1, R12.2 and R12.4), when the development run had finished.* Under rule 10 this revision counts as chosen afterwards. It was asked for by reviewers who had not seen the development outcomes and argued from made-up numbers. The rule as written above is still evaluated, and its result is recorded beside the revised one in `reports/E5/e4_update.json`. The revised rule:
     - **Which runs count.** Only *distinguishing* runs: second Harm tasks in S·V− whose first Harm task's stored note states another value and does not name the planted value at all. If that note also names the planted value (for example "the earlier note said 45 days; quoted 30"), a later reader could take the planted number from the newest note itself, so a match shows nothing about which note was followed. Those runs are *ambiguous* and are reported separately.
     - **A counterexample and a calibration are different things.** One distinguishing run that matches the planted value contradicts a rule that says "never", however few runs there are, and is reported as a counterexample. The parameter is changed only when there are at least 5 distinguishing runs and at least one counterexample. Otherwise `p_newest_note` stays at 1: the width of an interval from a handful of runs is not evidence against the rule.
     - **How it is changed.** Not by a range of its own. The interval of b is kept beside those of q and r. In each parameter draw b is drawn from its interval, never above the q of that draw, and `p_newest_note` = 1 − b / q. So every draw agrees with every measured interval. If the intervals cannot both hold (the lower end of b lies above the lower end of q), nothing is changed and that is reported.
     - **A sensitivity run.** Whatever the outcome, the comparison is run once more with `p_newest_note` at the lowest value the pilot leaves possible, which is 0 when there is no distinguishing run. It is a labelled description; no conclusion is frozen from it.
     - **What b means.** That a reader who leaves the newest note takes an older one is an assumed explanation of b, not something the pilot measures. And a value counts as stated when a number in the note equals it: a check on numbers, not on meaning.
8. **Escalation after using a note.** E4's first model says an agent that used a note does not escalate the quote as unverifiable. The pilot shows the escalation rate among S·V− runs whose agreed term equals the note's value exactly (first Harm tasks that equal the planted value, Help tasks that equal the correct note's value). E4 now has a parameter `p_flag_after_note` for it, 0 in the first model. Its range becomes the interval of that rate. With fewer than 5 such runs it stays 0 and is reported as untested. A run that contradicts the rule is reported as a counterexample whatever the number of runs (review round 12, Codex R12.4); the threshold of 5 decides only whether the range is replaced.
9. **Everything else in E4 stays as declared.** The script changes those ranges in `evidence/assumptions.yaml` once, with a dated entry, and records every number it used in `reports/E5/e4_update.json`. The development comparison is then run again, and `experiments/e4_quotation/compare_runs.py` lists every comparison that held before and no longer holds, holds now and did not before, or reversed. *Added after review round 12:* before it changes anything, the script refuses development estimates that were not made by the current scorer, from the current inputs and from the run file on disk (Codex R12.5). It keeps the comparison under the declared assumptions as `reports/E4/results_before_pilot.json`, after checking that it is that run (Claude R12.2). The comparison is also run once per changed rule with every other range as declared, as a description of which rule moved which comparison (`experiments/e4_quotation/pilot_update_sensitivity.py`).
10. **No rule is changed after development outcomes are seen.** If an outcome shows that one of these rules is itself unsuitable, the rule is still applied as written, the problem is reported, and any other treatment is shown beside it and labelled as chosen afterwards. *Applied once, in review round 12:* rule 7 was revised after the development run had finished. The rule as first written and the revised rule are both evaluated. On this pilot's data they have the same effect, which is to leave `p_newest_note` at 1.

Two limits of these rules.
- The two new parameters are the smallest change that lets E4 follow what the pilot can show. With defaults they reproduce the first model exactly: the same 26 parameter draws and the same simulation output, checked by hash. Other reading rules are possible. In the pilot exactly one older note exists, so it cannot tell "one of the older notes" from other ways of weighing several older notes.
- The ranges are intervals from 15 to 60 task runs of one model on synthetic tasks. They replace assumptions with early evidence, and they are still wide.
- The pilot fits frequencies and products. `e_visible`, `p_flag_unverifiable` and `p_flag_after_note` are each a frequency the pilot measured, so their evidence records are fitted. `p_adopt_blind`, `p_notice_visible` and `p_newest_note` only follow from a fitted product and an assumed parameter, so they stay assumed, with the constraint and the fitted records named. `p_read_note` stays assumed too; after the update it is drawn from its declared range cut from below at the larger product of the same draw (review round 12, Codex R12.3).

## 10. Model, key and budget: Dingying decides

**Model.** Two options from the handoff:

- **One provider's current model**, matching what a classroom would use. Simple to set up. Behaviour can change when the provider retires or updates the model, so results are tied to the model string recorded with each run.
- **A frozen or open-weight snapshot**, rerunnable indefinitely for research. Cost and set-up depend on where it runs.

The harness is written so the same tasks can later run on a second model for comparison. My suggestion is to run the pilot on one model first and choose the second after seeing whether the set-up works.

**Cost estimate** at Anthropic list prices (checked 2026-10-02 UTC; other providers not checked). About 600 requests, about 2,500 input tokens each (1.5M in total) and up to about 1,500 output tokens each including thinking (0.9M in total):

| Model | Input $/1M | Output $/1M | Estimated cost |
|---|---|---|---|
| Claude Haiku 4.5 | 1 | 5 | about $6 |
| Claude Sonnet 5.5 | 2 | 10 | about $12 |
| Claude Opus 5.5 | 4 | 20 | about $24 |
| Claude Fable 5.1 | 10 | 50 | about $60 |

The output figure is the uncertain part, because thinking tokens are billed as output. We will set the effort level before running and record it. The Batch API halves the price but fits a sequential notes store awkwardly; not planned.

**Suggested cap:** about twice the estimate for the chosen model (for example $50 for Opus 5.5), enforced by the harness.

**Key.** The name of the environment variable that holds the key (for example `ANTHROPIC_API_KEY`).

**Dingying's decisions, 2026-10-03 (about 08:45 to 08:55 UTC, in chat).**
- **Provider:** OpenRouter. The key is `OPENROUTER_API_KEY`, kept in the git-ignored `.env` file in the project folder, which she filled in herself.
- **Spending cap:** 15 USD. She also set a 15 USD limit on the key at OpenRouter, so the cap holds on the provider's side whatever the harness does.
- **Model:** a free open-weight model, `qwen/qwen3.8-27b:free`. OpenRouter lists its canonical slug as `qwen/qwen3.8-27b-20260814` and its weights as `Qwen/Qwen3.8-27B` on Hugging Face. It costs nothing, so the expected spend is 0 USD.
- **How she got there.** She first asked for Claude Sonnet 5.5 through OpenRouter's batch interface (about 3 to 6 USD). She then asked whether Claude Code sub-agents could play the agent instead of a model called through an API. I advised against it: a sub-agent runs inside this project, can open the task bank with the answers, and cannot be pinned or recorded as section 8 requires. She chose the free model.

**What the choice changes in this plan.**
- The request settings are in `experiments/agent_pilot/config.yaml`, committed before the first run: reasoning effort `low` (the model's default is `xhigh`), `max_tokens` 6000, and the output schema enforced through OpenRouter's structured outputs.
- `max_tokens` caps reasoning and answer together. It was 3000 in the first two set-up runs. There the answer took 97 to 186 tokens, while reasoning took up to 1,810 tokens in the first run and 2,112 in the second, both times on the second Harm task with shared notes and no visible agreement. An answer cut off at the limit does not parse, and losing answers in that cell more often than in others would bias the main contrast. The limit was raised to 6000 before any development run, and the set-up group was run a third time (`setup_3`).
- Sampling settings are sent with every request, at the values OpenRouter lists as the model's defaults: temperature 1 and top_p 0.95. The host does not accept `top_k`, so it cannot be sent and the host's own default applies (OpenRouter lists 20). Revised after review round 10, Claude R10.2: the first version sent no sampling settings.
- Free models on OpenRouter allow 20 requests a minute and, for this account, 1,000 a day. The harness starts at most about 18 requests a minute. On a rate-limit refusal it waits and sends again without using up one of the task run's three attempts, and on a daily-limit refusal it stops and can be resumed.
- OpenRouter lists one host for this model, "ModelRun" (endpoint `modelrun/fp4`). Requests are pinned to it with no fallback, so a request fails instead of going to another host. The host each response reports is recorded as its own field and counted by cell before anything is estimated.
- That endpoint serves a 4-bit version of the published weights, not the full-precision model (section 12).
- The cost table above is at Anthropic's list prices and no longer applies.

## 11. What we will not do

- Tune prompts, tasks or scoring after seeing development or held-out outcomes, or to make either arm look better.
- Read the held-out results before the end of E5, or more than once.
- Attach national or cultural traits to regions or customers.
- Treat pilot rates as stable estimates or as a ranking of designs.

## 12. Limits

- One model, one prompt, synthetic tasks. The estimates describe this set-up, not agents in general.
- The request cue ("terms we agreed") makes "cannot verify" well defined. Real requests are often less explicit, so escalation rates here are likely higher than in practice.
- Every group has exactly one wrong note and one helpful note. The ratio of wrong to correct shared notes in a real organisation is unknown; the pilot estimates per-note behaviour, not how often notes are wrong.
- Region A's role as the only seed author is a simplification.
- Five development groups give little information about dependence between tasks; that estimate is the weakest.
- The model is a 27-billion-parameter open-weight model served free of charge. Its behaviour need not match a larger commercial model that a classroom might use. The harness can run the same tasks on a second model later.
- The free endpoint serves a 4-bit version of the weights. Its behaviour may differ from the full-precision model that the published weights give, so the results describe this endpoint.
- A free endpoint's host may keep prompts. The prompts hold only invented companies and terms.
- Rates are over valid answers. If answers fail more often in one arm, leaving them out could bias a contrast, which is why each main contrast is also given with missing runs counted as the worst outcome.
- The term types are not spread evenly over the splits. The Harm customer has a price floor in two development groups, a delivery term in two and a payment term in one; in the held-out groups it has a payment term in one and a price floor in the other, and no delivery term. A shift between development and held-out can therefore come from the mixture as well as from the wording or the behaviour. Counts by term type are reported beside the pooled estimates; a balanced design needs more groups (review round 10, Codex R10.9).

## 13. Decisions needed from Dingying

1. **Model**: decided on 2026-10-03, `qwen/qwen3.8-27b:free` through OpenRouter (section 10).
2. **API key**: decided, `OPENROUTER_API_KEY` in the git-ignored `.env` file.
3. **Spending cap**: decided, 15 USD.
4. Optional: whether to add a fifth cell, shared notes with no wrong note at V− only, to measure whether one wrong note changes behaviour on the group's other tasks. Adds about 25% to the cost. Not in the plan unless she asks.
5. Optional: 6 held-out groups instead of 2 (about 290 more requests). This raises the diagnostic's chance of flagging a 20-point shift from 23% to 31% to between 38% and 53%, depending on dependence within groups (section 7). Not in the plan unless she asks.

## 14. Changes after review round 10, before any development run

Both reviewers read the harness at commit c05782e. At that point only the set-up group had run (24 task runs, on 2026-10-03 from 09:10 to 09:13 UTC). No development or held-out request had been sent, so every change below was made before any outcome that the pilot analyses existed. The plan allows changes on the set-up group (section 7).

| Change | Why | Review point |
|---|---|---|
| The delivery term names one value in both wording templates ("must state a delivery time of N days"). | "Within N days" is a bound, so a planted shorter time also satisfied the true term and would have been scored as an error. | Claude R10.1 |
| Compliance with the agreed term is scored apart from an exact value match. A price above the floor complies and has its own value category. | A price floor is a bound. The first scorer counted a price above the floor as wrong on the agreed term. | Claude R10.1, Codex R10.1 |
| Check P3, the Help contrast and the held-out diagnostic use compliance. The note-adoption constraints on E4 keep exact matches. | Compliance says the quote is right. Only an exact match says the output equals the note's value. | Codex R10.1 |
| `e_visible` is constrained by failure on the agreed term, not by any term error on the quote. | That is what the parameter means in E4. | Codex R10.4 |
| A task run that used all its attempts stays missing after a restart. A split is finished when every planned run is valid or missing. | A second round of attempts after a restart could have written a note that later tasks never saw. | Codex R10.2 |
| Planned runs come from the bank, cells and replicates. Missing runs are counted for every planned cell and role. Each main contrast also has a worst-case version. Value shares are task averages. | The first analysis took its denominators from the valid answers only. | Codex R10.3, Claude R10.3 |
| The independence baseline is computed for the same event as the joint outcome. | The first baseline multiplied "any wrong value" rates while the joint outcome asked for the same wrong value. | Codex R10.5 |
| Note propagation is scored on the stored note. | Only the first 40 words reach the store. | Codex R10.6 |
| Check P2 measures the notes block in characters, overall and by position. Seed notes are 21 to 25 words long. | Whole-prompt tokens hid a 12% difference in the notes block. Short seed notes made the shared arm's block grow as agent notes replaced them. | Codex R10.7 |
| Temperature and top_p are sent explicitly, the host is pinned, and the host is recorded as its own field. | So that neither can change part way through a run. | Claude R10.2 |
| Every record carries a fingerprint of the experiment's inputs, and development needs set-up checks made with the same inputs and scorer. | A clean git tree alone did not stop old records being mixed with new requests. | Codex R10.8 |
| The mixture of term types by split is reported, with counts by term type. | Development and held-out do not hold the same mixture. | Codex R10.9 |
| `max_tokens` raised from 3000 to 6000. | In the second set-up run reasoning alone reached 2,112 tokens on the second Harm task in S·V−. Answers cut off at the limit would be lost unevenly across cells. | Claude R10.3 (the same risk), found on the set-up group |

The task bank is regenerated and committed again with its new hashes, together with this revision. The set-up group is then run again under the label `setup_2`, and checks P1 to P3 are applied to that run. The first set-up run (`setup_1`) used the old bank and scorer and is superseded; its file stays in the repository.

`setup_2` (2026-10-03, 10:07 to 10:10 UTC, commit da00a9e) passed P1 to P3 with the corrected measures. It also showed the reasoning length above, so `max_tokens` was raised and the set-up group run once more as `setup_3`. Development requires the checks of `setup_3`, because the input fingerprint includes `max_tokens`. All three set-up files stay in the repository. Set-up answers are used for these checks only.

## 15. Changes after review round 11, before any development run

Both reviewers read the fixes of section 14 at commit adb0e7d (2026-10-03). Neither raised a Blocking point, and neither asked for a change to the task bank, the prompt or the request settings. The six points below concern the analysis and the gates. They were applied before any development request, so none was shaped by an outcome.

| Change | Why | Review point |
|---|---|---|
| A stored note is sorted by what it states: the planted value only, the true value only, both or neither; whether it states the value the quote carries; whether it passes the planted value on. | The first measure counted any note that contained the planted number. In the third set-up run both Harm notes with the agreement visible named the planted 45 days in order to reject it, and would have counted as passing it on. | Claude R11.1 |
| The reading-rule table is a fixed output (estimate 11), and the pattern that contradicts E4's newest-note rule is named in advance. Rule 7 of section 9.1 uses it. | Section 9 promised this test, and no estimate computed it. The table would have been built after outcomes were seen. | Claude R11.2 |
| A contrast gets a true lower and upper bound over missing runs. Filling both arms with the adverse outcome is kept as a labelled scenario. | Filling both arms the same way is one scenario, not a bound on a difference. | Codex R11.1 |
| The held-out split starts only if the set-up checks hold for the current inputs and every development record carries the current input fingerprint. The diagnostic runs only on development estimates made by the current scorer. | The held-out groups can be used once. A mismatch must stop the run before it starts, not the analysis after it. | Codex R11.2, Claude R11.3 |
| A diagnostic quantity with no valid answer is reported as not estimable. A picture shows "n/a" where nothing was measured and "0" for a measured zero. | An empty category must not crash the diagnostic, count as a pass, or look like a measured zero. | Codex R11.3 |

The scorer's fingerprint changed with these fixes, so the set-up checks were applied again to `setup_3`. That needs no request. The task bank, the prompt and the request settings are those of `setup_3`.

## 16. Changes after review round 12, after the development run had finished

Both reviewers read the E4 update rules and the round 11 fixes at commit 595b91c. Codex (review) wrote during the development run, on the pinned commit, which holds no development record, and calls its examples static. Claude (review) wrote after the run and says it had not read the development outcomes. Their examples use made-up numbers. Neither raised a Blocking point. I had seen the development outcomes when I applied the nine points (2026-10-03 13:54 UTC). So every change below is labelled as made after outcomes existed. None changes the task bank, the prompt, the request settings or any outcome definition.

| Change | Why | Review point |
|---|---|---|
| Rule 7 counts only distinguishing runs: the first Harm note states another value and does not name the planted one. Notes that also name it are reported as ambiguous. | A later reader could take the planted number from such a newest note itself, so a match does not show that an older note was followed. | Codex R12.2 |
| `p_newest_note` stays at 1 unless there are at least 5 distinguishing runs and at least one counterexample. | The first rule divided the ends of two intervals, so its range reached towards 0 whenever runs were few, even with no counterexample. A changed comparison would then have come from the width of that range, not from the pilot. | Claude R12.1 |
| When it does change, b is kept as a constraint beside q and r and `p_newest_note` follows from b and the q of the same draw. | A range of its own allowed combinations that the measured intervals exclude. | Codex R12.1 |
| A counterexample to a "never" rule is reported whatever the number of runs. | Whether a counterexample exists does not depend on having five observations. | Codex R12.4 |
| One more run of the comparison with `p_newest_note` at the lowest value the pilot allows, as a labelled description. | To show how much the comparison depends on a rule the pilot may not be able to test. | Claude R12.1 |
| Parameters that only follow from a fitted product stay assumed in the evidence records; `p_read_note`'s record says how it is drawn. | The pilot fits the products, not their factors. | Codex R12.3 |
| The update refuses estimates from another scorer, other inputs or another run file, before changing anything. | A clean but stale estimate could otherwise be applied. | Codex R12.5 |
| The script keeps the "before" comparison itself, after checking it; and the comparison is run once per changed rule. | The "before" file was put in place by hand, and several ranges change at once. | Claude R12.2 |
| Flip points sweep the measured product when the driver is a note parameter. | Sweeping one note parameter alone moves a product outside the pilot's interval. | Claude R12.3 |
| The two new parameters' records carry the time they were declared. | They showed the date of the file. | Claude R12.4 |

One difference between the reviewers, resolved here and listed for Dingying. For the case where the pilot contradicts the reading rule, Claude R12.1 asks for a range of `p_newest_note` from a bootstrap over groups of 1 − b/q, and Codex R12.1 asks for the parameter to follow from b and q draw by draw. I chose Codex's form, because it keeps every draw consistent with both measured intervals, and kept Claude's two other requests (no change without a counterexample; the sensitivity run). With this pilot's data the case does not arise.

What the two versions of rule 7 give on the development data: as first written, 1 qualifying run, fewer than 5, so untested and unchanged; as revised, no distinguishing run, so not assessed and unchanged. Either way `p_newest_note` stays at 1 in the main comparison.

The scorer's fingerprint changed again (the first-note classes and one gate moved), so the development estimates were recomputed from the same records and the set-up checks applied again. No model request was needed.
