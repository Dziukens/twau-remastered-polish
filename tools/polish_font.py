"""Add Polish glyphs (ą ć ę ł ń ś ź ż + capitals, ó/Ó when missing) to a Telltale .font.

Glyphs are composed from pieces of the font itself so they match its style:
  acute  - top part of é / É      dot    - dot of i
  ogonek - mirrored cedilla of ç  stroke - drawn with the stem thickness of l / L
New glyphs go into rows appended below page 0 (height doubled); existing blocks stay bit-identical.
"""
import numpy as np
from PIL import Image, ImageDraw

import bcn
from font import Font

PL = 'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ'
BASE = dict(zip(PL, 'acelnoszzACELNOSZZ'))

# The engine treats any character above U+00FF as a line-break opportunity (CJK style), so words
# were split after ł, ę, ... The build stores these letters as unused Latin-1 letters instead
# (case pairs, so upper/lower conversion stays consistent) and the fonts draw the Polish glyphs there.
REMAP = str.maketrans('ąćęłńśźżĄĆĘŁŃŚŹŻ', 'ãåêðõöýûÃÅÊÐÕÖÝÛ')


class Composer:
    def __init__(self, font):
        self.f = font
        self.imgs = [font.image(i).astype(np.int32) for i in range(len(font.pages))]
        img = self.imgs[0]
        flat = img.reshape(-1, 4)
        vals, counts = np.unique(flat, axis=0, return_counts=True)
        self.bg = vals[counts.argmax()]
        dist = np.abs(flat - self.bg).max(1)
        self.fg = flat[dist.argmax()]
        self.up = self.fg >= self.bg  # per-channel combine direction

    # --- bitmap helpers (bitmaps are RGBA int arrays, positioned in pen space) ---
    def bitmap(self, ch):
        g = self.f.glyphs.get(ord(ch))
        if g is None:
            return None
        pg = self.f.pages[g[0]]
        x, y = round(g[2] * pg.w), round(g[4] * pg.h)
        w, h = int(g[6]), int(g[7])
        px = self.imgs[g[0]][y:y + h, x:x + w].copy()
        ink = self.cov(px) > 0.08
        if not ink.any():
            return None
        r, c = np.where(ink.any(1))[0], np.where(ink.any(0))[0]
        px = px[r[0]:r[-1] + 1, c[0]:c[-1] + 1]
        return dict(px=px, x=g[8] + c[0], y=g[9] + r[0], adv=g[10], w=px.shape[1], h=px.shape[0],
                    rect_x=g[8], rect_r=g[8] + w)

    def cov(self, px):
        d = np.abs(px - self.bg).max(-1).astype(np.float32)
        m = np.abs(self.fg - self.bg).max()
        return d / max(m, 1)

    def from_cov(self, c):
        return (self.bg + (self.fg - self.bg) * c[..., None]).round().astype(np.int32)

    def part(self, bm, rows):
        """Sub-bitmap of rows (pen-space y predicate), trimmed to ink."""
        ys = bm['y'] + np.arange(bm['h'])
        sel = rows(ys)
        px = bm['px'][sel]
        if px.size == 0:
            return None
        ink = self.cov(px) > 0.08
        if not ink.any():
            return None
        r = np.where(ink.any(1))[0]
        c = np.where(ink.any(0))[0]
        px = px[r[0]:r[-1] + 1, c[0]:c[-1] + 1]
        return dict(px=px, x=bm['x'] + c[0], y=bm['y'] + np.where(sel)[0][r[0]], w=px.shape[1], h=px.shape[0])

    def first_blob(self, bm):
        """Top-most run of inked rows (e.g. the dot of i)."""
        ink_rows = (self.cov(bm['px']) > 0.08).any(1)
        r = np.where(ink_rows)[0]
        if len(r) == 0:
            return None
        end = r[0]
        while end + 1 < len(ink_rows) and ink_rows[end + 1]:
            end += 1
        top = bm['y'] + r[0]
        bot = bm['y'] + end
        p = self.part(bm, lambda ys: (ys >= top) & (ys <= bot))
        stem_rows = ink_rows[end + 1:]
        return p if stem_rows.any() else None  # no gap -> not a separate dot

    def compose(self, pieces, adv, shift_x=0):
        x0 = min(p['x'] for p in pieces)
        y0 = min(p['y'] for p in pieces)
        x1 = max(p['x'] + p['w'] for p in pieces)
        y1 = max(p['y'] + p['h'] for p in pieces)
        x0, y0, x1, y1 = int(np.floor(x0)), int(np.floor(y0)), int(np.ceil(x1)), int(np.ceil(y1))
        canvas = np.empty((y1 - y0, x1 - x0, 4), np.int32)
        canvas[:] = self.bg
        for p in pieces:
            ox, oy = int(round(p['x'] - x0)), int(round(p['y'] - y0))
            ox = min(max(ox, 0), canvas.shape[1] - p['w'])
            oy = min(max(oy, 0), canvas.shape[0] - p['h'])
            dst = canvas[oy:oy + p['h'], ox:ox + p['w']]
            canvas[oy:oy + p['h'], ox:ox + p['w']] = np.where(self.up, np.maximum(dst, p['px']), np.minimum(dst, p['px']))
        return dict(px=canvas, x=x0 + shift_x, y=y0, w=canvas.shape[1], h=canvas.shape[0], adv=adv)

    def stem(self, bm, frac):
        """(center x, width) of the left-most stem at relative height frac."""
        row = self.cov(bm['px'][int(bm['h'] * frac)]) > 0.5
        xs = np.where(row)[0]
        if len(xs) == 0:
            return None
        end = xs[0]
        while end + 1 < len(row) and row[end + 1]:
            end += 1
        return bm['x'] + (xs[0] + end + 1) / 2, end + 1 - xs[0]

    def stem_right(self, bm, frac):
        """Center x of the right-most inked run at relative height frac."""
        row = self.cov(bm['px'][min(bm['h'] - 1, int(bm['h'] * frac))]) > 0.5
        xs = np.where(row)[0]
        if len(xs) == 0:
            return bm['x'] + bm['w'] * 0.8
        start = xs[-1]
        while start - 1 >= 0 and row[start - 1]:
            start -= 1
        return bm['x'] + (start + xs[-1] + 1) / 2

    def ogonek(self, ax, top, rx, ry, thick):
        """Hook hanging from (ax, top): arc from the attach point round the left side, ending bottom-right."""
        ss = 4
        pad = thick
        w = int(np.ceil(rx * 2 + pad * 2)) + 1
        h = int(np.ceil(ry * 2 + pad * 2)) + 1
        im = Image.new('L', (w * ss, h * ss), 0)
        # ellipse whose top point is the attach point; keep the right half short so the tail curls right
        box = [(pad) * ss, (pad) * ss, (pad + rx * 2) * ss, (pad + ry * 2) * ss]
        ImageDraw.Draw(im).arc(box, start=50, end=275, fill=255, width=max(1, int(round(thick * ss))))
        c = np.array(im.resize((w, h), Image.LANCZOS), np.float32) / 255
        return dict(px=self.from_cov(c), x=ax - pad - rx, y=top - pad + thick / 2, w=w, h=h)

    def stroke(self, cx, cy, length, thick, angle=32):
        ss = 4
        a = np.radians(angle)
        dx, dy = np.cos(a) * length / 2, np.sin(a) * length / 2
        nx, ny = -np.sin(a) * thick / 2, np.cos(a) * thick / 2
        w = int(np.ceil(abs(dx) * 2 + abs(nx) * 2)) + 2
        h = int(np.ceil(abs(dy) * 2 + abs(ny) * 2)) + 2
        im = Image.new('L', (w * ss, h * ss), 0)
        mx, my = w / 2, h / 2
        poly = [(mx - dx + nx, my + dy + ny), (mx - dx - nx, my + dy - ny),
                (mx + dx - nx, my - dy - ny), (mx + dx + nx, my - dy + ny)]
        ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
        c = np.array(im.resize((w, h), Image.LANCZOS), np.float32) / 255
        return dict(px=self.from_cov(c), x=cx - w / 2, y=cy - h / 2, w=w, h=h)

    # --- glyph builders ---
    def accent(self, plain, accented):
        p, a = self.bitmap(plain), self.bitmap(accented)
        if not p or not a:
            return None
        acc = self.part(a, lambda ys: ys < p['y'])
        if acc is None:
            return None
        acc['dx'] = acc['x'] + acc['w'] / 2 - (p['x'] + p['w'] / 2)
        return acc

    def build(self, ch):
        base = self.bitmap(BASE[ch])
        if base is None:
            return None
        upper = ch.isupper()
        acute_l = self.accent('e', 'é') or self.accent('o', 'ó')
        acute_u = self.accent('E', 'É') or self.accent('O', 'Ó')
        bc = base['x'] + base['w'] / 2
        if ch in 'ćńśźóĆŃŚŹÓ':
            acc = acute_u if upper else acute_l
            if acc is None and upper and acute_l is not None:
                e = self.bitmap('e')
                gap = e['y'] - (acute_l['y'] + acute_l['h'])
                acc = dict(acute_l, y=base['y'] - gap - acute_l['h'])
            if acc is None:
                return None
            piece = dict(acc, x=bc + acc['dx'] - acc['w'] / 2)
            return self.compose([base, piece], base['adv'])
        if ch in 'żŻ':
            i = self.bitmap('i')
            dot = self.first_blob(i) if i else None
            if dot is None:  # dot merged with the stem at small sizes: borrow a middle dot / period
                dot = self.bitmap('·') or self.bitmap('.')
                ref = acute_l
                if dot is None or ref is None:
                    return None
                dot = dict(dot, y=ref['y'] + ref['h'] - dot['h'])
            if upper:
                ref = acute_u
                if ref is not None:
                    y = ref['y'] + ref['h'] - dot['h']
                else:
                    e = self.bitmap('e')
                    y = base['y'] - (e['y'] - (dot['y'] + dot['h'])) - dot['h']
                dot = dict(dot, y=y)
            return self.compose([base, dict(dot, x=bc - dot['w'] / 2)], base['adv'])
        if ch in 'ąęĄĘ':
            l, e = self.bitmap('l'), self.bitmap('e')
            st = self.stem(l, 0.6) if l else None
            if not st or not e:
                return None
            thick = max(1.5, st[1] * 0.8)
            xh = e['h']
            rx, ry = xh * 0.15, xh * 0.24
            if upper:
                rx, ry = rx * 1.15, ry * 1.15
            bottom = base['y'] + base['h']
            if ch == 'ą':
                ax = self.stem_right(base, 0.85)
            elif ch == 'Ą':
                ax = self.stem_right(base, 0.97) - thick * 0.3
            elif ch == 'ę':
                ax = bc + base['w'] * 0.12
            else:
                ax = base['x'] + base['w'] * 0.72
            og = self.ogonek(ax, bottom - thick * 0.55, rx, ry, thick)
            return self.compose([base, og], base['adv'])
        if ch in 'łŁ':
            st = self.stem(base, 0.6)
            if st is None:
                return None
            sx, sw = st
            e = self.bitmap('e')
            xh = e['h'] if e else base['h'] * 0.6
            thick = max(1.5, min(sw * 0.75, xh * 0.14))
            length = sw * 1.3 + xh * 0.42
            if ch == 'ł':
                xh_top = e['y'] if e else base['y'] + base['h'] * 0.35
                cy = xh_top + (base['y'] + base['h'] - xh_top) * 0.38
            else:
                cy = base['y'] + base['h'] * 0.55
            s = self.stroke(sx, cy, length, thick)
            # stroke may overhang the stem; widen the advance by part of the overhang so it does not collide
            left_over = max(0, base['x'] - s['x'] - 1)
            right_over = max(0, s['x'] + s['w'] - (base['x'] + base['w']) - 1) if ch == 'ł' else 0
            g = self.compose([base, s], 0, shift_x=round(left_over * 0.6))
            g['adv'] = base['adv'] + round(left_over * 0.6 + right_over * 0.6)
            return g
        return None

    @staticmethod
    def scale(px, k):
        h, w = px.shape[:2]
        out = np.stack([np.array(Image.fromarray(px[..., i].astype(np.uint8)).resize(
            (max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)) for i in range(4)], -1)
        return out.astype(np.int32)


def set_unicode(data):
    """Set the font's unicode flag (bool '1'). With '0' the engine draws every UTF-8 byte as its own glyph."""
    font = Font(data)
    pos = font.map_pos - 9  # flag byte sits before base size + height floats
    if data[pos] == 0x31:
        return data
    assert data[pos] == 0x30, data[pos]
    return data[:pos] + b'\x31' + data[pos + 1:]


def patch_font(data, log=print):
    data, built, aliased = _patch_font(set_unicode(data), log)
    return data, built, aliased


def _patch_font(data, log):
    font = Font(data)
    comp = Composer(font)
    built, aliased = [], []
    new = {}
    for ch in PL:
        if ord(ch) in font.glyphs:
            continue
        g = None
        try:
            g = comp.build(ch)
        except Exception as ex:  # fall back to the plain letter
            log('   build %s failed: %r' % (ch, ex))
        if g is not None:
            new[ch] = g
            built.append(ch)
        elif ord(BASE[ch]) in font.glyphs:
            font.glyphs[ord(ch)] = list(font.glyphs[ord(BASE[ch])])
            aliased.append(ch)
    if not new:
        remap_glyphs(font)
        return font.rebuild(0, font.pages[0].h, b''), built, aliased

    pg = font.pages[0]
    old_h = pg.h
    new_h = old_h * 2
    area = np.empty((old_h, pg.w, 4), np.int32)
    area[:] = comp.bg
    x = y = 2
    row_h = 0
    for ch, g in new.items():
        if x + g['w'] + 2 > pg.w:
            x, y = 2, y + row_h + 3
            row_h = 0
        if y + g['h'] + 2 > old_h:
            raise RuntimeError('glyph area full')
        area[y:y + g['h'], x:x + g['w']] = g['px']
        g['ax'], g['ay'] = x, y + old_h
        x += g['w'] + 3
        row_h = max(row_h, g['h'])
    for code, gl in font.glyphs.items():
        if gl[0] == 0:
            gl[4] *= old_h / new_h
            gl[5] *= old_h / new_h
    for ch, g in new.items():
        font.glyphs[ord(ch)] = [0, 15, g['ax'] / pg.w, (g['ax'] + g['w']) / pg.w, g['ay'] / new_h,
                                (g['ay'] + g['h']) / new_h, float(g['w']), float(g['h']), float(g['x']),
                                float(g['y']), float(g['adv'])]
    remap_glyphs(font)
    area = np.clip(area, 0, 255).astype(np.uint8)
    pixels = encode_sparse(area, pg.fmt, comp.bg.astype(np.uint8))
    return font.rebuild(0, new_h, pixels), built, aliased


def remap_glyphs(font):
    """Draw each Polish letter at its REMAP substitute too (replacing that Latin-1 glyph)."""
    for src, dst in REMAP.items():
        if src in font.glyphs:
            font.glyphs[dst] = list(font.glyphs[src])


def encode_sparse(img, fmt, bg):
    """Encode, reusing one pre-encoded block for every block that is pure background."""
    h, w = img.shape[:2]
    empty = bcn.encode(np.broadcast_to(bg, (4, 4, 4)).copy(), fmt)
    out = bytearray()
    for by in range(h // 4):
        rows = img[by * 4:by * 4 + 4]
        if (rows == bg).all():
            out += empty * (w // 4)
            continue
        for bx in range(w // 4):
            blk = rows[:, bx * 4:bx * 4 + 4]
            out += empty if (blk == bg).all() else bcn.encode(blk.copy(), fmt)
    return bytes(out)
