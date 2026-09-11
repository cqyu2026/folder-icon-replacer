#!/usr/bin/env python3
"""Prepare quarantined candidates with existing macOS tools; never promote/apply."""
import argparse
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

gate = importlib.import_module('portable-icon-gate')


def run(args):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if result.returncode: raise ValueError(result.stderr.strip() or result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description=gate.GUIDANCE)
    parser.add_argument('image', type=Path)
    parser.add_argument('output', type=Path, help='new candidate directory outside the target folder')
    args = parser.parse_args()
    skill = Path(__file__).resolve().parents[1]
    source, output = args.image.resolve(), args.output.resolve()
    try:
        data = source.read_bytes()
        if not data.startswith(gate.PNG):
            if not data.startswith(b'\xff\xd8') or sys.platform != 'darwin' or not shutil.which('clang') or not shutil.which('sips'):
                raise ValueError(gate.GUIDANCE)
        if output.exists(): raise ValueError('refusing_existing_output')
        output.mkdir(parents=True)
        if data.startswith(gate.PNG):
            candidate = output/'candidate-01.png'
            candidate.write_bytes(data)
            candidates = [candidate]
        else:
            run(['/bin/sh',skill/'scripts/build-native-tools.sh',skill/'.build'])
            run(['/bin/sh',skill/'scripts/build-png-normalizer.sh',skill/'.build'])
            run([skill/'.build/foreground-extractor','extract',source,output/'raw'])
            candidates = []
            for raw in sorted((output/'raw').glob('candidate-*.png')):
                candidate = output/raw.name
                run([skill/'.build/png-normalizer',raw,candidate])
                candidates.append(candidate)
        reports = []
        for candidate in candidates:
            report = gate.assess(candidate)
            report['candidate'] = str(candidate)
            if report['status'] == 'failed':
                rejected = output/'rejected'; rejected.mkdir(exist_ok=True)
                candidate.replace(rejected/candidate.name)
                report['candidate'] = str(rejected/candidate.name)
            else:
                report['previews'] = gate.previews(candidate,output/'previews')
                report['status'] = 'awaiting_visual_review'
            reports.append(report)
        result = {'source':str(source),'source_sha256':gate.hashlib.sha256(data).hexdigest(),'candidates':reports}
        (output/'qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if reports and all(r['status']=='awaiting_visual_review' for r in reports) else 1
    except (OSError,ValueError) as error:
        print(json.dumps({'status':'failed','reason':str(error),'next_action':gate.GUIDANCE},ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
