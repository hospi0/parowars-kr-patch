# -*- coding: utf-8 -*-
"""그림 묶음 펼쳐 보기(읽기 전용): 머리 없는 화소 덩어리를 «stride 128 B(= 16비트 64칸) 쪽» 기준으로 4bpp 회색으로 펼친다.
   큰 덩어리는 256줄 단위 쪽을 옆으로 나란히. → work/gfxdump/<이름>.png
   python tools/gfx_dump.py 파일_또는_덩어리... [--stride 128]"""
import sys, os
import numpy as np
from PIL import Image
args = [a for a in sys.argv[1:] if not a.startswith('--')]
stride = int(sys.argv[sys.argv.index('--stride') + 1]) if '--stride' in sys.argv else 128
os.makedirs('work/gfxdump', exist_ok=True)
for p in args:
    if p == str(stride): continue
    d = open(p, 'rb').read(); n = len(d) // stride
    a = np.frombuffer(d[:n * stride], np.uint8).reshape(n, stride)
    g = (np.stack([a & 15, a >> 4], 2).reshape(n, stride * 2) * 17).astype(np.uint8)
    cols = [g[i:i + 256] for i in range(0, n, 256)]
    h = 256 if len(cols) > 1 else n
    cols = [np.pad(c, ((0, h - c.shape[0]), (0, 4)), constant_values=40) for c in cols]
    per = 6
    rows = [np.hstack(cols[i:i + per] + [np.full((h, cols[0].shape[1]), 40, np.uint8)] * (per - len(cols[i:i + per]))) for i in range(0, len(cols), per)]
    img = np.vstack([np.pad(r, ((0, 6), (0, 0)), constant_values=90) for r in rows])
    name = os.path.basename(p).replace('.bin', '')
    Image.fromarray(img).save('work/gfxdump/%s.png' % name); print(name, img.shape)
