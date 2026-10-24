"""
Theme for the Maddrugamers channel (youtube.com/@maddrugamers): original pixel art in the channel's
style (black, a chunky bright green "MADDRUGAMERS" with a dark green 3D shadow, an arcade joystick
with a red button), no copied images.
  - maddruga/banner.png (288x24) and maddruga/wallpaper.png (320x224)
  - ../temas/maddrugamers/EDMD/BANNER.ART (with the theme colours) and WALL.ART, via make_banner.py
    and make_wallpaper.py

    python arte/gen_maddruga.py
"""
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent
OUT = HERE / 'maddruga'
PACK = HERE.parent / 'temas' / 'maddrugamers' / 'EDMD'

# theme colours (Mega Drive 0BGR): backdrop, menu bar, bar shadow, text, dim text, accent (gold text)
CORES = '000,0A0,040,EEE,4C4,2E4'

FONT = {    # 7x6, the OS font style (as gen_arte.py)
    'M': ["##...##", "###.###", "#######", "##.#.##", "##...##", "##...##"],
    'A': ["..##...", ".####..", "##..##.", "##..##.", "######.", "##..##."],
    'D': ["#####..", "##..##.", "##..##.", "##..##.", "##..##.", "#####.."],
    'R': ["#####..", "##..##.", "##..##.", "#####..", "##.##..", "##..##."],
    'U': ["##..##.", "##..##.", "##..##.", "##..##.", "##..##.", ".####.."],
    'G': [".#####.", "##.....", "##.....", "##.###.", "##..##.", ".#####."],
    'E': ["######.", "##.....", "#####..", "##.....", "##.....", "######."],
    'S': [".#####.", "##.....", ".####..", "....##.", "....##.", "#####.."],
}

BLACK = (0, 0, 0)
GREEN = [(144, 252, 108), (72, 252, 36), (36, 216, 0), (36, 216, 0), (0, 180, 0), (0, 180, 0),
         (0, 144, 0), (0, 144, 0)]                  # top to bottom of a letter
SHADOW = (0, 72, 0)
SHADOW2 = (0, 36, 0)


def joystick(px, x0, y0, w=20):
    """an arcade joystick seen from the front-left: grey base, black stick, red button"""
    base = [(180, 180, 180), (108, 108, 108), (72, 72, 72)]
    for y in range(y0 + 13, y0 + 20):              # base, lighter on top
        for x in range(x0, x0 + w):
            px[x, y] = base[0] if y == y0 + 13 else base[1] if y < y0 + 18 else base[2]
    for y in range(y0 + 15, y0 + 17):              # red button with a highlight
        for x in range(x0 + 2, x0 + 6):
            px[x, y] = (252, 36, 36) if y == y0 + 15 else (180, 0, 0)
    px[x0 + 3, y0 + 15] = (252, 180, 180)
    sx = x0 + 12
    for y in range(y0 + 4, y0 + 14):               # stick
        px[sx, y] = (144, 144, 144)
        px[sx + 1, y] = (72, 72, 72)
    for y in range(y0, y0 + 5):                    # ball on top
        for x in range(sx - 2, sx + 4):
            if (x - sx - 0.5) ** 2 + (y - y0 - 2) ** 2 <= 7:
                px[x, y] = (72, 72, 72)
    px[sx - 1, y0 + 1] = (216, 216, 216)
    px[sx, y0 + 1] = (144, 144, 144)
    for x in range(sx - 3, sx + 5):                # dark ring around the stick
        px[x, y0 + 13] = (36, 36, 36)


