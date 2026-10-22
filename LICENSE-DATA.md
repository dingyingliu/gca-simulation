# Licences of data and third-party material

The code in this repository is under the MIT licence (`LICENSE`). Some files are derived from, or depend on, material under other terms.

## BPI Challenge 2020: Domestic Declarations

- **What it is:** a public, anonymised event log of about 10,500 travel-expense claims at Eindhoven University of Technology, 2017 to 2018.
- **Creator:** Boudewijn van Dongen, Eindhoven University of Technology. Published on 4TU.ResearchData.
- **DOI:** 10.4121/uuid:3f422315-ed9d-4882-891f-e180b5b4feb5
- **Licence:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0), https://creativecommons.org/licenses/by-nc/4.0/
- **In this repository:** the log itself is **not** included. Files derived from it (aggregated counts, timings and the recovered workflow) are shared under CC BY-NC 4.0, not under MIT. They may not be used commercially. These are `specs/bpic2020_declarations.workflow.json`, the evidence records `evidence/records/*.bpic2020.json`, the E3 results and pictures in `reports/E3/` and the report `reports/E3_real_log.md`. `data/metadata/4tu_article_12692543.json` is the dataset's public metadata record, saved as 4TU.ResearchData returned it.

## τ-bench

- **What it is:** recorded conversations between AI agents and simulated customers, published by Sierra in the repository https://github.com/sierra-research/tau-bench (commit 59a200c6d575d595120f1cb70fea53cef0632f6b).
- **Licence:** MIT, Copyright (c) 2024 Sierra.
- **In this repository:** the recordings are **not** included. Counts derived from them, and short excerpts quoted for the hand check, are in `reports/E6/`, `reports/E6_taubench_check.md` and `evidence/records/*.taubench_retail.json`, under τ-bench's MIT licence.

## PM4Py

The analysis of the BPI Challenge 2020 log uses PM4Py, which is licensed AGPL-3.0-or-later. PM4Py is **not** included in this repository and is not needed by the simulator or the agent experiment. It is an optional install (`pip install ".[process-mining]"`).
