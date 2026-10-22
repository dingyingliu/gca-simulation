# Licences of data and third-party material

The code in this repository is under the MIT licence (`LICENSE`). Some files are derived from, or depend on, material under other terms.

## BPI Challenge 2020: Domestic Declarations

- **What it is:** a public, anonymised event log of about 10,500 travel-expense claims at Eindhoven University of Technology, 2017 to 2018.
- **Creator:** Boudewijn van Dongen, Eindhoven University of Technology. Published on 4TU.ResearchData.
- **DOI:** 10.4121/uuid:3f422315-ed9d-4882-891f-e180b5b4feb5
- **Licence:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0), https://creativecommons.org/licenses/by-nc/4.0/
- **In this repository:** the log itself is **not** included. Files derived from it (aggregated counts, timings and the recovered workflow) are shared under CC BY-NC 4.0, not under MIT. They may not be used commercially. At present that is `specs/bpic2020_declarations.workflow.json`; later additions are listed here as they are published.

## PM4Py

The analysis of the BPI Challenge 2020 log uses PM4Py, which is licensed AGPL-3.0-or-later. PM4Py is **not** included in this repository and is not needed by the simulator or the agent experiment. It is an optional install (`pip install ".[process-mining]"`).
