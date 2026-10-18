from PIL import Image
from t_all_lib import *
m = new()
[m.press('down') for _ in range(8)]
shots = []
for t in range(4):
    if t:
        m.press('a', after=300)
    m.screen(f'shot_theme_{t}.png'); shots.append(Image.open(f'shot_theme_{t}.png'))
print('stopped:', m.stopped, 'theme in flash:', lists(m).get('theme'))
sheet = Image.new('RGB', (1280, 896))
for i, im in enumerate(shots):
    sheet.paste(im, ((i % 2) * 640, (i // 2) * 448))
sheet.save('shot_themes.png')
