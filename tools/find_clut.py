# -*- coding: utf-8 -*-
"""8비트 텍스처의 팔레트(CLUT) 찾기: 텍스처 불투명 조각을 VRAM 의 256색 줄 후보(화면 버퍼 밖)로 칠해 화면 버퍼에서 찾는다.
   python tools/find_clut.py 상태 텍스처x 텍스처y 폭(16비트 단위) 높이"""
import sys
import numpy as np
st, tx, ty, w, h = sys.argv[1], *map(int, sys.argv[2:6])
raw = open('work/st/%s/vram.bin' % st, 'rb').read()
v = np.frombuffer(raw, '<u2').reshape(512, 1024); b = np.frombuffer(raw, np.uint8).reshape(512, 2048)
idx = b[ty:ty + h, tx * 2:(tx + w) * 2].astype(int)
fb = (v[0:240, 0:640] & 0x7FFF)
fbb = fb.astype('<u2').tobytes()
cands = []
for yy in range(4, h - 8, 3):
    for xx in range(8, idx.shape[1] - 8, 5):
        p = idx[yy:yy + 4, xx:xx + 8]
        if (p == 0).any() or len(np.unique(p)) < 6: continue
        cands.append((yy, xx, p))
cands = cands[:3]
res = []
for cy in range(512):
    for cx in range(0, 1024 - 255, 16):
        if cx < 640 and cy < 240: continue
        cl = v[cy, cx:cx + 256] & 0x7FFF
        ok = 0
        for yy, xx, p in cands:
            pat = cl[p]
            if len(np.unique(pat)) < 3: break
            s = fbb.find(pat[0].astype('<u2').tobytes())
            found = False
            while s >= 0:
                if s % 2 == 0:
                    sy, sx = divmod(s // 2, 640)
                    if sx + 8 <= 640 and sy + 4 <= 240 and (fb[sy:sy + 4, sx:sx + 8] == pat).all(): found = True; pos = (sx - xx, sy - yy); break
                s = fbb.find(pat[0].astype('<u2').tobytes(), s + 2)
            if not found: break
            ok += 1
        if ok == len(cands): res.append((cx, cy, pos))
print(st, '팔레트 (x,y) → 화면 위치', res[:6])
