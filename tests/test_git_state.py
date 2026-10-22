"""Provenance: a failed git inspection is never recorded as a clean tree."""

import subprocess
from types import SimpleNamespace

import pytest

from gca_sim import evidence


def _fake(results):
    calls = iter(results)

    def run(cmd, **kwargs):
        return next(calls)

    return run


def test_failed_rev_parse_raises(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake([SimpleNamespace(returncode=128, stdout="", stderr="dubious ownership")]))
    with pytest.raises(evidence.GitStateError):
        evidence.git_state()


def test_failed_status_raises(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake([
        SimpleNamespace(returncode=0, stdout="abc1234\n", stderr=""),
        SimpleNamespace(returncode=128, stdout="", stderr="not a git repository"),
    ]))
    with pytest.raises(evidence.GitStateError):
        evidence.git_state(["gca_sim"])


def test_clean_and_dirty(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake([
        SimpleNamespace(returncode=0, stdout="abc1234\n", stderr=""),
        SimpleNamespace(returncode=0, stdout="", stderr=""),
    ]))
    assert evidence.git_state() == {"code_commit": "abc1234", "code_dirty": False}
    monkeypatch.setattr(subprocess, "run", _fake([
        SimpleNamespace(returncode=0, stdout="abc1234\n", stderr=""),
        SimpleNamespace(returncode=0, stdout=" M gca_sim/evidence.py\n", stderr=""),
    ]))
    assert evidence.git_state() == {"code_commit": "abc1234", "code_dirty": True}


def test_real_repository():
    state = evidence.git_state()
    assert state["code_commit"] and isinstance(state["code_dirty"], bool)
