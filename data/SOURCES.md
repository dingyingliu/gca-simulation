# Sources

Every external dataset, repository and reference file this project uses, with what was checked and when. Rechecked by Claude Code (build) at E0 on 2026-10-02 (UTC) against the live 4TU.ResearchData API, the GitHub API, the Hugging Face API and PyPI. Licences are recorded as each source states them. Nothing here is legal advice.

## Datasets

### BPI Challenge 2020, Domestic Declarations (used in E3)

| Field | Value |
|---|---|
| Title | BPI Challenge 2020: Domestic Declarations |
| Creator | Boudewijn van Dongen, Eindhoven University of Technology |
| 4TU article | 12692543 (uuid 6a0a26d2-82d0-4018-b1cd-89afb0e8627f), version 1, published 2020-03-26 |
| DOI | 10.4121/uuid:3f422315-ed9d-4882-891f-e180b5b4feb5 (resolves to data.4tu.nl/articles/_/12692543/1, checked 2026-10-02 UTC) |
| Landing page | https://data.4tu.nl/datasets/6a0a26d2-82d0-4018-b1cd-89afb0e8627f/1 |
| Licence (as stated on the dataset record) | CC BY-NC 4.0, https://creativecommons.org/licenses/by-nc/4.0/ |
| Stated content | 10,500 cases, 56,437 events. Travel expense claims, 2017 (two departments) and 2018 (whole university). |
| Stated process | Submission by the employee, then travel administration, then budget owner, then supervisor (one step if budget owner and supervisor are the same person), sometimes director, then payment requested and paid. |
| Downloaded | 2026-10-02 20:05 UTC, direct download, no login |
| File | `data/raw/DomesticDeclarations.xes.gz`, 933,930 bytes |
| Download URL | https://data.4tu.nl/file/6a0a26d2-82d0-4018-b1cd-89afb0e8627f/6eeb0328-f991-48c7-95f2-35033504036e |
| SHA-256 | 0bc3312acf0b9ee5ae6f4ebe9df204005ef11665d62f2d21dd04995161d7532b |
| MD5 | 6a78c39491498363ce4788e0e8ca75ef (matches the MD5 supplied by 4TU) |
| File | `data/raw/BPIC2020_DomesticDeclarations_README.txt`, 1,616 bytes |
| SHA-256 | 1cd883bbb879375ffdf34c2616a7184e01dc57d55d4dac2e0d48a230c14eb31f |
| MD5 | 08bbb2eaa626fe911dad264a9660247b (matches the MD5 supplied by 4TU) |

Metadata record, kept so the licence and checksums can be checked again without the live site:

| Field | Value |
|---|---|
| API URL | https://data.4tu.nl/v2/articles/12692543 |
| Saved response | `data/metadata/4tu_article_12692543.json`, byte for byte as returned, retrieved 2026-10-02 22:14 UTC, SHA-256 a232119172281a49d86aec7be653b91ef78375adf19df87f175ba778a131881b |
| Licence field in the response | `{"value": 10, "name": "CC BY-NC 4.0", "url": "https://creativecommons.org/licenses/by-nc/4.0/"}` |
| Note | The 20:05 UTC check read the same API URL but did not save the response. The 22:14 UTC response gives the same licence, DOI, version (1, modified 2020-07-28) and file MD5s as recorded above. |

Every evidence record and workflow spec derived from this log carries `"licence": "CC BY-NC 4.0"` in its `source`, so derived values can be filtered out of any release that the non-commercial term does not allow. `tests/test_evidence_records.py` checks that every record citing a DOI carries a licence.

Licence note. CC BY-NC 4.0 requires attribution and forbids commercial use. Local research use is fine. Any derived values used in a course delivered for a fee, or in a hosted product, should be checked against the non-commercial term first. Derived evidence records cite this source.

Note. The DOI 10.4121/uuid:ea03d361-a7cd-4f5e-83d8-5fbdf0362550 is the travel-permit log. The Domestic Declarations log has its own DOI, given above. Both resolve.

### BPI Challenge 2020, Travel Permits (not downloaded)

| Field | Value |
|---|---|
| DOI | 10.4121/uuid:ea03d361-a7cd-4f5e-83d8-5fbdf0362550, resolves to data.4tu.nl/articles/_/12718178/1 (checked 2026-10-02 UTC) |
| Status | Not used in the first round |

### BPI Challenge 2017, Offer log (not downloaded, not needed in the first round)

| Field | Value |
|---|---|
| 4TU article | 12705737 (uuid cc497753-1175-41f6-a107-425787c54266), version 2 |
| DOI | 10.4121/12705737.v2 |
| Licence (as stated on the dataset record) | 4TU General Terms of Use, https://doi.org/10.4121/resource:terms_of_use. Not a Creative Commons licence. Read the terms before using it. |
| File available | `BPI Challenge 2017 - Offer log.xes.gz`, 5,010,479 bytes, direct download, MD5 130221de81e95f95581f2ec2e37a4aca (supplied by 4TU) |

