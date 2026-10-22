# E6. Can τ-bench's historical trajectories supply evidence on escalation and verification?

Claude Code (build), 2026-10-02 (UTC). Early result.
- **Revised on 2026-10-03 at 01:00 UTC after review round 4:** the confirmation check is redone in context on a stratified sample, and the claim about the two models is narrowed.
- **Revised at 01:40 UTC after review round 5:** the estimate from that sample is labelled fitted and kept apart from the observed counts.

**Labels.**
- The counts are **observed** from the τ-bench files named below.
- The annotation counts are one annotator's judgements of those files.
- The share of all writes made with explicit confirmation is **fitted**: estimated from 50 annotated writes per model (section "Confirmation read in context", review round 5, Codex R5.3).

Their transfer to the quotation episode is analogue at most.

## Question

Do the old τ-bench retail trajectories record enough to serve as evidence on how an agent escalates and verifies under a written policy, and can they be turned into event logs like the rest of the project's evidence?

## Data

sierra-research/tau-bench (MIT), commit 59a200c (2026-03-18), cloned into `third_party/` without line-ending conversion. Two retail files: `gpt-4o-retail.json` (460 runs: 115 tasks × 4 trials) and `sonnet-35-new-retail.json` (920 runs: 115 tasks × 8 trials). Sizes, SHA-256 and git blob ids are in `data/SOURCES.md`. The repository warns that its tasks are outdated; τ³-bench has fixed tasks but ships no trajectories. The airline files were not used.

## Method

`experiments/e6_taubench/check_taubench.py` (first run at 52696e4; rerun on a clean tree at da38cab after review round 3 and at f35a6a6 after review round 4) checks the pinned commit and file hashes, lists what each record holds, and measures three behaviours the retail policy makes testable:

1. **Authenticate first.** The policy requires locating the user by email, or by name and zip code, before anything else. We count runs that read user data or write to the database before an authentication call.
2. **Explicit confirmation before a database write.** The policy requires an explicit "yes" before cancelling, modifying, returning or exchanging. We take the latest customer message before each write call and check whether it contains the word "yes". This is a keyword heuristic, so we also read a stratified sample of writes in context (section "Confirmation read in context").
3. **Transfer to a human.** The policy says to transfer "if and only if the request cannot be handled". We compare runs that call `transfer_to_human_agents` with tasks whose gold actions include a transfer.

It also converts four runs per file to the event format (case, activity, order, resource), in `reports/E6/events_sample.csv`.

## What the records hold

| Recorded | Not recorded |
|---|---|
| The full message sequence: system policy text, simulated customer, agent, tool results | Timestamps (messages are ordered, not timed) |
| Every tool call with its arguments and its result | Model name, version, date, temperature or seed (the model is named only in the file name) |
| The task: user id, the customer simulator's instruction, gold actions, expected outputs | Token usage of the agent (only the user simulator's cost) |
| Reward (0 or 1) and the action-match component | Any reviewer, queue or shared context: one agent per conversation |

## Results (observed)

| | gpt-4o, retail | sonnet-35-new, retail |
|---|---|---|
| Runs (tasks × trials) | 460 (115 × 4) | 920 (115 × 8) |
| Mean reward | 0.60 | 0.69 |
| Tasks where every trial succeeds | 38% | 36% |
| Tasks where some but not all trials succeed | 43% | 58% |
| Runs reading user data before a successful lookup | 1 | 33 (3.7%) |
| Runs writing before a successful lookup | 0 | 2 |
| Database writes whose preceding customer message contains "yes" (keyword proxy) | 76% (73% to 79%) | 90% (89% to 92%) |
| Writes made with explicit confirmation, **fitted** from a stratified sample of 50 read in context (one annotator; 95% credible interval; below) | 99% (90% to 99.7%) | 98% (87% to 99%) |
| Runs transferring to a human | 25 (5.4%) | 79 (8.6%) |
| of which the task expected a transfer | 11 | 20 |
| Expected transfers that did not happen | 5 of 16 | 12 of 32 |
| Failed runs with an extra or wrong write / with a missing write | 55 / 102 of 182 | 51 / 127 of 283 |

Intervals are 95% Wilson intervals, treating writes as independent; they are not. The fitted row has a Bayesian credible interval, described below.

## What this shows and does not show

**Usable:**
- **Escalation decisions can be scored against a written rule.** Transfers are logged and gold actions say when one was expected. Transfers are often unnecessary (14 of 25 and 59 of 79 runs that transferred had no expected transfer), and some expected ones are missed. That is the shape of evidence the quotation model needs for escalation (`p_flag_unverifiable`). But the trigger here is a request outside the agent's scope, not terms the agent cannot verify.
- **Procedural checks before acting are measurable.** Authentication is near perfect for gpt-4o and slightly less so for sonnet-35-new, counting only lookups that succeed (review round 3, Codex R3.4; the first version also counted failed lookups, and slightly undercounted). The keyword proxy for confirmation suggested a model difference (76% against 90%). Read in context, the sample cannot distinguish the two models (next section). This is an analogue for the agent's own check before release (`p_selfcheck`), though it checks procedure, not whether the content is right.
- **Agent behaviour is strongly stochastic.** On 43% and 58% of tasks the same agent both succeeds and fails across trials. This supports the E2 plan's replicate runs and the model's treatment of agent behaviour as a probability.
- **Event conversion works** (case, activity, order, resource), so the trajectories can be process-mined. With no timestamps, though, mining gives order and routing, not time.

