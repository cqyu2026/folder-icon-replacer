"""Deterministic, original synthetic fixtures; no macOS or image dependencies."""
import hashlib
import importlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
gate = importlib.import_module('portable-icon-gate')


def fixture(path, kind='clean', size=128):
    pixels = bytearray()
    for y in range(size):
        for x in range(size):
            u, v = x/size, y/size
            pixel = (250, 248, 242, 255) if (u-.5)**2+(v-.5)**2 < .32**2 else (0,0,0,0)
            if kind == 'opaque': pixel = (120,60,180,255)
            if kind == 'rectangle' and .18 < u < .82 and .18 < v < .82: pixel = (120,60,180,255)
            if kind == 'interior' and .36 < u < .64 and .4 < v < .6: pixel = (120,60,180,255)
            if kind == 'small-interior' and .45 < u < .55 and .45 < v < .55: pixel = (120,60,180,255)
            if kind == 'speckle' and x == size//8 and y == size//8: pixel = (120,60,180,255)
            if kind == 'edge' and x == 0 and y == size//2: pixel = (255,255,255,255)
            pixels.extend(pixel)
    path.write_bytes(gate.encode(size,size,pixels))
    return path


def approve_fixture(path):
    # Test-only attestation for these synthetic fixtures, never arbitrary user images.
    review = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'reviewer': 'synthetic fixture test', **dict.fromkeys(gate.CHECKS,'passed')}
    Path(str(path)+'.review.json').write_text(json.dumps(review))
    return review
