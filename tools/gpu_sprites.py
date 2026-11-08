# -*- coding: utf-8 -*-
"""스테이트 램에서 GPU 스프라이트·사각형 패킷 찾기(읽기 전용) — 조각마다 텍스처 사각형(u,v,w,h)·화면 위치·CLUT·tpage.
   SPRT 0x64~0x67: [색|코드][y<<16|x][clut<<16|v<<8|u][h<<16|w]
   POLY_FT4 0x2C~0x2F: [색|코드][xy0][clut|uv0][xy1][tpage|uv1][xy2][uv2][xy3][uv3]
   python tools/gpu_sprites.py 상태 [u0 v0 u1 v1 (텍스처 범위 거름)]"""
import sys, struct
st = sys.argv[1]
flt = list(map(int, sys.argv[2:6])) if len(sys.argv) > 5 else None
r = open('work/st/%s/ram.bin' % st, 'rb').read()
W = lambda o: struct.unpack_from('<I', r, o)[0]
out = []
for o in range(4, len(r) - 40, 4):
    w0 = W(o); code = w0 >> 24
    if code in (0x64, 0x65, 0x66, 0x67):
        xy = W(o + 4); uvc = W(o + 8); wh = W(o + 12)
        x, y = xy & 0xFFFF, xy >> 16; u, v, clut = uvc & 0xFF, uvc >> 8 & 0xFF, uvc >> 16; w, h = wh & 0xFFFF, wh >> 16
        if not (0 < w <= 256 and 0 < h <= 256 and x < 1024 and y < 512): continue
        if x > 0x8000: continue
        cx, cy = (clut & 0x3F) * 16, clut >> 6
        out.append(('SPRT', o, x, y, u, v, w, h, cx, cy, None))
    elif code in (0x2C, 0x2D, 0x2E, 0x2F):
        p = [W(o + 4 + 4 * k) for k in range(8)]
        xs = [p[0] & 0xFFFF, p[2] & 0xFFFF, p[4] & 0xFFFF, p[6] & 0xFFFF]; ys = [p[0] >> 16, p[2] >> 16, p[4] >> 16, p[6] >> 16]
        us = [p[1] & 0xFF, p[3] & 0xFF, p[5] & 0xFF, p[7] & 0xFF]; vs = [p[1] >> 8 & 0xFF, p[3] >> 8 & 0xFF, p[5] >> 8 & 0xFF, p[7] >> 8 & 0xFF]
        if max(xs) > 1023 or max(ys) > 511: continue
        clut = p[1] >> 16; tp = p[3] >> 16
        cx, cy = (clut & 0x3F) * 16, clut >> 6
        tx, ty = (tp & 0xF) * 64, (tp >> 4 & 1) * 256; depth = tp >> 7 & 3
        out.append(('FT4', o, min(xs), min(ys), min(us), min(vs), max(us) - min(us), max(vs) - min(vs), cx, cy, (tx, ty, depth)))
for e in out:
    t, o, x, y, u, v, w, h, cx, cy, tp = e
    if flt and not (flt[0] <= u < flt[2] and flt[1] <= v < flt[3]): continue
    print('%s ram %06X 화면(%d,%d) uv(%d,%d) %dx%d clut(%d,%d) %s' % (t, o, x, y, u, v, w, h, cx, cy, tp or ''))
print('합계', len(out))
