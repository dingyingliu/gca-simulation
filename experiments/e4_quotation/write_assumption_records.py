"""Write one evidence record per declared E4 parameter, from evidence/assumptions.yaml."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gca_sim import evidence  # noqa: E402
from gca_sim.process_logs import bpic2020  # noqa: E402
from gca_sim.simulator import params  # noqa: E402

UNITS = {"effort_lead": "working days", "delay_lead": "working days", "effort_ho": "working days",
         "delay_ho": "working days", "sigma_review": "log scale"}
# after the agent pilot (E5): the pilot's evidence records behind each range it set
PILOT_RECORDS = {"e_visible": ["e_visible.agent_pilot"], "p_flag_unverifiable": ["flag_unverifiable.agent_pilot"],
                 "p_adopt_blind": ["note_adoption_blind.agent_pilot", "note_adoption_help.agent_pilot"],
                 "p_notice_visible": ["note_adoption_visible.agent_pilot"],
                 "p_newest_note": ["note_reading_rule.agent_pilot", "note_adoption_blind.agent_pilot"],
                 "p_flag_after_note": ["flag_after_note.agent_pilot"]}
PILOT_SOURCE = {"name": "GCA controlled agent pilot (E5), development groups, applied by "
                        "experiments/e4_quotation/apply_pilot.py", "doi": None, "licence": None, "retrieved_utc": None}


PRODUCT_NOTE = ("Not identified on its own. The pilot fits a combination of parameters (the records named in the "
                "notes); this parameter follows from that combination and from an assumed parameter, so it stays an "
                "assumption.")


def parameter_record(name: str, spec: dict, versions: dict, declared: str, pilot_constraints: dict | None = None) -> dict:
    """The evidence record of one declared parameter.

    - A range that is the pilot's interval for a frequency which is this parameter (status `pilot`) is recorded
      as fitted, with the pilot as its source.
    - A parameter that follows from a fitted combination and an assumed parameter (status `pilot_product`) stays
      assumed, with the constraint and the fitted records named: the pilot does not identify it on its own
.
    - Every other range is a declared assumption. After the pilot, p_read_note's record says how it is drawn.

    The declared time is the parameter's own if it has one and otherwise the time of the file. For a range the pilot set, the notes say when it was set."""
    analogue = spec["status"] == "analogue"
    pilot = spec["status"] == "pilot"
    product = spec["status"] == "pilot_product"
    source = ({**bpic2020.SOURCE, "name": "Declared assumption, range informed by BPI Challenge 2020 "
                                          "Domestic Declarations (analogue)"} if analogue
              else PILOT_SOURCE if pilot
              else {"name": "Declared assumption, constrained by the GCA controlled agent pilot (E5)", "doi": None,
                    "licence": None, "retrieved_utc": None} if product
              else {"name": "Declared assumption, evidence/assumptions.yaml", "doi": None, "licence": None,
                    "retrieved_utc": None})
    constrained_read = name == "p_read_note" and bool((pilot_constraints or {}).get("products"))
    if product:
        distribution = ("not drawn on its own: it follows from a combination drawn from the pilot's interval and "
                        "from an assumed parameter (gca_sim/simulator/params.py)")
    elif constrained_read:
        distribution = ("uniform over the declared range cut from below, draw by draw, at the larger of the two "
                        "products drawn from the pilot's intervals (p_read_note x p_adopt_blind and p_read_note x "
                        "(1 - p_notice_visible))")
    else:
        distribution = "uniform over the range (Latin hypercube draws)"
    rec = {
        "id": params.evidence_id(name),
        "mechanism": spec["meaning"],
        "measures": ("Nothing measured directly. The range is set from an observed analogue: "
                     + spec["basis"]) if analogue else (spec["basis"] if pilot or product
                                                        else "Nothing measured. A declared assumption."),
        "simulator_parameter": name,
        "estimable": "partly" if analogue or pilot else "no",
        "estimable_note": ("The analogue measures elapsed time including queueing and off-hours, not review "
                           "service time, so it bounds the range rather than estimating the value."
                           if analogue else
                           "A pilot: few tasks per cell, one model, one prompt, synthetic tasks. The range is the "
                           "pilot's interval, not a stable estimate."
                           if pilot else
                           PRODUCT_NOTE
                           if product else
                           "No evidence yet. " + (f"Planned estimate: {spec['replaced_by']}."
                                                  if spec.get("replaced_by") else "No estimate planned this round.")),
        "value": {"unit": UNITS.get(name, "probability"), "range": [float(x) for x in spec["range"]],
                  "distribution": distribution},
        "status": "fitted" if pilot else "assumed",
        "source": source,
        "conditions": "E4 quotation research model; every design, context and week",
        "transfer": spec["basis"],
        "versions": versions,
        "disagreements": [],
        "tests": [],
        "declared_utc": spec.get("declared_utc") or declared,
        "created_utc": evidence.utc_now(),
        "used_by": ["gca_sim/simulator"],
    }
    if analogue:
        rec["notes"] = "Analogue records: " + ", ".join(spec.get("analogue_records", []))
    if spec.get("context_records"):
        rec["notes"] = ("Context only, not a bound (review round 3, Codex R3.3): "
                        + ", ".join(spec["context_records"]))
    set_on = (pilot_constraints or {}).get("applied_utc")
    when = f" Range set on {set_on} by experiments/e4_quotation/apply_pilot.py." if set_on else ""
    if pilot:
        rec["use"] = "range_only"
        rec["notes"] = "Pilot records behind this range: " + ", ".join(PILOT_RECORDS[name]) + "." + when
    if product:
        rec["notes"] = "Constrained through the fitted pilot records: " + ", ".join(PILOT_RECORDS[name]) + "." + when
    if constrained_read:
        rec["notes"] = ("The pilot does not measure reading a note on its own. This parameter is constrained "
                        "through the fitted records note_adoption_blind.agent_pilot, note_adoption_help.agent_pilot "
                        "and note_adoption_visible.agent_pilot.")
    return rec


