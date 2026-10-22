"""A picture of the pilot's design for readers new to it: one group's six requests, and what the notes store
says about each customer in the two kinds of store. Drawn from the fixed design (plan section 3.2), not from data.

    .venv/Scripts/python.exe experiments/agent_pilot/make_schematic.py     # reports/E5/experiment_design.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "E5" / "experiment_design.png"

COLOUR = {"Standard": "#d9d9d9", "Help": "#a6d3a0", "Harm": "#f0b08a", "Own": "#9fbce0"}
TASKS = [  # order, region, role, the customer in plain words
    (1, "Region B", "Standard", "no agreement"),
    (2, "Region B", "Help", "has an agreement"),
    (3, "Region C", "Harm", "has an agreement"),
    (4, "Region B", "Own", "has an agreement"),
    (5, "Region B", "Harm", "same customer\nas request 3"),
    (6, "Region C", "Standard", "no agreement"),
]
SHARED = ["nothing", "a correct note\nfrom Region A", "a WRONG note\nfrom Region A", "nothing",
          "the WRONG note,\nand the note written\nat request 3", "nothing"]
ISOLATED = ["nothing"] * 6


def box(ax, x, y, w, h, text, colour, size=8, weight="normal", edge="#555555"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06", facecolor=colour,
                                edgecolor=edge, linewidth=0.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, fontweight=weight)


def main() -> None:
    fig, ax = plt.subplots(figsize=(12.5, 5.6))
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    left, w, gap = 2.55, 1.6, 0.14
    ax.text(0.1, 6.15, "One group of the experiment: six customer requests, answered in this order by the AI agent",
            fontsize=11, fontweight="bold")
    for i, (order, region, role, customer) in enumerate(TASKS):
        x = left + i * (w + gap)
        box(ax, x, 4.55, w, 1.25, f"Request {order}\n{region}\n{role} customer\n({customer})", COLOUR[role], size=8)
        if i < 5:
            ax.annotate("", xy=(x + w + gap - 0.01, 5.17), xytext=(x + w + 0.01, 5.17),
                        arrowprops=dict(arrowstyle="->", color="#555555", lw=0.8))
    ax.text(0.1, 5.17, "The request", fontsize=9, fontweight="bold", va="center")

    ax.text(0.1, 3.55, "What the notes store\nsays about this customer\nwhen notes are SHARED\nby all regions", fontsize=9,
            fontweight="bold", va="center")
    for i, text in enumerate(SHARED):
        wrong = "WRONG" in text
        box(ax, left + i * (w + gap), 3.0, w, 1.1, text, "#fde3d3" if wrong else ("#e3f1e0" if "correct" in text else "#f7f7f7"),
            size=8, weight="bold" if wrong else "normal", edge="#c4652b" if wrong else "#999999")

    ax.text(0.1, 2.05, "...and when each region\nkeeps its own notes\n(ISOLATED)", fontsize=9, fontweight="bold", va="center")
    for i, text in enumerate(ISOLATED):
        box(ax, left + i * (w + gap), 1.6, w, 0.9, text, "#f7f7f7", size=8, edge="#999999")

    ax.text(0.1, 0.95, "Each group is run in four conditions: notes shared or isolated, and the customer's agreement visible in the "
                       "register the agent sees, or not visible.", fontsize=9)
    ax.text(0.1, 0.55, "Every condition is repeated three times. In both kinds of store the agent sees ten notes; the others are "
                       "about customers who play no part.", fontsize=9)
    ax.text(0.1, 0.15, "After each request the agent adds one note of its own to the store. Region A writes the two notes shown "
                       "and answers no request.", fontsize=9)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print("written", OUT.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
