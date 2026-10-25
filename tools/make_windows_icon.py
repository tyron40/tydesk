from PIL import Image,ImageDraw
from pathlib import Path
Path('build').mkdir(exist_ok=True)
im=Image.new('RGBA',(256,256),'#0d1420');d=ImageDraw.Draw(im)
d.rounded_rectangle((18,30,238,190),radius=24,fill='#48dfbd')
d.rounded_rectangle((35,47,221,169),radius=12,fill='#152131')
d.rectangle((110,190,146,219),fill='#48dfbd');d.rounded_rectangle((72,215,184,233),radius=8,fill='#48dfbd')
d.line((72,86,96,109,72,133),fill='white',width=12);d.line((116,133,172,133),fill='white',width=12)
im.save('build/tydesk.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
