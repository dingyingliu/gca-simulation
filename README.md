# GCA Simulation (Global Collaboration with AI Agents)

A research simulator of AI-assisted office work, and an experiment harness that tests a real AI model on the same tasks.

It was built for **Global Collaboration with AI Agents (GCA)**, an economics and management research project, funded by the 2026 CEMS Philippe Louvet Innovation Grant, with a cross-school course for the CEMS alliance of business schools. In the course, student teams run a simulated multinational company where AI agents do part of the work. Each team chooses a management design, deciding which work goes to AI agents, who may do what, who checks whose work, and who can see which information. The simulator plays out a week of work under that design and shows the consequences.

The research question is economic. A management design sets the division of labour and of information between people and AI agents, and the research asks how that choice changes productivity, how it trades the cost of review against the cost of errors, and who bears the cost when an agent is wrong.

The first exercise is about customer quotations. AI agents draft price quotes for regional sales teams, and people review some of them. Some customers have special terms agreed with head office, and not everyone can see them.

## What it does

- **A simulator in which nobody can see the right answer.** Every role (AI agent, regional lead, head office) decides only from what it can observe, and a test checks that no decision ever reads the ground truth. Mistakes therefore arise as they do in a real organisation, through missing information, wrong notes and reviews that fail.
- **Every number has a stated source.** Each parameter is labelled *observed* (counted in real data), *fitted* (estimated from a sample), *assumed* (a stated guess, given as a range) or *illustrative*. Conclusions are tested across the whole range of every guess (`evidence/assumptions.yaml`, `evidence/records/`).
- **An experiment with a real AI model.** An open-weight large language model, acting as the quoting agent, drafted 504 quotes under four conditions. It could see the customer's agreement or not, and it either had a shared notebook of earlier agents' notes or did not. The experiment tests the model's judgement under missing information, whether it passes a quote it cannot verify to a person or follows a colleague's note. The plan was fixed before the runs, and some tasks were held back and used once at the end (`experiments/agent_pilot_plan.md`).
- **The experiment's results feed back into the simulator.** Its estimates replaced the matching guesses, and the change to every conclusion is reported.

## What the first round found

- **Information matters more than monitoring. Who can see the customer's agreement matters more than who reviews it.** In the simulator, the design that lets the agent and head office read every agreement had the fewest wrong quotes under every combination of assumptions tried. In the experiment, the agent that could see the agreement got all 120 quotes right and ignored a wrong note.
- **A shared notebook cuts both ways.** When the agent could not see the agreement, it followed a note about the customer most of the time, whether the note was right (14 of 15) or wrong (19 of 30).
- **The model's caution limited the damage.** It passed most quotes it could not verify to a person. The wrong note reached the customer in 7 of 30 cases, against 3 of 30 without shared notes. The experiment is too small to say this difference is real.
- **Real evidence changed the simulator's conclusions.** Putting the experiment's numbers into the simulator changed 14 of its 135 comparisons.
- **The largest gap is human behaviour.** No data used here says how often a human reviewer catches a mistake or how long a review takes. Several conclusions depend on those guesses.

The full account, written for a reader new to the project, is in [`reports/first_round_report.md`](reports/first_round_report.md). The detailed reports are in `reports/`.

## Install and run the tests

Requires Python 3.13.

    git clone https://github.com/dingyingliu/gca-simulation.git
    cd gca-simulation
    python3 -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    python -m pip install -r requirements.lock
    python -m pytest

Three tests are skipped unless the BPI Challenge 2020 log is downloaded (see `data/SOURCES.md`). The log analysis also needs the optional install `pip install -r requirements-process-mining.lock`.

## Rebuild the recorded results

The recorded run files are in the repository, so the analysis can be rebuilt without calling any model.

    python experiments/agent_pilot/analyse_pilot.py --development
    python experiments/agent_pilot/make_tables.py
    python experiments/e4_quotation/make_tables.py

The analysis checks the scoring code, the prompt and the run file against the SHA-256 fingerprints recorded with the results, and refuses to run if any of them differ. A rebuild gives the same numbers, and only timestamps and commit ids change.

## Repository map

| Folder | What is in it |
|---|---|
| `gca_sim/simulator/` | The research simulator |
| `gca_sim/pilot/` | The experiment harness: tasks, prompt, model client, spending guard, scoring, analysis |
| `gca_sim/demo_replica/` | An exact Python replica of the course's original demonstration, checked against its JavaScript |
| `gca_sim/process_logs/` | A reader for the BPI Challenge 2020 event log |
| `specs/simulated_weeks/` | The frozen simulated weeks: development and held-out |
| `evidence/` | The assumptions file and one record for every number's source |
| `experiments/` | The experiment plan and run scripts, and the AI model's recorded answers |
| `reports/` | Reports, tables and figures |
| `tests/` | The test suite |

## How it was built

The code was written by Claude Code under the direction of Dingying Liu, who decided every disagreement and every question of money or scope. Two further AI agents, a second Claude and Codex, reviewed each batch of work independently, without seeing each other's reviews. Over thirteen review rounds they raised 85 points. Six were blocking, and work on that part stopped until they were fixed. The first round ran on 2 and 3 October 2026 and cost nothing in model fees.

## Where the recorded results come from

The results were produced in a private development repository, whose history is not published. For this release the code was given clearer names, and [`RENAMES.md`](RENAMES.md) maps old names to new ones and explains what was left unchanged on purpose. The reports keep the old names and refer to the project's private brief, lab log and reviews, which are not included. The frozen data files and the experiment's code are byte for byte as they were run, and the public code reproduces the recorded results.

## Author

Dingying Liu, principal investigator. To cite this work, see [`CITATION.cff`](CITATION.cff).

## Licence

The code is under the MIT licence ([`LICENSE`](LICENSE)). Files derived from the BPI Challenge 2020 log (Boudewijn van Dongen, Eindhoven University of Technology, 4TU.ResearchData, DOI 10.4121/uuid:3f422315-ed9d-4882-891f-e180b5b4feb5) are under CC BY-NC 4.0, and the log itself is not included. Excerpts from τ-bench are under its MIT licence. PM4Py (AGPL-3.0) is not included and is used only by the optional log analysis. Details are in [`LICENSE-DATA.md`](LICENSE-DATA.md).
