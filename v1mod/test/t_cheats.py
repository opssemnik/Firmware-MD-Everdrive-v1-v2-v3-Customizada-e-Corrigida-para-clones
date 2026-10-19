"""v1: file menu -> Jogar com cheats: loads the game, opens the GG code menu, B starts the game"""
from t_all_lib import *
m = new()
m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
m.press('down'); m.press('a', after=120); m.press('down'); m.press('down'); m.press('a', after=200)
show(m, 'file menu')
m.press('down'); m.press('down'); m.press('a', after=900); show(m, 'Jogar com cheats -> cheat menu')
m.press('b', after=900); print('B ->', m.stopped, lists(m).get('recent'))
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