### Confirmation read in context (review rounds 4 and 5)

The round 3 hand-check judged the latest customer message alone, and two of its labels were wrong once the agent's preceding proposal was read (review round 4, Codex R4.3). We redid it (`experiments/e6_taubench/confirmation_handcheck.py`, output `reports/E6/confirmation_handcheck.json`).

- **Sample.** Per model, 20 random writes whose latest customer message contains "yes" and 30 whose message does not (review round 4, Claude R4.5), drawn with a fixed seed from the pinned files. Each judgement is keyed by file hash and task, trial, message and tool-call ids.
- **Standard.** A write counts as confirmed if the agent had described the action and the customer explicitly approved it ("yes" or an equivalent go-ahead, in the latest message or earlier), and the write made no change the customer had not approved. A customer's own request that the agent carried out without describing the action first does not count.
- **Annotator.** Claude Code (build) read every sampled write. This is one reader's judgement, not independent ground truth. 16 of the 100 judgements are marked borderline. In most, the customer answered with a choice, a correction or a reason rather than a plain go-ahead, or the agent did not restate the final details before writing.

| | gpt-4o, retail | sonnet-35-new, retail |
|---|---|---|
| Writes after "yes" judged confirmed | 20 of 20 | 20 of 20 (2 borderline) |
| Writes without "yes" judged confirmed | 29 of 30 (10 borderline) | 24 of 30 (4 borderline) |
| Estimated share of all writes made with explicit confirmation, fitted (95% credible interval) | 99% (90% to 99.7%) | 98% (87% to 99%) |
| Same, counting every borderline judgement as not confirmed | 91% | 88% |
| Keyword proxy, all writes | 76% | 90% |

The estimate weights each stratum by its size (507 and 159 writes for gpt-4o, 1,220 and 132 for sonnet-35-new).
- **The interval** is a 95% Bayesian credible interval. Each stratum's share has a Jeffreys prior, and posterior draws are combined with the stratum weights.
- **Annotation error** is not in it: one annotator cannot measure it.
- **Its width** comes mainly from reading only 20 writes after "yes" per model. The point estimate sits near the top because none of those 20 was unconfirmed.
- **Scope.** These are estimates for the writes in these two files, not general rates for these model versions: the tasks are outdated, the customers simulated and the domain one.

The estimate is its own record, labelled fitted, apart from the observed keyword counts (review round 5, Codex R5.3).

**The writes judged not confirmed:**
- gpt-4o: one write on a general request, with no order or item identified to the customer.
- sonnet-35-new:
  - four writes carrying out the customer's own request without describing the action first;
  - one refund switched to a gift card without asking, after the approved refund failed;
  - one write after the customer had only asked a question.

**What the sample supports.** Every sampled write after "yes" was a real confirmation. Most writes without "yes" were confirmations worded otherwise ("go ahead", "do it", choosing an offered option). So the keyword proxy understates confirmation. In the sample the 14-point keyword gap between the models closes to about 1 point (sonnet-35-new minus gpt-4o, −1 point, 95% credible interval −10 to +7), so the sample cannot rule out a modest difference in either direction. An earlier version said most of the gap was wording; the sample supports only that the keyword gap is not evidence of a difference.

**Not usable:**
- No timing, no shared context, no reviewers, nothing about quotation terms.
- Model versions are not recorded beyond the file name, so the estimates cannot be tied to a model snapshot as the E2 plan requires.
- The tasks are outdated (the repository says so).

**Verdict.** Worth using later, cheaply and with no model calls, as analogue evidence on escalation precision and recall and on pre-action checks. Not a substitute for the E5 pilot, which measures escalation when terms cannot be verified and shared-note behaviour directly. Full process mining of these files adds little beyond what this check already extracts, because without timestamps it can recover order and routing but not time.

## Evidence records created

- **Observed:**
  - `transfer_to_human.taubench_retail` (partly estimable);
  - `confirm_before_write.taubench_retail` (partly): the keyword counts, with the annotation counts in its tests;
  - `trial_consistency.taubench_retail` (yes).
- **Fitted:** `confirm_before_write_in_context.taubench_retail` (partly): the estimated share and its credible interval, for reference only (review round 5, Codex R5.3).

All are MIT-licensed, with the commit and model names recorded. None replaces an E4 parameter; they are analogue ranges for later.

## Departures from the plan

- Used both retail files (gpt-4o and sonnet-35-new) rather than "a handful": the whole file is as cheap to read as a few runs, and the second model shows the behaviours differ by model.
- Line-ending conversion on Windows changed the files at the first checkout; re-cloned with conversion off so hashes match the repository.

## Next steps

Proposed for after the first round, not started: score transfers and confirmations against gold across both domains (airline included) as evidence records with model as a condition.
