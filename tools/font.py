"""Full parse of TWAU Remastered .font files (glyph table + embedded T3Texture pages).

T3Texture tail layout (relative to the surface-format field F):
    F-16: width, height, depth, arraySize | F: format | F+4..F+20: 4x u32 | F+24: swizzle block (8 bytes)
    F+32: 3 floats | F+44: alphaMode, colorMode | F+52: uvOffset, uvScale | F+68: 2 empty arrays
    F+84: regionCount, auxCount, totalSize | F+96: region(face, mip, mipCount, size, pitch, slicePitch)
Pixel data for all pages is concatenated in the async section.
"""
import struct

import bcn

FORMATS = {0x40: 'bc1', 0x42: 'bc3'}
GLYPH = struct.Struct('<II4f5f')  # page, channel, l, r, t, b (uv), w, h, xoff, yoff, advance
SWZ = b'\x08\x00\x00\x00\x00\x01\x02\x03'


class Page:
    pass


class Font:
    def __init__(self, d):
        self.d = d
        assert d[:4] == b'6VSM'
        self.def_size, self.dbg_size, self.async_size, nver = struct.unpack_from('<IIII', d, 4)
        self.ds = 20 + 12 * nver
        p = self.ds
        p += struct.unpack_from('<I', d, p)[0]  # name block
        p += 1 + 8  # bool + base size + height
        self.map_pos = p
        map_blk, count = struct.unpack_from('<II', d, p)
        p += 8
        self.glyphs = {}
        for _ in range(count):
            code = struct.unpack_from('<I', d, p)[0]
            self.glyphs[code] = list(GLYPH.unpack_from(d, p + 4))
            p += 48
        assert p == self.map_pos + map_blk
        self.tex_pos = p
        tex_blk, n_pages = struct.unpack_from('<II', d, p)
        tex_end = p + tex_blk
        self.pages = []
        data_off = self.ds + self.def_size
        s = p
        while len(self.pages) < n_pages:
            s = d.index(SWZ, s + 1, tex_end)
            pg = Page()
            pg.fmt_pos = s - 24
            pg.w, pg.h, _depth, _arr, fmt = struct.unpack_from('<5I', d, pg.fmt_pos - 16)
            pg.fmt = FORMATS[fmt]
            nreg, naux, total = struct.unpack_from('<III', d, pg.fmt_pos + 84)
            _face, mip, mipc, size, pg.pitch, _sp = struct.unpack_from('<6I', d, pg.fmt_pos + 96)
            assert (nreg, naux, mip, mipc) == (1, 0, 0, 1) and total == size, (nreg, naux, mip, mipc, total, size)
            bpp = 8 if pg.fmt == 'bc1' else 16
            assert size == pg.w * pg.h // 16 * bpp
            pg.pixels = d[data_off:data_off + size]
            data_off += size
            self.pages.append(pg)
        assert data_off == len(d)

    def image(self, page=0):
        pg = self.pages[page]
        return bcn.decode(pg.pixels, pg.w, pg.h, pg.fmt)

    def rebuild(self, page, new_h, extra_pixels):
        """Grow one page to new_h rows (extra_pixels = encoded blocks for the added rows).
        Caller must already have rescaled glyph v coords; self.glyphs is written as-is."""
        d = self.d[:self.ds + self.def_size]
        glyph_bytes = bytearray()
        for code in sorted(self.glyphs):
            glyph_bytes += struct.pack('<I', code) + GLYPH.pack(*self.glyphs[code])
        out = bytearray(d[:self.map_pos])
        out += struct.pack('<II', 8 + len(glyph_bytes), len(self.glyphs)) + glyph_bytes
        delta = len(out) - self.tex_pos
        out += d[self.tex_pos:]
        pg = self.pages[page]
        size = len(pg.pixels) + len(extra_pixels)
        f = pg.fmt_pos + delta
        struct.pack_into('<I', out, f - 12, new_h)
        struct.pack_into('<I', out, f + 84 + 8, size)
        struct.pack_into('<I', out, f + 96 + 12, size)
        struct.pack_into('<I', out, f + 96 + 20, size)
        pixels = b''.join(p.pixels + (extra_pixels if i == page else b'') for i, p in enumerate(self.pages))
        struct.pack_into('<III', out, 4, self.def_size + delta, self.dbg_size, len(pixels))
        return bytes(out) + pixels
