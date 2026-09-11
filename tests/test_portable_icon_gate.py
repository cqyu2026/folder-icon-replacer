#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from png_fixtures import fixture, approve_fixture, gate

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    for kind, reason in [('opaque','missing_real_alpha'), ('rectangle','suspected_rectangular_background'), ('interior','suspected_rectangular_background'), ('speckle','isolated_edge_pixels'), ('edge','subject_touches_canvas_edge')]:
        path = fixture(root / (kind+'.png'),kind)
        approve_fixture(path)  # A positive review cannot override failed technical QA.
        assert reason in gate.assess(path,Path(str(path)+'.review.json'))['errors'], kind
    assert 'isolated_edge_pixels' in gate.assess(fixture(root/'large-speckle.png','speckle',1024))['errors']
    small = fixture(root/'small-interior.png', 'small-interior')
    assert gate.assess(small)['status'] == 'technical_pass'  # Below automatic rectangle threshold.
    small_review = Path(str(small)+'.review.json')
    assert gate.assess(small,small_review)['status'] == 'failed'
    approve_fixture(small)
    record = json.loads(small_review.read_text()); record['sha256'] = 'outdated'
    small_review.write_text(json.dumps(record))
    assert gate.assess(small,small_review)['status'] == 'failed'
    approve_fixture(small)
    record = json.loads(small_review.read_text()); record['background_removed'] = 'failed'
    small_review.write_text(json.dumps(record))
    assert 'visual_review_failed' in gate.assess(small,small_review)['errors']
    path = fixture(root/'clean.png')
    assert gate.assess(path)['status'] == 'technical_pass'
    review = Path(str(path)+'.review.json')
    assert gate.assess(path, review)['status'] == 'failed'
    approve_fixture(path)
    assert gate.assess(path, review)['status'] == 'passed'
    record = json.loads(review.read_text()); record['sha256'] = 'stale'; review.write_text(json.dumps(record))
    assert gate.assess(path, review)['status'] == 'failed'
    corrupt = root/'corrupt.png'; corrupt.write_bytes(path.read_bytes()[:-2])
    assert gate.assess(corrupt)['status'] == 'failed'
    jpg = root/'photo.jpg'; jpg.write_bytes(b'\xff\xd8\xff\xe0JPEG')
    result = subprocess.run([sys.executable,str(Path(gate.__file__)),str(jpg)],capture_output=True,text=True)
    assert result.returncode != 0 and '透明 PNG' in result.stdout and 'macOS' in result.stdout
    # Simulate a non-macOS host with no native subprocess capability.
    import importlib
    from unittest.mock import patch
    prepare = importlib.import_module('prepare-icon')
    with patch.object(sys, 'platform', 'linux'), patch.object(sys, 'argv', ['prepare-icon.py',str(jpg),str(root/'unused')]), patch.object(prepare.subprocess, 'run', side_effect=AssertionError('native tools must not run')):
        assert prepare.main() == 1
        assert not (root/'unused').exists()
    print('portable gate: opaque/padded rectangle/interior purple/speckle/edge/corrupt/stale review/JPEG rejected; small residue requires matching explicit visual approval; clean PNG allowed')
