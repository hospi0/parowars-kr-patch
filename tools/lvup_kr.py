# -*- coding: utf-8 -*-
"""그림 J — 전투 레벨업 «ﾚﾍﾞﾙUP»(MATI.BIN 평문 8비트, VRAM (960,224) u0~39·v224~239, 팔레트 (256,237)).
   ⚠ 파일 안 행 순서가 VRAM 과 거꾸로(VRAM 행 y = 파일 0x18EA8 − 128·y). 회전 연출 때문에 스테이트 화면에선 뒤집혀 보였음(하스피 지적).
   정방향(파일 주소 오름차순) 기준 글자 = 5~12줄·6~40열, 흰 몸 1 + 회색 그림자 8, «UP» 은 주황 0x3F + 빨강 0x0F.
   한글 «레벨UP» = 갈무리7. VRAM 238·239행(정방향 0·1줄, 01 가득)은 다른 그림이라 보존.
   python tools/lvup_kr.py → work/미리보기_그림_J/"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_J'; os.makedirs(OUT, exist_ok=True)
G7 = bdf.Font('C:/claude/utils/font/Galmuri-v2.40.3/Galmuri7.bdf')
TOP = 0x11EA8                  # VRAM 224 행의 파일 위치(행마다 −128)
LO = TOP - 128 * 15            # 정방향 첫 줄(VRAM 239) 파일 위치


def mask(s):
    pts = []; x = 0
    for ch in s:
        p, w = G7.draw(ch); pts += [(x + a, b) for a, b in p]; x += w
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for a, b in pts: m[b - min(ys), a - min(xs)] = True
    return m


def shift(m, dy, dx):
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return o


def build(d):
    up = np.frombuffer(d[LO:LO + 128 * 16], np.uint8).reshape(16, 128).copy()     # 정방향 16줄(0 = VRAM 239)
    new = up.copy()
    new[2:16, 0:40] = 0                                                             # 글자 영역(VRAM 224~237행·0~39열) 비움
    a = mask('레벨'); b = mask('UP')
    T = np.zeros((16, 40), bool); U = np.zeros((16, 40), bool)
    y0 = 5 + (8 - a.shape[0]) // 2
    T[y0:y0 + a.shape[0], 3:3 + a.shape[1]] = a
    xb = 3 + a.shape[1] + 2
    U[5 + (8 - b.shape[0]) // 2:5 + (8 - b.shape[0]) // 2 + b.shape[0], xb:xb + b.shape[1]] = b
    assert xb + b.shape[1] + 1 <= 40, xb + b.shape[1]
    blk = np.zeros((16, 40), np.uint8)
    blk[(shift(T, 1, 1) & ~T)] = 8; blk[(shift(U, 1, 1) & ~U)] = 0x0F
    blk[T] = 1; blk[U] = 0x3F
    new[2:16, 0:40] = blk[2:16]
    return up, new


if __name__ == '__main__':
    d = open('work/files/DATA/MATI.BIN', 'rb').read()
    up, new = build(d)
    open(OUT + '/mati_lvup_new.bin', 'wb').write(new.tobytes())                   # 파일 LO 부터 2,048 B 그대로 덮을 것
    V = np.frombuffer(open('work/st/57/vram.bin', 'rb').read(), '<u2').reshape(512, 1024); CL = V[237, 256:512].astype(int)
    def col(px):
        im = np.zeros(px.shape + (3,), np.uint8); im[:] = (40, 90, 40)
        for i in np.unique(px):
            if i: c = CL[i]; im[px == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
        return im
    s = np.vstack([col(up[:, :48]), np.zeros((2, 48, 3), np.uint8), col(new[:, :48])])
    Image.fromarray(s).resize((48 * 10, s.shape[0] * 10), Image.NEAREST).save(OUT + '/미리보기_레벨업_위원본_아래한글.png')
    print(OUT, hex(LO))
