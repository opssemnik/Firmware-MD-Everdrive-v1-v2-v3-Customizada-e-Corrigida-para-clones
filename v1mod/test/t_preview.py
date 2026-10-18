from t_all_lib import *
m = new()
loads = []
m.mu.hook_add(emu.UC_HOOK_CODE, lambda mu, a, s, u: loads.append(m.vbl), begin=0xFF324E, end=0xFF324E)  # osFind = art lookup
def go_usa():
    m.press('down'); m.press('a', after=120); m.press('down'); m.press('a', after=120)
    m.press('down'); m.press('a', after=120)
go_usa()
m.run(60); print('resting on 1st game for 60 frames -> art lookups:', len(loads)); m.screen('shot_prev_1.png')
show(m, 'list with preview (1st game)')
# quick scrolling: taps 8 frames apart must not trigger lookups
n0 = len(loads)
for _ in range(3): m.press('down', hold=3, after=8)
print('quick taps -> new lookups:', len(loads) - n0)
show(m, 'after quick taps (no art, rows intact)')
m.run(60); show(m, 'rest on Game Genie'); m.screen('shot_prev_2.png')
# press during load: cursor moves, art not drawn
m.press('up', hold=3, after=20)       # 20 frames: below threshold
m.press('up', hold=3, after=60); show(m, 'rest on Columns'); m.screen('shot_prev_3.png')
n1 = len(loads)
m.press('a', after=200); print('A after preview -> extra lookups (cache):', len(loads) - n1, '| stopped', m.stopped)
show(m, 'file menu from cache'); m.screen('shot_prev_filemenu.png')
m.press('b', after=200); show(m, 'back to list')
print('\n'.join(l for l in logs if l.startswith('!!')) or 'no emulator errors')
