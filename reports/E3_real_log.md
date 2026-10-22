# E3. One real log: BPI Challenge 2020 Domestic Declarations

Claude Code (build), 2026-10-02 (UTC). Early result.

Sections 1 to 3 (inspection and estimand table) were written and committed before any quantity was estimated. Results follow in section 4 onwards.

## 1. Question

What can a real approval-chain log tell the quotation simulator, and what can it not? Specifically: which simulator parameters can be estimated from it, which only partly, and which not at all, and for those it supports, what are the values and how far do they transfer to quotation review?

## 2. Data and inspection

**Source.** BPI Challenge 2020, Domestic Declarations (van Dongen, Eindhoven University of Technology), DOI 10.4121/uuid:3f422315-ed9d-4882-891f-e180b5b4feb5, licence CC BY-NC 4.0 as stated on the 4TU record, downloaded 2026-10-02 20:05 UTC, SHA-256 0bc3312a…7532b. Details in `data/SOURCES.md`. The process: an employee submits a travel expense declaration after a domestic trip; travel administration, a budget owner and a supervisor approve it (budget owner and supervisor collapse into one step when they are the same person; sometimes a director); then payment is requested and made.

**Inspection, all observed from the file** (`gca_sim/logs/bpic2020.py`):

| Item | Finding |
|---|---|
| Size | 10,500 cases, 56,437 events, 17 activities. Matches the dataset description. |
| Period | First event 2017-01-09, last 2019-06-17 (UTC). 2,240 cases start in 2017 (two departments), 8,260 in 2018 (whole university). |
| Case attributes | `Amount` (float), `DeclarationNumber`, `BudgetNumber`, `id`. `BudgetNumber` has one value for every case, so it carries no information. `DeclarationNumber` is "UNKNOWN" for 452 cases. |
| Amount | Median 41.51, 95th percentile 324.76, maximum 3,292.54, zero for 446 cases. The currency is not stated, and the challenge page says amounts "are not exact amounts". All 446 zero-amount cases ended without payment, so amounts are only meaningful for paid cases. |
| Event attributes | `concept:name`, `time:timestamp`, `org:resource`, `org:role`, `id`. No `lifecycle:transition`. |
| What a timestamp records | One timestamp per event: the moment the step was recorded in the system. There is no start-of-work event, so no event says when someone began looking at a declaration. |
| Resolution and time zone | Whole seconds. Local Dutch time with offsets +01:00 and +02:00; the offset matches the Europe/Amsterdam daylight-saving rule for 100% of events. |
| Resource field | Only "STAFF MEMBER" (36,353 events) or "SYSTEM" (20,084). Individuals cannot be identified (the challenge page says so). Everything about people is therefore by role. |
| Role field | EMPLOYEE 13,031; SUPERVISOR 10,425; ADMINISTRATION 9,155; BUDGET OWNER 2,879; PRE_APPROVER 772; MISSING 91; UNDEFINED 20,084 (all SYSTEM events). No director role appears in this log. |
| Events to cases | Events are nested in their trace. Event ids start `st_step` (workflow steps) or `dd_declaration` (payment request and payment). Within a case, file order is chronological (no backward steps; 10 equal timestamps). |
| Activity semantics | Each activity is "Declaration <OUTCOME> by <ROLE>", plus "Request Payment" and "Payment Handled" (SYSTEM). "REJECTED by EMPLOYEE" follows a reviewer's rejection in 1,357 of 1,365 cases: it is the declaration being returned to the employee, who then resubmits (1,081) or stops (284). It is not a review decision. "REJECTED by MISSING" mostly follows a supervisor's final approval (86 of 91), by a role the log does not name. |
| Payment timing | "Payment Handled" is a batch run: 9,923 of 10,044 events (99%) at 17:30 to 17:32 local time, almost all on Mondays and Thursdays. Its timing reflects the payment schedule, not anyone's work. |

## 3. Estimand table (written before estimating)

