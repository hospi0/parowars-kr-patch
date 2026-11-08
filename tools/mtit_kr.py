# -*- coding: utf-8 -*-
"""묶음 F — 이벤트 큰 제목 12장(DATA/MTIT/MTIT1~12.BIN) 한글화 → work/미리보기_그림_F/(새 파일 + 글자판 미리보기).
   파일 구조(실측): [0:8192] 4비트 128×128 그림(VRAM (896,0)에 행 그대로) · [8192:8448] 팔레트 8개(게임은 0번 = VRAM (512,241), 나머지는 색 순환)
                   · [8448:] u32 조각 수 + 조각마다 u32×6 (화면 x, y, 폭, 높이, u, v) — 원문은 큰 글자 줄(128 폭에서 접힘) + 후리가나 조각.
   한글: 줄마다 한 장으로 그려 128px 조각으로 잘라 그림판 24줄 띠(v=0,24,…)에 넣고, 배치표를 새로 씀(조각 수 ≤ 원문, 남는 칸 0, 줄마다 화면 가운데,
         후리가나 없음). 글자 = 나눔고딕 ExtraBold 기울임(전단), 색 = 원문 실측: 위 절반 흰 1 + 획 아래 그림자 8, 아래 절반 행마다 2→11 그라데이션.
   python tools/mtit_kr.py"""
import sys, os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_F'; os.makedirs(OUT, exist_ok=True)
FONT = 'C:/claude/utils/font/nanum-gothic/NanumGothicExtraBold.ttf'
TITLES = {1: ['프랜시스＝페드로 섬에', '잠들어라!'], 2: ['2월 7일에 포효하라!'], 3: ['북방의 금괴', '내가 접수한데이～!'],
          4: ['거대 제국의 가브리로부터'], 5: ['최저 대해전'], 6: ['판판 요새만은', '날려 버려라!'], 7: ['친한 사이에도 전쟁이다!'],
          8: ['문어의 영광!'], 9: ['빅 더 전격 작전'], 10: ['이걸로 끝이다!', '전설의 라스트 배틀'], 11: ['초 싱＆댄스 해전'],
          12: ['라이라이현 이상한 얼굴 사건']}
SCREEN_W = 320


def line_img(text, maxw=300):
    """24줄 띠 하나: 글자 높이 18(행 2~19 근처) 기울임, 색은 원문 규칙."""
    for size in range(26, 10, -1):
        f = ImageFont.truetype(FONT, size * 4)
        im = Image.new('L', (size * 4 * (len(text) + 2), size * 8), 0); ImageDraw.Draw(im).text((16, 16), text, font=f, fill=255)
        im = im.transform(im.size, Image.AFFINE, (1, 0.22, -size * 0.9, 0, 1, 0), Image.BILINEAR)     # 기울임(원문처럼 오른쪽으로)
        a = np.array(im.resize((im.width // 4, im.height // 4), Image.BOX)) >= 120
        ys, xs = np.nonzero(a); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if a.shape[0] <= 21 and a.shape[1] <= maxw: break
    H = 24; T = np.zeros((H, a.shape[1] + 2), bool); top = 1 + (21 - a.shape[0]) // 2
    T[top:top + a.shape[0], 1:1 + a.shape[1]] = a
    c = np.zeros(T.shape, np.uint8)
    for y in range(H):
        c[y][T[y]] = 1 if y < 12 else min(11, 2 + (y - 12))
    S = np.zeros_like(T); S[1:] = T[:-1]; S &= ~T; S[12:] = False             # 위 절반: 획 바로 아래 그림자 8
    c[S] = 8
    return c


def build(k):
    d = bytearray(open('work/files/DATA/MTIT/MTIT%d.BIN' % k, 'rb').read())
    tab = 8192 + 256
    n0 = struct.unpack_from('<I', d, tab)[0]
    ents0 = [struct.unpack_from('<6I', d, tab + 4 + 24 * i) for i in range(n0)]
    ys = sorted({e[1] for e in ents0 if e[3] == 24})                       # 원문 큰 글자 줄 화면 y
    lines = TITLES[k]; assert len(lines) <= len(ys), (k, lines, ys)
    px = np.zeros((128, 128), np.uint8); ents = []; v = 0
    for li, t in enumerate(lines):
        c = line_img(t)
        W = c.shape[1]; x0 = (SCREEN_W - W) // 2
        for u0 in range(0, W, 128):
            w = min(128, W - u0); assert v + 24 <= 128, (k, '그림판 넘침')
            px[v:v + 24, 0:w] = c[:, u0:u0 + w]
            ents.append((x0 + u0, ys[li], (w + 7) // 8 * 8, 24, 0, v)); v += 24
    assert len(ents) <= n0, (k, len(ents), n0)
    a = (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()
    d[0:8192] = a
    struct.pack_into('<I', d, tab, len(ents))
    for i in range(n0):
        e = ents[i] if i < len(ents) else (0, 0, 0, 0, 0, 0)
        struct.pack_into('<6I', d, tab + 4 + 24 * i, *e)
    return bytes(d), px, ents


def sheet(d):
    a = np.frombuffer(d[:8192], np.uint8).reshape(128, 64); px = np.zeros((128, 128), np.uint8)
    px[:, 0::2] = a & 15; px[:, 1::2] = a >> 4
    pal = np.frombuffer(d[8192:8224], '<u2').astype(int)
    im = np.zeros((128, 128, 3), np.uint8); im[:] = (40, 90, 40)
    for i in range(1, 16): c = pal[i]; im[px == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return im


if __name__ == '__main__':
    rows = []
    for k in range(1, 13):
        orig = open('work/files/DATA/MTIT/MTIT%d.BIN' % k, 'rb').read()
        new, px, ents = build(k)
        assert len(new) == len(orig)
        open(OUT + '/MTIT%d_new.BIN' % k, 'wb').write(new)
        print(k, TITLES[k], ents)
        rows.append(np.hstack([sheet(orig), np.zeros((128, 4, 3), np.uint8), sheet(new), np.zeros((128, 12, 3), np.uint8)]))
    g = np.vstack([np.hstack(rows[i:i + 3]) for i in range(0, 12, 3)])
    Image.fromarray(g).resize((g.shape[1] * 2, g.shape[0] * 2), Image.NEAREST).save(OUT + '/미리보기_글자판_원본과한글_12장_v2.png')
    print(OUT)
