# Tables of the quotation model's comparison, before and after the agent pilot

Written by `experiments/e4_quotation/make_tables.py` from the result files in this folder. Every number is a model output. Before the pilot every parameter range is assumed. After it, the frequencies and products the pilot measured are fitted; the single parameters that only follow from a fitted product stay assumed under that constraint; and everything about human reviewers stays assumed.

## Before the pilot (commit 5c9079c, 2026-10-03 14:00 UTC)

| Measure, per week | Review every quote | Release within shared limits | Refer local exceptions |
|---|---|---|---|
| Quotes with wrong terms reaching customers (of 20) | 2.94 (2.05 to 3.87; run SD 1.17) | 1.66 (1.15 to 2.24; run SD 1.00) | 3.78 (2.62 to 4.80; run SD 1.29) |
| Average days to customer | 3.13 (1.18 to 5.10; run SD 0.44) | 1.06 (0.69 to 1.46; run SD 0.27) | 1.40 (1.01 to 1.83; run SD 0.26) |
| Reviews by regional leads | 20.0 (20.0 to 20.0; run SD 0.0) | 0.0 (0.0 to 0.0; run SD 0.0) | 5.8 (4.4 to 6.9; run SD 1.3) |
| Reviews by head office | 1.0 (0.5 to 1.6; run SD 0.8) | 3.9 (3.3 to 4.4; run SD 0.9) | 3.4 (3.0 to 3.8; run SD 0.6) |
| Busiest lead's review effort, share of the week | 1.38 (0.33 to 2.38; run SD 0.23) | 0.00 (0.00 to 0.00; run SD 0.00) | 0.54 (0.12 to 0.92; run SD 0.19) |
| Customers with inconsistent terms across quotes | 1.15 (0.96 to 1.48; run SD 0.62) | 0.08 (0.00 to 0.17; run SD 0.25) | 1.04 (0.80 to 1.24; run SD 0.65) |
| Repeat customers with every quote wrong | 0.41 (0.14 to 0.72; run SD 0.53) | 0.00 (0.00 to 0.01; run SD 0.01) | 0.28 (0.07 to 0.55; run SD 0.44) |
| Wrong terms: standard quotes (11 a week) | 0.37 (0.10 to 0.70; run SD 0.56) | 0.75 (0.27 to 1.34; run SD 0.84) | 0.64 (0.23 to 1.13; run SD 0.77) |
| Wrong terms: written agreements (5 a week) | 2.34 (1.68 to 3.04; run SD 0.92) | 0.12 (0.01 to 0.27; run SD 0.31) | 2.52 (1.70 to 3.30; run SD 0.97) |
| Wrong terms: verbal promise (1 a week) | 0.23 (0.08 to 0.35; run SD 0.40) | 0.79 (0.59 to 0.96; run SD 0.38) | 0.62 (0.43 to 0.81; run SD 0.47) |

### Shared minus isolated notes, wrong terms per week

| Design | Notes record drafted terms | Notes record released terms |
|---|---|---|
| Review every quote | +0.000 (+0.00 to +0.00); 0% of draws one way | -0.080 (-0.28 to +0.00); 91% of draws one way |
| Release within shared limits | +0.014 (+0.00 to +0.04); 78% of draws one way | +0.008 (+0.00 to +0.03); 75% of draws one way |
| Refer local exceptions | +0.018 (+0.00 to +0.05); 92% of draws one way | -0.146 (-0.27 to -0.06); holds across ranges |

### Design comparisons, isolated notes, drafted terms

| Comparison (first minus second) | Measure | Mean difference | Draws first higher | Draws first lower | Verdict (95% rule) | Reversing draws listed |
|---|---|---|---|---|---|---|
| Review every quote against Release within shared limits | wrong terms | +1.28 | 98% | 2% | holds: first is higher | 1 |
| Review every quote against Release within shared limits | days mean | +2.07 | 94% | 6% | depends on the assumptions | 0 |
| Review every quote against Release within shared limits | total reviews | +17.09 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | inconsistent customers | +1.07 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | repeat all wrong | +0.41 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Refer local exceptions | wrong terms | -0.84 | 5% | 95% | holds: first is lower | 3 |
| Review every quote against Refer local exceptions | days mean | +1.73 | 97% | 3% | holds: first is higher | 2 |
| Review every quote against Refer local exceptions | total reviews | +11.81 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Refer local exceptions | inconsistent customers | +0.12 | 80% | 19% | depends on the assumptions | 0 |
| Review every quote against Refer local exceptions | repeat all wrong | +0.13 | 100% | 0% | holds: first is higher | 0 |
| Release within shared limits against Refer local exceptions | wrong terms | -2.12 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | days mean | -0.34 | 6% | 94% | depends on the assumptions | 0 |
| Release within shared limits against Refer local exceptions | total reviews | -5.28 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | inconsistent customers | -0.95 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | repeat all wrong | -0.28 | 0% | 100% | holds: first is lower | 0 |