## Agent traces

### τ-bench (E6)

| Field | Value |
|---|---|
| Repository | https://github.com/sierra-research/tau-bench |
| Licence | MIT (GitHub API, 2026-10-02 UTC) |
| Last push | 2026-03-18 |
| `historical_trajectories/` | gpt-4o-airline.json (4,114,038 bytes), gpt-4o-retail.json (10,813,408), sonnet-35-new-airline.json (10,888,682), sonnet-35-new-retail.json (26,544,890) |
| Notice in README | The tasks in this repository are not updated. It points to τ³-bench (repository sierra-research/tau2-bench). |
| Status | Cloned into `third_party/tau-bench/` (git-ignored) at E6 on 2026-10-02 22:43 UTC, with `core.autocrlf=false` so the files match the repository byte for byte (a first clone with Windows line-ending conversion gave different sizes and hashes and was discarded). |
| Commit used | 59a200c6d575d595120f1cb70fea53cef0632f6b (2026-03-18) |
| Files used (E6) | `historical_trajectories/gpt-4o-retail.json`: 10,813,408 bytes, SHA-256 df01707894836168ff0ec9616b0bf08f66c7e5afcf313e5fe4f7a2f5c2ec938b, git blob 27f588d9157513c3ad11de3db9e824021152d580. `historical_trajectories/sonnet-35-new-retail.json`: 26,544,890 bytes, SHA-256 0df526398e9d2720c32d340815cffb04fe8c4f8a61b1f4f84bf3bb558f760131, git blob f2296500688950bac6c54578752ef134961aee06. `experiments/e6_taubench/check_taubench.py` refuses to run if the commit or either hash differs. |
| Not used | The two airline files (gpt-4o-airline.json SHA-256 e9e6c0297660c537f83d4fd9c476ce7a9a86ecd2784874b7bfc13be598e37bfa; sonnet-35-new-airline.json SHA-256 fe62fcd514b855b36f156dd4c3c7748597b392b006aff739b53337a9f3ba94d1). |

### τ³-bench (repository sierra-research/tau2-bench)

| Field | Value |
|---|---|
| Licence | MIT (GitHub API, 2026-10-02 UTC) |
| Pre-computed trajectories | None in the repository tree (1,772 paths checked). It holds a leaderboard example submission whose `trajectories/` folder contains only a README, and three voice-test fixtures. Whether leaderboard submissions host trajectories elsewhere was not checked. |

### Who&When (later, not this round)

| Field | Value |
|---|---|
| Dataset | https://huggingface.co/datasets/Kevin355/Who_and_When, public, not gated, last modified 2025-12-21 |
| Content | 184 annotated failure tasks (algorithm-generated and hand-crafted multi-agent systems), with the responsible agent and decisive error step |
| Dataset licence | Not stated on the dataset card or in its tags. Reuse terms are unclear. Ask the authors or check the paper before using it beyond reading. |
| Code | https://github.com/mingyin1/Agents_Failure_Attribution, MIT |

## Software

| Package or repository | Version | Licence | Note |
|---|---|---|---|
| PM4Py | 2.7.23.8 | AGPL-3.0 (GitHub), AGPL-3.0-or-later (PyPI) | An optional install, used only by the E3 log analysis, and not included in this repository. It prints a licence banner on import. |
| SimPy | 4.1.2 | MIT | |
| mini-racer | 0.14.1 | ISC | Embeds V8. One of two engines for regenerating the E1 golden outputs from the original prototype JavaScript; confined to `tests/golden/make_demo_golden.py` by a test. |
| Node | v24.19.0 | MIT | Not installed system-wide. A local copy was used at 22:13 UTC on 2026-10-02 to cross-check the golden outputs; both engines gave byte-identical files. Nothing was installed. |
| numpy, pandas, scipy, matplotlib, pyyaml, jsonschema, pytest | see `pyproject.toml` | BSD, MIT or PSF-compatible | |
| OrgForge | not cloned | MIT | The repository moved from aeriesec/orgforge to https://github.com/tenurehq/orgforge. Ideas only. |

## Project reference files (not included)

| File | SHA-256 | Note |
|---|---|---|
| `One_Week_in_the_Course.html` | 9fcd4c02491d0714ba99a3424665899acbec487a9431629c5900d5a9d18c6bb5 | Prototype walkthrough, last modified 2026-09-15. A copy of its `<script>` block is kept in `gca_sim/demo_replica/original/` for the E1 golden outputs. Invented, illustrative case. |
