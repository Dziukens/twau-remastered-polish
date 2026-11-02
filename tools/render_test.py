"""Render a test string with a (patched) .font to PNG for visual checking."""
import sys

import numpy as np
from PIL import Image

from font import Font

TEST = 'Zażółć gęślą jaźń. ŻÓŁĆ GĘŚLĄ JAŹŃ. Łódź, Świętokrzyskie, ąę ĄĘ'


def render(data, path, s=TEST):
    f = Font(data)
    imgs = [f.image(i) for i in range(len(f.pages))]
    pen = 10
    W = int(sum(f.glyphs.get(ord(c), f.glyphs[32])[10] for c in s)) + 20
    top = int(-min(0, min(g[9] for g in f.glyphs.values()))) + 4
    H = int(max(g[7] + g[9] for g in f.glyphs.values())) + 10 + top
    cv = np.zeros((H, W), np.uint8)
    for c in s:
        g = f.glyphs.get(ord(c))
        if g is None:
            pen += 10
            continue
        pg, img = f.pages[g[0]], imgs[g[0]]
        bgp = img[-1, -1].astype(int)
        x, y, w, h = round(g[2] * pg.w), round(g[4] * pg.h), int(g[6]), int(g[7])
        sub = np.abs(img[y:y + h, x:x + w].astype(int) - bgp).max(-1).astype(np.uint8)
        bx, by = int(pen + g[8]), int(g[9]) + top
        if w > 0 and h > 0 and bx >= 0 and by >= 0:
            sub = sub[:H - by, :W - bx]
            cv[by:by + sub.shape[0], bx:bx + sub.shape[1]] = np.maximum(cv[by:by + sub.shape[0], bx:bx + sub.shape[1]], sub)
        pen += g[10]
    Image.fromarray(255 - cv).save(path)


if __name__ == '__main__':
    render(open(sys.argv[1], 'rb').read(), sys.argv[2])
