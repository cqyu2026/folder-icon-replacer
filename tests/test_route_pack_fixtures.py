#!/usr/bin/env python3
"""Run all three routing modes through the real qualification boundary."""
from png_fixtures import fixture, approve_fixture
import importlib.util
import json
import tempfile
from pathlib import Path

base = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, base / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
route = load("plan-pack-route"); qualify = load("qualify-pack")

cases = [("independent_elements", 3, 3), ("anchor_narrative", 1, 3), ("folder_semantic", 0, 3)]
with tempfile.TemporaryDirectory() as temp:
    for expected, anchors, count in cases:
        root = Path(temp) / expected; generations = root / "source-pack/generations"; generations.mkdir(parents=True)
        assert route.plan(anchors, count)["mode"] == expected
        (generations / "input.jpg").write_bytes(b"original-input")
        (generations / "candidate-01.png").write_bytes(b"candidate")
        fixture(generations / "normalized-01.png")
        approve_fixture(generations / "normalized-01.png")
        (root / "source-pack/visual-qa.json").write_text(json.dumps({
            "anchor": "sun" if anchors else None, "wallpaper": "wallpaper.png", "icons": [{
                "file": "normalized-01.png", "source_input": "input.jpg", "candidate": "candidate-01.png",
                "normalized": "normalized-01.png", "technical_qa": "passed", "visual_qa": "passed",
                "pose": "carry", "action_part": "handle", "concept_signature": expected,
            }]}), encoding="utf-8")
        result = qualify.qualify(root, expected, "source-pack/generations/input.jpg", "normalized-01.png")
        assert result["pack_qa"] == "passed"
        assert (root / "final-pack/normalized-01.png").is_file()
        manifest = json.loads((root / "final-pack/manifest.md").read_text(encoding="utf-8").split("```json\n")[1].split("\n```")[0])
        icon = manifest["icons"][0]
        assert all(icon[key] for key in ("source_input", "candidate", "normalized", "pose", "action_part", "concept_signature"))
print("three route pack fixtures: passed")
