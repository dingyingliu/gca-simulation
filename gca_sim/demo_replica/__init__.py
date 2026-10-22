"""Python port of the walkthrough demo (E1). A regression baseline only.

Its routing reads each quote's true category and its bypass rule is an assumption about
staff behaviour. Neither belongs in research use. Do not import this package from the
research model in `gca_sim/`; `tests/test_research_isolation.py` enforces that once the
research model exists.
"""

from .walkthrough import PrototypeAssumptions, WALKTHROUGH_ASSUMPTIONS, simulate, summary

__all__ = ["PrototypeAssumptions", "WALKTHROUGH_ASSUMPTIONS", "simulate", "summary"]
