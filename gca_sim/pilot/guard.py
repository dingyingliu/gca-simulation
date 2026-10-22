"""Spending guard for the paid pilot (plan section 8; review round 2, Codex R2.4).

Usage is reported only after a request, so the guard reserves before a request is sent: an upper bound on the
input tokens at the input price, plus `max_tokens` at the output price. A request is sent only if actual spend,
all outstanding reservations and this reservation together stay within the cap. After the response the
reservation is replaced by the cost of the reported usage. A request that times out or fails without a usage
report keeps its whole reservation as spent. Spend is kept in a ledger file, so the cap holds across restarts and
across the set-up, development and held-out runs.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
from pathlib import Path


class CapExceeded(RuntimeError):
    pass


def input_token_upper_bound(*texts: str) -> int:
    """No tokeniser splits text into more tokens than it has bytes, so the byte count is a safe upper bound.
    The allowance covers message framing and the response-format schema."""
    return sum(len(t.encode("utf-8")) for t in texts) + 2000


class SpendingGuard:
    def __init__(self, cap_usd: float, input_usd_per_token: float, output_usd_per_token: float,
                 ledger: Path | None = None):
        if cap_usd is None or cap_usd <= 0:
            raise ValueError("a spending cap is required")
        self.cap = float(cap_usd)
        self.input_price = float(input_usd_per_token)
        self.output_price = float(output_usd_per_token)
        self.ledger = ledger
        self._lock = threading.Lock()
        self._reserved: dict[str, float] = {}
        self.spent = 0.0
        if ledger is not None and ledger.exists():
            for line in ledger.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.spent += float(json.loads(line)["usd"])

    @property
    def committed(self) -> float:
        """Actual spend plus every outstanding reservation."""
        return self.spent + sum(self._reserved.values())

    def reserve(self, request_key: str, input_tokens_upper: int, max_tokens: int) -> float:
        amount = input_tokens_upper * self.input_price + max_tokens * self.output_price
        with self._lock:
            if request_key in self._reserved:
                raise ValueError(f"{request_key} already holds a reservation")
            if self.committed + amount > self.cap + 1e-12:
                raise CapExceeded(f"request refused: ${self.committed:.4f} committed, ${amount:.4f} to reserve, "
                                  f"cap ${self.cap:.2f}")
            self._reserved[request_key] = amount
        return amount

    def _record(self, request_key: str, kind: str, usd: float) -> None:
        self.spent += usd
        if self.ledger is not None:
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            entry = {"utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                     "request": request_key, "kind": kind, "usd": round(usd, 8)}
            with open(self.ledger, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(entry) + "\n")

    def settle(self, request_key: str, actual_usd: float) -> None:
        """Replace the reservation by the cost of the reported usage."""
        with self._lock:
            self._reserved.pop(request_key)
            self._record(request_key, "settled", float(actual_usd))

    def forfeit(self, request_key: str) -> None:
        """No usage was reported (a timeout or an error): the whole reservation counts as spent."""
        with self._lock:
            self._record(request_key, "forfeited", self._reserved.pop(request_key))
