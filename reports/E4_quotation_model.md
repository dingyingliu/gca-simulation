# E4. The quotation research model and a first comparison of designs

**Read this first (2026-10-03 14:40 UTC).** Sections 1 to 13 report the comparison under the declared assumptions, before the agent pilot. Section 14 reports what changed when the pilot's estimates were put in, and the robustness check. Where the two differ, section 14 is the current result.

Claude Code (build), 2026-10-02 (UTC). Early result. **Revised at 23:45 UTC after review round 3, and on 2026-10-03 at 00:40 UTC after review round 4:**
- wrong terms and releases beyond authority are now separate measures;
- the policy gate's effect is restated;
- the draws that reverse a conclusion are listed;
- a bypass-timer bug is fixed.

**Revised again at 01:40 UTC after review round 5:**
- the speed reversals are restated with their full conditions, and a two-driver sweep added;
- the run standard error of a pooled difference is computed at seed level;
- section 11 is corrected on what changed the review-against-local comparison.

**Revised at 02:28 UTC after review round 6:** the sweep figure gives each column its own legend, and its overlay of the development draws is checked against the run it came from.

Round 3 made two model changes:
- The engine now enforces the written limits as a hard permission (the policy gate).
- Review time is split into capacity-consuming effort and a response delay.

The first comparison (run at ec16504) is superseded and kept in git history; section 11 says what changed.

**Labels.** Every number in sections 4 to 8 is a model output computed from **assumed** parameter ranges. None is observed. The walkthrough's numbers quoted for comparison are **illustrative**. The results describe what this model does under these assumptions, not how real organisations behave.

## 1. Question

When routing can only act on what people and agents can actually see, how do the three walkthrough designs compare on errors reaching customers, days to customer, review load and releases without approval? Does sharing agents' notes across regions change that? What does a shared-context mechanism add beyond independent errors? Which conclusions hold across the declared ranges, and which depend on assumptions?

## 2. Data

- **Cases.** The walkthrough's 20 quotes as world truth only (W0), without its behaviour fixtures or its routing by true kind. Four generated development weeks (G1 to G4) with the same composition per week (11 standard, 5 agreement, 1 verbal promise, 3 beyond policy) and two cross-market repeat customers. All frozen in `specs/quotation_cases/` (42d16f3).
- **Parameters.** 26, each declared with a range in `evidence/assumptions.yaml` and each with an evidence record (`evidence/records/quotation.*.json`). All are **assumed**. The E3 elapsed gaps are cited as context for the four time parameters, not as bounds (review round 3, Codex R3.3). The ranges were changed once after the first comparison, for the reasons logged in the file's `changes` list (22:58 to 23:36 UTC) and declared before this rerun.
- **Robustness check (held-out weeks).** Four generated weeks (H1 to H4) with customers disjoint from development, frozen with hashes. They come from the same generator, so they test whether the conclusions depend on which synthetic weeks were drawn, not the model against anything independent (review round 3, Claude R3.4). Not run. They are evaluated once, after E5, by `run_e4.py --heldout-final`. That command applies the declared rule to development conclusions frozen beforehand, and refuses to run twice.

## 3. Method

**Truth, observation and decision are kept apart.** Truth (`gca_sim/quotation/truth.py`) holds each request's true category and correct terms, and who holds which agreement. Each role receives an observation (`observations.py`) holding copies of only what it can see under the design. Decisions (`decisions.py`: draft, recognise a local exception, check own draft, route, review) take only an observation, matched random draws and parameters, and can be wrong. The engine runs every decision inside a guard where reading any truth object raises an error.

**Routing acts on observable features only:** a request beyond a written limit, the agent's own recognition of a local exception (from a cue in the request or a register entry it can see; recognition can fail either way), and the customer record's owning market. It never uses the true category, unlike the walkthrough (its line 480).

