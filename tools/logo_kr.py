# -*- coding: utf-8 -*-
"""타이틀 큰 로고(ROGO.BIN)·로딩 작은 로고(SLPM_860.16 0x2CB18 / ATDM_OV.BIN 0xD0 사본) 한글화 — 미리보기 전용(빌드 안 함).
   하스피: 큰 로고가 배경과 분리돼 있으면 작업, 아니면 큰·작은 로고 둘 다 하지 말 것 → 둘 다 분리된 8비트 스프라이트 확인(2026-11-08).
   방식: 원본 색 번호(팔레트 = 큰 로고 VRAM (0,253), 작은 로고는 화면에서 역산)로 원본과 같은 겹을 다시 그림.
     파란 입체 그림자(168, 아래 가장자리 173) → 남색 외곽선(182) → 흰 띠(9) → 빨강→분홍 세로 그라데이션 글자.
     미사일 엠블럼·PARO WARS·TM 은 원본 화소 유지(엠블럼은 고유색 + 그에 붙은 외곽선만).
   python tools/logo_kr.py 글꼴이름 [글자]  → work/미리보기_로고_<글꼴>/"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')
FONTS = {'jua': r'C:\claude\utils\font\jua\Jua-Regular.ttf', 'bhs': r'C:\claude\utils\font\blackhansans\BlackHanSans-Regular.ttf',
         'gasoek': r'C:\claude\utils\font\logo\GasoekOne-Regular.ttf', 'dohyeon': r'C:\claude\utils\font\dohyeon\DoHyeon-Regular.ttf'}
fname = sys.argv[1] if len(sys.argv) > 1 else 'jua'; TEXT = sys.argv[2] if len(sys.argv) > 2 else '파로워즈'
OUT = 'work/미리보기_로고_%s' % fname; os.makedirs(OUT, exist_ok=True)
RED = [41, 254, 37, 35, 34, 33, 30, 250, 249, 246, 27, 26, 24, 22, 19, 18]     # 위(진빨강) → 아래(분홍)
WHITE, NAVY, BLUE, BLUE_DK = 9, 182, 168, 173
BOLD = 1
BLUEFAM = {168, 166, 174, 172, 176, 163, 167, 173, 151, 156, 134}


def dil(m, r):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r + r: continue
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def text_mask(h_target, w_max, font):
    f = ImageFont.truetype(FONTS[font], h_target * 2)
    im = Image.new('L', (w_max * 3, h_target * 4), 0); ImageDraw.Draw(im).text((10, 10), TEXT, font=f, fill=255)
    a = np.array(im) > 127; ys, xs = np.nonzero(a); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = a.shape; s = min(h_target / h, w_max / w)
    im2 = Image.fromarray((a * 255).astype(np.uint8)).resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    return np.array(im2) > 110


def build(idx, pal, box, keep_boxes, h_text, w_text, ow, nav, depth, font, emblem_box):
    x0, y0, x1, y1 = box
    out = idx.copy()
    rgb = lambda i: ((pal[i] & 31) << 3, (pal[i] >> 5 & 31) << 3, (pal[i] >> 10 & 31) << 3)
    keep = np.zeros(idx.shape, bool)
    for (a, b, c, d) in keep_boxes:                       # PARO WARS·TM: 파란 그림자 빼고 유지
        sub = idx[b:d, a:c]; keep[b:d, a:c] = (sub > 0) & ~np.isin(sub, list(BLUEFAM))
    ea, eb, ec, ed = emblem_box                            # 엠블럼: 상자 안 원본 화소, 단 왼쪽 아래(ズ 윗부분)의 빨강·분홍·흰색 제외
    sub = idx[eb:ed, ea:ec]
    col = np.array([rgb(i) for i in range(256)]); c = col[sub]
    redwhite = ((c[..., 0] > 150) & (c[..., 1] < 200)) | (sub == WHITE) | ((c[..., 0] > 200) & (c[..., 1] > 150) & (c[..., 2] > 150))
    yy = np.arange(sub.shape[0])[:, None]; xx = np.arange(sub.shape[1])[None, :]
    zpart = redwhite & (yy >= (ed - eb) * 0.6) & (xx < (ec - ea) * 0.45)
    keep[eb:ed, ea:ec] |= (sub > 0) & ~zpart
    # 글자 영역 비우기
    zone = np.zeros(idx.shape, bool); zone[y0:y1, x0:x1] = True
    out[zone & ~keep] = 0
    # 새 글자
    m = text_mask(h_text, w_text, font); th, tw = m.shape
    T = np.zeros(idx.shape, bool); ox = x0 + 2 + ow + nav; oy = y0 + 2 + ow + nav
    T[oy:oy + th, ox:ox + tw] = m
    T = dil(T, BOLD)                                         # 원본처럼 통통하게
    W = dil(T, ow); N = dil(W, nav)
    S = np.zeros_like(N)
    for k in range(1, depth + 1): S |= np.roll(np.roll(N, k, 0), k // 2, 1)          # 오른쪽 아래로 기운 입체
    S &= ~N; Sd = S & ~np.roll(S, -1, 0)                   # 그림자 아래 가장자리
    lay = np.zeros(idx.shape, int)
    lay[S] = BLUE; lay[Sd] = BLUE_DK; lay[dil(S, 1) & ~S & ~N] = NAVY
    lay[N] = NAVY; lay[W] = WHITE
    ys = np.nonzero(T.any(1))[0]
    for y in range(ys.min(), ys.max() + 1):
        t = (y - ys.min()) / max(1, ys.max() - ys.min()); i = RED[min(len(RED) - 1, int(t * t * len(RED)))]
        lay[y][T[y]] = i
    put = (lay > 0) & zone & ~keep
    out[put] = lay[put]
    return out


def show(idx, pal, scale):
    r = pal[idx]; im = np.stack([(r & 31) << 3, (r >> 5 & 31) << 3, (r >> 10 & 31) << 3], 2).astype(np.uint8)
    im[idx == 0] = (255, 0, 255)
    return Image.fromarray(im).resize((idx.shape[1] * scale, idx.shape[0] * scale), Image.NEAREST)


def on_screen(st, idx, pal, sx, sy, orig=None):
    v = np.frombuffer(open('work/st/%s/vram.bin' % st, 'rb').read(), '<u2').reshape(512, 1024)
    fb = v[0:240, 0:320].astype(int).copy()
    h, w = idx.shape
    for y in range(h):
        for x in range(w):
            if not (0 <= sy + y < 240 and 0 <= sx + x < 320): continue
            if idx[y, x]: fb[sy + y, sx + x] = pal[idx[y, x]]
            elif orig is not None and orig[y, x]: fb[sy + y, sx + x] = 0x3DEF      # 원래 로고가 가리던 배경(모름) = 회색
    return Image.fromarray(np.stack([(fb & 31) << 3, (fb >> 5 & 31) << 3, (fb >> 10 & 31) << 3], 2).astype(np.uint8))


if __name__ == '__main__':
    # 큰 로고: 1번 스테이트 VRAM (768,128) 448×128, 팔레트 (0,253), 화면 (16,38)
    raw = open('work/st/1/vram.bin', 'rb').read(); v = np.frombuffer(raw, '<u2').reshape(512, 1024); b = np.frombuffer(raw, np.uint8).reshape(512, 2048)
    big = b[128:256, 768 * 2:992 * 2].astype(int); palb = v[253, 0:256].astype(int)
    newb = build(big, palb, (0, 0, 300, 118), [(64, 74, 208, 95), (254, 85, 270, 95)], 60, 214, 4, 1, 14, fname, (226, 0, 292, 37))
    np.save(OUT + '/big_idx.npy', newb)
    sb = Image.new('RGB', (320 * 2 * 2 + 8, 240 * 2), (0, 0, 0))
    sb.paste(on_screen('1', big, palb, 16, 38).resize((640, 480), Image.NEAREST), (0, 0))
    sb.paste(on_screen('1', newb, palb, 16, 38, big).resize((640, 480), Image.NEAREST), (648, 0))
    sb.save(OUT + '/미리보기_타이틀_왼쪽원본_오른쪽한글.png')
    show(newb[:, :300], palb, 3).save(OUT + '/큰로고_확대.png')
    # 작은 로고: 3번 스테이트 VRAM (832,0) 128×56, 팔레트 = 화면 역산(work/pal_small.npy), 화면 (181,159)
    raw = open('work/st/3/vram.bin', 'rb').read(); b = np.frombuffer(raw, np.uint8).reshape(512, 2048)
    small = b[0:56, 832 * 2:896 * 2].astype(int); pals = np.load('work/pal_small.npy')
    news = build(small, pals, (0, 0, 126, 50), [(40, 36, 92, 50), (112, 38, 128, 46)], 26, 88, 2, 1, 6, fname, (92, 0, 126, 22))
    np.save(OUT + '/small_idx.npy', news)
    ss = Image.new('RGB', (320 * 2 * 2 + 8, 240 * 2), (0, 0, 0))
    ss.paste(on_screen('3', small, pals, 181, 159).resize((640, 480), Image.NEAREST), (0, 0))
    ss.paste(on_screen('3', news, pals, 181, 159, small).resize((640, 480), Image.NEAREST), (648, 0))
    ss.save(OUT + '/미리보기_로딩_왼쪽원본_오른쪽한글.png')
    show(news[:, :128], pals, 5).save(OUT + '/작은로고_확대.png')
    print(OUT)
