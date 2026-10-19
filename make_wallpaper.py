"""
PNG -> /EDMD/WALL.ART: the wallpaper behind the game list and the menus (v1 and v3).

The image (320x224, cropped/resized when needed) is darkened so the menu text stays readable,
reduced to 14 colours + black, cut into 8x8 tiles and deduplicated (also mirrored tiles). Black
is colour 0: it shows the backdrop, which follows the theme. At most MAX_TILES different tiles fit
in the video memory both cartridges have free; above that, the most similar tiles are merged.

File layout (padded to a multiple of 7 sectors, 3584 bytes):
  - 32 bytes : 16 big-endian words; word 0 = tile count, words 1..14 = palette 1 colours 1..14
  - 2240 bytes: 40x28 name-table words, ready for plane B (palette 1, tile 0x1DC.., H/V flip bits)
  - tile count x 32 bytes: 4bpp tiles, loaded at VRAM 0x3B80 (tile 0x1DC)

    python make_wallpaper.py wallpaper.png                     # writes WALL.ART next to the PNG
    python make_wallpaper.py wallpaper.png E:/EDMD/WALL.ART --dim 0.5
"""
import argparse
import struct
from pathlib import Path

from PIL import Image

W, H = 320, 224
TILE_BASE = 0x1DC           # VRAM 0x3B80, the same on both cartridges
MAX_TILES = 800             # up to VRAM 0x9FFF
CHUNK = 7 * 512


def md9(r, g, b):
    q = lambda v: min(7, (v + 18) // 36)
    return (q(b) * 2 << 8) | (q(g) * 2 << 4) | (q(r) * 2)


def rgb(c):
    return ((c >> 1 & 7) * 36, (c >> 5 & 7) * 36, (c >> 9 & 7) * 36)


def load(src, dim):
    im = Image.open(src).convert('RGB')
    if im.size != (W, H):
        scale = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
        left, top = (im.width - W) // 2, (im.height - H) // 2
        im = im.crop((left, top, left + W, top + H))
    if dim != 1:
        im = Image.eval(im, lambda v: int(v * dim))
    raw = im.tobytes()
    px = [md9(*raw[i:i + 3]) for i in range(0, len(raw), 3)]
    colours = sorted(set(px) - {0})
    if len(colours) > 14:
        q = Image.frombytes('RGB', (W, H), bytes(v for c in px for v in rgb(c)))
        q = q.quantize(colors=15, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
        raw = q.tobytes()
        px = [md9(*raw[i:i + 3]) for i in range(0, len(raw), 3)]
        colours = sorted(set(px) - {0})
    keep = colours[:14]
    index = {0: 0}
    for i, c in enumerate(keep):
        index[c] = i + 1
    for c in set(px) - set(index):          # anything left over: the nearest kept colour
        near = min([0] + keep, key=lambda k: sum((x - y) ** 2 for x, y in zip(rgb(k), rgb(c))))
        index[c] = index[near]
    pal = [0] * 16
    for c, i in index.items():
        if 0 < i < 15:
            pal[i] = c
    return [index[c] for c in px], pal


def tiles_of(idx):
    out = []
    for ty in range(H // 8):
        for tx in range(W // 8):
            out.append(tuple(tuple(idx[(ty * 8 + y) * W + tx * 8 + x] for x in range(8)) for y in range(8)))
    return out


def variants(t):
    h = tuple(tuple(reversed(r)) for r in t)
    return ((t, 0), (h, 0x800), (tuple(reversed(t)), 0x1000), (tuple(reversed(h)), 0x1800))


def dedupe(tiles):
    uniq, lookup, refs = [], {}, []
    for t in tiles:
        for v, flip in variants(t):
            if v in lookup:
                refs.append((lookup[v], flip))
                break
        else:
            lookup[t] = len(uniq)
            uniq.append(t)
            refs.append((len(uniq) - 1, 0))
    return uniq, refs


def merge(tiles, pal, limit):
    """merge the most similar tiles until at most limit remain (greedy, by colour distance)"""
    cols = [rgb(c) for c in pal]
    flat = lambda t: [cols[p] for row in t for p in row]
    vecs = [flat(t) for t in tiles]
    use = list(range(len(tiles)))
    owner = list(range(len(tiles)))

    def dist(a, b):
        return sum(abs(x[0] - y[0]) + abs(x[1] - y[1]) + abs(x[2] - y[2]) for x, y in zip(vecs[a], vecs[b]))

    while len(use) > limit:
        # cheap pass: compare each tile with a window of its sorted neighbours (by mean colour)
        key = sorted(use, key=lambda i: tuple(sum(c[k] for c in vecs[i]) for k in range(3)))
        best = None
        for n, a in enumerate(key):
            for b in key[n + 1:n + 8]:
                d = dist(a, b)
                if best is None or d < best[0]:
                    best = (d, a, b)
        _, keep, drop = best
        use.remove(drop)
        for i, o in enumerate(owner):
            if o == drop:
                owner[i] = keep
    return use, owner


def convert(src, dim):
    idx, pal = load(src, dim)
    uniq, refs = dedupe(tiles_of(idx))
    owner = list(range(len(uniq)))
    keep = owner
    if len(uniq) > MAX_TILES:
        keep, owner = merge(uniq, pal, MAX_TILES)
    slot = {t: n for n, t in enumerate(keep)}
    names = [0x2000 | flip | (TILE_BASE + slot[owner[u]]) for u, flip in refs]
    out = bytearray(struct.pack('>16H', len(keep), *pal[1:16]))
    out += struct.pack(f'>{len(names)}H', *names)
    for t in keep:
        for row in uniq[t]:
            out += bytes(row[i] << 4 | row[i + 1] for i in range(0, 8, 2))
    pad = -len(out) % CHUNK
    return bytes(out) + bytes(pad), len(uniq), len(keep), sum(1 for c in pal[1:15] if c)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('png')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--dim', type=float, default=1.0, help='brightness factor (0.5 = half), default 1')
    a = ap.parse_args()
    src = Path(a.png)
    dst = Path(a.out) if a.out else src.with_name('WALL.ART')
    data, n_uniq, n_tiles, n_cols = convert(src, a.dim)
    dst.write_bytes(data)
    merged = f' (merged from {n_uniq})' if n_uniq != n_tiles else ''
    print(f'{dst}: {n_tiles} tiles{merged}, {n_cols} colours + black, {len(data)} bytes')


if __name__ == '__main__':
    main()
