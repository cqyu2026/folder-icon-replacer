#!/usr/bin/env python3
from pathlib import Path
import importlib.util

script = Path(__file__).resolve().parents[1] / "scripts" / "plan-pack-route.py"
spec = importlib.util.spec_from_file_location("plan_pack_route", script)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)

assert module.plan(5, 5)["mode"] == "independent_elements"
assert module.plan(1, 5)["mode"] == "anchor_narrative"
assert module.plan(0, 5)["mode"] == "folder_semantic"
assert module.plan(5, 5, True)["mode"] == "folder_semantic"
print("pack route self-check: passed")
