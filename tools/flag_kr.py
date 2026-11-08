# -*- coding: utf-8 -*-
"""턴 시작 큰 나라 이름 — DATA/FLAG.BIN 압축 덩어리 9개(0x20부터 잇달아, 풀면 8,192 B = 4비트 128×128: 0~23행 이름 1줄, 24~47행 2줄, 아래 국기).
   덩어리 0~7 = 묶음 D 띠(band_kr strips_new)와 같은 이름 — 원문 블록이 같으면 그대로 씀.
   예외: 모아이(5) 2줄엔 «VS» 가 없음 → 64열부터는 FLAG 원문 유지. 판다(6)는 원문 글자 순서가 달라도(獣民茶会主義) 한글은 띠와 같은 이름.
   덩어리 8 = «ニャー帝国» → «냥 제국»(band_kr 글꼴·색 규칙).
   python tools/flag_kr.py → work/미리보기_그림_D/flag_*.bin + 미리보기"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzk, band_kr
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_D'
OFFS = [0x20, 0x884, 0xEE9, 0x163D, 0x1F3D, 0x26FA, 0x2D4F, 0x357D, 0x3A9C]
NYAN = '냥 제국'


def unpx(raw):
    a = np.frombuffer(raw[:0xC00], np.uint8).reshape(48, 64); px = np.zeros((48, 128), np.uint8)
    px[:, 0::2] = a & 15; px[:, 1::2] = a >> 4; return px


def edits():
    """[(파일 내 덩어리 위치, 풀린 위치 0, 새 0xC00 B)]"""
    d = open('work/files/DATA/FLAG.BIN', 'rb').read()
    N = np.load(OUT + '/strips_new.npy'); S = np.load(OUT + '/strips_orig.npy'); out = []; pv = []
    o = 0x20
    for i, off in enumerate(OFFS):
        assert o == off, (hex(o), hex(off))
        raw, used = lzk.unpack(d, off); o += used
        px = unpx(raw); new = px.copy()
        if i < 8:
            assert i == 6 or (px[0:24] == S[i][0:24]).all(), i
            new[0:24] = N[i][0:24]
            if i == 5:
                assert (px[24:48, 0:64] == S[i][24:48, 0:64]).all()
                new[24:48, 0:64] = N[i][24:48, 0:64]
            elif i == 6:
                new[24:48] = N[i][24:48]
            else:
                assert (px[24:48] == S[i][24:48]).all(), i
                new[24:48] = N[i][24:48]
        else:
            l1 = px[0:24]; prof = band_kr.profile(l1)
            rows = [y for y in range(24) if (l1[y] > 1).any()]; top = rows[0]; bh = rows[-1] - top + 1
            hh = min(bh, 24 - top - 3)
            m = band_kr.glyphs(NYAN, hh, 124)
            img = band_kr.paint(m, 24, prof, top + (hh - m.shape[0]) // 2)
            new[0:24] = 0; new[0:24, :img.shape[1]] = img[:, :128]
            assert not px[24:48].any()
        out.append((off, 0, band_kr.pack4(new)))
        pv.append((px, new))
    return out, pv


if __name__ == '__main__':
    v = open('work/st/12/vram.bin', 'rb').read()
    CL = np.frombuffer(v, '<u2').reshape(512, 1024)[246, 128:144].astype(int)
    _, pv = edits()
    rows = [np.hstack([band_kr.colorize(np.hstack([a[0:24], a[24:48]]), CL), np.zeros((24, 8, 3), np.uint8),
                       band_kr.colorize(np.hstack([b[0:24], b[24:48]]), CL)]) for a, b in pv]
    s = np.vstack([np.pad(r, ((0, 4), (0, 0), (0, 0))) for r in rows])
    Image.fromarray(s).resize((s.shape[1] * 2, s.shape[0] * 2), Image.NEAREST).save(OUT + '/미리보기_턴시작_나라이름_왼쪽원본_오른쪽한글.png')
    print(OUT)
