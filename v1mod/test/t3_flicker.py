"""v3: what is on screen, frame by frame, while LEFT/RIGHT switch games in the file menu"""
import sys
import emu3
OS = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\MDOS.ptbr.BIN'
m = emu3.boot(OS, 'sd/sd.img', frames=60, log=print)
m.press('a', after=200); m.press('down'); m.press('a', after=150); m.press('down'); m.press('a', after=150)
m.press('down'); m.press('down'); m.press('a', after=200)
for key in ('right', 'left'):
    m.pad = emu3.emu.PAD[key] if hasattr(emu3.emu, 'PAD') else m.pad
    states = []
    m.press(key, hold=3, after=0)
    for f in range(200):
        m.run(1)
        t = m.text()
        rows = [l.strip() for l in t.splitlines() if l.strip()]
        if 'NOTAS.TXT' in t or '128K' in t:
            s = 'LISTA'
        elif 'Menu Arquivo' in t:
            s = 'menu: ' + (rows[1] if len(rows) > 1 else '')
        else:
            s = 'outro: ' + ' | '.join(rows[:2])
        if not states or states[-1][0] != s:
            states.append([s, 1])
        else:
            states[-1][1] += 1
    print(key, '->', ' ; '.join(f'{s} x{n}' for s, n in states))
