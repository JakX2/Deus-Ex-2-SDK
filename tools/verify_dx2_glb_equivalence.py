#!/usr/bin/env python3
"""Compare DX2 exporter GLBs without changing any source asset.

Exact mode requires identical GLB bytes. Decoded-png mode tolerates ONLY
lossless recompression of the embedded PNGs and altered BIN offsets;
decoded image pixels, geometry, scene graph and material metadata must match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

MAX_GLB = 512 * 1024 * 1024
MAX_IMAGE_PIXELS = 4096 * 4096


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _png_rgba(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Embedded image is not PNG')
    position = 8
    width = height = 0
    compressed = []
    seen_ihdr = seen_iend = False
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError('PNG chunk truncated')
        length = struct.unpack_from('>I', data, position)[0]
        end = position + 12 + length
        if end > len(data):
            raise ValueError('PNG chunk length invalid')
        kind = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        actual = struct.unpack_from('>I', data, position + 8 + length)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != actual:
            raise ValueError('PNG CRC mismatch')
        position = end
        if kind == b'IHDR':
            if seen_ihdr or length != 13:
                raise ValueError('PNG header invalid')
            width, height, depth, color, comp, fil, interlace = struct.unpack(
                '>IIBBBBB', payload)
            if ((depth, color, comp, fil, interlace) != (8, 6, 0, 0, 0)
                or not 0 < width <= 4096 or not 0 < height <= 4096
                or width * height > MAX_IMAGE_PIXELS):
                raise ValueError('Unsupported PNG image layout or size')
            seen_ihdr = True
        elif kind == b'IDAT':
            if not seen_ihdr or seen_iend:
                raise ValueError('PNG IDAT outside image')
            compressed.append(payload)
        elif kind == b'IEND':
            if not seen_ihdr or length != 0 or end != len(data):
                raise ValueError('PNG end invalid')
            seen_iend = True
            break
        elif kind[0] & 32 == 0:
            raise ValueError('Unexpected critical PNG chunk')
    if not seen_iend or not compressed:
        raise ValueError('PNG incomplete')
    expected = height * (width * 4 + 1)
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(b''.join(compressed), expected + 1)
    if (len(raw) != expected or not decompressor.eof
        or decompressor.unconsumed_tail or decompressor.unused_data):
        raise ValueError('PNG decompressed size or trailing data invalid')
    stride = width * 4 + 1
    if any(raw[y * stride] != 0 for y in range(height)):
        raise ValueError('Only source-exporter filter-zero PNG supported')
    pixels = b''.join(
        raw[y * stride + 1:(y + 1) * stride] for y in range(height))
    return width, height, pixels


def _glb(path: Path) -> tuple[dict, bytes]:
    if path.suffix.lower() != '.glb' or not path.is_file():
        raise ValueError('Expected an existing GLB file')
    size = path.stat().st_size
    if size < 28 or size > MAX_GLB:
        raise ValueError('GLB size outside safety bounds')
    blob = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', blob)
    if (magic, version, total) != (b'glTF', 2, len(blob)):
        raise ValueError('GLB header invalid')
    offset = 12
    chunks = []
    while offset < len(blob):
        if offset + 8 > len(blob):
            raise ValueError('GLB chunk header truncated')
        length, kind = struct.unpack_from('<I4s', blob, offset)
        offset += 8
        if length % 4 or offset + length > len(blob):
            raise ValueError('GLB chunk size invalid')
        chunks.append((kind, blob[offset:offset + length]))
        offset += length
    if (len(chunks) != 2 or chunks[0][0] != b'JSON'
        or chunks[1][0] != b'BIN\x00'):
        raise ValueError('Expected exactly one JSON and one BIN chunk')
    doc = json.loads(chunks[0][1].decode('utf-8'))
    if type(doc) is not dict:
        raise ValueError('GLB JSON root invalid')
    return doc, chunks[1][1]


def _semantic(doc: dict, binary: bytes) -> tuple[dict, list[tuple], list[bytes]]:
    # Make a private mutable copy: never change the parsed original.
    doc = json.loads(json.dumps(doc))
    views = doc.get('bufferViews')
    images = doc.get('images', [])
    buffers = doc.get('buffers')
    if (not isinstance(views, list) or not isinstance(images, list)
        or not isinstance(buffers, list) or len(buffers) != 1):
        raise ValueError('Unsupported GLB buffer/image structure')
    image_ids = []
    for image in images:
        if (not isinstance(image, dict) or image.get('mimeType') != 'image/png'
            or type(image.get('bufferView')) is not int):
            raise ValueError('Source exporter image must be embedded PNG')
        image_ids.append(image['bufferView'])
    if len(image_ids) != len(set(image_ids)):
        raise ValueError('GLB image bufferView reused')
    imgset = set(image_ids)
    decoded = {}
    geometry = []
    for i, view in enumerate(views):
        if not isinstance(view, dict) or view.get('buffer') != 0:
            raise ValueError('Unsupported GLB buffer view')
        start = view.get('byteOffset', 0)
        length = view.get('byteLength')
        if (type(start) is not int or type(length) is not int
            or start < 0 or length < 0 or start + length > len(binary)):
            raise ValueError('Invalid GLB buffer view bounds')
        chunk = binary[start:start + length]
        view.pop('byteOffset', None)
        if i in imgset:
            decoded[i] = _png_rgba(chunk)
            view.pop('byteLength', None)
        else:
            geometry.append(chunk)
    if not isinstance(buffers[0], dict):
        raise ValueError('GLB buffer metadata invalid')
    buffers[0].pop('byteLength', None)
    return doc, [decoded[i] for i in image_ids], geometry


def verify(baseline: Path, candidate: Path, mode: str = 'exact') -> dict:
    if mode not in ('exact', 'decoded-png'):
        raise ValueError('Unknown comparison mode')
    a, b = Path(baseline), Path(candidate)
    if not a.is_file() or not b.is_file():
        raise ValueError('Both GLB paths must exist')
    if a.stat().st_size > MAX_GLB or b.stat().st_size > MAX_GLB:
        raise ValueError('GLB exceeds size limit')
    left, right = a.read_bytes(), b.read_bytes()
    same = left == right
    if mode == 'exact' and not same:
        raise ValueError('GLB bytes differ (exact mode)')
    images = geometry = 0
    if mode == 'decoded-png':
        da, ba = _glb(a)
        db, bb = _glb(b)
        na, ia, ga = _semantic(da, ba)
        nb, ib, gb = _semantic(db, bb)
        if na != nb or ia != ib or ga != gb:
            raise ValueError('GLB scene, geometry or decoded PNG pixels differ')
        images, geometry = len(ia), len(ga)
    return {
        'schema': 'DX2SDK-GLB-export-equivalence-v1',
        'mode': mode,
        'equivalent': True,
        'byte_identical': same,
        'embedded_images_checked': images,
        'nonimage_views_checked': geometry,
        'baseline_sha256': _sha(left),
        'candidate_sha256': _sha(right),
        'comparison_is_read_only': True,
        'native_dx2_game_map_writer': False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--mode', choices=('exact', 'decoded-png'),
                        default='exact')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(
            verify(args.baseline, args.candidate, args.mode),
            sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError, struct.error,
            json.JSONDecodeError, zlib.error) as exc:
        print('DX2 GLB comparison REFUSED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