def banner():
    W, H = 288, 24
    img = Image.new('RGB', (W, H), BLACK)
    px = img.load()
    rnd = random.Random(7)
    for y in range(H):                              # faint scanlines + a few stars
        if y % 3 == 2:
            for x in range(W):
                px[x, y] = (0, 18, 0)
    for _ in range(14):
        px[rnd.randrange(W), rnd.randrange(H)] = (36, 108, 36)
    text = 'MADDRUGAMERS'
    TOP = 2                                         # letters: 6 font rows x 3 px = rows 2-19
    adv = 16                                        # 7 columns x 2 px + 2
    x0 = (W - adv * len(text) + 1) // 2
    mask = set()
    for i, ch in enumerate(text):
        for ry, row in enumerate(FONT[ch]):
            for rx, p in enumerate(row):
                if p == '#':
                    for dy in (0, 1, 2):
                        for dx in (0, 1):
                            mask.add((x0 + i * adv + rx * 2 + dx, TOP + ry * 3 + dy))
    for d, c in ((3, SHADOW2), (2, SHADOW), (1, SHADOW)):   # extruded 3D shadow, down-right
        for (x, y) in mask:
            q = (x + d, y + d)
            if q not in mask and q[1] < H:
                px[q] = c
    for (x, y) in mask:                             # black outline around the letters + shadow
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if q not in mask and 0 <= q[1] < H and px[q] not in (SHADOW, SHADOW2):
                    px[q] = BLACK
    for (x, y) in mask:
        px[x, y] = GREEN[(y - TOP) * len(GREEN) // 18]
    joystick(px, 4, 2)
    joystick(px, W - 24, 2)
    return img


def wallpaper():
    W, H, HOR = 320, 224, 150
    img = Image.new('RGB', (W, H), BLACK)
    px = img.load()
    rnd = random.Random(1983)
    glow = [(0, 18, 0), (0, 36, 0), (18, 54, 18), (36, 72, 36)]
    for y in range(HOR):                            # night: black, then a green glow towards the horizon
        k = (y - 86) // 16
        c = glow[k] if k >= 0 else BLACK
        for x in range(W):
            if k < 0 or (x + y) % 2 == 0 or k == 0 or (y - 86) % 16 >= 4:
                px[x, y] = c
            else:
                px[x, y] = glow[k - 1]              # dithered band edges
    for _ in range(60):
        x, y = rnd.randrange(W), rnd.randrange(100)
        px[x, y] = (72, 144, 72) if rnd.random() < 0.7 else (180, 252, 180)
    for x in range(W):                              # pixel hills against the glow
        h = 8 + abs((x // 4) % 14 - 7) + (10 - abs(x - 90) // 4 if abs(x - 90) < 40 else 0)             + (14 - abs(x - 40) // 3 if abs(x - 40) < 42 else 0)
        for y in range(HOR - h, HOR):
            px[x, y] = (0, 18, 0)
    floor, line = (0, 18, 0), (0, 108, 0)
    for y in range(HOR, H):
        for x in range(W):
            px[x, y] = floor
    for x in range(W):
        px[x, HOR] = (36, 144, 36)
    z = 1.0
    while True:                                     # perspective grid, green
        y = HOR + int(6 / z * 6)
        if y >= H:
            break
        for x in range(W):
            px[x, y] = line
        z *= 0.62
    cx = W // 2
    for k in range(-14, 15):
        x0 = cx + k * 34
        for y in range(HOR + 1, H):
            t = (y - HOR) / (H - HOR)
            x = int(cx + (x0 - cx) * t)
            if 0 <= x < W:
                px[x, y] = line
    big = Image.new('RGB', (28, 22), BLACK)        # a big joystick standing on the grid, centre right
    joystick(big.load(), 2, 1, 24)
    big = big.resize((28 * 3, 22 * 3), Image.NEAREST)
    bx, by = 214, HOR - 50
    bp = big.load()
    for y in range(big.height):
        for x in range(big.width):
            if bp[x, y] != BLACK:
                px[bx + x, by + y] = bp[x, y]
    return img


def main():
    OUT.mkdir(exist_ok=True)
    PACK.mkdir(parents=True, exist_ok=True)
    banner().save(OUT / 'banner.png')
    banner().resize((288 * 3, 24 * 3), Image.NEAREST).save(OUT / 'banner_3x.png')
    wallpaper().save(OUT / 'wallpaper.png')
    root = HERE.parent
    for cmd in ([sys.executable, root / 'make_banner.py', OUT / 'banner.png', PACK / 'BANNER.ART', '--cores', CORES],
                [sys.executable, root / 'make_wallpaper.py', OUT / 'wallpaper.png', PACK / 'WALL.ART']):
        subprocess.run([str(c) for c in cmd], check=True)


if __name__ == '__main__':
    main()
