"""Bounded 8-bit RGBA PNG reader/writer using only the standard library."""
import struct
import zlib

PNG = b"\x89PNG\r\n\x1a\n"
GUIDANCE = "Export a transparent 8-bit RGBA non-interlaced PNG."

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