**Hard permissions.** With the policy gate on, which is the main model, the system refuses any release by an agent or a lead whose terms exceed the written limits without head-office authorisation, and escalates the quote to head office (review round 3, Codex R3.1). **Head office authorises every exception it sees** (`decisions.review`). A beyond-policy quote released by head office is never counted as wrong, so with the gate on, releases beyond authority are zero by construction. The gate checks releases by agents and leads only, not a quote the sales team sends out after a bypass (section 6). With the gate off, a labelled sensitivity, those releases go out and are counted, as in the walkthrough (Q12). The gate never changes which terms are wrong (section 6). Which is the main model is Dingying's decision (LAB_LOG Q7).

**Review time (new).** A review occupies the reviewer for its effort (lognormal, median `effort_lead` or `effort_ho`). The decision then goes out after a response delay (median `delay_lead` or `delay_ho`) that uses no capacity. One first-in-first-out server per regional lead and one for head office. Detection falls with backlog (`lambda_workload`). Time is in working days.

**The three designs**, as in the walkthrough presets:

| Design | Registers shared with agent and head office | What the agent may release | What goes to a person |
|---|---|---|---|
| Review every quote | No | Nothing | Every quote to the drafting market's lead |
| Release within shared limits | Yes | Drafts that pass its own check | Requests beyond limits and drafts its check flags, to head office |
| Refer local exceptions | No | Drafts that pass its own check | Requests beyond limits to head office; cross-market accounts to the owning lead; recognised local exceptions to its lead; flagged drafts to head office |

In every design, the gate escalates any release attempt beyond the written limits to head office.

**Shared context as a mechanism.** Each agent writes a note per quote about the customer's term. A later draft reads the newest readable note with probability `p_read_note`. If the agent can see the register and the note contradicts it, it notices with probability `p_notice_visible`. Without the register, it adopts the note with probability `p_adopt_blind`, right or wrong. Shared context makes every region's notes readable; isolated context only the drafting region's own. Out-of-date notes can exist at the start of a week. Whether notes record drafted or released terms is a structural assumption; both are run.

**Independent-errors baseline.** Each quote's drafting outcome is drawn independently from its own distribution in the full model, with notes off. Everything after drafting is unchanged.

**Uncertainty.** 64 Latin-hypercube draws over the declared ranges (parameter uncertainty) × 64 seeds with matched random streams (run-to-run variation), five development weeks pooled.
- **Run SD:** one week's spread across seeds.
- **Run SE of a pooled difference** (used to judge reversing draws): the paired difference is averaged over the five weeks within each seed, and the standard error is its spread over the 64 seeds. The weeks are fixed cases and share the seeds, so they are not independent replicates (review round 5, Codex R5.2).
- **Parameter range:** the 5th to 95th percentile of draw means.
- **Holds across the declared ranges:** the sign is the same in at least 95% of draws. The shares assume every value in each declared range is equally likely (uniform sampling). That matters most for `effort_lead`, whose range spans a factor of 12.
- **Flip points:** each conclusion's two top drivers swept one at a time over their whole domain (probabilities 0 to 1, times 0 to 3 days), with the other parameters at central values (`experiments/e4_quotation/flip_points.py`).

**Tests** (all 253 tests in the repository pass, 2026-10-03 02:28 UTC):
- the access test, with a planted cheating decision;
- hard constraints over every design, context, notes assumption, development week, central and corner parameters and several seeds: each quote released once; no release beyond the design's authority; no agent or lead release beyond the written limits; approver and rule recorded; queue accounting conserved; time never backwards; same seed identical output;
- deterministic tests for the Q18 counterexample and for a missed agent check;
- trace completeness: provenance of sampled world states, both outcomes of routing checks, note lineage, old and new values, owner queries, and every cited evidence id resolving;
- matched streams; the held-out evaluator and guard, on fabricated inputs.

