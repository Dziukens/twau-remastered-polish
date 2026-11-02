"""Minimal BC1 (DXT1) / BC3 (DXT5) decode + encode with numpy."""
import numpy as np


def _565(c):
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.int32)


def _color_blocks(blk, bc1):
    """blk: (N, 8) uint8 color part -> (N, 16, 4) rgba."""
    c0 = blk[:, 0].astype(np.int32) | (blk[:, 1].astype(np.int32) << 8)
    c1 = blk[:, 2].astype(np.int32) | (blk[:, 3].astype(np.int32) << 8)
    p0, p1 = _565(c0), _565(c1)
    four = (c0 > c1) | (not bc1)
    pal = np.zeros((len(blk), 4, 4), np.int32)
    pal[:, 0, :3], pal[:, 1, :3] = p0, p1
    pal[:, 2, :3] = np.where(four[:, None], (2 * p0 + p1) // 3, (p0 + p1) // 2)
    pal[:, 3, :3] = np.where(four[:, None], (p0 + 2 * p1) // 3, 0)
    pal[:, :, 3] = 255
    pal[:, 3, 3] = np.where(four, 255, 0)
    idx = blk[:, 4:8].astype(np.uint32)
    bits = idx[:, 0] | (idx[:, 1] << 8) | (idx[:, 2] << 16) | (idx[:, 3] << 24)
    sel = (bits[:, None] >> (2 * np.arange(16, dtype=np.uint32))) & 3
    return np.take_along_axis(pal, sel[:, :, None].astype(np.int64).repeat(4, 2), 1)


def _alpha_blocks(blk):
    a0 = blk[:, 0].astype(np.int32)
    a1 = blk[:, 1].astype(np.int32)
    pal = np.zeros((len(blk), 8), np.int32)
    pal[:, 0], pal[:, 1] = a0, a1
    big = a0 > a1
    for i in range(1, 7):
        pal[:, i + 1] = np.where(big, ((7 - i) * a0 + i * a1) // 7, 0)
    for i in range(1, 5):
        pal[:, i + 1] = np.where(big, pal[:, i + 1], ((5 - i) * a0 + i * a1) // 5)
    pal[:, 6] = np.where(big, pal[:, 6], 0)
    pal[:, 7] = np.where(big, pal[:, 7], 255)
    bits = np.zeros(len(blk), np.uint64)
    for i in range(6):
        bits |= blk[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    sel = (bits[:, None] >> (np.uint64(3) * np.arange(16, dtype=np.uint64))) & np.uint64(7)
    return np.take_along_axis(pal, sel.astype(np.int64), 1)


def decode(data, w, h, fmt):
    bs = 8 if fmt == 'bc1' else 16
    bw, bh = w // 4, h // 4
    blk = np.frombuffer(data, np.uint8, bw * bh * bs).reshape(-1, bs)
    if fmt == 'bc1':
        px = _color_blocks(blk, True)
    else:
        px = _color_blocks(blk[:, 8:], False)
        px[:, :, 3] = _alpha_blocks(blk[:, :8])
    img = px.reshape(bh, bw, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, 4)
    return img.astype(np.uint8)


def _enc565(rgb):
    r, g, b = (int(rgb[0]) * 31 + 127) // 255, (int(rgb[1]) * 63 + 127) // 255, (int(rgb[2]) * 31 + 127) // 255
    return (r << 11) | (g << 5) | b


def _encode_color(px, bc1):
    """px: (16,4) uint8 -> 8 bytes. Simple bounding-box endpoint fit on luminance axis."""
    rgb = px[:, :3].astype(np.int32)
    transparent = bc1 and (px[:, 3] < 128).any()
    lum = rgb.sum(1)
    hi, lo = rgb[lum.argmax()], rgb[lum.argmin()]
    c0, c1 = _enc565(hi), _enc565(lo)
    if transparent:
        if c0 > c1:
            c0, c1 = c1, c0
    else:
        if c0 < c1:
            c0, c1 = c1, c0
        if c0 == c1:
            idx = np.zeros(16, np.uint32)
            return _pack_color(c0, c1, idx)
    p0, p1 = _565(np.array([c0]))[0], _565(np.array([c1]))[0]
    if c0 > c1 or not bc1:
        cand = [p0, p1, (2 * p0 + p1) // 3, (p0 + 2 * p1) // 3]
    else:
        cand = [p0, p1, (p0 + p1) // 2, None]
    best = np.zeros(16, np.uint32)
    for i in range(16):
        if transparent and px[i, 3] < 128:
            best[i] = 3
            continue
        d = [((rgb[i] - c) ** 2).sum() if c is not None else 1 << 30 for c in cand]
        best[i] = int(np.argmin(d))
    return _pack_color(c0, c1, best)


def _pack_color(c0, c1, idx):
    bits = 0
    for i in range(16):
        bits |= int(idx[i]) << (2 * i)
    return bytes([c0 & 255, c0 >> 8, c1 & 255, c1 >> 8]) + bits.to_bytes(4, 'little')


def _encode_alpha(a):
    a = a.astype(np.int32)
    a0, a1 = int(a.max()), int(a.min())
    if a0 == a1:
        return bytes([a0, a1]) + bytes(6)
    pal = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
    pal = np.array(pal)
    idx = np.abs(a[:, None] - pal[None, :]).argmin(1)
    bits = 0
    for i in range(16):
        bits |= int(idx[i]) << (3 * i)
    return bytes([a0, a1]) + bits.to_bytes(6, 'little')


def encode(img, fmt):
    h, w = img.shape[:2]
    out = bytearray()
    for by in range(h // 4):
        for bx in range(w // 4):
            px = img[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4].reshape(16, 4)
            if fmt == 'bc1':
                out += _encode_color(px, True)
            else:
                out += _encode_alpha(px[:, 3]) + _encode_color(px, False)
    return bytes(out)