## After the pilot (commit 3029b32, 2026-10-03 14:05 UTC)

| Measure, per week | Review every quote | Release within shared limits | Refer local exceptions |
|---|---|---|---|
| Quotes with wrong terms reaching customers (of 20) | 2.94 (2.05 to 3.87; run SD 1.17) | 1.34 (0.76 to 1.90; run SD 1.00) | 3.50 (2.43 to 4.60; run SD 1.32) |
| Average days to customer | 3.13 (1.18 to 5.10; run SD 0.44) | 1.05 (0.72 to 1.35; run SD 0.25) | 1.47 (1.05 to 1.94; run SD 0.29) |
| Reviews by regional leads | 20.0 (20.0 to 20.0; run SD 0.0) | 0.0 (0.0 to 0.0; run SD 0.0) | 5.8 (4.4 to 6.9; run SD 1.3) |
| Reviews by head office | 1.0 (0.5 to 1.6; run SD 0.8) | 3.8 (3.5 to 4.2; run SD 0.8) | 3.7 (3.2 to 4.4; run SD 0.8) |
| Busiest lead's review effort, share of the week | 1.38 (0.33 to 2.38; run SD 0.23) | 0.00 (0.00 to 0.00; run SD 0.00) | 0.54 (0.12 to 0.92; run SD 0.19) |
| Customers with inconsistent terms across quotes | 1.17 (0.99 to 1.48; run SD 0.61) | 0.03 (0.00 to 0.07; run SD 0.15) | 0.98 (0.73 to 1.22; run SD 0.66) |
| Repeat customers with every quote wrong | 0.41 (0.14 to 0.72; run SD 0.53) | 0.00 (0.00 to 0.00; run SD 0.00) | 0.25 (0.05 to 0.50; run SD 0.42) |
| Wrong terms: standard quotes (11 a week) | 0.37 (0.10 to 0.70; run SD 0.56) | 0.75 (0.27 to 1.34; run SD 0.84) | 0.64 (0.23 to 1.13; run SD 0.77) |
| Wrong terms: written agreements (5 a week) | 2.34 (1.68 to 3.04; run SD 0.92) | 0.05 (0.00 to 0.10; run SD 0.19) | 2.32 (1.43 to 3.11; run SD 1.00) |
| Wrong terms: verbal promise (1 a week) | 0.23 (0.08 to 0.35; run SD 0.40) | 0.54 (0.33 to 0.77; run SD 0.48) | 0.55 (0.33 to 0.75; run SD 0.48) |

### The same with shared notes

| Measure, per week | Review every quote | Release within shared limits | Refer local exceptions |
|---|---|---|---|
| Quotes with wrong terms reaching customers (of 20) | 2.94 (2.05 to 3.87; run SD 1.17) | 1.34 (0.77 to 1.91; run SD 1.00) | 3.52 (2.43 to 4.60; run SD 1.32) |
| Average days to customer | 3.13 (1.18 to 5.10; run SD 0.44) | 1.05 (0.72 to 1.36; run SD 0.25) | 1.47 (1.04 to 1.94; run SD 0.29) |
| Reviews by regional leads | 20.0 (20.0 to 20.0; run SD 0.0) | 0.0 (0.0 to 0.0; run SD 0.0) | 5.8 (4.4 to 6.9; run SD 1.3) |
| Reviews by head office | 1.0 (0.5 to 1.6; run SD 0.8) | 3.9 (3.5 to 4.2; run SD 0.9) | 3.6 (3.2 to 4.3; run SD 0.8) |
| Busiest lead's review effort, share of the week | 1.38 (0.33 to 2.38; run SD 0.23) | 0.00 (0.00 to 0.00; run SD 0.00) | 0.54 (0.12 to 0.92; run SD 0.19) |
| Customers with inconsistent terms across quotes | 1.14 (0.95 to 1.47; run SD 0.62) | 0.04 (0.00 to 0.08; run SD 0.16) | 0.98 (0.73 to 1.21; run SD 0.66) |
| Repeat customers with every quote wrong | 0.41 (0.14 to 0.72; run SD 0.53) | 0.00 (0.00 to 0.00; run SD 0.00) | 0.25 (0.05 to 0.50; run SD 0.42) |
| Wrong terms: standard quotes (11 a week) | 0.37 (0.10 to 0.70; run SD 0.56) | 0.75 (0.27 to 1.34; run SD 0.84) | 0.64 (0.23 to 1.13; run SD 0.77) |
| Wrong terms: written agreements (5 a week) | 2.34 (1.68 to 3.04; run SD 0.92) | 0.06 (0.00 to 0.12; run SD 0.20) | 2.33 (1.44 to 3.13; run SD 1.00) |
| Wrong terms: verbal promise (1 a week) | 0.23 (0.08 to 0.35; run SD 0.40) | 0.54 (0.33 to 0.77; run SD 0.48) | 0.55 (0.33 to 0.75; run SD 0.48) |

