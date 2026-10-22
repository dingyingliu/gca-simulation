"""The two-driver sweep overlays the development draws only from a cache bound to the committed development run and
to the current ranges and weeks. Fabricated caches in a temporary folder."""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

from gca_sim import evidence

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("two_driver_sweep",
                                              ROOT / "experiments" / "e4_quotation" / "two_driver_sweep.py")
sweep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sweep)

LABELS = [f"full|{d}|isolated|draft" for d in ("review", "limits", "local")]


def _cache(folder: Path, drop=(), committed=None, data_hash=None, assumptions_hash=None, manifest_hash=None) -> dict:
    ass, man = folder / "assumptions.yaml", folder / "manifest.json"
    ass.write_bytes(b"ranges: 1")
    man.write_bytes(b'{"heldout": {}}')
    data = np.arange(36, dtype=float).reshape(2, 3, 3, 2, 1)  # [week, draw, config, seed, measure]
    fields = {"data": data, "configs": np.array(LABELS), "measures": np.array(["days_mean"]),
              "draw_params": np.array([[0.1, 1.5, 0.2], [0.5, 0.3, 0.4], [1.0, 0.9, 0.6]]),
              "param_names": np.array(["effort_lead", "effort_ho", "delay_lead"]),
              "assumptions_sha256": np.array(assumptions_hash or hashlib.sha256(ass.read_bytes()).hexdigest()),
              "heldout_manifest_sha256": np.array(manifest_hash or hashlib.sha256(man.read_bytes()).hexdigest()),
              "data_sha256": np.array(data_hash or evidence.array_sha256(data))}
    for k in drop:
        fields.pop(k)
    raw, res = folder / "e4_development.npz", folder / "results.json"
    np.savez_compressed(raw, **fields)
    res.write_text(json.dumps({"raw_data_sha256": committed or evidence.array_sha256(data)}), encoding="utf-8")
    return {"raw": raw, "results": res, "assumptions": ass, "manifest": man}


def test_a_bound_cache_gives_the_overlay_with_its_own_coordinates(tmp_path):
    out = sweep.development_draws(**_cache(tmp_path))
    assert "omitted" not in out
    assert out["effort_lead"] == [0.1, 0.5, 1.0] and out["effort_ho"] == [1.5, 0.3, 0.9]
    assert all(len(out[f"{x}-{y}"]) == 3 for x, y in sweep.PAIRS)


def test_a_stale_or_unbound_cache_is_omitted_with_a_reason(tmp_path):
    variants = [{"assumptions_hash": "changed ranges"}, {"manifest_hash": "changed weeks"},
                {"committed": "another run"}, {"data_hash": "edited array"}, {"drop": ("draw_params",)},
                {"drop": ("data_sha256",)}]
    for i, kw in enumerate(variants):
        folder = tmp_path / str(i)
        folder.mkdir()
        out = sweep.development_draws(**_cache(folder, **kw))
        assert set(out) == {"omitted"} and out["omitted"], kw
    assert set(sweep.development_draws(raw=tmp_path / "none.npz")) == {"omitted"}


def test_array_fingerprint_depends_on_shape_and_content_not_memory_layout():
    a = np.arange(6.0).reshape(2, 3)
    assert evidence.array_sha256(a) == evidence.array_sha256(a.copy())
    assert evidence.array_sha256(a.T) == evidence.array_sha256(np.ascontiguousarray(a.T))
    assert evidence.array_sha256(a) != evidence.array_sha256(a.reshape(3, 2))
    assert evidence.array_sha256(a) != evidence.array_sha256(a + 1)
