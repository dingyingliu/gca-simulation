"""Model clients for the pilot: OpenRouter over HTTPS, and a fake agent for dry runs and tests.

The API key is read from the environment variable named in the config, or from the git-ignored `.env` file in the
project folder. It is passed only in the request's Authorization header. It is never printed, logged or written
to any record, and error messages are built from the response body, never from the request.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from gca_sim.pilot.bank import DELIVERY_POOL, PAYMENT_AGREED, PAYMENT_OTHERS
from gca_sim.pilot.prompting import OUTPUT_SCHEMA
from gca_sim.pilot.scoring import FIELD, numbers_in

ROOT = Path(__file__).resolve().parents[2]


class ClientError(RuntimeError):
    """A request that produced no usable response and no usage report."""


class RateLimited(ClientError):
    """The provider refused the request because of a rate limit (HTTP 429). Nothing ran."""

    def __init__(self, detail: str, retry_after: float | None = None, daily: bool = False):
        super().__init__(detail)
        self.retry_after, self.daily = retry_after, daily


def load_key(env_name: str, env_file: Path = ROOT / ".env") -> str:
    value = os.environ.get(env_name, "").strip()
    if not value and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, _, v = line.partition("=")
            if name.strip() == env_name:
                value = v.strip().strip('"').strip("'")
    if not value:
        raise SystemExit(f"no API key: set {env_name} in the environment or fill it in {env_file.name}")
    return value


class OpenRouterClient:
    """One chat-completion request per call, with the output schema enforced where the endpoint supports it."""

    paid = True

    def __init__(self, key: str, config: dict, opener=urllib.request.urlopen, sleep=time.sleep):
        self._key = key
        self.config = config
        self._open = opener
        self._sleep = sleep
        self._gate = threading.Lock()
        self._next_start = 0.0

    def _pace(self) -> None:
        """Keep request starts at least `min_seconds_between_requests` apart, across all worker threads."""
        gap = self.config.get("min_seconds_between_requests") or 0
        if gap <= 0:
            return
        with self._gate:
            now = time.monotonic()
            wait = max(0.0, self._next_start - now)
            self._next_start = max(now, self._next_start) + gap
        if wait:
            self._sleep(wait)

    def request_body(self, system: str, user: str) -> dict:
        c = self.config
        body = {"model": c["model"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": c["max_tokens"]}
        if c.get("structured_outputs", True):
            body["response_format"] = {"type": "json_schema",
                                       "json_schema": {"name": "quote", "strict": True, "schema": OUTPUT_SCHEMA}}
            body["provider"] = {"require_parameters": True}
        if c.get("reasoning_effort"):
            body["reasoning"] = {"effort": c["reasoning_effort"]}
        # sampling settings are sent explicitly, and the host is pinned, so that neither can change part way
        # through a run (review round 10, Claude R10.2)
        for name in ("temperature", "top_p"):
            if c.get(name) is not None:
                body[name] = c[name]
        if c.get("provider_order"):
            body.setdefault("provider", {}).update({"order": c["provider_order"], "allow_fallbacks": False})
        return body

    def complete(self, system: str, user: str, meta: dict | None = None) -> dict:
        body = self.request_body(system, user)
        req = urllib.request.Request(self.config["base_url"], data=json.dumps(body).encode("utf-8"), method="POST",
                                     headers={"Authorization": f"Bearer {self._key}",
                                              "Content-Type": "application/json"})
        self._pace()
        try:
            with self._open(req, timeout=self.config.get("timeout_seconds", 180)) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            if e.code == 429:
                after = (e.headers or {}).get("Retry-After")
                raise RateLimited(f"HTTP 429: {detail}", float(after) if after and after.isdigit() else None,
                                  daily="per-day" in detail or "per day" in detail or "daily" in detail.lower()) from None
            raise ClientError(f"HTTP {e.code}: {detail}") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            raise ClientError(f"{type(e).__name__}: {str(e)[:300]}") from None
        if "choices" not in raw or not raw["choices"]:
            error = raw.get("error") or {}
            if error.get("code") == 429:
                text = json.dumps(error)[:500]
                raise RateLimited(f"429 in the response body: {text}", None,
                                  daily="per-day" in text or "per day" in text or "daily" in text.lower())
            raise ClientError(f"no choices in the response: {json.dumps(raw)[:500]}")
        choice = raw["choices"][0]
        message = choice.get("message") or {}
        usage = raw.get("usage") or {}
        return {"raw": raw, "text": message.get("content"), "finish_reason": choice.get("finish_reason"),
                "refusal": bool(message.get("refusal")), "usage": usage, "model": raw.get("model"),
                "host": raw.get("provider"), "id": raw.get("id"), "cost_reported_usd": usage.get("cost"),
                "request_parameters": {k: v for k, v in body.items() if k != "messages"}}

    def key_info(self) -> dict:
        """The key's own limit and usage, from OpenRouter. Costs nothing."""
        url = self.config["base_url"].replace("/chat/completions", "/key")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._key}"})
        try:
            with self._open(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8")).get("data", {})
        except urllib.error.HTTPError as e:
            raise ClientError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None


class FakeClient:
    """A stand-in agent for dry runs and tests. It is given the task's ground truth, which a real agent never
    sees, and follows fixed probabilities: it uses a visible agreement, otherwise adopts a note about the
    customer, otherwise drafts from the standard terms and sometimes escalates what it cannot verify. Its outputs
    say nothing about any real model."""

    paid = False

    def __init__(self, config: dict, seed: int = 0, p_use_register: float = 0.9, p_adopt_note: float = 0.75,
                 p_escalate_unverifiable: float = 0.5, bad_json_rate: float = 0.0, error_rate: float = 0.0,
                 rate_limit_calls: tuple = (), daily_limit_after: int | None = None):
        self.config = config
        self.seed, self.p_use_register, self.p_adopt_note = seed, p_use_register, p_adopt_note
        self.p_escalate, self.bad_json_rate, self.error_rate = p_escalate_unverifiable, bad_json_rate, error_rate
        self.rate_limit_calls, self.daily_limit_after, self.calls = set(rate_limit_calls), daily_limit_after, 0
        self._count = threading.Lock()

    def complete(self, system: str, user: str, meta: dict | None = None) -> dict:
        from gca_sim.pilot.prompting import mentions

        task, view, exp = meta["task"], meta["view"], meta["exposure"]
        with self._count:
            self.calls += 1
            call = self.calls
        if self.daily_limit_after is not None and call > self.daily_limit_after:
            raise RateLimited("HTTP 429: fake free-models-per-day limit", daily=True)
        if call in self.rate_limit_calls:
            raise RateLimited("HTTP 429: fake per-minute limit", retry_after=0)
        rng = random.Random(f"{self.seed}:{meta['request_key']}")
        if rng.random() < self.error_rate:
            raise ClientError("fake timeout")
        t = task["truth"]
        out = {"unit_price_eur": t["standard_unit_price"], "discount_percent": task["requested_discount"],
               "payment_terms_days": 30, "delivery_days": None, "decision": "release",
               "reason": "Standard terms from the price list and the policy.",
               "sources_used": ["standard_template", "request"], "note": ""}
        said = "standard terms"
        if task["agreed_field"]:
            field = FIELD[task["agreed_field"]]
            about = [n for n in view if mentions(n["text"], task["customer"])]
            if exp["agreement_in_register"] and rng.random() < self.p_use_register:
                out[field] = task["values"]["true"]
                out["sources_used"] = ["agreement_register", "request"]
                said = f"agreed {task['agreed_field']} {out[field]}"
            elif about and rng.random() < self.p_adopt_note:
                nums = numbers_in(about[-1]["text"])
                wanted = {"payment": lambda n: n in PAYMENT_AGREED + PAYMENT_OTHERS,
                          "delivery": lambda n: n in DELIVERY_POOL,
                          "price_floor": lambda n: abs(n - round(n)) > 1e-9}[task["agreed_field"]]
                value = next((n for n in reversed(nums) if wanted(n)), None)
                if value is not None:
                    out[field] = value if task["agreed_field"] == "price_floor" else int(value)
                    out["sources_used"] = ["notes_store", "request"]
                    said = f"agreed {task['agreed_field']} {out[field]}"
            elif not exp["agreement_in_register"] and rng.random() < self.p_escalate:
                out["decision"] = "escalate"
                out["reason"] = "The request cites agreed terms that are not in the register."
        # about as long as a real agent's note; the term it applied is the last number in the note
        out["note"] = (f"Quote for {task['customer']}: {task['quantity']} units of {task['product']} at "
                       f"{task['requested_discount']}% discount on {said}; decision {out['decision']} per the price "
                       "list and the policy.")
        text = "not json {" if rng.random() < self.bad_json_rate else json.dumps(out)
        prompt_tokens, completion_tokens = (len(system) + len(user)) // 4, 150
        cost = prompt_tokens * self.config["input_usd_per_token"] + completion_tokens * self.config["output_usd_per_token"]
        return {"raw": {"fake": True, "choices": [{"message": {"content": text}, "finish_reason": "stop"}]},
                "text": text, "finish_reason": "stop", "refusal": False,
                "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "cost": cost},
                "model": "fake-agent", "host": "fake-host", "id": f"fake-{meta['request_key']}",
                "cost_reported_usd": cost,
                "request_parameters": {"model": "fake-agent", "max_tokens": self.config["max_tokens"]}}
