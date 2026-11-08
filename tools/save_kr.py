# -*- coding: utf-8 -*-
"""묶음 H — 세이브 칸 라벨(MCWGRPH.BIN 0xC000 = VRAM (928,0) 4비트 128×256, 팔레트 VRAM (256,253) 회색) 한글화 — 미리보기 + 빌드용 바이트.
   글자판(실측): 1~4줄 «나라 이름 | 뒤 낱말»(クリア·ターン·第·章·マップ), 5~8줄 나라 이름(7·8줄 오른쪽은 얼굴 그림 — 보존),
   シナリオ·マップバトル(다른 팔레트), 그 아래 숫자·ABCD(보존).
   게임이 이 판을 그리는 사각형은 램 패킷에서 못 찾음 → 한글은 «원문 항목 잉크 범위 안»에만(넘치면 잘림 위험).
   양식: 테두리(가장자리 최다 번호) 1px + 몸은 행마다 원문 그 행 최다색(그라데이션) — 갈무리11 굵게(BDF 화소 그대로).
   python tools/save_kr.py → work/미리보기_그림_H/"""
import sys, os, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_H'; os.makedirs(OUT, exist_ok=True)
GD = 'C:/claude/utils/font/Galmuri-v2.40.3/'
FB, FC = bdf.Font(GD + 'Galmuri11-Bold.bdf'), bdf.Font(GD + 'Galmuri11-Condensed.bdf')
FR = bdf.Font(GD + 'Galmuri11.bdf')
REGULAR = {'맵 배틀'}                       # 굵은 글씨는 «배틀» 획이 뭉개짐(하스피) → 보통 굵기
OFF = 0xC000
# (y0, y1, x0, x1, 한글, 정렬) — x 범위 = 원문 항목 잉크 범위(열 점유 지도 실측, 2026-11-08)
ITEMS = [(0, 19, 0, 80, '펭타 왕국', 'L'), (0, 19, 80, 104, '완료', 'C'),
         (19, 39, 0, 80, '미카엘 제국', 'L'), (19, 39, 80, 105, '턴', 'R'),
         (39, 59, 0, 80, '아카시야랜드', 'L'), (39, 59, 80, 92, '제', 'C'), (39, 59, 92, 105, '장', 'C'),
         (59, 80, 0, 80, '러블리 연방', 'L'), (59, 80, 80, 105, '맵', 'C'),
         (80, 100, 0, 80, '이녀석저녀석', 'L'),
         (100, 120, 0, 76, '모아이국', 'C'),
         (124, 146, 0, 73, '판다국', 'C'),
         (146, 166, 0, 79, '멍멍국', 'C'),
         (166, 184, 0, 57, '시나리오', 'C'),
         (184, 206, 0, 57, '맵 배틀', 'C')]


def unpack4(b):
    a = np.frombuffer(b, np.uint8).reshape(-1, 64); px = np.zeros((a.shape[0], 128), np.uint8)
    px[:, 0::2] = a & 15; px[:, 1::2] = a >> 4; return px


