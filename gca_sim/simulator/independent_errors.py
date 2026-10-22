"""The independent-errors baseline (E4).

Same per-quote drafting behaviour, no shared state: for each quote we take the distribution of its
drafting outcome (value, source, whether a note was used) across seeds in the full model, and the
baseline draws each quote's outcome independently from that distribution, with notes switched off.
Everything after drafting (routing, the agent's own check, review, queues) is unchanged. The
difference between the full model and this baseline is what the shared-notes mechanism adds:
dependence between quotes, not a different error rate per quote.
"""

from __future__ import annotations

from collections import Counter


def draft_distribution(results) -> dict:
    """Quote id -> [(cumulative probability, value, source, note_used)] from full-model runs."""
    counts: dict[str, Counter] = {}
    n = 0
    for res in results:
        n += 1
        for qid, q in res.quotes.items():
            counts.setdefault(qid, Counter())[(repr(q.drafted), q.draft_source, q.note_used)] += 1
    values = {}
    for res in results:
        for qid, q in res.quotes.items():
            values.setdefault(qid, {})[repr(q.drafted)] = q.drafted
    out = {}
    for qid, c in counts.items():
        cum, rows = 0.0, []
        for (vrepr, source, note_used), k in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])):
            cum += k / n
            rows.append((cum, values[qid][vrepr], source, note_used))
        rows[-1] = (1.0 + 1e-12,) + rows[-1][1:]  # guard against rounding at the top
        out[qid] = rows
    return out