### Shared minus isolated notes, wrong terms per week

| Design | Notes record drafted terms | Notes record released terms |
|---|---|---|
| Review every quote | +0.000 (+0.00 to +0.00); 0% of draws one way | -0.122 (-0.44 to -0.00); 94% of draws one way |
| Release within shared limits | +0.006 (+0.00 to +0.02); 77% of draws one way | +0.005 (-0.00 to +0.01); 70% of draws one way |
| Refer local exceptions | +0.019 (+0.00 to +0.04); 89% of draws one way | -0.228 (-0.37 to -0.12); holds across ranges |

### Design comparisons, isolated notes, drafted terms

| Comparison (first minus second) | Measure | Mean difference | Draws first higher | Draws first lower | Verdict (95% rule) | Reversing draws listed |
|---|---|---|---|---|---|---|
| Review every quote against Release within shared limits | wrong terms | +1.60 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | days mean | +2.08 | 97% | 3% | holds: first is higher | 2 |
| Review every quote against Release within shared limits | total reviews | +17.14 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | inconsistent customers | +1.14 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | repeat all wrong | +0.41 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Refer local exceptions | wrong terms | -0.56 | 16% | 84% | depends on the assumptions | 0 |
| Review every quote against Refer local exceptions | days mean | +1.66 | 95% | 5% | holds: first is higher | 3 |
| Review every quote against Refer local exceptions | total reviews | +11.52 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Refer local exceptions | inconsistent customers | +0.19 | 92% | 8% | depends on the assumptions | 0 |
| Review every quote against Refer local exceptions | repeat all wrong | +0.16 | 100% | 0% | holds: first is higher | 0 |
| Release within shared limits against Refer local exceptions | wrong terms | -2.17 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | days mean | -0.42 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | total reviews | -5.62 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | inconsistent customers | -0.95 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | repeat all wrong | -0.25 | 0% | 100% | holds: first is lower | 0 |

### Design comparisons, shared notes, drafted terms

| Comparison (first minus second) | Measure | Mean difference | Draws first higher | Draws first lower | Verdict (95% rule) | Reversing draws listed |
|---|---|---|---|---|---|---|
| Review every quote against Release within shared limits | wrong terms | +1.60 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | days mean | +2.08 | 97% | 3% | holds: first is higher | 2 |
| Review every quote against Release within shared limits | total reviews | +17.13 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | inconsistent customers | +1.10 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Release within shared limits | repeat all wrong | +0.41 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Refer local exceptions | wrong terms | -0.58 | 16% | 84% | depends on the assumptions | 0 |
| Review every quote against Refer local exceptions | days mean | +1.66 | 95% | 5% | holds: first is higher | 3 |
| Review every quote against Refer local exceptions | total reviews | +11.54 | 100% | 0% | holds: first is higher | 0 |
| Review every quote against Refer local exceptions | inconsistent customers | +0.16 | 84% | 12% | depends on the assumptions | 0 |
| Review every quote against Refer local exceptions | repeat all wrong | +0.16 | 100% | 0% | holds: first is higher | 0 |
| Release within shared limits against Refer local exceptions | wrong terms | -2.18 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | days mean | -0.41 | 2% | 98% | holds: first is lower | 1 |
| Release within shared limits against Refer local exceptions | total reviews | -5.59 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | inconsistent customers | -0.94 | 0% | 100% | holds: first is lower | 0 |
| Release within shared limits against Refer local exceptions | repeat all wrong | -0.25 | 0% | 100% | holds: first is lower | 0 |

## Which comparisons changed

14 of 135 comparisons changed their verdict.

