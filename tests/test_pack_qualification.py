#!/usr/bin/env python3
from png_fixtures import fixture, approve_fixture
import importlib.util
import json
import tempfile
from unittest.mock import patch
from pathlib import Path

script = Path(__file__).resolve().parents[1] / "scripts" / "qualify-pack.py"
spec = importlib.util.spec_from_file_location("qualify_pack", script)
module = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp); (root / "source-pack/generations").mkdir(parents=True)
    for name in ("good.png", "bad.png"):
        path = fixture(root / "source-pack/generations" / name, "clean" if name == "good.png" else "interior")
        approve_fixture(path)
    (root / "source-pack/visual-qa.json").write_text(json.dumps({"anchor": "sun", "icons": [
        {"file": "good.png", "technical_qa": "passed", "visual_qa": "passed"},
        {"file": "bad.png", "technical_qa": "passed", "visual_qa": "failed", "rejection_reason": "style_outlier"},
    ]}), encoding="utf-8")
    result = module.qualify(root, "anchor_narrative", "fixture.jpg", "good.png")
    assert result["pack_qa"] == "failed"
    assert (root / "final-pack/good.png").is_file()
    assert not (root / "final-pack/bad.png").exists()
    assert (root / "source-pack/rejected/bad.png").is_file()
    # Requalification must remove a previously promoted file after QA fails.
    fixture(root / "source-pack/generations/good.png", "rectangle")
    module.qualify(root, "anchor_narrative", "fixture.jpg")
    assert not (root / "final-pack/good.png").exists()
    # An automatic pass for small residue must never promote without current visual approval.
    small = fixture(root / "source-pack/generations/small.png", "small-interior")
    (root / "source-pack/visual-qa.json").write_text(json.dumps({"icons":[{"file":"small.png","visual_qa":"passed"}]}))
    result = module.qualify(root,"direct","fixture")
    assert result["pack_qa"] == "failed" and not (root / "final-pack/small.png").exists()
    # Source or review changes after successful validation must not reach final-pack.
    candidate = root / "source-pack/generations/race.png"
    (root / "source-pack/visual-qa.json").write_text(json.dumps({"icons":[{"file":"race.png","visual_qa":"passed"}]}))
    original_assess = module.gate.assess
    for change_review in (False, True):
        fixture(candidate); approve_fixture(candidate)
        def mutate_after_qa(path, review=None):
            result = original_assess(path,review)
            if path == candidate:
                if change_review:
                    record = json.loads(review.read_text()); record["background_removed"] = "failed"
                    review.write_text(json.dumps(record))
                else:
                    fixture(candidate,"opaque")
            return result
        with patch.object(module.gate,"assess",side_effect=mutate_after_qa):
            result = module.qualify(root,"direct","fixture")
        assert result["pack_qa"] == "failed"
        assert result["icons"][0]["rejection_reason"] == "candidate_or_review_changed_after_qa"
        assert not (root / "final-pack/race.png").exists()
print("pack qualification: normal promotion, small-residue review gate and source/review TOCTOU rejection passed")
