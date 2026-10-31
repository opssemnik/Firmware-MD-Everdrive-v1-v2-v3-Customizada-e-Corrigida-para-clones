"""
Original pixel art for the themes in TEMAS.BIN (no copied images, no third-party logos):
  - padrao     : "EVERDRIVE MD" in chrome over a circuit board
  - rgpoa      : "RETROGAMER POA" in gold, sunset over the Guaiba with the Gasometro chimney
  - sega16     : "16-BIT POWER" in blue chrome, checkerboard floor under a ringed planet
  - outrun     : "OUTRUN" over a sunset road with palm trees
  - retrochimp : "RETROCHIMP" in cream with a 70s rainbow shadow, a chimp with glasses and cap
  - synthwave  : the original synthwave art (gen_arte.py), now with its own colours
Each theme gets temas/<name>/EDMD/BANNER.ART (with the theme colours) and WALL.ART, plus PNG
previews in arte/temas/. make_temas.py then packs every theme into /EDMD/TEMAS.BIN.

    python arte/gen_temas.py
"""
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parent
PREV = HERE / 'temas'

# theme colours (Mega Drive 0BGR): backdrop, menu bar, bar shadow, text, dim text, accent
CORES = {
    'padrao':     '000,AAA,444,EEE,666,2CE',
    'rgpoa':      '002,00A,004,0EE,048,0AE',
    'sega16':     '200,A40,620,EEE,A86,0CE',
    'outrun':     '202,A0A,606,EE0,A4A,E4E',
    'synthwave':  '202,A0A,404,EEE,A6A,0AE',
    'retrochimp': '000,04C,026,CEE,68A,0CE',
}

FONT = {    # 7x6, the OS font style
    'A': ["..##...", ".####..", "##..##.", "##..##.", "######.", "##..##."],
    'B': ["#####..", "##..##.", "#####..", "##..##.", "##..##.", "#####.."],
    'C': [".####..", "##..##.", "##.....", "##.....", "##..##.", ".####.."],
    'D': ["#####..", "##..##.", "##..##.", "##..##.", "##..##.", "#####.."],
    'E': ["######.", "##.....", "#####..", "##.....", "##.....", "######."],
    'G': [".#####.", "##.....", "##.....", "##.###.", "##..##.", ".#####."],
    'H': ["##..##.", "##..##.", "######.", "##..##.", "##..##.", "##..##."],
    'I': ["######.", "..##...", "..##...", "..##...", "..##...", "######."],
    'M': ["##...##", "###.###", "#######", "##.#.##", "##...##", "##...##"],
    'N': ["##...##", "###..##", "####.##", "##.####", "##..###", "##...##"],
    'O': [".####..", "##..##.", "##..##.", "##..##.", "##..##.", ".####.."],
    'P': ["#####..", "##..##.", "##..##.", "#####..", "##.....", "##....."],
    'R': ["#####..", "##..##.", "##..##.", "#####..", "##.##..", "##..##."],
    'S': [".#####.", "##.....", ".####..", "....##.", "....##.", "#####.."],
    'T': ["######.", "..##...", "..##...", "..##...", "..##...", "..##..."],
    'U': ["##..##.", "##..##.", "##..##.", "##..##.", "##..##.", ".####.."],
    'V': ["##..##.", "##..##.", "##..##.", "##..##.", ".####..", "..##..."],
    'W': ["##...##", "##...##", "##.#.##", "#######", "###.###", "##...##"],
    '1': ["..##...", ".###...", "..##...", "..##...", "..##...", "######."],
    '6': [".####..", "##.....", "#####..", "##..##.", "##..##.", ".####.."],
    '-': [".......", ".......", "#####..", ".......", ".......", "......."],
}

BLACK = (0, 0, 0)


def new(w, h, c=BLACK):
    img = Image.new('RGB', (w, h), c)
    return img, img.load()


