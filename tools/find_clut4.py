# -*- coding: utf-8 -*-
"""4비트 텍스처의 16색 팔레트 찾기: 텍스처 쪽(VRAM tx,ty, 폭 w 하프워드=4w px, 높이 h)의 불투명 4×8 조각을
   VRAM 16색 줄 후보(화면 버퍼 320×240×2 밖)로 칠해 화면 버퍼(0~640×0~240)에서 찾는다. 찾으면 (팔레트 x,y, 화면 위치) 출력.
   python tools/find_clut4.py 상태 tx ty w h [조각수]"""
import sys
import numpy as np
st, tx, ty, w, h = sys.argv[1], *map(int, sys.argv[2:6])
NC = int(sys.argv[6]) if len(sys.argv) > 6 else 3
raw = open('work/st/%s/vram.bin' % st, 'rb').read()
v = np.frombuffer(raw, '<u2').reshape(512, 1024); b = np.frombuffer(raw, np.uint8).reshape(512, 2048)
sub = b[ty:ty + h, tx * 2:(tx + w) * 2]
idx = np.stack([sub & 15, sub >> 4], 2).reshape(h, w * 4).astype(int)
fb = (v[0:240, 0:640] & 0x7FFF); fbb = fb.astype('<u2').tobytes()
cands = []
for yy in range(0, h - 4, 2):
    for xx in range(0, idx.shape[1] - 8, 3):
        p = idx[yy:yy + 4, xx:xx + 8]
        if (p == 0).any() or len(np.unique(p)) < 4: continue
        if all(abs(yy - c[0]) > 6 or abs(xx - c[1]) > 20 for c in cands): cands.append((yy, xx, p))
    if len(cands) >= NC: break
res = []
for cy in range(512):
    for cx in range(0, 1024, 16):
        if cx < 640 and cy < 240: continue
        cl = v[cy, cx:cx + 16] & 0x7FFF
        if len(np.unique(cl)) < 4: continue
        ok = 0; pos = None
        for yy, xx, p in cands:
            pat = cl[p]; key = pat[0].astype('<u2').tobytes(); s = fbb.find(key); found = False
            while s >= 0:
                if s % 2 == 0:
                    sy, sx = divmod(s // 2, 640)
                    if sx + 8 <= 640 and sy + 4 <= 240 and (fb[sy:sy + 4, sx:sx + 8] == pat).all(): found = True; pos = (sx - xx, sy - yy); break
                s = fbb.find(key, s + 2)
            if not found: break
            ok += 1
        if ok == len(cands): res.append((cx, cy, pos))
print(st, '조각', len(cands), '팔레트 (x,y) → 텍스처 왼쪽 위의 화면 위치', res[:8])
