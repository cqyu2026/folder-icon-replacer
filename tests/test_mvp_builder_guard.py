#!/usr/bin/env python3
"""The synthetic MVP builder must not become a user-image generator."""
from pathlib import Path
import subprocess
import sys
import tempfile

skill = Path(__file__).resolve().parents[1]
builder = skill / "scripts" / "build-mvp-pack.py"
fixture = skill / "tests" / "skill-test-image.jpg"

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    no_ack = subprocess.run([sys.executable, str(builder), str(fixture), str(root / "no-ack")], text=True, capture_output=True)
    assert no_ack.returncode and "fixture-only" in (no_ack.stdout + no_ack.stderr)
    other = root / "user-photo.jpg"
    other.write_bytes(b"not-a-packaged-fixture")
    wrong_source = subprocess.run([sys.executable, str(builder), str(other), str(root / "wrong-source"), "--fixture-only"], text=True, capture_output=True)
    assert wrong_source.returncode and "only accepts" in (wrong_source.stdout + wrong_source.stderr)

print("MVP builder guard: arbitrary user artwork is refused")
