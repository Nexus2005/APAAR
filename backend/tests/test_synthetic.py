from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.generate_synthetic import generate  # noqa: E402


def _hashes(folder: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.iterdir())
        if path.is_file()
    }


def test_generation_is_byte_identical_twice():
    with (
        tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as first,
        tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as second,
    ):
        out_a = Path(first) / "synthetic"
        out_b = Path(second) / "synthetic"
        truth_a = generate(42, out_a)
        truth_b = generate(42, out_b)
        assert _hashes(out_a) == _hashes(out_b)
        assert truth_a == truth_b
        truth_json_a = (Path(first) / "ground_truth.json").read_bytes()
        truth_json_b = (Path(second) / "ground_truth.json").read_bytes()
        assert truth_json_a == truth_json_b


def test_ground_truth_counts_match_design_targets():
    truth = json.loads((ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))
    seeded = truth["seeded"]
    assert truth["totals"]["institutions"] == 12
    assert truth["totals"]["programmes"] == 32
    assert seeded["malformed_apaar"] == 150
    assert seeded["missing_apaar"] == 60
    assert seeded["pending_declined"] == 40
    assert seeded["in_file_duplicates"] == 40
    assert seeded["cross_institution_pairs"] == 35
    assert seeded["whitelisted_pairs"] == 5
    assert len(seeded["over_intake"]) == 3
    assert len(seeded["anomalous_institutions"]) == 3
    assert seeded["implausible_dates"] == 25