**Decision–consequence log.** One JSONL file per configuration for the walkthrough week at central values, seed 0 (`reports/E4/traces/`). Each starts with a run manifest (case hash, parameters, seed, code commit), then records evaluator-only provenance events and every decision. Each decision event carries the observation the actor had and the evidence ids of the parameters that shaped it. Notes have ids linking writer and reader. Event tables for process mining are written alongside.

## 4. Results: the three designs (development weeks pooled, isolated notes, notes record drafted terms, gate on)

| Measure, per week | Review every quote | Release within shared limits | Refer local exceptions |
|---|---|---|---|
| Quotes with wrong terms reaching customers (of 20) | 2.94 (2.05 to 3.87; run SD 1.17) | 1.66 (1.15 to 2.24; run SD 1.00) | 3.78 (2.62 to 4.80; run SD 1.29) |
| Average days to customer | 3.13 (1.18 to 5.10; run SD 0.44) | 1.06 (0.69 to 1.46; run SD 0.27) | 1.40 (1.01 to 1.83; run SD 0.26) |
| Human reviews | 20 lead + 1.0 head office (gate) | 3.9 head office | 5.8 lead + 3.4 head office |
| Busiest lead's review effort, share of the week | 1.38 (0.33 to 2.38) | 0 | 0.54 (0.12 to 0.92) |
| Releases beyond authority (zero by construction with the gate on and the bypass off) | 0 | 0 | 0 |
| Releases with no recorded approval (zero with the bypass off) | 0 | 0 | 0 |
| Customers with inconsistent terms across quotes | 1.15 | 0.08 | 1.04 |

Ranges in brackets are parameter ranges (5th to 95th percentile of draw means). Releases beyond authority are zero because the gate escalates them. Releases with no recorded approval are zero because the bypass assumption is off. Section 6 shows both switched the other way. Figures: `reports/E4/tradeoff_errors_days.png`, `reports/E4/measures_two_uncertainties.png`.

**Where the errors come from** (quotes per week of each kind in brackets):

| Errors by kind | Review every quote | Release within shared limits | Refer local exceptions |
|---|---|---|---|
| Standard (11) | 0.37 | 0.75 | 0.64 |
| Written agreement (5) | 2.34 | 0.12 | 2.52 |
| Verbal promise (1) | 0.23 | 0.79 | 0.62 |
| Beyond policy (3) | 0.00 | 0.00 | 0.00 |

The mechanisms behind the numbers:

- **Release within shared limits.** The agent and head office can read the registers, so agreement quotes are drafted right in the first place. Nobody can catch a promise written nowhere, and no person reads standard quotes.
- **Review every quote.** Leads catch most of their own market's agreement errors, but cross-market ones only if they think to ask. Their load now ranges from comfortably under capacity to more than twice over, depending on the effort per review.
- **Refer local exceptions.** The agent recognises roughly 40% of local exceptions from what it can see; the rest are released from the template.

## 5. Which conclusions hold across the declared ranges

**Hold across the declared ranges** (at least 95% of draws, in all four combinations of context and notes):

| Conclusion | Share of draws | Top drivers (Spearman) | Flip point, one driver at a time, others central |
|---|---|---|---|
| Shared limits has fewer wrong terms than Review every quote (1.3 fewer per week, 0.3 to 2.3) | 97% to 98% | `p_detect_informed` −0.83, `e_std` −0.45 | `p_detect_informed` alone: no reversal on 0 to 1 (gap 0.35 even at perfect detection); `e_std` alone: reverses above 0.395, outside its range (0.02 to 0.15) |
| Shared limits has fewer wrong terms than Refer local exceptions (2.1 fewer, 1.1 to 3.0) | 100% | `p_detect_informed` 0.73, `p_cue` 0.71 | neither alone reverses it |
| Review every quote has fewer wrong terms than Refer local exceptions (0.8 fewer, 0.1 to 1.6) | 95% to 98%, gate on or off | `p_cue` 0.56, `e_std` −0.36 | neither alone reverses it |
| Review every quote is slower than Refer local exceptions (1.7 days more) | 97% | `effort_lead` 0.96, `delay_lead` 0.45 | neither alone reverses it. Two draws inside the ranges do, and so does part of the two-driver sweep at a short lead response delay (below) |
| Review load ranks Review every quote (21) above Refer local exceptions (9) above Shared limits (4) | 100% | case composition | none |
| Shared limits has fewer customers with inconsistent terms, and fewer repeat customers all wrong, than both others | 100% | `p_cue`, `e_visible`, `p_detect_informed` | none |
| Review every quote has more repeat customers all wrong than Refer local exceptions (0.13 more) | 100% | `p_query` −0.54, `p_detect_informed` −0.45 | `p_detect_informed` alone: reverses below 0.31, outside its range (0.6 to 0.95) |