def main() -> None:
    a = params.load_assumptions()
    git = evidence.git_state(["evidence/assumptions.yaml", "experiments/e4_quotation/write_assumption_records.py"])
    versions = {**git, "analysis": "experiments/e4_quotation/write_assumption_records.py", "model": None}
    declared = a["declared_utc"]
    for old in evidence.RECORDS_DIR.glob("quotation.*.json"):  # this script owns every quotation.* record
        old.unlink()
    for name in params.PARAM_NAMES:
        evidence.write(parameter_record(name, a["parameters"][name], versions, declared, a.get("pilot_constraints")))
    s = a["structural"]
    structural = [
        ("t_draft", "Time for the agent to draft and send a quote", "illustrative",
         {"unit": "working days", "point": s["t_draft"]["value"]}, s["t_draft"]["basis"]),
        ("notes_record", "What an agent's note records: the drafted terms or the terms as released after review",
         "assumed", {"summary": {"values": s["notes"]["notes_record"]["values"]}},
         s["notes"]["notes_record"]["treatment"]),
        ("bypass_after_days", "Staff send a quote unreviewed after it waits this long in a review queue",
         "assumed", {"summary": {"main": s["bypass_after_days"]["main"],
                                 "sensitivity": s["bypass_after_days"]["sensitivity"]}},
         s["bypass_after_days"]["basis"]),
        ("policy_gate", "The system refuses releases beyond the written limits without head-office authorisation",
         "assumed", {"summary": {"main": s["policy_gate"]["main"], "sensitivity": s["policy_gate"]["sensitivity"]}},
         s["policy_gate"]["basis"]),
    ]
    for name, mech, status, value, basis in structural:
        evidence.write({
            "id": params.evidence_id(name), "mechanism": mech, "measures": "Nothing measured. A structural assumption.",
            "simulator_parameter": name, "estimable": "no", "estimable_note": "Structural assumption; no evidence.",
            "value": value, "status": status,
            "source": {"name": "Declared assumption, evidence/assumptions.yaml", "doi": None, "licence": None,
                       "retrieved_utc": None},
            "conditions": "E4 quotation research model", "transfer": basis, "versions": versions,
            "disagreements": [], "tests": [], "declared_utc": declared, "created_utc": evidence.utc_now(),
            "used_by": ["gca_sim/simulator"]})
    print("records written")


if __name__ == "__main__":
    main()