For each candidate simulator parameter: what the log quantity measures, what the parameter means in the quotation simulator, and whether the log can estimate it. "Estimable" means estimable **for this process**; transfer to quotations is a separate question, in the last column.

| # | Simulator parameter (quotation model) | Log quantity | What the log quantity actually measures | Estimable | Could inform the quotation episode? |
|---|---|---|---|---|---|
| 1 | Review latency: time from a quote reaching a reviewer to the reviewer's decision | Time between the event that hands a declaration to a role and that role's decision event | Elapsed calendar time between two recorded events. It includes queueing behind other work, nights, weekends, notification delay and waiting for information. No start event, so work time cannot be separated out. | **Partly.** An upper envelope on decision latency at the load observed. Missing: start of work, queue position. | Yes, as an analogue **range** for reviewer response time, with the caution that in a model with explicit queues it double-counts queueing. |
| 2 | Review effort: working time per review | None | Nothing in the log measures time spent working | **No** | No. Stays a declared assumption. |
| 3 | Reviewer capacity: reviews one person can do per week | Decisions per week by role | Throughput, which follows arrivals. Individuals are anonymised and the number of people per role is unknown. | **No** | No. Stays a declared assumption. |
| 4 | Queueing time, separately from review time | None | Elapsed gaps mix the two | **No** | No |
| 5 | Routing rule: which items go to which reviewer | Observed paths through the approval steps, by case | The paths cases took. The rule behind them depends on things the log does not record (for example whether the budget owner is also the supervisor). | **Partly.** Observed routing frequencies, not the rule. | As an example of how routing varies in practice, not as a rule |
| 6 | Number of review steps an item passes through | Approval events in the round that led to payment | Observed chain length | **Yes** | As an analogue range for how many reviewers an item sees |
| 7 | Probability a reviewer catches an error | Rejection share at each step | The share of decisions that are rejections. Reasons are not recorded and neither is whether the declaration was actually wrong, so it mixes caught errors, missing paperwork and policy refusals, and misses errors nobody caught. | **No.** A rejection rate is not a detection probability. | No. Detection stays a declared assumption, varied across ranges. |
| 8 | Share of items returned for correction at a review step | Rejection share at each step, per decision | Observed return rate in this process | **Yes**, as an observed rate | As a plausibility range for how often review returns items, not as detection |
| 9 | Rework: chance a returned item is resubmitted, and time to resubmit | "REJECTED by EMPLOYEE" followed by a new submission; the gap between them | Observed resubmission share and elapsed time | **Yes** (elapsed time, so including the employee's other work) | As an analogue range for a correction loop |
| 10 | A later reviewer rejecting what an earlier reviewer approved | Supervisor or budget-owner rejection after an administration approval | Observed share of later-step decisions that are rejections after an earlier approval | **Yes**, as an observed share. It is not evidence about which reviewer was right. | Weakly: shows that sequential reviewers disagree, at an observed rate |
| 11 | Working calendar: when decisions happen | Hour and weekday of decision events by role | Recorded decision times | **Yes** | As an analogue: reviews happen in office hours on weekdays |
| 12 | Release or payment timing | "Request Payment" to "Payment Handled" | A twice-weekly batch schedule | **Yes**, but it measures the schedule | No |
| 13 | Errors reaching the customer (wrong items released) | None | No ground truth about which declarations were wrong | **No** | No |
| 14 | Staff sending items round a slow review (the walkthrough's bypass) | None | The log records only steps taken in the system | **No** | No. Stays an assumption, off by default (E1). |
| 15 | Arrival rate | Submissions per week | Arrivals of travel declarations | **Yes** for this process | No. Quotation arrivals are a different process. |
| 16 | Value-based escalation (larger items get more approvers) | Chain length and path against `Amount` | Association between an inexact amount and the path taken, for paid cases | **Partly.** Association only; amounts are perturbed and unrecorded identity relations also change the path. | As an example of whether value and routing go together, not as a threshold |
| 17 | Error dependence: errors on related items happening together | None | No error ground truth, nothing about shared context | **No** | No. That is for the agent pilot (E5). |

Four cautions from the handoff, applied above: the gap between two events is not review time (rows 1, 4); cases handled per week is not capacity (row 3); a rejection rate is not the chance a reviewer catches an error (row 7); the paths cases took are not the formal rules (row 5).

## 4. Method

`experiments/e3_bpic2020/run_e3.py`, PM4Py 2.7.23.8. First run at commit 28d2f22; rerun at a342e21 (clean tree) after review round 2, which split time to decision by the preceding step, moved the lognormal fits to a reference-only record, and added the 2017 against 2018 comparison and the precision check. All numbers below are in `reports/E3/results.json`. Every number is **observed** from this log unless marked fitted. Intervals are 95% Wilson intervals for shares and bootstrap intervals for medians, both treating events as independent. Decisions cluster within cases and within reviewers the log cannot identify, so these intervals understate uncertainty; the difference between 2017 and 2018 is a better guide to how much the quantities vary.

## 5. Results

**Size and variants (observed).** 10,500 cases, 56,437 events, 99 distinct variants. Three variants cover 80% of cases, nine cover 95%. The top three: submission, administration, supervisor, payment (44.0%); the same with a budget-owner step (23.6%); submission straight to supervisor (13.3%).

**Routes in the round that led to payment (observed, 10,044 paid cases).** Administration then supervisor 5,133 (51%); administration, budget owner, supervisor 2,788 (28%); supervisor only 1,462 (15%); pre-approver then supervisor 659 (7%). Chain length 1, 2 or 3 approvals.

**Discovered models (fitted).** Inductive miner with no noise filtering fits every trace by construction (token-replay fitness 1.0) but is imprecise (precision 0.39). With noise threshold 0.2: fitness 0.967 by token replay and 0.937 by alignments, 67.5% of traces fit exactly, precision 0.38. A model discovered on the 2,240 cases from 2017 (two departments) replays the 8,260 cases from 2018 (whole university) with fitness 0.996 (95.8% of traces fitting) without filtering, 0.977 (85.7%) with it. But its precision on 2018 is only 0.22 (0.43 with filtering), so it fits mainly because it allows a great deal. High replay fitness here does not show that the process carried over, and the direct comparison below shows it did not. Figures: `reports/E3/dfg.png`; models in `reports/E3/*.pnml` and `*_tree.txt`.

**2017 against 2018 (observed; review round 2).** The two years run different processes. In 2017 (two departments) 68% of paid cases go straight to a supervisor and 31% through a pre-approver; administration appears in under 1%. In 2018 (whole university) every paid case starts at administration: 65% then go to a supervisor and 35% through a budget owner first. Steps comparable across years give similar elapsed times: supervisor after pre-approver (2017) median 0.90 days, supervisor after administration (2018) 0.87. The supervisor's return share is 3.1% in 2017 and 2.7% in 2018. Other return shares exist in one year only, so most of their spread is between roles, not years. Record: `year_comparison.bpic2020`.

**Handover by role (observed).** A sequential chain: employee to administration (9,155), administration to supervisor (5,323) or budget owner (2,879), budget owner to supervisor (2,820), supervisor to the payment system (10,046), with return loops to the employee from administration (948), supervisor (288) and pre-approver (86). Figure: `reports/E3/handover_by_role.png`.

**Outcomes at each approval step (observed, per decision event).**

| Step | Decisions | Rejected | Rejection share (95% CI) |
|---|---|---|---|
| Administration | 9,154 | 952 | 10.4% (9.8 to 11.0) |
| Pre-approver | 771 | 86 | 11.2% (9.1 to 13.6) |
| Budget owner | 2,879 | 59 | 2.0% (1.6 to 2.6) |
| Supervisor | 10,424 | 293 | 2.8% (2.5 to 3.2) |

Later reviewers sometimes return what an earlier one approved: supervisors reject 3.6% (3.1 to 4.1) of declarations straight after an administration approval and 1.1% (0.8 to 1.6) after a budget-owner approval. This is disagreement between steps, not evidence of who was right. Returned declarations are resubmitted 79.2% of the time (77.0 to 81.3), median 0.2 days to resubmit (90th percentile 11 days). 1,019 cases (9.7%) were submitted more than once. 10,044 cases were paid and 456 ended unpaid.

**Time between steps (observed; elapsed time between recorded events, not review time).**

| From → to | n | Median days (95% CI) | Interquartile range | 90th percentile | Spans a weekend day |
|---|---|---|---|---|---|
| Submitted → administration approved | 8,202 | 0.00 | 0.00 to 0.003 | 0.02 | 11% |
| Administration approved → budget owner approved | 2,820 | 0.87 (0.84 to 0.89) | 0.13 to 2.7 | 4.9 | 30% |
| Administration approved → supervisor approved | 5,133 | 0.87 (0.85 to 0.89) | 0.12 to 2.8 | 4.8 | 32% |
| Budget owner approved → supervisor approved | 2,788 | 1.91 (1.86 to 1.98) | 0.88 to 5.0 | 6.7 | 40% |
| Pre-approver approved → supervisor approved | 674 | 0.90 (0.84 to 0.96) | 0.12 to 3.0 | 6.2 | 31% |
| Returned to employee → resubmitted | 1,081 | 0.20 (0.14 to 0.29) | 0.03 to 2.2 | 11.1 | 23% |
| Request payment → payment handled | 10,037 | 3.24 | 2.3 to 4.3 | 4.9 | 49% |

Three things stand out. First, 91% of administration decisions are recorded within an hour of the submission (median under a minute), and 93% of direct submission-to-supervisor approvals likewise. Either these checks are very fast or the two events are recorded together; the log cannot tell which, so these gaps say nothing about review time. Second, for the later steps (budget owner, supervisor) the median elapsed time is about 0.9 to 1.9 days with a long right tail, and 30 to 40% of the gaps include a weekend day. Third, lognormal fits to these gaps are poor (Kolmogorov–Smirnov statistic 0.13 to 0.17), because the working calendar shapes them. For the later steps they imply means of 4.3 to 5.5 days and 99th percentiles of 49 to 81 days, against observed means of 1.9 to 2.9 and 99th percentiles of 6.8 to 13.7. The empirical quantiles are the evidence. The fits sit only in a separate record marked fitted and reference only (`lognormal_fits.bpic2020`), never in the observed records, and a test enforces that. Whole case: submission to final approval median 1.6 days (90th percentile 9.4); submission to payment median 7.4 days, driven by the payment batch. Figure (by preceding step): `reports/E3/time_to_decision_by_step.png`.

Time to decision split by the step before it (review round 2, Claude R2.2): straight after submission, administration, pre-approver and supervisor decisions have medians of 0.00 days, with 91% to 93% under an hour. They are recorded as **not estimable** as review latency. After an earlier approval: budget owner after administration 0.86 days, supervisor after administration 0.87, after pre-approver 0.90, after budget owner 1.93. These are **partly estimable**, usable only as an upper envelope.

**Working calendar (observed).** 83% to 94% of each role's decisions are recorded on weekdays between 08:00 and 18:00. Supervisors record 6.9% between 22:00 and 06:00. Payments run in a batch at about 17:30 on Mondays and Thursdays (98.8% of payment events). Figure: `reports/E3/decisions_by_hour.png`.

**Approval chain against declared amount (observed, inexact amounts).** The share of paid cases with a budget-owner step is flat across amount bands: 27% (0 to 25), 26% (25 to 50), 27% (50 to 100), 32% (100 to 250), 28% (250 to 500), 30% (500 and above). Spearman correlation between amount and chain length 0.04. In this log, with perturbed amounts, larger declarations do not visibly pass more approvers; routing seems to follow organisational relationships the log does not record. Figure: `reports/E3/budget_owner_share_by_amount.png`.

**Arrivals (observed).** 2018 median 186 submissions a week (10th to 90th percentile 66 to 249). Not transferable.

## 6. Which quantities could inform the quotation episode, as analogue ranges

| Quantity | Estimable | Analogue use in E4 |
|---|---|---|
| Time to a reviewer's decision after an earlier approval (budget owner after administration; supervisor after administration, pre-approver or budget owner): median 0.86 to 1.93 days, interquartile range about 0.1 to 5 days, similar in 2017 and 2018 where comparable | Partly | Range for how long a quotation reviewer takes to respond, as an upper envelope (includes queueing and off-hours). The walkthrough's illustrative 1 day (regional) and 2.5 days (head office) fall inside it; that is consistency, not validation. |
| Return share per review step: 2% to 11% | Yes, as a return rate | Plausibility range for how often review returns an item. Not a detection probability. |
| Resubmission after a return: 79%, median 0.2 days | Yes | Range for a correction loop |
| Working calendar: decisions mostly on weekdays in office hours | Yes | Reviews happen in working time |
| Sequential reviewers disagree: 1% to 4% | Yes, observed | Weak: a second reviewer is not a duplicate of the first |
| Routing and value | Partly | Example only: routing here does not follow value |

Not estimable from this log, and so declared assumptions in E4: review effort, reviewer capacity, queueing separately from processing, the chance a reviewer catches an error, errors reaching the customer, staff bypassing slow review, and error dependence.

## 7. What this does and does not show

It shows how one real approval chain behaves: a few dominant routes, a return loop used about one time in ten, return rates that differ by step, and elapsed times shaped by the working week. It also shows that the process changed between 2017 (two departments) and 2018 (whole university): different routes, with similar elapsed times for comparable steps. An earlier version of this report said the process structure transferred between the years. That rested on replay fitness alone and is withdrawn (review round 2, Claude R2.3 and Codex R2.8). The 2017-discovered model fits 2018 because it is permissive (precision 0.22), not because the routes carried over.

It does not show how long reviewing takes, how many reviews a person can handle, or whether reviewers catch errors. It is a university's travel expenses, not sales quotations, so whatever transfers does so as an analogue range, recorded as such.

## 8. Evidence records and spec

23 records in `evidence/records/*.bpic2020.json`, each validated against `evidence/schema.json` by `tests/test_evidence_records.py`.
- Rejection shares carry the simulator parameter "share of items returned at a review step (not detection probability)", with their 2017 and 2018 values.
- Seven time-to-decision records, one per preceding step: the three straight after submission are "no" as review latency; the four after an earlier approval are "partly" and marked `use: range_only`. They hold empirical quantiles only.
- The lognormal fits are in `lognormal_fits.bpic2020` (status fitted, `use: reference_only`, estimable "no").
- A semantic test ensures no observed record carries fitted parameters, and that every record `assumptions.yaml` cites as an analogue is usable.

Workflow spec: `specs/bpic2020_declarations.workflow.json`, with time to decision by preceding step and a `not_in_log` list.

## 9. Departures from the plan

- No Graphviz on the machine, so figures are drawn with matplotlib and networkx rather than PM4Py's renderer.
- Added a transfer check (model discovered on 2017 cases, replayed on 2018), not asked for, because it is cheap and is the nearest thing to a held-out test this log offers.
- Amount analysis restricted to paid cases, because all zero-amount cases ended unpaid.
- After review round 2: time-to-decision records split by preceding step; lognormal fits moved out of the observed records; precision of the 2017 model on 2018 and a direct 2017 against 2018 comparison added; the transfer claim withdrawn.

## 10. Next steps

E4 takes the time-to-decision range (later steps only) and the return-rate range as analogue evidence, and declares everything else as assumptions with ranges before running any comparison.