On wrong terms, days and review load together, Shared limits is no worse than Review every quote in 91% to 92% of draws, no worse than Refer local exceptions in 92% to 94%, and no worse than both at once in 86% to 89%. Those multi-measure statements fall short of the 95% bar because of speed, which depends on review effort.

These conclusions hold across the declared ranges, and each is **conditional on assumed reviewer detection, which has no evidence**. They also rest on structural choices the ranges do not vary:
- the walkthrough's bundling of shared registers with the release design (the comparison cannot separate information access from release authority; LAB_LOG Q8);
- one lead per market working first in first out;
- one term at risk per quote;
- fallible recognition in Refer local exceptions;
- the policy gate (LAB_LOG Q7).

The flip-point column says only that **no single driver, moved alone from central values, reverses the conclusion within its declared range** (review round 4, Claude R4.2). Combinations can reverse it, and do in a few draws.

**Draws inside the declared ranges that reverse a conclusion held in fewer than 100% of draws** (isolated notes, drafted terms unless stated; all listed in `reports/E4/results.json` under each comparison's `reversals`):

| Conclusion | Reversing draws: difference (run SE) and the values that matter | Larger than two run SEs? |
|---|---|---|
| Shared limits fewer wrong terms than Review every quote | draw 46: −0.07 (0.06); informed detection 0.94, standard slips 0.15. Shared notes add draw 5: −0.01 (0.09), detection 0.88. | No. Both are within run noise. |
| Review every quote fewer wrong terms than Refer local exceptions | draw 22: +0.12 (0.08), cue rate 0.51, query 0.12, escalation when unverifiable 0.78; draw 39: +0.03 (0.08); draw 49: +0.003 (0.08) | No, except draw 22 with shared notes recording released terms (+0.19, SE 0.09). |
| Review every quote slower than Refer local exceptions | draw 3: −0.14 days (0.015): lead effort 0.18 days, lead response delay 0.14, head-office effort 1.64; head office at 122% of capacity under Refer local exceptions and 15% under Review every quote. Draw 63: −0.22 (0.025): lead effort 0.22, delay 0.04, head-office effort 1.38; head office at 114% against 24%. | **Yes.** Reviewing everything is faster only when lead reviews are quick, in both effort and response delay, and head office is slow in the other design, where in both draws it is over capacity. Seven other draws with lead effort under 0.25 days do not reverse it; their lead response delays are longer, or head office is under capacity. |

Every reversing draw's full parameter values, and each design's head-office and lead utilisation, are in `reports/E4/results.json` (review round 5, Claude R5.1), which also holds every draw's parameter values (`parameter_draw_values`). The run SEs here are the seed-level ones (section 3). Recomputing them that way changed none of the verdicts in the last column.

**Two-driver sweep for the speed conclusions** (review round 5, Claude R5.1; `experiments/e4_quotation/two_driver_sweep.py`, `reports/E4/two_driver_sweep.json`, figure `reports/E4/two_driver_days.png`). The one-at-a-time flip points never moved head-office effort, which is not a top driver of any speed conclusion. Lead effort and head-office effort were swept together over their declared ranges, with the other parameters at central values:
- At the central lead response delay (0.5 days), Review every quote is slower than both other designs everywhere on the plane.
- At a lead response delay of 0.1 days, it is faster than Refer local exceptions on 7% of the plane and faster than Shared limits on 9%: where lead effort is at most about 0.25 days and head-office effort at least about 0.5 days. Head office need not be over capacity there (its utilisation starts at 0.38 under Refer local exceptions and 0.45 under Shared limits), because every quote the other design sends to head office also waits head office's response delay (1.1 days at its central value).
- Shared limits is faster than Refer local exceptions on 99.6% of the plane at the central delay and 88% at 0.1 days. Where it is not, head-office effort is high and lead effort low.

So the speed conclusions that involve Review every quote turn on how long a lead review takes (effort and response delay together) against how long the other designs' head-office referrals take. Reviewer time has no evidence.

The figure's marks for the 64 development draws come from the local cache of the development run. They are drawn only when that cache matches the run recorded in `reports/E4/results.json` (a data fingerprint) and the current ranges and weeks, and they use the draw values the run stored rather than regenerated ones (review round 6, Codex R6.1).

**Depend on assumptions:**
- **Review every quote is slower than Shared limits:** 94% of draws (`effort_lead` Spearman 0.95, `delay_lead` 0.48). It reverses in draws 3, 18, 41 and 63, which share three conditions. Lead effort is 0.22 days or less and the lead response delay under 0.34 days. Head office is slow and over capacity under Shared limits (1.26 to 1.64 days per review, utilisation 1.20 to 1.31). Shared limits sends head office about 4 quotes a week, while Review every quote sends it only gate escalations.
- **Shared limits is faster than Refer local exceptions:** 92% to 94% of draws (`effort_lead` −0.77, `delay_lead` −0.59). It reverses in draws 18, 21, 37 and 41, where head office is slow (1.26 to 1.54 days per review) and over capacity under Shared limits (utilisation 1.21 to 1.57). Shared limits sends it 4.0 to 4.5 quotes a week, against 3.3 to 3.8 under Refer local exceptions, whose local exceptions go to the leads.
- **Review every quote against Refer local exceptions on inconsistent terms:** 80% of draws.
- **Review every quote against Refer local exceptions on the combined count** (wrong terms plus releases beyond authority) **with the gate off:** 56%. Review every quote's extra release beyond authority a week is added in. On wrong terms alone the conclusion holds with or without the gate (section 6).

## 6. Sensitivities: the policy gate off, and the walkthrough's bypass

**What the policy gate changes** (review round 4, Claude R4.1). Switching the gate off leaves wrong terms identical in every design, to four decimals. It changes only whether releases beyond authority happen:

| Gate off minus gate on | Review every quote | Shared limits | Refer local exceptions |
|---|---|---|---|
| Wrong terms | 0 | 0 | 0 |
| Releases beyond authority per week | +0.98 (0.54 to 1.57) | +0.03 | +0.03 |
| Head-office reviews per week | −0.98 | −0.03 | −0.03 |
| Days to customer | −0.12 (−0.27 to −0.03) | −0.004 | −0.004 |

So the gate buys the removal of about one release beyond authority a week in Review every quote, at about one extra head-office review a week and 0.12 days. With the gate off, Review every quote still has fewer wrong terms than Refer local exceptions in 95% of draws. Adding the two measures together hides that (an earlier version of this report said the comparison held only with the gate on; that was the sum, not wrong terms). Q7 decides only whether releases beyond authority can happen at all. Another option for Dingying: make the gate a checkpoint a design can include, since the course asks students to set permissions and checkpoints.

**Bypass after three days** (the walkthrough's assumption; off in the main model, as the case memo asks; rerun after fixing a timer bug, review round 4, Codex R4.1): Review every quote releases 1.6 quotes a week with no recorded approval (0 to 4.9), including 0.16 a week beyond authority. These happen with the gate on because the gate checks releases by agents and leads, and a quote sent out by the sales team after a bypass is neither. Its wrong terms rise from 2.9 to 3.1, and it looks faster (2.7 days instead of 3.1). It is bypassed only in some draws, because effort per review spans under- and over-capacity.

## 7. Shared against isolated notes, and against independent errors

**Sharing notes changes wrong terms very little.** Shared minus isolated, wrong terms per week:

| Design | Notes record drafted terms | Notes record released terms |
|---|---|---|
| Review every quote | 0.000 (identical) | −0.08 (−0.28 to 0.00), 91% of draws |
| Release within shared limits | +0.01 (0.00 to +0.04), 78% | +0.01 (0.00 to +0.03), 75% |
| Refer local exceptions | +0.02 (0.00 to +0.05), 92% | −0.15 (−0.27 to −0.06), **holds across ranges** |

All are below 0.2 wrong terms per week, against a run-to-run SD of 1.0 to 1.3 for one week. Figure: `reports/E4/shared_minus_isolated_errors.png`.

A note can matter only when the same customer is quoted again in another market after the note exists. Without the register, a wrong note from another market mostly repeats the template error the agent would have made anyway. When notes record released terms, a lead's correction travels with the note, and sharing helps. Whether corrections reach the shared notes matters more than sharing itself.

**Against independent errors,** the full model gives the same number of wrong terms in every design (no difference holds; all within ±0.02). What changes is the pattern:
- Quotes to the same customer agree more often, right or wrong. Inconsistent customers are lower with sharing than with independent errors, holding across ranges in Review every quote (−0.02 and −0.05 a week) and Refer local exceptions (−0.03 and −0.12).
- When wrong, they are wrong together. Refer local exceptions with released-term notes has +0.05 repeat customers all wrong per week (0.01 to 0.10), holding across ranges.

Consistency is not correctness. That matters for the case's trigger, which was inconsistent terms.

## 8. Continuity with the walkthrough week (W0 alone, gate on)

| Design | Walkthrough page (illustrative; bypass on, routing by true kind) | This model, W0 only (assumed ranges; bypass off, gate on) |
|---|---|---|
| Review every quote | 4 wrong, 1.7 days | 2.34 wrong (1.60 to 3.27), 2.8 days |
| Release within shared limits | 2 wrong, 0.8 days | 1.73 wrong (1.19 to 2.37), 1.1 days |
| Refer local exceptions | 1 wrong, 1.0 days | 4.25 wrong (2.90 to 5.29), 1.2 days |

On the walkthrough's own week, Refer local exceptions has more wrong terms than both other designs in every one of the 64 draws. The gap depends mostly on how often requests cite agreed terms (`p_cue`, Spearman 0.69 against Review every quote). The walkthrough's best design becomes the worst here because it can no longer route on which quotes truly are exceptions. Review every quote against Shared limits on W0 does not hold across ranges (review higher in 80% of draws).

## 9. Plausibility check against E3 (not a fit)

Under Review every quote, leads change 27% of the quotes they review (Refer local exceptions: 48% of referrals). BPIC 2020 return shares are 2% to 11% per step. The higher rate follows from the case composition (9 of 20 quotes need terms the template does not give). It is not a check on detection, and nothing was adjusted to it.

## 10. What this shows and does not show

It shows a working research model in which:
- routing cannot see the truth;
- permissions are enforced as hard rules;
- every consequential change has a recorded source and an audit trail;
- the design comparison is stated with its two kinds of uncertainty kept apart and with flip points.

Under the declared ranges, the error ranking is driven by who can see the agreements, and Refer local exceptions depends heavily on how well exceptions are recognised. Speed comparisons depend on how long reviews take, lead effort and response delay against the time of head-office referrals, and reviewer time has no evidence. Sharing notes changes the pattern of errors far more than their number.

It does not show that any design is better for a real company. Agent behaviour is assumed until E5, reviewer behaviour has no evidence at all, the weeks are synthetic, and several structural choices are not varied. The robustness check across synthetic weeks has not been run.

## 11. Evidence records, and what changed after review round 3

30 records (`evidence/records/quotation.*.json`): one per declared parameter (all assumed; the time parameters cite E3 records as context only), plus `t_draft` (illustrative), `notes_record`, `bypass_after_days` and `policy_gate` (structural).

Changes from the superseded first comparison:
- **Policy gate on.** Releases beyond authority fall to zero in every design. Review every quote's combined count of wrong terms and releases beyond authority falls from 4.03 to 2.94 a week. Of that drop, 1.01 is the releases beyond authority the gate removes, and 0.08 is wrong terms (3.02 to 2.94, with the effort and delay split below).
- **`m_lead` and `m_ho` replaced by effort and delay.** Leads are no longer overloaded in every draw, so "Review every quote is slowest in every draw" no longer holds against Shared limits.
- **One conclusion reversed: separating the measures, not removing the overload, changed it** (review round 5, Claude R5.2). The first comparison counted wrong terms and releases beyond authority together, and on that count Review every quote against Refer local exceptions was a toss-up (review worse in 61% of draws). Its top driver was `p_lead_knows_policy` (−0.51), which acts only through beyond-policy quotes. Review every quote already had fewer wrong terms then (3.02 a week against 3.79), and its 1.01 releases beyond authority a week were what made the count a toss-up. On wrong terms alone, review now has fewer in 95% to 98% of draws, with or without the gate. Removing the overload moved its wrong terms only from 3.02 to 2.94. An earlier version of this bullet credited the overload.

## 12. Departures from the plan

- Development uses the walkthrough week plus four generated weeks; the held-out weeks are a group of customers, and are called a robustness check.
- Wrong notes arise inside the model, plus stale notes at the start of a week, rather than one planted note (that design is E5's).
- Two added measures: customers with inconsistent terms, repeat customers all wrong. Two more after round 3: gate escalations and releases beyond authority.
- A plain event loop instead of SimPy (allowed).
- The policy gate is a modelling choice that departs from the walkthrough's behaviour; it is the main model pending Dingying's decision (Q7).

## 13. Next steps

- **E5,** once Dingying approves model and budget: replace the agent parameters marked `replaced_by: E5` (as constrained products where the pilot cannot identify single parameters) and rerun.
- **After E5:** freeze the development conclusions (`run_e4.py --freeze-conclusions`), commit them, then run the robustness check once. The freeze leaves out review counts and the gate sensitivities, and applies the 80% target to wrong terms and to days separately. The run refuses unless the results, ranges, code and frozen weeks match what was frozen, and the conclusions file is committed and equal to the freeze recomputed from the results (review round 5, Codex R5.1).
- **If Dingying agrees (Q8):** the one-factor split of register access within each release design.

## 14. After the agent pilot (E5): the update, the comparison again, and the robustness check

*Added 2026-10-03 14:40 UTC. Every number is a model output. The frequencies and products the pilot measured are **fitted**; the single parameters that only follow from a fitted product stay **assumed**; everything about human reviewers stays **assumed**. Tables: `reports/E4/tables_pilot_update.md`, written from the result files by script.*

**What went in** (plan section 9.1; `reports/E5/e4_update.json`): `e_visible` 0 to 0.20 became 0 to 0.06; `p_flag_unverifiable` 0.10 to 0.80 became 0.82 to 0.98; the product `p_read_note` x `p_adopt_blind` is drawn from 0.42 to 1.00 and the product `p_read_note` x (1 - `p_notice_visible`) from 0 to 0.20; `p_flag_after_note`, a new parameter whose default of 0 was the first model's rule, became 0.35 to 0.85. `p_newest_note`, the other new parameter, stays at 1 because the pilot could not test the rule. With both new parameters at their defaults the model reproduces sections 4 to 8 exactly (same simulation output by SHA-256).

**The three designs after the update** (isolated notes, drafted terms, gate on; 5th to 95th percentile of draw means in brackets):

| Measure, per week | Review every quote | Release within shared limits | Refer local exceptions |
|---|---|---|---|
| Quotes with wrong terms (of 20) | 2.94 (2.05 to 3.87) | 1.34 (0.76 to 1.90) | 3.50 (2.43 to 4.60) |
| Average days to customer | 3.13 (1.18 to 5.10) | 1.05 (0.72 to 1.35) | 1.47 (1.05 to 1.94) |
| Human reviews | 20 lead + 1.0 head office | 3.8 head office | 5.8 lead + 3.7 head office |
| Customers with inconsistent terms | 1.17 | 0.03 | 0.98 |

**Which conclusions changed** (14 of 135 comparisons; `reports/E4/pilot_update_comparison.json`):
- *No longer holds:* Review every quote has fewer wrong terms than Refer local exceptions (95% to 98% of draws before; 83% to 84% now; mean difference 0.84 before, 0.56 now). Top driver `p_cue` (Spearman 0.72).
- *Now holds:* Release within shared limits is faster than Refer local exceptions (98% to 100% of draws), and Review every quote is slower than Release within shared limits (97%; it still reverses in draws 3 and 63, with quick lead reviews and head office over capacity under Shared limits).
- *Now holds:* with released-term notes, Review every quote has fewer customers with inconsistent terms under shared notes (100%).
- *Unchanged:* Release within shared limits has the fewest wrong terms (100% of draws against both others); Review every quote is slower than Refer local exceptions (95%; reverses in draws 3, 41 and 63); the review-load ranking; the gate changes no wrong term and removes about one release beyond authority a week in Review every quote; on the walkthrough week Refer local exceptions has the most wrong terms in every draw (4.01 against 2.34 and 1.43).

**Which rule moved what** (`reports/E4/pilot_update_attribution.json`, each rule applied alone; a description): the speed results move with `e_visible`; the wrong-terms result of Review every quote against Refer local exceptions moves with `p_flag_unverifiable`; the note products move small shared-against-isolated differences.

**The reading rule at its lowest allowed value** (`reports/E4/reading_rule_sensitivity.json`): with `p_newest_note` at 0, five comparisons between shared and isolated notes change, each a difference under 0.04 a week; no design comparison on wrong terms changes.

**Flip points and the two-driver sweep, recomputed.** No top driver, moved alone, reverses a conclusion inside its range. At the central lead response delay Review every quote is faster than Refer local exceptions on 0.8% of the lead-effort by head-office-effort plane and never faster than Shared limits; at a delay of 0.1 days, on 11% and 7%. The versions before the pilot are kept in `reports/E4/before_pilot/`.

**Sharing notes** still changes wrong terms very little: every shared-minus-isolated difference is under 0.25 a week. With released-term notes sharing helps Refer local exceptions (-0.23, holds across draws) and Review every quote (-0.12, 94% of draws).

**Robustness check on the held-out weeks, run once** (`reports/E4/results_heldout.json`). 51 conclusions were frozen from the comparison after the update (`experiments/e4_quotation/dev_conclusions.json`). Outcome: **pass**. All 10 conclusions on wrong terms and all 12 on days to customer hold on the four held-out weeks (target 80% each). 47 of 51 hold overall; the four that do not are on customers with inconsistent terms, shared notes against isolated notes or independent errors (72% to 89% of held-out draws against the 90% bar). The held-out weeks come from the same generator, so this shows the conclusions do not depend on which synthetic weeks were drawn, and nothing more.

**What this adds up to.** The pilot replaced four assumptions about the agent with early evidence and contradicted one rule. One design conclusion did not survive it, and two became firmer. The reviewer parameters, which drive the error ranking and the speed results, are still assumptions with no evidence.