def pack4(px):
    return (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()


def shift(m, dy, dx):
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return o


def mask(font, s, sq=0):
    pts = []; x = 0
    for ch in s:
        p, w = font.draw(ch); pts += [(x + a, b) for a, b in p]; x += w - sq
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for a, b in pts: m[b - min(ys), a - min(xs)] = True
    return m


def build(px, alt=None):
    new = px.copy(); info = []
    for y0, y1, x0, x1, ko, al in ITEMS:
        if alt and ko in alt: ko = alt[ko]
        box = px[y0:y1, x0:x1]; ink = box > 0
        edge = ink & ~(shift(ink, 1, 0) & shift(ink, -1, 0) & shift(ink, 0, 1) & shift(ink, 0, -1))
        outl = collections.Counter(box[edge].tolist()).most_common(1)[0][0]
        rows = np.nonzero((ink & (box != outl)).any(1))[0]; b0, b1 = rows.min(), rows.max()
        cc = collections.Counter(box[ink & (box != outl)].tolist()).most_common(2)
        main = cc[0][0]; shade = cc[1][0] if len(cc) > 1 else main          # 몸 주색 · 음영(아래 가장자리) — 원문 실측(3·11 / 7 / 15)
        if outl == 8 and main not in (7, 15): main, shade = 3, 11                 # 은색 글자는 전부 흰 몸 3 + 음영 11 로 통일(턴이 13 회색으로 잡혀 어둡던 것 — 하스피 «턴 색깔»)
        W = x1 - x0
        for font, sq in (((FR, 0), (FR, 1)) if ko in REGULAR else ((FB, 0), (FB, 1))):
            m = mask(font, ko, sq)
            if m.shape[1] + 2 <= W: break
        assert m.shape[1] + 2 <= W or (len(ko) == 1 and m.shape[1] <= W), (ko, m.shape, W)    # 한 글자 칸(제·장)은 테두리 한쪽 잘림 허용
        assert m.shape[0] + 2 <= y1 - y0, (ko, m.shape)
        H = b1 - b0 + 1
        oy = y0 + b0 + (H - m.shape[0]) // 2
        ox = x0 + (1 if al == 'L' else W - 1 - m.shape[1] if al == 'R' else (W - m.shape[1]) // 2)
        new[y0:y1, x0:x1] = 0
        T = np.zeros(px.shape, bool); T[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
        O = shift(T, 1, 0) | shift(T, -1, 0) | shift(T, 0, 1) | shift(T, 0, -1)
        if ko not in REGULAR: O |= shift(T, 1, 1) | shift(T, 1, -1) | shift(T, -1, 1) | shift(T, -1, -1)   # 보통 굵기는 4방향 테두리(획 안 묻힘)
        O &= ~T
        O[:, :x0] = False; O[:, x1:] = False; O[:y0] = False; O[y1:] = False
        new[O] = outl
        if outl == 7: main, shade = 1, 5                      # 시나리오: 하늘색 몸 + 파랑 음영(행별 색 옮기기 = 줄무늬 → 하스피 «파란 줄» 지적)
        elif outl == 15: main, shade = 9, 14                  # 맵 배틀: 주황 몸 + 자주 음영
        new[T] = main
        if ko in REGULAR: new[O & shift(T, 1, 0)] = shade      # 맵 배틀: 음영 = 글자 바로 아래 테두리 화소(몸 안에 넣으면 1px 획이 뭉개짐)
        else: new[T & ~shift(T, -1, 0)] = shade               # 아래 가장자리 = 음영
        info.append((ko, 'FB' if font is FB else 'FC', -sq, m.shape, W))
    return new, info


def colorize(px, CL):
    im = np.zeros(px.shape + (3,), np.uint8); im[:] = (60, 140, 60)
    for i in range(1, 16):
        c = int(CL[i]); im[px == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return Image.fromarray(im)


if __name__ == '__main__':
    d = open('work/files/DATA/MCWGRPH.BIN', 'rb').read()
    v = open('work/st/51/vram.bin', 'rb').read()
    assert d[OFF:OFF + 64 * 256] == np.frombuffer(v, np.uint8).reshape(512, 2048)[0:256, 928 * 2:960 * 2].tobytes()
    px = unpack4(d[OFF:OFF + 64 * 256])
    new, info = build(px)
    for i in info: print(i)
    open(OUT + '/mcw_C000_new.bin', 'wb').write(pack4(new))
    VV = np.frombuffer(v, '<u2').reshape(512, 1024)
    CLS = [(0, 166, VV[253, 256:272]), (166, 184, VV[253, 272:288]), (184, 208, VV[254, 432:448])]   # 은색 / 시나리오 파랑 / 맵 배틀 주황 — 항목별 실제 팔레트
    def colz(a):
        im = np.zeros((208, 128, 3), np.uint8)
        for y0_, y1_, cl in CLS: im[y0_:y1_] = np.array(colorize(a[y0_:y1_], cl.astype(int)))
        return Image.fromarray(im)
    tiles = [colz(px[:208]), colz(new[:208])]
    S = 4; s = Image.new('RGB', (128 * S * 2 + 12, 208 * S + 12 + 20 * S), (0, 0, 0))
    s.paste(tiles[0].resize((128 * S, 208 * S), Image.NEAREST), (0, 0)); s.paste(tiles[1].resize((128 * S, 208 * S), Image.NEAREST), (128 * S + 12, 0))
    s.save(OUT + '/미리보기_글자판_왼쪽원본_오른쪽한글_v7.png'); print(OUT)