def text_mask(text, y0, sx=2, sy=2, adv=16, space=8, W=288, x0=None):
    width = sum(space if ch == ' ' else adv for ch in text) - (adv - 7 * sx)
    x = (W - width) // 2 if x0 is None else x0
    mask = set()
    for ch in text:
        if ch == ' ':
            x += space
            continue
        for ry, row in enumerate(FONT[ch]):
            for rx, p in enumerate(row):
                if p == '#':
                    for dy in range(sy):
                        for dx in range(sx):
                            mask.add((x + rx * sx + dx, y0 + ry * sy + dy))
        x += adv
    return mask


def put_text(px, mask, fill, H, shadows=(), outline=BLACK, top=None):
    """shadows: [(dx, dy, colour)], drawn from the last to the first; fill(y) -> colour"""
    for dx, dy, c in reversed(shadows):
        for (x, y) in mask:
            q = (x + dx, y + dy)
            if q not in mask and 0 <= q[1] < H:
                px[q] = c
    if outline:
        shadow_px = {(x + dx, y + dy) for dx, dy, _ in shadows for (x, y) in mask}
        for (x, y) in mask:
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    q = (x + ox, y + oy)
                    if q not in mask and q not in shadow_px and 0 <= q[1] < H:
                        px[q] = outline
    for (x, y) in mask:
        px[x, y] = fill(y)


def sprite(px, rows, pal, x0, y0, scale=1):
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != '.':
                for dy in range(scale):
                    for dx in range(scale):
                        px[x0 + x * scale + dx, y0 + y * scale + dy] = pal[ch]


def grad(stops, y, y0, y1):
    k = (y - y0) * len(stops) // max(1, y1 - y0)
    return stops[max(0, min(len(stops) - 1, k))]


# ---------------------------------------------------------------------------------------- padrao
CART = ["..############..",
        ".#############..",
        ".#LLLLLLLLLLL#..",
        ".#LWWWWWWWWWL#..",
        ".#LWccccccWWL#..",
        ".#LWWWWWWWWWL#..",
        ".#LLLLLLLLLLL#..",
        ".#############..",
        ".#############..",
        ".##.##.##.##.#..",
        ".#############..",
        "..#y#y#y#y#y#...",
        "..#y#y#y#y#y#..."]
CART_PAL = {'#': (72, 72, 90), 'L': (36, 36, 54), 'W': (180, 180, 180), 'c': (0, 180, 216), 'y': (216, 180, 0)}


