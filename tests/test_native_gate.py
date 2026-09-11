#!/usr/bin/env python3
"""Direct native/wrapper rejection regression; only temporary empty test folders."""
import json
import os
import subprocess
import sys
import tempfile
import importlib
import io
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path
from png_fixtures import fixture,approve_fixture

if sys.platform != 'darwin':
    print('native gate: skipped (requires macOS)'); raise SystemExit(0)
base=Path(__file__).resolve().parents[1]
(base/'.build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='native-gate-',dir=base/'.build') as temp:
    root=Path(temp); target=root/'target'; target.mkdir()
    before_attrs=subprocess.run(['/usr/bin/xattr','-l',str(target)],capture_output=True,text=True,check=True).stdout
    setter=base/'.build/folder-icon-setter'
    subprocess.run(['/bin/sh',str(base/'scripts/build-icon-setter.sh'),str(setter.parent)],check=True,capture_output=True)
    small=fixture(root/'small.png','small-interior')
    good=fixture(root/'good.png'); bad=fixture(root/'bad.png','interior'); approve_fixture(bad)
    for image in (good,bad,small,base/'tests/skill-test-image.jpg'):
        for command in ([str(setter),'set-and-verify'],[sys.executable,str(base/'scripts/apply-icon.py')],['/bin/sh',str(base/'scripts/terminal-apply.sh')]):
            result=subprocess.run(command+[str(image),str(target)],capture_output=True,text=True)
            assert result.returncode != 0 and ('quality_gate' in result.stderr or '质量门拒绝' in result.stdout),result
            assert list(target.iterdir()) == [] and subprocess.run(['/usr/bin/xattr','-l',str(target)],capture_output=True,text=True,check=True).stdout == before_attrs
    # Native loading cannot substitute another valid, newly reviewed PNG for the wrapper's approved hash.
    apply = importlib.import_module('apply-icon')
    original_assess = apply.gate.assess
    approve_fixture(good)
    def mutate_after_qa(path, review=None):
        result = original_assess(path,review)
        w,h,pixels = apply.gate.decode(path.read_bytes())
        pixels[(64*w+64)*4] -= 1
        path.write_bytes(apply.gate.encode(w,h,pixels))
        approve_fixture(path)
        return result
    captured = io.StringIO()
    with patch.object(sys,'argv',['apply-icon.py',str(good),str(target)]), patch.object(apply.gate,'assess',side_effect=mutate_after_qa), redirect_stdout(captured):
        assert apply.main() != 0
    assert 'image_hash_changed_after_qa' in captured.getvalue()
    assert list(target.iterdir()) == []
    assert subprocess.run(['/usr/bin/xattr','-l',str(target)],capture_output=True,text=True,check=True).stdout == before_attrs
    approve_fixture(good)
    app=root/'forbidden.app'; app.mkdir()
    result=subprocess.run([str(setter),'set-and-verify',str(good),str(app)],capture_output=True,text=True)
    assert result.returncode != 0 and 'target_package_not_allowed' in result.stderr
print('native gate: direct/wrapper/terminal reject missing review, small/large interior residue and JPEG; changed approved hash rejected without writes; App rejected')
