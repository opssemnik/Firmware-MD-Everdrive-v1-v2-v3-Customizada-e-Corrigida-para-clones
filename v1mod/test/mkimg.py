import shutil, struct, subprocess, sys
from pathlib import Path
S = Path(sys.argv[1]); R = Path(r'C:\Users\Antonio\reverse-engineer-anything\mega-genesis\ROMS')
st = S / 'stage'; shutil.rmtree(st, ignore_errors=True)
picks = {'ROMS/USA': '01 USA Games (A-M)', 'ROMS/JAP': '05 JAP Games (A-S)'}
def h(p):
    s = p.read_bytes()[:512]; v = 0
    for w in struct.unpack('>256H', s.ljust(512, b'\0')): v = ((v << 5 | v >> 27) & 0xFFFFFFFF) ^ w
    return f'{v:08X}'
(st / 'EDMD/ART').mkdir(parents=True); (st / 'EDMD/SAVE').mkdir(parents=True)
for d, folder in picks.items():
    (st / d).mkdir(parents=True, exist_ok=True)
    allp = sorted((R / folder).glob('*.bin'), key=lambda p: (p.stat().st_size, p.name))
    withart = [p for p in allp if (R / 'EDMD/ART' / (h(p) + '.ART')).exists()][:4 if d.endswith('USA') else 2]
    noart = [p for p in allp if p not in withart][:1]
    for p in withart + noart:
        shutil.copy(p, st / d / p.name)
        art = R / 'EDMD/ART' / (h(p) + '.ART')
        print(d, p.name, p.stat().st_size, h(p), 'ART' if art.exists() else '-')
        if art.exists(): shutil.copy(art, st / 'EDMD/ART' / art.name)
(st / 'LEIAME.TXT').write_text('teste\n')
(st / 'ROMS/USA/notas.txt').write_text('nao e rom\n')