| Family | Comparisons | Changed | Held before | Hold after |
|---|---|---|---|---|
| baseline | 18 | 0 | 5 | 5 |
| context | 30 | 1 | 2 | 3 |
| design | 60 | 12 | 49 | 53 |
| gate_effect | 12 | 0 | 3 | 3 |
| gate_off_design | 9 | 1 | 7 | 6 |
| notes_assumption | 6 | 0 | 2 | 2 |

| Family | First | Second | Measure | Change | Draws higher / lower, before | after | Mean difference before | after |
|---|---|---|---|---|---|---|---|---|
| context | Review every quote, shared notes, notes record released terms | Review every quote, isolated notes, notes record released terms | inconsistent customers | now holds | 5% / 94% | 0% / 100% | -0.085 | -0.150 |
| design | Release within shared limits, isolated notes, notes record draft terms | Refer local exceptions, isolated notes, notes record draft terms | days mean | now holds | 6% / 94% | 0% / 100% | -0.343 | -0.421 |
| design | Release within shared limits, isolated notes, notes record released terms | Refer local exceptions, isolated notes, notes record released terms | days mean | now holds | 6% / 94% | 0% / 100% | -0.343 | -0.421 |
| design | Release within shared limits, shared notes, notes record draft terms | Refer local exceptions, shared notes, notes record draft terms | days mean | now holds | 8% / 92% | 2% / 98% | -0.330 | -0.414 |
| design | Release within shared limits, shared notes, notes record released terms | Refer local exceptions, shared notes, notes record released terms | days mean | now holds | 6% / 94% | 2% / 98% | -0.334 | -0.416 |
| design | Review every quote, isolated notes, notes record draft terms | Release within shared limits, isolated notes, notes record draft terms | days mean | now holds | 94% / 6% | 97% / 3% | +2.074 | +2.080 |
| design | Review every quote, isolated notes, notes record draft terms | Refer local exceptions, isolated notes, notes record draft terms | wrong terms | no longer holds | 5% / 95% | 16% / 84% | -0.843 | -0.564 |
| design | Review every quote, isolated notes, notes record released terms | Release within shared limits, isolated notes, notes record released terms | days mean | now holds | 94% / 6% | 97% / 3% | +2.074 | +2.080 |
| design | Review every quote, isolated notes, notes record released terms | Refer local exceptions, isolated notes, notes record released terms | wrong terms | no longer holds | 5% / 95% | 16% / 84% | -0.843 | -0.564 |
| design | Review every quote, shared notes, notes record draft terms | Release within shared limits, shared notes, notes record draft terms | days mean | now holds | 94% / 6% | 97% / 3% | +2.065 | +2.078 |
| design | Review every quote, shared notes, notes record draft terms | Refer local exceptions, shared notes, notes record draft terms | wrong terms | no longer holds | 2% / 98% | 16% / 84% | -0.861 | -0.583 |
| design | Review every quote, shared notes, notes record released terms | Release within shared limits, shared notes, notes record released terms | days mean | now holds | 94% / 6% | 97% / 3% | +2.069 | +2.079 |
| design | Review every quote, shared notes, notes record released terms | Refer local exceptions, shared notes, notes record released terms | wrong terms | no longer holds | 3% / 97% | 17% / 83% | -0.777 | -0.459 |
| gate_off_design | Review every quote, isolated notes, notes record draft terms, gate off | Refer local exceptions, isolated notes, notes record draft terms, gate off | wrong terms | no longer holds | 5% / 95% | 16% / 84% | -0.843 | -0.564 |

## Robustness check on the held-out weeks

Outcome: **pass**. 47 of 51 frozen conclusions pass.

| Measure | Conclusions | Passed | Share | Target (80%) |
|---|---|---|---|---|
| wrong_terms | 10 | 10 | 100% | pass |
| days_mean | 12 | 12 | 100% | pass |
| inconsistent_customers | 16 | 12 | 75% | reported only |
| repeat_all_wrong | 13 | 13 | 100% | reported only |

Conclusions that did not pass:

| First | Second | Measure | Share of held-out draws with the frozen sign |
|---|---|---|---|
| Review every quote, shared notes, notes record draft terms | Review every quote, shared notes, notes record draft terms, independent errors | inconsistent customers | 81% |
| Review every quote, shared notes, notes record released terms | Review every quote, isolated notes, notes record released terms | inconsistent customers | 89% |
| Review every quote, shared notes, notes record released terms | Review every quote, shared notes, notes record released terms, independent errors | inconsistent customers | 88% |
| Refer local exceptions, shared notes, notes record draft terms | Refer local exceptions, shared notes, notes record draft terms, independent errors | inconsistent customers | 72% |
