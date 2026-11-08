# -*- coding: utf-8 -*-
"""묶음 E — 세계지도 지명 21개(DEMO/WMAP0 풀린 덩어리 0, 8비트 128px 폭, 16 px 줄마다 지명 하나, VRAM (768,0), 팔레트 (0,241)) 한글화.
   실측: 지명 = 회색 단계(0xE1 흰 → 0xEF 어두움) 부드러운 글씨, 줄 안 0~W(8의 배수) = 지명 칸(바탕 0 = 투명), W~127 = 255(검정, 칸 밖 — 보존).
   게임은 지명마다 W×15 사각형으로 찍음(상태 42: プリンス王国·ペン太郎王国 = 64×15 = W). 한글 = 갈무리9 흰 몸(0xE1)+오른쪽 아래 그림자(0xEC), 칸 W 안.
   python tools/wmap_kr.py → work/미리보기_그림_E/"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_E'; os.makedirs(OUT, exist_ok=True)
GD = 'C:/claude/utils/font/Galmuri-v2.40.3/'
G9 = bdf.Font(GD + 'Galmuri9.bdf')
NAMES = ['그레이트＝펭쿠로 섬', '프린스 왕국', '러블리 연방 합중국', '이녀석＆저녀석 연방 공화국', '펭타로 왕국', '푸린푸린H 섬',
         '친코코＝칸 왕국', '핀핀 연봉 왕국', '2월 7일 섬', '냥 대륙', '멍멍국', '구웨이트 지방', '류견 지방', '아카시야랜드 공화국',
         '판다 다회주의 수민 공화국', '미카엘 제국', '수남성', '모아이 제도 수장국', '립체이서 섬', '프랜시스＝페드로 섬', '존 냥지로령']
BODY, SHADOW = 0xE1, 0xEC


def shift(m, dy, dx):
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return o


def mask(s, sq=0):
    pts = []; x = 0
    for ch in s:
        if ch == ' ': x += 3; continue
        p, w = G9.draw(ch); pts += [(x + a, b) for a, b in p]; x += w - sq
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((16, max(xs) + 1), bool)
    for a, b in pts: m[b, a] = True                 # 갈무리9 y = 윗선 기준(한글 2~10)
    return m


def build(a):
    new = a.copy(); info = []
    for r, ko in enumerate(NAMES):
        band = a[r * 16:r * 16 + 16]
        k = np.nonzero((band == 255).all(0))[0]; W = int(k.min()) if len(k) else 128
        for sq in (0, 1):
            m = mask(ko, sq)
            if m.shape[1] + 4 <= W: break
        assert m.shape[1] + 4 <= W, (ko, m.shape[1], W)
        T = np.zeros((16, 128), bool); T[1:16, 3:3 + m.shape[1]] = m[0:15]       # 글자 행 3~11(원문 3~12)
        S = shift(T, 1, 1) & ~T
        blk = np.zeros((16, W), np.uint8); blk[S[:, :W]] = SHADOW; blk[T[:, :W]] = BODY
        new[r * 16:r * 16 + 16, :W] = blk
        info.append((ko, '폭 %d/%d' % (m.shape[1] + 4, W), '자간-%d' % sq))
    return new, info


if __name__ == '__main__':
    d = open('work/unpk/DATA_DEMO_WMAP0.BIN@0.bin', 'rb').read()
    a = np.frombuffer(d[:21 * 16 * 128], np.uint8).reshape(-1, 128).astype(np.uint8)
    new, info = build(a)
    for i in info: print(i)
    open(OUT + '/wmap_0_new.bin', 'wb').write(new.tobytes())
    CL = np.frombuffer(open('work/st/42/vram.bin', 'rb').read(), '<u2').reshape(512, 1024)[241, 0:256].astype(int)
    def col(x):
        im = np.zeros(x.shape + (3,), np.uint8); im[:] = (40, 80, 160)                  # 투명 = 바다색
        for i in np.unique(x):
            if i: c = int(CL[i]); im[x == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
        return im
    s = np.hstack([col(a), np.zeros((a.shape[0], 6, 3), np.uint8), col(new)])
    Image.fromarray(s).resize((s.shape[1] * 3, s.shape[0] * 3), Image.NEAREST).save(OUT + '/미리보기_지명_왼쪽원본_오른쪽한글.png')
    print(OUT)
