"""Matched random streams (common random numbers).

Every draw is tied to a fixed key: the run seed, an entity (a quote, a customer, a region) and a
purpose. The draw is the same whatever the design, so changing the design never changes the
underlying luck; it changes only the probability the draw is compared against.

For each (seed, entity) we spawn a generator from numpy.random.SeedSequence with the entity's
CRC-32 as spawn key and take one uniform per purpose, in the fixed order of PURPOSES. PURPOSES is
append-only: adding a purpose at the end leaves every existing draw unchanged
(a test checks this).
"""

from __future__ import annotations

import zlib

import numpy as np

PURPOSES = (
    "read_note", "note_judgement", "slip", "as_requested",       # drafting
    "recognise", "policy_flag", "self_check", "unverifiable",    # routing and the agent's own check
    "detect", "query",                                           # review decisions
    "service_lead", "service_ho", "query_delay",                 # review times
    "cites_agreement", "stale_note", "knows_policy",             # world draws (per quote, customer, region)
    "baseline_draft",                                            # independent-errors baseline
    "response_delay",                                            # review response delay (round 3)
    "note_choice", "note_pick",                                  # which readable note a reader takes (E5)
)
_INDEX = {p: i for i, p in enumerate(PURPOSES)}


def entity_key(entity: str) -> int:
    return zlib.crc32(entity.encode("utf-8"))


class Streams:
    """Uniform draws for one seed, precomputed per entity."""

    def __init__(self, seed: int, entities):
        self.seed = int(seed)
        self._table = {}
        for e in entities:
            ss = np.random.SeedSequence(entropy=self.seed, spawn_key=(entity_key(e),))
            self._table[e] = np.random.default_rng(ss).random(len(PURPOSES)).tolist()

    def u(self, entity: str, purpose: str) -> float:
        return self._table[entity][_INDEX[purpose]]

    def for_entity(self, entity: str, purposes) -> dict:
        row = self._table[entity]
        return {p: row[_INDEX[p]] for p in purposes}


def case_entities(case) -> list[str]:
    ents = [r.id for r in case.requests]
    ents += [f"customer:{a.customer}" for a in case.agreements]
    ents += [f"region:{r}" for r in ("BR", "TR", "SG")]
    return ents
