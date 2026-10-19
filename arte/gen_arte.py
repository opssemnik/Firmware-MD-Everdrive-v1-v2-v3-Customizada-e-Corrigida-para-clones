"""
Original retro art for the SD card (free to share, no third-party characters or logos):
  - wallpaper.png (320x224): dark synthwave night - banded sky, stars, striped sun, mountains and
    a perspective grid. Dark on purpose: it sits behind the game list text.
  - banner.png (288x24): "RETROGAMER POA" in the OS font, chrome gradient, over a small sunset.
Convert with ../make_wallpaper.py and ../make_banner.py (WALL.ART / BANNER.ART in /EDMD).
"""
import math
import random
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent

FONT = {    # the OS 8x8 font, columns 1..7 of rows 1..6 (same letters as the built-in banner)
    'R': ["#####..", "##..##.", "##..##.", "#####..", "##.##..", "##..##."],
    'E': ["######.", "##.....", "#####..", "##.....", "##.....", "######."],
    'T': ["######.", "..##...", "..##...", "..##...", "..##...", "..##..."],
    'O': [".####..", "##..##.", "##..##.", "##..##.", "##..##.", ".####.."],
    'G': [".#####.", "##.....", "##.....", "##.###.", "##..##.", ".#####."],
    'A': ["..##...", ".####..", "##..##.", "##..##.", "######.", "##..##."],
    'M': ["##...##", "###.###", "#######", "##.#.##", "##...##", "##...##"],
    'P': ["#####..", "##..##.", "##..##.", "#####..", "##.....", "##....."],
}


def wallpaper():
    W, H, HOR = 320, 224, 152
    sky = [(0, 0, 36), (18, 0, 54), (36, 0, 72), (54, 0, 90), (72, 0, 90)]    # bands of 32 px
    img = Image.new('RGB', (W, H))
    px = img.load()
    for y in range(HOR):
        band = sky[min(len(sky) - 1, y // 32)]
        for x in range(W):
            px[x, y] = band
    rnd = random.Random(1987)
    for _ in range(40):                                  # stars, upper sky only
        x, y = rnd.randrange(W), rnd.randrange(96)
        px[x, y] = (108, 108, 144) if rnd.random() < 0.7 else (180, 180, 216)
    cx, cy, r = 160, 128, 44                             # striped sun, cut by the horizon
    sun = [(144, 72, 0), (144, 54, 36), (108, 36, 72), (90, 0, 90)]
    for y in range(cy - r, HOR):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                k = (y - (cy - r)) * len(sun) // (2 * r)
                gap = y > cy - 8 and (y - (cy - 8)) % 8 < 1 + (y - cy + 8) // 10
                if not gap:
                    px[x, y] = sun[min(k, len(sun) - 1)]
    for x in range(W):                                   # mountains in front of the sun
        h = 14 + 10 * math.sin(x / 23.0) + 7 * math.sin(x / 9.0 + 1.3) + 5 * math.sin(x / 41.0 + 2)
        if 110 < x < 210:
            h -= 10                                       # a valley that shows the sun
        for y in range(max(0, int(HOR - h)), HOR):
            px[x, y] = (18, 0, 36)
    floor, line = (18, 0, 36), (108, 0, 108)
    for y in range(HOR, H):                              # perspective grid
        for x in range(W):
            px[x, y] = floor
    for x in range(W):
        px[x, HOR] = (144, 36, 144)
    z = 1.0
    while True:                                          # horizontal lines, closer together far away
        y = HOR + int(6 / z * 6)
        if y >= H:
            break
        for x in range(W):
            px[x, y] = line
        z *= 0.62
    for k in range(-14, 15):                             # lines to the vanishing point
        x0 = cx + k * 34
        for y in range(HOR + 1, H):
            t = (y - HOR) / (H - HOR)
            x = int(cx + (x0 - cx) * t)
            if 0 <= x < W:
                px[x, y] = line
    return img


def banner():
    W, H = 288, 24
    img = Image.new('RGB', (W, H))
    px = img.load()
    sky = [(18, 0, 54), (36, 0, 72), (72, 0, 90), (108, 0, 108)]                 # bands of 6 px
    for y in range(H):
        for x in range(W):
            px[x, y] = sky[min(3, y // 6)]
    rnd = random.Random(42)
    for _ in range(18):
        px[rnd.randrange(W), rnd.randrange(10)] = (180, 180, 216)
    for cx in (24, W - 25):                              # two small striped suns at the ends
        for y in range(8, 21):
            for x in range(cx - 9, cx + 10):
                if (x - cx) ** 2 + (y - 18) ** 2 <= 81 and not (y > 14 and y % 2):
                    px[x, y] = (252, 180, 0) if y < 13 else (252, 108, 36) if y < 16 else (216, 36, 108)
    for x in range(W):                                   # horizon + grid stripe
        px[x, 20] = (216, 0, 216)
        for y in (21, 22, 23):
            px[x, y] = (54, 0, 72)
        if (x - W // 2) % 12 == 0:
            px[x, 22] = px[x, 23] = (144, 0, 144)
    text = "RETROGAMER POA"
    mask = set()
    x0 = (W - (13 * 16 + 8 - 2)) // 2
    for ch in text:
        if ch == ' ':
            x0 += 8
            continue
        for ry, row in enumerate(FONT[ch]):
            for rx, p in enumerate(row):
                if p == '#':
                    for dy in (0, 1):
                        for dx in (0, 1):
                            mask.add((x0 + rx * 2 + dx, 3 + ry * 2 + dy))
        x0 += 16
    for (x, y) in mask:                                  # drop shadow
        if (x + 1, y + 1) not in mask:
            px[x + 1, y + 1] = (54, 0, 72)
    for (x, y) in mask:                                  # outline
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q not in mask and 0 <= q[1] < H:
                    px[q] = (0, 0, 0)
    chrome = [(216, 252, 252), (216, 252, 252), (144, 216, 252), (144, 216, 252), (252, 252, 252), (252, 180, 216),
              (252, 108, 180), (252, 108, 180), (252, 180, 0), (252, 180, 0), (252, 108, 36), (252, 108, 36)]
    for (x, y) in mask:
        px[x, y] = chrome[y - 3]
    return img


if __name__ == '__main__':
    wallpaper().save(HERE / 'wallpaper.png')
    banner().save(HERE / 'banner.png')
    banner().resize((288 * 3, 24 * 3), Image.NEAREST).save(HERE / 'banner_3x.png')
    print('ok')
