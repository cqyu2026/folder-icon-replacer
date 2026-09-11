#!/usr/bin/env python3
"""Stdlib-only conservative PNG QA. Technical pass is never visual approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from collections import deque
from pathlib import Path

PNG = b"\x89PNG\r\n\x1a\n"
GUIDANCE = "请提供已验证的透明 PNG，或在支持 macOS Vision/ImageIO 本地流水线的环境运行；不能自动抠取 JPEG。"
CHECKS = ("background_removed", "edges_clean", "subject_intact", "previews_reviewed")


def decode(data):
    if not data.startswith(PNG):
        raise ValueError("requires_verified_transparent_png: " + GUIDANCE)
    offset, payload, header, ended = 8, bytearray(), None, False
    while offset + 12 <= len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + size]
        if offset + size + 12 > len(data) or zlib.crc32(kind + body) != struct.unpack_from(">I", data, offset + 8 + size)[0]:
            raise ValueError("invalid_png_crc_or_length")
        if header is None and kind != b"IHDR":
            raise ValueError("invalid_png_header")
        if kind == b"IHDR":
            if header is not None or len(body) != 13:
                raise ValueError("invalid_png_header")
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT": payload.extend(body)
        elif kind == b"IEND":
            ended = not body and offset + size + 12 == len(data)
            break
        elif kind == b"acTL" or (kind[0] < 97 and kind != b"PLTE"):
            raise ValueError("unsupported_png_chunk")
        offset += size + 12
    if not ended or header is None:
        raise ValueError("invalid_png")
    w, h, depth, color, compression, filtering, interlace = header
    if not (1 <= w <= 2048 and 1 <= h <= 2048):
        raise ValueError("png_dimensions_out_of_range")
    if (depth, color, compression, filtering, interlace) != (8, 6, 0, 0, 0):
        raise ValueError("requires_8bit_rgba_noninterlaced_png")
    stride, expected = w * 4, (w * 4 + 1) * h
    decoder = zlib.decompressobj()
    raw = decoder.decompress(bytes(payload), expected + 1)
    if len(raw) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError("invalid_png_pixel_length")
    pixels, previous = bytearray(), bytearray(stride)
    for y in range(h):
        at = y * (stride + 1)
        method, row = raw[at], bytearray(raw[at + 1:at + 1 + stride])
        if method > 4: raise ValueError("invalid_png_filter")
        for i in range(stride):
            a, b, c = row[i - 4] if i >= 4 else 0, previous[i], previous[i - 4] if i >= 4 else 0
            if method == 1: predictor = a
            elif method == 2: predictor = b
            elif method == 3: predictor = (a + b) // 2
            elif method == 4:
                p = a + b - c
                distances = (abs(p - a), abs(p - b), abs(p - c))
                predictor = (a, b, c)[distances.index(min(distances))]
            else: predictor = 0
            row[i] = (row[i] + predictor) & 255
        pixels.extend(row); previous = row
    return w, h, pixels


def encode(w, h, pixels):
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    rows = b"".join(b"\0" + pixels[y*w*4:(y+1)*w*4] for y in range(h))
    return PNG + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def technical(w, h, pixels):
    alpha = pixels[3::4]
    if min(alpha) != 0 or max(alpha) < 250: return ["missing_real_alpha"]
    if any(alpha[x] or alpha[(h-1)*w+x] for x in range(w)) or any(alpha[y*w] or alpha[y*w+w-1] for y in range(h)):
        return ["subject_touches_canvas_edge"]
    visible = [i for i, a in enumerate(alpha) if a > 16]
    if not 0.15 <= len(visible)/(w*h) <= 0.72: return ["visible_coverage_out_of_range"]
    for i in visible:
        if all(alpha[n] <= 16 for n in (i-1, i+1, i-w, i+w)):
            return ["isolated_edge_pixels"]
    # ponytail: bounded 128 px color/alpha topology is conservative; semantic residue still needs visual review.
    step = max(1, max(w, h)//128)
    gw, gh = (w+step-1)//step, (h+step-1)//step
    colors = []
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b, a = pixels[(y*w+x)*4:(y*w+x)*4+4]
            colors.append((r//32, g//32, b//32) if a > 16 else None)
    errors = []
    for by_color in (False, True):
        seen = set()
        for start, color in enumerate(colors):
            if color is None or start in seen: continue
            queue, component = deque([start]), []
            seen.add(start)
            while queue:
                i = queue.popleft(); component.append(i)
                x, y = i % gw, i // gw
                for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    n = ny*gw+nx
                    if 0 <= nx < gw and 0 <= ny < gh and n not in seen and colors[n] is not None and (not by_color or colors[n] == color):
                        seen.add(n); queue.append(n)
            xs, ys = [i%gw for i in component], [i//gw for i in component]
            bw, bh = max(xs)-min(xs)+1, max(ys)-min(ys)+1
            if len(component) >= gw*gh*0.025 and min(bw,bh) >= 8 and len(component)/(bw*bh) > 0.97:
                errors.append("suspected_rectangular_background")
            if not by_color and len(component) < max(3, gw*gh*0.0005):
                errors.append("isolated_edge_pixels")
    return sorted(set(errors))


def assess(path, review=None):
    try:
        data = path.read_bytes()
        w, h, pixels = decode(data)
        errors = technical(w, h, pixels)
        result = {"status": "failed" if errors else "technical_pass", "sha256": hashlib.sha256(data).hexdigest(), "errors": errors}
        if review is not None and not errors:
            review_data = review.read_bytes()
            record = json.loads(review_data)
            result["review_sha256"] = hashlib.sha256(review_data).hexdigest()
            if not isinstance(record, dict) or record.get("sha256") != result["sha256"] or not record.get("reviewer") :
                errors.append("missing_or_stale_visual_review")
            elif any(record.get(k) != "passed" for k in CHECKS):
                errors.append("visual_review_failed")
            if not errors: result["status"] = "passed"
        if errors: result["status"] = "failed"
        return result
    except (OSError, ValueError, KeyError, TypeError, struct.error, zlib.error) as error:
        return {"status": "failed", "errors": [str(error)]}


def png_alpha(path):
    result = assess(path)
    return result["status"] == "technical_pass", "; ".join(result["errors"]) or "passed"


def previews(path, directory):
    w, h, pixels = decode(path.read_bytes())
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for size in (64, 128, 1024):
        for background in ("light", "dark", "checker"):
            output = bytearray()
            for y in range(size):
                for x in range(size):
                    i = ((y*h//size)*w + x*w//size)*4
                    r, g, b, a = pixels[i:i+4]
                    base = 245 if background == "light" else 32 if background == "dark" else (200 if (x//8+y//8)%2 else 255)
                    output.extend(((v*a + base*(255-a))//255 for v in (r,g,b)))
                    output.append(255)
            dest = directory / f"{path.stem}-{size}-{background}.png"
            dest.write_bytes(encode(size,size,output)); paths.append(str(dest))
    return paths


def main():
    parser = argparse.ArgumentParser(description=GUIDANCE)
    parser.add_argument("image", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--require-review", action="store_true")
    parser.add_argument("--preview-dir", type=Path)
    args = parser.parse_args()
    review = args.review or (Path(str(args.image)+".review.json") if args.require_review else None)
    result = assess(args.image, review)
    if args.preview_dir and result["status"] != "failed": result["previews"] = previews(args.image, args.preview_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
