#!/usr/bin/env python3
"""Check generated icons, export review previews, and apply on macOS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import struct
import subprocess
import sys
import zlib

from png_codec import decode, encode

ROOT = Path(__file__).resolve().parent.parent


def inspect(image):
    data = image.read_bytes()
    w, h, pixels = decode(data)
    alpha = pixels[3::4]
    errors = []
    if not any(alpha) or min(alpha) != 0:
        errors.append('requires_visible_subject_and_real_transparency')
    edge = (list(alpha[:w]) + list(alpha[-w:]) +
            list(alpha[::w]) + list(alpha[w-1::w]))
    if any(edge):
        errors.append('canvas_edges_not_fully_transparent')
    isolated = 0
    for y in range(1, h-1):
        for x in range(1, w-1):
            i = y*w+x
            if alpha[i] > 16 and all(alpha[i+dy*w+dx] <= 16
                                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                    if dx or dy):
                isolated += 1
    if isolated:
        errors.append('isolated_visible_pixels')
    return {'status': 'failed' if errors else 'technical_pass',
            'image': str(image), 'width': w, 'height': h,
            'sha256': hashlib.sha256(data).hexdigest(),
            'isolated_pixels': isolated, 'errors': errors,
            'visual_review_required': True}


def previews(image, output):
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for size in (1024, 128, 64):
        resized = output / f'{size}-alpha.png'
        subprocess.run(['/usr/bin/sips', '-Z', str(size), str(image),
                        '--out', str(resized)], check=True, capture_output=True)
        w, h, pixels = decode(resized.read_bytes())
        for background in ('light', 'dark', 'checker'):
            composite = bytearray(pixels)
            for i in range(w*h):
                x, y = i % w, i // w
                base = (245 if background == 'light' else 32 if background == 'dark'
                        else 200 if (x//8+y//8) % 2 else 255)
                a = pixels[i*4+3]
                for channel in range(3):
                    composite[i*4+channel] = (pixels[i*4+channel]*a + base*(255-a))//255
                composite[i*4+3] = 255
            dest = output / f'{size}-{background}.png'
            dest.write_bytes(encode(w, h, composite))
            paths.append(str(dest))
    return paths


def build():
    if not shutil.which('clang'):
        raise ValueError('Apple Command Line Tools are required for icon replacement')
    source = ROOT / 'scripts/folder_icon.m'
    directory = ROOT / '.build'
    directory.mkdir(exist_ok=True)
    binary, stamp = directory/'folder-icon-replacer', directory/'source.sha256'
    fingerprint = hashlib.sha256(source.read_bytes() + str(source).encode()).hexdigest()
    if not binary.exists() or not stamp.exists() or stamp.read_text() != fingerprint:
        env = dict(os.environ, TMPDIR=str(directory),
                   CLANG_MODULE_CACHE_PATH=str(directory/'module-cache'))
        subprocess.run(['clang', '-fobjc-arc', '-framework', 'Foundation',
                        '-framework', 'AppKit', str(source), '-o', str(binary)],
                       check=True, env=env)
        stamp.write_text(fingerprint)
    return binary


def apply(image, target):
    report = inspect(image)
    if report['status'] != 'technical_pass':
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    identity = target.lstat()
    if not stat.S_ISDIR(identity.st_mode):
        raise ValueError('target must be an ordinary directory, not a symlink')
    result = subprocess.run([str(build()), 'set-and-verify', str(image), str(target),
                             str(identity.st_dev), str(identity.st_ino), report['sha256']])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    check = commands.add_parser('check')
    check.add_argument('image', type=Path)
    check.add_argument('--previews', type=Path)
    for name in ('apply', 'command'):
        command = commands.add_parser(name)
        command.add_argument('image', type=Path)
        command.add_argument('target', type=Path)
    args = parser.parse_args()
    try:
        if sys.platform != 'darwin':
            raise ValueError('folder-icon-replacer supports local macOS only')
        image = args.image.expanduser()
        if args.action == 'check':
            report = inspect(image)
            if args.previews:
                report['previews'] = previews(image, args.previews)
                (args.previews/'check.json').write_text(
                    json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return int(report['status'] != 'technical_pass')
        target = args.target.expanduser()
        if not image.is_absolute() or not target.is_absolute():
            raise ValueError('image and target must use absolute paths')
        if args.action == 'command':
            print(shlex.join(['/bin/sh', str(ROOT/'scripts/terminal-apply.sh'),
                              str(image), str(target)]))
            return 0
        return apply(image, target)
    except (OSError, ValueError, struct.error, zlib.error, subprocess.CalledProcessError) as error:
        print(json.dumps({'status': 'failed', 'reason': str(error)}, ensure_ascii=False),
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
