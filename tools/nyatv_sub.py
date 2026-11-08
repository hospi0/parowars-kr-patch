# -*- coding: utf-8 -*-
"""냥티비 자막 쪽 그림 만들기(2026-11-08, 하스피 «오른쪽 상단 티비 밑에 작게»)
   work/voice/nyatv_ko.tsv → 번호마다 쪽(최대 LINES 줄) 1비트 그림. 글꼴 = 갈무리(BDF 화소 그대로), 글자 + 1px 테두리.
   상자 = 폭 BOX_W(화면 x 216~312, 티비 창 228~299 아래 가운데).
   python tools/nyatv_sub.py [Galmuri9|Galmuri7] → work/voice/sub_<글꼴>/ 미리보기"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, punct
sys.stdout.reconfigure(encoding='utf-8')
FN = sys.argv[1] if len(sys.argv) > 1 else 'Galmuri9'
F = bdf.Font('C:/claude/utils/font/Galmuri-v2.40.3/%s.bdf' % FN)
BOX_W = 96
LINES = 4
LH = {'Galmuri9': 11, 'Galmuri7': 9}[FN]


def width(s):
    return sum(F.draw(c)[1] for c in s)


def wrap(s):
    """BOX_W-2(테두리) 안에 — 끊는 자리 = 띄어쓰기 또는 부호(.,!?~…) 뒤(부호 뒤 공백은 지워져 있음). 한 조각이 한 줄보다 길면 글자 단위."""
    import re
    toks = []                                   # (조각, 앞에 공백?)
    for wi, w in enumerate(s.split(' ')):
        parts = [x for x in re.split(r'(?<=[.,!?~…])', w) if x]
        for pi, x in enumerate(parts): toks.append((x, wi > 0 and pi == 0))
    out, cur = [], ''
    for x, sp in toks:
        t = (cur + (' ' if sp else '') + x) if cur else x
        if width(t) <= BOX_W - 2: cur = t; continue
        if cur: out.append(cur)
        cur = ''
        for ch in x:
            if width(cur + ch) > BOX_W - 2: out.append(cur); cur = ''
            cur += ch
    if cur: out.append(cur)
    return out


def render(line):
    pts = []; x = 0
    for c in line:
        p, w = F.draw(c); pts += [(x + a, b) for a, b in p]; x += w
    return pts, x


def page_img(lines):
    H = LH * len(lines) + 2
    T = np.zeros((H, BOX_W), bool)
    for i, l in enumerate(lines):
        pts, w = render(l); ox = (BOX_W - w) // 2
        ys = [b for a, b in pts]
        for a, b in pts:
            y = 1 + i * LH + b
            if 0 <= y < H and 0 <= ox + a < BOX_W: T[y, ox + a] = True
    O = np.zeros_like(T)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            O |= np.roll(np.roll(T, dy, 0), dx, 1)
    return T, O & ~T


rows = [l.rstrip('\n').split('\t') for l in open('work/voice/nyatv_ko.tsv', encoding='utf-8')][1:]
pages = {}
for k, ko in rows:
    ls = wrap(punct.squeeze(ko))
    pages[int(k)] = [ls[i:i + LINES] for i in range(0, len(ls), LINES)]
cnt = [len(v) for v in pages.values()]
print(FN, '줄 폭', BOX_W, '쪽 수 분포', {n: cnt.count(n) for n in sorted(set(cnt))}, '총 쪽', sum(cnt))
OUT = 'work/voice/sub_%s' % FN; os.makedirs(OUT, exist_ok=True)
# 미리보기: 번호 1~8 쪽들 (반투명 검정 바탕 위 흰 글자 + 검은 테두리 가정)
tiles = []
for k in list(range(1, 9)):
    for pg in pages[k]:
        T, O = page_img(pg)
        im = np.zeros(T.shape + (3,), np.uint8); im[:] = (40, 40, 60); im[O] = (0, 0, 0); im[T] = (255, 255, 255)
        tiles.append(np.pad(im, ((2, 2), (2, 2), (0, 0)), constant_values=90))
Hm = max(t.shape[0] for t in tiles)
tiles = [np.pad(t, ((0, Hm - t.shape[0]), (0, 0), (0, 0))) for t in tiles]
g = np.vstack([np.hstack(tiles[i:i + 6] + [np.zeros_like(tiles[0])] * (6 - len(tiles[i:i + 6]))) for i in range(0, len(tiles), 6)])
Image.fromarray(g).resize((g.shape[1] * 3, g.shape[0] * 3), Image.NEAREST).save(OUT + '/미리보기_쪽_1-8번.png')
print(OUT)
