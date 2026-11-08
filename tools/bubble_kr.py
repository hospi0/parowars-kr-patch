# -*- coding: utf-8 -*-
"""보류 그림 ④ — DEMO/PEN4_01 풀린 덩어리 0x4000 쪽(8비트 128×128)의 말풍선 두 개 한글화(배경과 분리된 조각, 안쪽 투명 0).
   실측: 글자 = 남색 테두리 8 + 몸 파랑 단계(2~7). 팔레트 = DEMO/COL_PEN4 10번(미리보기용).
   말풍선 1 안쪽 8~37행·40~119열 «うすしおＦＣ／（警備中）» → «우스시오FC / (경비 중)»
   말풍선 2 안쪽 53~82행·19~119열 «ごうか客船／パロニャン子号» → «호화 여객선 / 파로냥코호»
   python tools/bubble_kr.py → work/미리보기_그림_K/"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_K'; os.makedirs(OUT, exist_ok=True)
FB = bdf.Font('C:/claude/utils/font/Galmuri-v2.40.3/Galmuri11-Bold.bdf')
PAGE = 0x4000
BUBBLES = [((8, 38, 40, 120), ['우스시오FC', '(경비 중)']), ((53, 83, 19, 120), ['호화 여객선', '파로냥코호'])]


def mask(s):
    pts = []; x = 0
    for ch in s:
        p, w = FB.draw(ch); pts += [(x + a, b) for a, b in p]; x += w
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for a, b in pts: m[b - min(ys), a - min(xs)] = True
    return m


def shift(m, dy, dx):
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return o


def build(pg):
    new = pg.copy()
    for (y0, y1, x0, x1), lines in BUBBLES:
        # 말풍선 상자(안쪽 ±6) 안에서 «테두리 고리(상자 가장자리에 닿는 덩어리)»가 아닌 화소 = 원문 글자 → 0
        Y0, Y1, X0, X1 = y0 - 6, y1 + 6, x0 - 6, x1 + 6
        sub = pg[Y0:Y1, X0:X1] > 0; seen = np.zeros_like(sub); frame = np.zeros_like(sub)
        H_, W_ = sub.shape
        for sy in range(H_):
            for sx in range(W_):
                if not sub[sy, sx] or seen[sy, sx]: continue
                comp = []; st = [(sy, sx)]; seen[sy, sx] = True; edge = False
                while st:
                    a, b = st.pop(); comp.append((a, b))
                    if a in (0, H_ - 1) or b in (0, W_ - 1): edge = True
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):          # 4방향(대각선으로 붙은 글자를 테두리로 보지 않게)
                        if True:
                            na, nb = a + da, b + db
                            if 0 <= na < H_ and 0 <= nb < W_ and sub[na, nb] and not seen[na, nb]: seen[na, nb] = True; st.append((na, nb))
                if edge:
                    for a, b in comp: frame[a, b] = True
        blk = new[Y0:Y1, X0:X1]; blk[sub & ~frame] = 0
        H = (y1 - y0) // 2
        for k, t in enumerate(lines):
            m = mask(t); assert m.shape[1] + 2 <= x1 - x0 and m.shape[0] + 2 <= H, (t, m.shape)
            T = np.zeros(new.shape, bool)
            ty = y0 + k * H + (H - m.shape[0]) // 2; tx = x0 + (x1 - x0 - m.shape[1]) // 2
            T[ty:ty + m.shape[0], tx:tx + m.shape[1]] = m
            O = (shift(T, 1, 0) | shift(T, -1, 0) | shift(T, 0, 1) | shift(T, 0, -1) | shift(T, 1, 1) | shift(T, -1, -1) | shift(T, 1, -1) | shift(T, -1, 1)) & ~T
            new[O] = 8
            for y in range(ty, ty + m.shape[0]):
                new[y][T[y]] = 7 - round(4 * (y - ty) / max(1, m.shape[0] - 1))     # 위 밝음(7) → 아래 진함(3)
    return new


if __name__ == '__main__':
    d = open('work/unpk/DATA_DEMO_PEN4_01.BIN@0.bin', 'rb').read()
    pg = np.frombuffer(d[PAGE:PAGE + 16384], np.uint8).reshape(128, 128)
    new = build(pg)
    open(OUT + '/pen4_01_4000_new.bin', 'wb').write(new.astype(np.uint8).tobytes())
    P = np.frombuffer(open('work/files/DATA/DEMO/COL_PEN4.BIN', 'rb').read(), '<u2').astype(int).reshape(16, 256)[10]
    pal = np.stack([(P & 31) << 3, (P >> 5 & 31) << 3, (P >> 10 & 31) << 3], 1).astype(np.uint8)
    def col(x):
        im = pal[x].copy(); im[x == 0] = (90, 110, 90); return im             # 투명 = 회녹색
    s = np.hstack([col(pg[0:96]), np.zeros((96, 4, 3), np.uint8), col(new[0:96])])
    Image.fromarray(s).resize((s.shape[1] * 4, 96 * 4), Image.NEAREST).save(OUT + '/미리보기_말풍선_왼쪽원본_오른쪽한글_v2.png')
    print(OUT)