def padrao_banner():
    W, H = 288, 24
    img, px = new(W, H)
    for y in range(H):
        c = grad([(18, 18, 36), (18, 18, 36), (36, 36, 54), (36, 36, 54)], y, 0, 21)
        for x in range(W):
            px[x, y] = c
    for x in range(W):
        px[x, 21] = (0, 180, 216)
        px[x, 22] = (0, 72, 108)
        px[x, 23] = BLACK
    mask = text_mask('EVERDRIVE MD', 3, sx=2, sy=3, adv=17, space=10)
    chrome = [(252, 252, 252), (216, 252, 252), (180, 216, 252), (144, 180, 216), (216, 216, 216),
              (144, 144, 180), (108, 108, 144), (144, 216, 252), (180, 252, 252)]
    put_text(px, mask, lambda y: chrome[(y - 3) * len(chrome) // 18], H, shadows=[(1, 1, (0, 72, 108))])
    sprite(px, CART, CART_PAL, 6, 4)
    sprite(px, CART, CART_PAL, W - 22, 4)
    return img


def padrao_wall():
    W, H = 320, 224
    C, R = 40, 28
    img, px = new(W, H)
    rnd = random.Random(16)
    tr, pad, chip, pin = (0, 54, 54), (0, 108, 108), (36, 36, 36), (108, 108, 108)
    cells = {}                                       # (cx, cy) -> set of directions 'NESW'
    busy = set()
    for cx in range(14, 26):                         # a big chip in the middle-right, pins on its edges
        for cy in range(9, 17):
            busy.add((cx + 8, cy))
    opp = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
    step = {'N': (0, -1), 'S': (0, 1), 'E': (1, 0), 'W': (-1, 0)}
    ends = []
    for _ in range(34):                              # random traces with right-angle turns
        x, y = rnd.randrange(C), rnd.randrange(R)
        if (x, y) in busy:
            continue
        d = rnd.choice('NESW')
        ends.append((x, y))
        for _ in range(rnd.randrange(6, 22)):
            nx, ny = x + step[d][0], y + step[d][1]
            if not (0 <= nx < C and 0 <= ny < R) or (nx, ny) in busy:
                break
            cells.setdefault((x, y), set()).add(d)
            cells.setdefault((nx, ny), set()).add(opp[d])
            x, y = nx, ny
            if rnd.random() < 0.18:
                d = rnd.choice([k for k in 'NESW' if k not in (d, opp[d])])
        ends.append((x, y))
    for (cx, cy), ds in cells.items():
        bx, by = cx * 8, cy * 8
        for d in ds:
            if d == 'N':
                pts = [(bx + 3 + i, by + j) for i in range(2) for j in range(5)]
            elif d == 'S':
                pts = [(bx + 3 + i, by + 3 + j) for i in range(2) for j in range(5)]
            elif d == 'E':
                pts = [(bx + 3 + j, by + 3 + i) for i in range(2) for j in range(5)]
            else:
                pts = [(bx + j, by + 3 + i) for i in range(2) for j in range(5)]
            for p in pts:
                px[p] = tr
    for (cx, cy) in ends:                            # round pads at the trace ends
        bx, by = cx * 8, cy * 8
        for y in range(1, 7):
            for x in range(1, 7):
                if (x - 3.5) ** 2 + (y - 3.5) ** 2 <= 7.5:
                    px[bx + x, by + y] = pad if (x - 3.5) ** 2 + (y - 3.5) ** 2 > 2 else BLACK
    x0, y0, x1, y1 = 22 * 8, 9 * 8, 34 * 8, 17 * 8
    for y in range(y0 + 4, y1 - 4):                 # the chip
        for x in range(x0 + 4, x1 - 4):
            px[x, y] = chip
    for x in range(x0 + 8, x1 - 8, 8):               # pins
        for y in list(range(y0, y0 + 4)) + list(range(y1 - 4, y1)):
            px[x + 2, y] = px[x + 3, y] = pin
    for y in range(y0 + 8, y1 - 8, 8):
        for x in list(range(x0, x0 + 4)) + list(range(x1 - 4, x1)):
            px[x, y + 2] = px[x, y + 3] = pin
    for y in range(y0 + 8, y0 + 11):                 # pin 1 dot
        for x in range(x0 + 8, x0 + 11):
            px[x, y] = (72, 72, 72)
    return img


# ---------------------------------------------------------------------------------------- rgpoa
def chimney(px, x0, ybase, h, w0=5, w1=3, c=(18, 0, 0)):
    for y in range(ybase - h, ybase):
        t = (y - (ybase - h)) / h
        w = int(round(w1 + (w0 - w1) * t))
        for x in range(x0 - w // 2, x0 - w // 2 + w):
            px[x, y] = c


def rgpoa_banner():
    W, H = 288, 24
    img, px = new(W, H)
    sky = [(54, 0, 0), (72, 0, 0), (108, 0, 18), (144, 18, 0), (180, 54, 0)]
    for y in range(H):
        c = grad(sky, y, 0, 20)
        for x in range(W):
            px[x, y] = c
    for x in range(W):
        px[x, 20] = (252, 180, 0)
        for y in (21, 22, 23):
            px[x, y] = (36, 0, 0)
        if (x // 3) % 5 == 0:
            px[x, 22] = (144, 72, 0)
    for cx in (22, W - 23):                          # the Gasometro chimney + building at both ends
        for y in range(12, 20):
            for x in range(cx - 10, cx + 4):
                px[x, y] = (36, 0, 0)
        chimney(px, cx + 7, 20, 18, 4, 2, (36, 0, 0))
    mask = text_mask('RETROGAMER POA', 3, sx=2, sy=3, adv=16, space=8)
    gold = [(252, 252, 144), (252, 252, 72), (252, 216, 0), (252, 180, 0), (252, 144, 0), (216, 108, 0)]
    put_text(px, mask, lambda y: gold[(y - 3) * len(gold) // 18], H,
             shadows=[(1, 1, (108, 0, 0)), (2, 2, (54, 0, 0))])
    return img


def rgpoa_wall():
    W, H, HOR = 320, 224, 132
    img, px = new(W, H)
    sky = [BLACK, (18, 0, 0), (36, 0, 0), (54, 0, 18), (72, 18, 0), (108, 36, 0), (144, 54, 0)]
    for y in range(HOR):
        c = grad(sky, y, 0, HOR)
        for x in range(W):
            px[x, y] = c
    rnd = random.Random(1772)
    for _ in range(30):
        px[rnd.randrange(W), rnd.randrange(40)] = (108, 72, 72)
    cx, r = 112, 30                                  # the sun setting into the river
    for y in range(HOR - r, HOR):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - HOR) ** 2 <= r * r and not (y > HOR - 12 and y % 4 == 0):
                px[x, y] = (216, 144, 0) if y < HOR - 16 else (216, 108, 0)
    water = [(36, 0, 0), (36, 0, 18), (18, 0, 18), (18, 0, 0)]
    for y in range(HOR, H):
        c = grad(water, y, HOR, H)
        for x in range(W):
            px[x, y] = c
    for y in range(HOR + 2, H, 5):                   # the sun's reflection: broken streaks
        half = max(4, 30 - (y - HOR) // 4)
        for x in range(cx - half, cx + half):
            if (x * 7 + y * 3) % 11 < 7:
                px[x, y] = (180, 108, 0) if y < HOR + 40 else (108, 54, 0)
    for x in range(W):
        px[x, HOR] = (180, 72, 0)
    city = (18, 0, 0)                                # the skyline on the far shore, right side
    rnd = random.Random(4)
    x = 168
    while x < W:
        w, h = rnd.randrange(8, 20), rnd.randrange(8, 30)
        for yy in range(HOR - h, HOR):
            for xx in range(x, min(W, x + w)):
                px[xx, yy] = city
        x += w + rnd.randrange(0, 4)
    for yy in range(HOR - 26, HOR):                  # the Gasometro: long building + tall chimney
        for xx in range(196, 240):
            px[xx, yy] = (36, 0, 0)
    for yy in range(HOR - 22, HOR - 6, 4):
        for xx in range(199, 238, 5):
            px[xx, yy] = px[xx + 1, yy] = (108, 54, 0)
    chimney(px, 232, HOR - 26, 70, 9, 5, (36, 0, 0))
    sail = [(60, HOR + 40)]                          # a small sailboat
    for bx, by in sail:
        for i in range(14):
            for j in range(i // 2 + 1):
                px[bx + j, by - 14 + i] = (108, 72, 54)
        for xx in range(bx - 6, bx + 10):
            px[xx, by + 1] = (54, 18, 0)
            if bx - 4 <= xx < bx + 8:
                px[xx, by + 2] = (54, 18, 0)
    return img


# ---------------------------------------------------------------------------------------- sega16
def sega16_banner():
    W, H = 288, 24
    img, px = new(W, H)
    for y in range(H):
        c = grad([(36, 0, 0), (72, 18, 0), (108, 36, 0), (72, 18, 0)], y, 0, H)
        c = (c[2] // 2, c[1], c[0])                  # blue
        for x in range(W):
            px[x, y] = c
    for y in (4, 9, 14, 19):                         # speed lines
        for x in range(W):
            if (x + y * 7) % 37 < 20:
                px[x, y] = (0, 72, 180)
    mask = text_mask('16-BIT POWER', 3, sx=2, sy=3, adv=17, space=10)
    chrome = [(252, 252, 252), (216, 252, 252), (144, 216, 252), (72, 144, 252), (252, 252, 252),
              (180, 216, 252), (108, 180, 252), (36, 108, 252), (0, 72, 216)]
    put_text(px, mask, lambda y: chrome[(y - 3) * len(chrome) // 18], H,
             shadows=[(1, 1, (252, 180, 0)), (2, 2, (144, 72, 0))])
    return img


def sega16_wall():
    W, H, HOR = 320, 224, 120
    img, px = new(W, H)
    sky = [BLACK, (0, 0, 18), (0, 0, 36), (0, 18, 54), (0, 36, 72)]
    for y in range(HOR):
        c = grad(sky, y, 0, HOR)
        for x in range(W):
            px[x, y] = c
    rnd = random.Random(1988)
    for _ in range(50):
        px[rnd.randrange(W), rnd.randrange(HOR - 10)] = (108, 144, 216) if rnd.random() < 0.7 else (216, 216, 252)
    cx, cy, r = 70, 54, 26                           # a ringed planet
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if d <= r * r:
                band = ((y - cy + r) // 6) % 3
                px[x, y] = [(36, 72, 180), (18, 54, 144), (54, 108, 216)][band]
                if (x - cx + 8) ** 2 + (y - cy + 8) ** 2 < 60:
                    px[x, y] = (108, 180, 252)
    for a in range(0, 3600):
        t = math.radians(a / 10)
        for k, c in ((0, (144, 180, 252)), (2, (72, 108, 216))):
            x = int(cx + (r + 12 + k) * math.cos(t))
            y = int(cy + (r + 12 + k) * 0.28 * math.sin(t))
            if 0 <= x < W and 0 <= y < H and not (math.sin(t) < 0 and (x - cx) ** 2 + (y - cy) ** 2 <= r * r):
                px[x, y] = c
    for y in range(HOR, H):                          # checkerboard floor in perspective
        z = 40.0 / (y - HOR + 4)
        for x in range(W):
            u = (x - W / 2) * z / 6
            v = z * 20
            dark = (int(math.floor(u)) + int(math.floor(v))) % 2
            fade = min(1.0, (y - HOR) / 50)
            c = (0, 18, 72) if dark else (0, 54, 144)
            px[x, y] = tuple(int(ch * (0.4 + 0.6 * fade)) for ch in c)
    for x in range(W):
        px[x, HOR] = (144, 216, 252)
        px[x, HOR + 1] = (36, 108, 216)
    return img


# ---------------------------------------------------------------------------------------- outrun
PALM = ["......##.##.....",
        "....##..#..##...",
        "..##...###...##.",
        ".#....#####....#",
        "#....##.#.##....",
        "....#...#...#...",
        "........#.......",
        ".......##.......",
        ".......#........",
        ".......#........",
        "......##........",
        "......#.........",
        "......#.........",
        ".....##.........",
        ".....#..........",
        ".....#.........."]


def outrun_banner():
    W, H = 288, 24
    img, px = new(W, H)
    sky = [(54, 0, 72), (108, 0, 108), (180, 36, 108), (216, 72, 72), (252, 108, 36)]
    for y in range(H):
        c = grad(sky, y, 0, 21)
        for x in range(W):
            px[x, y] = c
    for x in range(W):
        for y in (21, 22, 23):
            px[x, y] = (36, 0, 54)
        px[x, 21] = (252, 180, 0)
    for x0 in (2, 18, W - 34, W - 18):
        sprite(px, PALM, {'#': (18, 0, 36)}, x0, 5 if x0 in (2, W - 18) else 6)
    mask = text_mask('OUTRUN', 2, sx=3, sy=3, adv=24, space=12)
    hot = [(252, 252, 180), (252, 252, 72), (252, 216, 0), (252, 180, 0), (252, 108, 0), (252, 72, 72),
           (252, 36, 108)]
    put_text(px, mask, lambda y: hot[(y - 2) * len(hot) // 18], H,
             shadows=[(2, 1, (0, 216, 252)), (3, 2, (0, 72, 144))])
    return img


def outrun_wall():
    W, H, HOR = 320, 224, 104
    img, px = new(W, H)
    sky = [(18, 0, 36), (36, 0, 54), (72, 0, 72), (108, 18, 72), (144, 36, 54), (180, 72, 36)]
    for y in range(HOR):
        c = grad(sky, y, 0, HOR)
        for x in range(W):
            px[x, y] = c
    cx, r = 160, 40                                  # striped sun
    for y in range(HOR - r, HOR):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - HOR) ** 2 <= r * r:
                gap = y > HOR - 20 and (y - (HOR - 20)) % 6 < 1 + (y - HOR + 20) // 8
                if not gap:
                    px[x, y] = (252, 216, 36) if y < HOR - 26 else (252, 144, 36) if y < HOR - 12 else (216, 72, 72)
    for x in range(W):                               # the sea on the horizon, left and right
        px[x, HOR] = (252, 180, 108)
    for y in range(HOR + 1, H):                      # sand, then the road
        t = (y - HOR) / (H - HOR)
        half = 4 + t * 190
        for x in range(W):
            dx = abs(x - cx)
            if dx <= half:
                px[x, y] = (54, 36, 72) if int(1 / (t + 0.02) * 3) % 2 else (36, 18, 54)
            elif dx <= half + 2 + t * 14:
                stripe = int(1 / (t + 0.02) * 3) % 2
                px[x, y] = (216, 216, 216) if stripe else (216, 36, 36)
            else:
                px[x, y] = (36, 0, 36) if y % 2 else (54, 0, 54)
        lane = 2 + t * 5
        if int(1 / (t + 0.02) * 2) % 2:
            for x in range(int(cx - lane / 2), int(cx + lane / 2) + 1):
                px[x, y] = (216, 216, 216)
    for x0, y0, s in ((6, 40, 4), (60, 70, 2), (W - 70, 70, 2), (W - 70, 40, 4)):    # palm trees
        sprite(px, PALM if x0 < cx else [r[::-1] for r in PALM], {'#': (18, 0, 18)}, x0, y0, s)
        top = y0 + len(PALM) * s
        for y in range(top, HOR + (12 if s == 4 else 2)):
            for k in range(s):
                xx = x0 + (5 if x0 < cx else 10) * s + k
                if 0 <= xx < W:
                    px[xx, y] = (18, 0, 18)
    return img


# ---------------------------------------------------------------------------------------- retrochimp
CHIMP = ["....WWWWWWWW....",
         "...WWWWWWWWWW...",
         "...WWRRRRRRWW...",
         "..NNNNNNNNNNNN..",
         "..BBBBBBBBBBBB..",
         ".EBBTTTTTTTTBBE.",
         "EEBKKKKTTKKKKBEE",
         "ETBKwwKKKKwwKBTE",
         "ETBKwkKTTKkwKBTE",
         ".EBKKKKTTKKKKBE.",
         "..BTTTTTTTTTTB..",
         "..BTTTnTTnTTTB..",
         "..BTTTTTTTTTTB..",
         "...TTKKKKKKTT...",
         "...BTTTTTTTTB...",
         "....BBBBBBBB...."]
CHIMP_PAL = {'W': (252, 252, 216), 'R': (216, 36, 36), 'N': (36, 36, 72), 'B': (72, 36, 0),
             'E': (108, 54, 18), 'T': (216, 144, 72), 'K': (0, 0, 0), 'w': (252, 252, 252),
             'k': (36, 18, 0), 'n': (108, 54, 18)}
RAINBOW = [(216, 36, 36), (252, 108, 0), (252, 180, 0), (0, 144, 144)]


def retrochimp_banner():
    W, H = 288, 24
    img, px = new(W, H)
    for i, c in enumerate(RAINBOW):                  # 70s stripes behind, top and bottom
        for x in range(W):
            px[x, i] = c
            px[x, H - 1 - i] = RAINBOW[3 - i]
    for y in range(4, H - 4):
        for x in range(W):
            px[x, y] = (18, 18, 36)
    mask = text_mask('RETROCHIMP', 3, sx=2, sy=3, adv=16, space=8)
    cream = [(252, 252, 216), (252, 252, 216), (252, 252, 180), (252, 216, 180)]
    put_text(px, mask, lambda y: cream[(y - 3) * len(cream) // 18], H,
             shadows=[(1, 1, RAINBOW[0]), (2, 2, RAINBOW[1]), (3, 3, RAINBOW[2])])
    sprite(px, CHIMP, CHIMP_PAL, 8, 4)
    sprite(px, CHIMP, CHIMP_PAL, W - 24, 4)
    return img


def retrochimp_wall():
    W, H = 320, 224
    img, px = new(W, H)
    cx, cy = 160, 236                                # 70s rainbow arcs rising from the bottom
    bands = [(0, 72, 72), (144, 108, 0), (144, 54, 0), (108, 18, 18)]
    for y in range(H):
        for x in range(W):
            d = math.hypot(x - cx, (y - cy) * 1.2)
            k = int((d - 120) // 14)
            if 0 <= k < 4:
                px[x, y] = bands[3 - k]
            elif k >= 4 and (k - 4) % 2 == 0 and d < 240:
                px[x, y] = (18, 18, 36)
    rnd = random.Random(83)
    for _ in range(40):
        x, y = rnd.randrange(W), rnd.randrange(80)
        if px[x, y] == BLACK:
            px[x, y] = (108, 108, 72) if rnd.random() < 0.7 else (252, 252, 216)
    sprite(px, CHIMP, CHIMP_PAL, 160 - 32, 150, 4)                    # the chimp, big, in the arcs
    invader = ["..#.....#..", "...#...#...", "..#######..", ".##.###.##.", "###########",
               "#.#######.#", "#.#.....#.#", "...##.##..."]
    sprite(px, invader, {'#': (216, 216, 180)}, 22, 168, 3)
    x0, y0, w, h = W - 76, 176, 60, 28               # a gamepad: rounded body, d-pad, two buttons
    for y in range(y0, y0 + h):
        for x in range(x0, x0 + w):
            dx = min(x - x0, x0 + w - 1 - x)
            dy = min(y - y0, y0 + h - 1 - y)
            if dx + dy >= 4 or (dx >= 2 and dy >= 2):
                px[x, y] = (72, 72, 108) if dy > 2 else (108, 108, 144)
    for k in range(-7, 8):
        for t in range(-2, 2):
            px[x0 + 15 + k, y0 + 14 + t] = (18, 18, 36)
            px[x0 + 15 + t, y0 + 14 + k] = (18, 18, 36)
    for bx, by in ((x0 + 40, y0 + 16), (x0 + 49, y0 + 10)):
        for y in range(by - 3, by + 4):
            for x in range(bx - 3, bx + 4):
                if (x - bx) ** 2 + (y - by) ** 2 <= 10:
                    px[x, y] = (216, 36, 36) if (x - bx) + (y - by) > -3 else (252, 108, 108)
    return img


THEMES = {
    'padrao': (padrao_banner, padrao_wall),
    'rgpoa': (rgpoa_banner, rgpoa_wall),
    'sega16': (sega16_banner, sega16_wall),
    'outrun': (outrun_banner, outrun_wall),
    'retrochimp': (retrochimp_banner, retrochimp_wall),
}


def convert(name, banner_png, wall_png, dim=None):
    pack = ROOT / 'temas' / name / 'EDMD'
    pack.mkdir(parents=True, exist_ok=True)
    wall = [sys.executable, ROOT / 'make_wallpaper.py', wall_png, pack / 'WALL.ART']
    if dim:
        wall += ['--dim', str(dim)]
    for cmd in ([sys.executable, ROOT / 'make_banner.py', banner_png, pack / 'BANNER.ART', '--cores', CORES[name]],
                wall):
        subprocess.run([str(c) for c in cmd], check=True)


def main():
    PREV.mkdir(exist_ok=True)
    only = sys.argv[1:]
    for name, (b, w) in THEMES.items():
        if only and name not in only:
            continue
        bi, wi = b(), w()
        bi.save(PREV / f'{name}_banner.png')
        bi.resize((288 * 3, 24 * 3), Image.NEAREST).save(PREV / f'{name}_banner_3x.png')
        wi.save(PREV / f'{name}_wallpaper.png')
        convert(name, PREV / f'{name}_banner.png', PREV / f'{name}_wallpaper.png')
    if not only or 'synthwave' in only:
        convert('synthwave', HERE / 'banner.png', HERE / 'wallpaper.png')


if __name__ == '__main__':
    main()
