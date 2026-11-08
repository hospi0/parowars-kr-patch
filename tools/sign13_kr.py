# -*- coding: utf-8 -*-
"""보류 ③ — DEMO/BACK13A 판다 궁전 간판(BACK13A·13B 두 장) «茶会主義» → «다회주의».
   흰 판 안쪽 = 40~47행 · 143~177열(바탕 1, 글자 남색 30), 142열 = 판 테두리색 2. 글자 = 갈무리7(8줄 안).
   bg_kr.py 출력(BACK13A 없음)과 별개 — work/미리보기_그림_K/BACK13A_new.bin
   python tools/sign13_kr.py"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, bg_kr
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_K'
FONT = sys.argv[1] if len(sys.argv) > 1 else 'Galmuri7'
G = bdf.Font('C:/claude/utils/font/Galmuri-v2.40.3/%s.bdf' % FONT)
TEXT = '다회주의'; Y0, Y1, X0, X1 = 40, 48, 143, 178


def mask(s, gap=0):
    pts = []; x = 0
    for ch in s:
        p, w = G.draw(ch); pts += [(x + a, b) for a, b in p]; x += w + gap
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for a, b in pts: m[b - min(ys), a - min(xs)] = True
    return m


SIGNS = {'BACK13A': 142, 'BACK13B': 78}                          # 간판 판 왼쪽 테두리 열(이어 붙인 화면 x) — 두 장 모두 같은 간판(2차원 검색, 다른 사본 없음)
rows = []
for nm, L in SIGNS.items():
    img, n = bg_kr.load(nm); new = img.copy(); dx = L - 142
    new[Y0:Y1, L] = 2; new[Y0:Y1, X0 + dx:X1 + dx] = 1
    m = mask(TEXT, 1)
    if m.shape[1] > X1 - X0: m = mask(TEXT, 0)
    assert m.shape[0] <= Y1 - Y0 and m.shape[1] <= X1 - X0, m.shape
    oy = Y0 + (Y1 - Y0 - m.shape[0]) // 2; ox = X0 + dx + (X1 - X0 - m.shape[1]) // 2
    new[oy:oy + m.shape[0], ox:ox + m.shape[1]][m] = 30
    print(nm, '글자', m.shape, '자리', oy, ox, '바뀐 화소', int((new != img).sum()))
    pages = np.concatenate([new[:, k * 128:(k + 1) * 128] for k in range(n)], 0)
    open(OUT + '/%s_new.bin' % nm, 'wb').write(pages.astype(np.uint8).tobytes())
    a = bg_kr.colorize(img[24:60, L - 22:L + 58], 'COL_MOA3', 0); b = bg_kr.colorize(new[24:60, L - 22:L + 58], 'COL_MOA3', 0)
    rows.append(np.hstack([a, np.zeros((36, 4, 3), np.uint8), b]))
s = np.vstack([rows[0], np.zeros((4, rows[0].shape[1], 3), np.uint8), rows[1]])
Image.fromarray(s).resize((s.shape[1] * 6, s.shape[0] * 6), Image.NEAREST).save(OUT + '/미리보기_BACK13AB_간판_왼쪽원본_오른쪽한글_%s.png' % FONT)
