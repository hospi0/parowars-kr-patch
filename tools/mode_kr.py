# -*- coding: utf-8 -*-
"""묶음 B — 모드 선택 큰 글씨(シナリオ モード / マップバトル モード) 한글화 — 미리보기 + 빌드용 npy.
   출처: DEMO/KABE0 풀린 덩어리 0x10000 쪽 = KABE3 풀린 덩어리 0 (같은 그림, 8비트 128×256, VRAM (768,0), 팔레트 VRAM (256,238)).
   화면: 위쪽 128줄 → (24,56), 아래쪽 → (168,56). 배경 별무늬와 분리된 위층 스프라이트.
   양식(원본 실측): 줄마다 가로 띠 그라데이션(줄 위 어둡게 → 약 1/3 지점 가장 밝게 → 아래 절반 진하게),
     그림자 = 글자 몸을 아래로 1~4px 민 자리(분홍 126, 파랑 142). 몸 색: 분홍 113~123, 파랑 129~139.
   한글: 원래 줄 띠(위·아래 줄)에 넣고, 그라데이션은 줄 높이 비율로 원본 행 색을 따라감. 글꼴·굵기는 비교판에서 하스피 선택.
   python tools/mode_kr.py → work/미리보기_그림_B/ (비교판 + 판별 npy)"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import menu_kr as MK
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_B'; os.makedirs(OUT, exist_ok=True)
FD = 'C:/claude/utils/font/'
SHADOW_DY = 4
# (원본 글자 몸 줄 범위 t0,t1, 한글, 몸 색 범위, 그림자 색)
LINES = [(11, 50, '시나리오', (113, 123), 126), (57, 93, '모드', (113, 123), 126),
         (134, 178, '맵 배틀', (129, 139), 142), (185, 221, '모드', (129, 139), 142)]
VARIANTS = [('A', '주아', FD + 'jua/Jua-Regular.ttf', 0),
            ('B', '주아 0.5px 굵게', FD + 'jua/Jua-Regular.ttf', 2),
            ('C', '주아 0.75px 굵게', FD + 'jua/Jua-Regular.ttf', 3),
            ('D', '검은고딕(Black Han Sans)', FD + 'blackhansans/BlackHanSans-Regular.ttf', 0),
            ('E', '도현 0.25px 굵게', FD + 'dohyeon/DoHyeon-Regular.ttf', 1)]


def render2(text, w, h, font, stroke):
    """text 를 높이 ≤h·폭 ≤w 최대 크기로(4배 그려 면적 평균으로 줄임, stroke = 4배 화소 단위 테두리 = 굵기). 낱말 사이 6px."""
    SS = 4
    for size in range(h + 12, 8, -1):
        f = ImageFont.truetype(font, size * SS); parts = []
        for wd in text.split(' '):
            im = Image.new('L', (size * SS * (len(wd) + 2), size * SS * 3), 0)
            ImageDraw.Draw(im).text((SS * 4, SS * 4), wd, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
            parts.append(np.array(im.resize((im.width // SS, im.height // SS), Image.BOX)) / 255.0)
        rows = np.nonzero(np.any([(p >= 0.12).any(1) for p in parts], 0))[0]
        top, bot = rows.min(), rows.max()
        segs = []
        for a in parts:
            cs = np.nonzero((a >= 0.12).any(0))[0]; segs.append(a[top:bot + 1, cs.min():cs.max() + 1])
        out = segs[0]
        for sg in segs[1:]: out = np.concatenate([out, np.zeros((out.shape[0], 6)), sg], 1)
        if out.shape[0] <= h and out.shape[1] <= w: return out
    raise ValueError(text)


def profile(pg, t0, t1, lo, hi):
    """원본 줄의 행별 몸 색(그 행 최다 번호)."""
    out = []
    for y in range(t0, t1 + 1):
        r = pg[y]; v = r[(r >= lo) & (r <= hi)]
        out.append(np.bincount(v).argmax() if len(v) else (out[-1] if out else hi))
    return out


def build(pg, font, stroke):
    # 이 쪽에는 두 글씨뿐(쓰인 번호가 전부 몸·그림자 색) → 통째로 다시 그림
    used = set(np.unique(pg).tolist()) - {0}
    assert used <= set(range(113, 124)) | {126} | set(range(129, 143)), used
    new = np.zeros_like(pg)
    for t0, t1, ko, (lo, hi), sh in LINES:
        prof = profile(pg, t0, t1, lo, hi)
        H0 = t1 - t0 + 1
        t = render2(ko, 124, H0 - 2, font, stroke)
        th, tw = t.shape
        oy = t0 + (H0 - th) // 2; ox = (128 - tw) // 2
        A = np.zeros(pg.shape, float); A[oy:oy + th, ox:ox + tw] = t
        body = A >= 0.45
        ys, xs = np.nonzero(body); assert xs.min() >= 0 and xs.max() <= 127 and ys.max() + SHADOW_DY <= 255
        for y in range(oy, oy + th):                            # 줄 높이 비율로 원본 행 색
            k = min(H0 - 1, int((y - oy) * H0 / th))
            new[y][body[y]] = prof[k]
        shadow = np.zeros_like(body)
        for k in range(1, SHADOW_DY + 1): shadow |= MK.shift(body, k, 0)
        new[shadow & ~body] = sh
    return new


def colorize(sh, CL):
    im = np.zeros(sh.shape + (3,), np.uint8); im[:] = (60, 140, 60)        # 투명 = 녹색
    for i in np.unique(sh):
        if i: c = int(CL[i]); im[sh == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return Image.fromarray(im)


if __name__ == '__main__':
    b0 = open('work/unpk/DATA_DEMO_KABE0.BIN@0.bin', 'rb').read(); b3 = open('work/unpk/DATA_DEMO_KABE3.BIN@0.bin', 'rb').read()
    assert b0[0x10000:0x18000] == b3[:0x8000]
    pg = np.frombuffer(b0[0x10000:0x18000], np.uint8).reshape(256, 128).astype(int)
    v = np.frombuffer(open('work/st/4/vram.bin', 'rb').read(), np.uint8).reshape(512, 2048)
    assert (v[0:256, 768 * 2:832 * 2] == pg).all(), 'VRAM (768,0) ≠ 덩어리 쪽'
    CL = np.frombuffer(open('work/st/4/vram.bin', 'rb').read(), '<u2').reshape(512, 1024)[238, 256:512].astype(int)
    tiles = [('원본', pg)]
    for key, nm, font, st in VARIANTS:
        n = build(pg, font, st); np.save(OUT + '/mode_new_%s.npy' % key, n.astype(np.uint8)); tiles.append((key + ' ' + nm, n))
    lab = ImageFont.truetype(FD + 'nanum-gothic/NanumGothicBold.ttf', 18)
    s = Image.new('RGB', (396 * len(tiles), 696 + 30), (0, 0, 0)); d = ImageDraw.Draw(s)
    for k, (nm, sh) in enumerate(tiles):
        s.paste(colorize(sh[:232], CL).resize((384, 696), Image.NEAREST), (k * 396, 30)); d.text((k * 396 + 4, 5), nm, font=lab, fill=(255, 255, 255))
    for p in os.listdir(OUT):
        if p.startswith('미리보기') or p == 'mode_new.npy': os.remove(os.path.join(OUT, p))
    s.save(OUT + '/미리보기_글자판_원본과_글꼴5종.png'); print(OUT)
