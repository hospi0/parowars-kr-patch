# -*- coding: utf-8 -*-
"""보류 그림 ①~③ — 배경 그림 속 글자(DEMO/BACK10A·BACK11A·BACK13A 풀린 덩어리, 8비트 128×128 쪽 3장, 화면 = 쪽을 가로로 이음) 한글화.
   글자 판정 = 지정한 글자 색 번호(바탕과 겹치지 않는 번호)만. 지우기 = 같은 행 가장 가까운 비글자 화소로(천 주름 무늬 유지).
   새 글자 = 나눔고딕 ExtraBold, 원문 줄의 행별 글자색 순서를 높이 비율로 따름. 미리보기 팔레트 = COL_* (색 순환 장면이라 근사).
   python tools/bg_kr.py → work/미리보기_그림_K/"""
import sys, os, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_K'; os.makedirs(OUT, exist_ok=True)
FONT = 'C:/claude/utils/font/nanum-gothic/NanumGothicExtraBold.ttf'
# 이름: (덩어리, 미리보기 팔레트(파일, 줄), 글자 색 번호, [(줄 상자 y0,y1,x0,x1, 한글, 정렬)])
JOBS = {
    'BACK10A': ('COL_PEN4', 10, set(range(105, 109)) | {69, 70},                   # 70·69 = 글자 그림자층(상자 안)
                [(42, 71, 69, 244, '파운드 포 파운드', 'C'), (76, 92, 148, 238, 'in 체스', 'C')]),
    'BACK11A': ('COL_MOA2', 0, set(range(105, 109)) | {69, 70},                   # 70 = 분홍 테두리
                [(45, 61, 46, 250, '파로월드 대항', 'C'), (62, 93, 46, 250, '초 싱＆댄스 대회', 'C')]),
}
OUTLINE = {'BACK11A': 70}


SHADOW = {'BACK10A': 70}


def load(nm):
    a = np.frombuffer(open('work/unpk/DATA_DEMO_%s.BIN@0.bin' % nm, 'rb').read(), np.uint8)
    n = len(a) // 16384
    return np.hstack([a[k * 16384:(k + 1) * 16384].reshape(128, 128) for k in range(n)]).copy(), n


def render(text, h, w):
    for size in range(h + 12, 6, -1):
        f = ImageFont.truetype(FONT, size * 4)
        im = Image.new('L', (size * 4 * (len(text) + 2), size * 8), 0); ImageDraw.Draw(im).text((16, 16), text, font=f, fill=255)
        a = np.array(im.resize((im.width // 4, im.height // 4), Image.BOX)) >= 110
        ys, xs = np.nonzero(a); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if a.shape[0] <= h and a.shape[1] <= w: return a
    raise ValueError(text)


def build(nm):
    img, n = load(nm); f, r, TX, lines = JOBS[nm]
    new = img.copy()
    # 지우기: 줄마다 글자 행·열 범위(+2px)를 합친 영역을 먼저 한꺼번에 — 열마다 그 영역 바로 위·아래 바깥 천 화소로 채움
    #         (줄별로 지우면 아래 줄이 위 줄 글자 행을 «바깥»으로 집어 찌꺼기 줄무늬 — 하스피 «찌꺼기 투성이»)
    E = np.zeros(img.shape, bool)
    for y0, y1, x0, x1, ko, al in lines:
        T = np.isin(img[y0:y1, x0:x1], list(TX)); tr0 = np.nonzero(T.any(1))[0]; tc0 = np.nonzero(T.any(0))[0]
        E[y0 + tr0.min() - 2:y0 + tr0.max() + 3, x0 + tc0.min() - 2:x0 + tc0.max() + 3] = True
    for x in range(img.shape[1]):
        ys = np.nonzero(E[:, x])[0]
        if not len(ys): continue
        for run in np.split(ys, np.nonzero(np.diff(ys) > 1)[0] + 1):
            Y0, Y1 = run[0], run[-1] + 1; top, bot = img[Y0 - 1, x], img[Y1, x]
            for y in range(Y0, Y1): new[y, x] = top if (y - Y0) < (Y1 - Y0) / 2 else bot
    for y0, y1, x0, x1, ko, al in lines:
        box = img[y0:y1, x0:x1]; T = np.isin(box, list(TX))
        prof = []                                                      # 행별 글자색(최다)
        for y in range(box.shape[0]):
            v = box[y][T[y]]
            v = [x for x in v.tolist() if x not in (69, 70)]
            prof.append(collections.Counter(v).most_common(1)[0][0] if len(v) else None)
        rows = [p for p in prof if p is not None]
        # 새 글자
        tr = np.nonzero(T.any(1))[0]; H = tr.max() - tr.min() + 1
        m = render(ko, H, x1 - x0 - 2)
        oy = y0 + tr.min() + (H - m.shape[0]) // 2
        ox = x0 + ((x1 - x0 - m.shape[1]) // 2 if al == 'C' else 1)
        SH = SHADOW.get(nm)
        if SH is not None:                                              # 원문 글자 그림자층(오른쪽 아래)
            Mf = np.zeros(new.shape, bool); Mf[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
            S = np.zeros_like(Mf); S[1:, 1:] = Mf[:-1, :-1]; S |= np.roll(S, 1, 1) & False
            S2 = np.zeros_like(Mf); S2[2:, 2:] = Mf[:-2, :-2]
            new[(S | S2) & ~Mf] = SH
        OL = OUTLINE.get(nm)
        if OL is not None:                                              # 원문 글자 둘레 테두리
            Mf = np.zeros(new.shape, bool); Mf[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
            O = np.zeros_like(Mf)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1): O |= np.roll(np.roll(Mf, dy, 0), dx, 1)
            new[O & ~Mf] = OL
        rows = [p for p in rows if p not in (SHADOW.get(nm), OUTLINE.get(nm))] or rows
        for y in range(m.shape[0]):
            c = rows[min(len(rows) - 1, y * len(rows) // m.shape[0])]
            new[oy + y, ox:ox + m.shape[1]][m[y]] = c
    return img, new, n, f, r


def colorize(x, f, r):
    row = np.frombuffer(open('work/files/DATA/DEMO/%s.BIN' % f, 'rb').read(), '<u2').astype(int).reshape(-1, 256)[r]
    pal = np.stack([(row & 31) << 3, (row >> 5 & 31) << 3, (row >> 10 & 31) << 3], 1).astype(np.uint8)
    return pal[x]


if __name__ == '__main__':
    for nm in (sys.argv[1:] or JOBS):
        img, new, n, f, r = build(nm)
        pages = np.concatenate([new[:, k * 128:(k + 1) * 128] for k in range(n)], 0)
        open(OUT + '/%s_new.bin' % nm, 'wb').write(pages.astype(np.uint8).tobytes())
        s = np.vstack([colorize(img, f, r), np.zeros((4, img.shape[1], 3), np.uint8), colorize(new, f, r)])
        Image.fromarray(s).resize((s.shape[1] * 2, s.shape[0] * 2), Image.NEAREST).save(OUT + '/미리보기_%s_위원본_아래한글_v5.png' % nm)
        print(nm, OUT)
