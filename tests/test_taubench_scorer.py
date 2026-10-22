"""E6 authentication scorer: a lookup counts only when it succeeds. Fixtures only."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_taubench", ROOT / "experiments" / "e6_taubench" / "check_taubench.py")
ct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ct)


def call(name):
    return {"role": "assistant", "content": None, "tool_calls": [{"function": {"name": name, "arguments": "{}"}}]}


def result(name, content):
    return {"role": "tool", "name": name, "content": content, "tool_call_id": "x"}


def run(*msgs):
    return {"traj": [{"role": "system", "content": "policy"}, {"role": "user", "content": "hi"}, *msgs]}


def test_failed_lookup_then_read_counts_as_before_authentication():
    r = run(call("find_user_id_by_email"), result("find_user_id_by_email", "Error: user not found"),
            call("get_user_details"))
    assert ct.actions_before_authentication(r) == (True, True, False)


def test_retry_then_success_authenticates():
    r = run(call("find_user_id_by_email"), result("find_user_id_by_email", "Error: user not found"),
            call("find_user_id_by_name_zip"), result("find_user_id_by_name_zip", "yusuf_rossi_9620"),
            call("get_user_details"), call("cancel_pending_order"))
    assert ct.actions_before_authentication(r) == (True, False, False)


def test_supplied_id_without_lookup_counts():
    r = run(call("get_user_details"), call("cancel_pending_order"))
    assert ct.actions_before_authentication(r) == (True, True, True)


def test_neutral_tools_are_not_actions():
    r = run(call("think"), call("calculate"))
    assert ct.actions_before_authentication(r) == (False, False, False)
