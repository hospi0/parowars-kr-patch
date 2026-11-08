# -*- coding: utf-8 -*-
"""묶음 G — 하단 상태 줄 나라 이름(FIX.BIN 0xC000 = VRAM (672,384) 4비트 128×128, 팔레트 VRAM (512,255)) 한글화 — 미리보기 + 빌드용 바이트.
   줄 = 16 px 띠 8개(ペン太郎王国·ラブリー合衆国·こいつ＆あいつ国·ミカエル帝国·バウバウ国·アカシヤ共和国·パンダ獣民共和国·モアイ諸島首長国),
   왼쪽 맞춤. 게임은 원문 잉크 폭만큼 잘라 찍으므로(상태 19 실측: ラブリー合衆国 = uv(128,144) 100×15) 한글은 원문 폭 안.
   양식(실측): 몸 1(흰) · 아래 1px 그림자 7(검) · 둘레 1px 테두리 8(회).
   ニャン次郎軍 = 1번 줄 오른쪽 + 4번 줄 오른쪽 두 조각 이음 → «냥지»+«로군»(조각 사각형 미확인, 원문 잉크 시작 열 88부터).
   python tools/fixbar_kr.py → work/미리보기_그림_G/"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_G'; os.makedirs(OUT, exist_ok=True)
G11 = bdf.Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf')
OFF = 0xC000                                   # FIX.BIN 안 위치(VRAM 672,384), 한 줄 64 B
NAMES = ['펭타로 왕국', '러블리 합중국', '이녀석＆저녀석국', '미카엘 제국', '멍멍국', '아카시야 공화국', '판다 수민 공화국', '모아이 제도 수장국']
NYAN_X = 86                                    # 1·4번 줄 이 열부터 오른쪽 = ニャン次郎軍 조각(보존) — 빈 열 85~87 실측


def unpack4(b):
    a = np.frombuffer(b, np.uint8).reshape(128, 64); px = np.zeros((128, 128), np.uint8)
    px[:, 0::2] = a & 15; px[:, 1::2] = a >> 4; return px


def pack4(px):
    return (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()


def shift(m, dy, dx):
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return o


def text_mask(s):
    pts = []; x = 0
    for ch in s:
        p, w = G11.draw(ch); pts += [(x + a, b) for a, b in p]; x += w
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((max(ys) + 1, max(xs) + 1), bool)
    for a, b in pts: m[b, a] = True
    return m


def build(px):
    new = px.copy(); info = []
    _, = [None]
    for r, ko in enumerate(NAMES):
        band = px[r * 16:r * 16 + 16]
        lim = NYAN_X if r in (0, 3) else 128
        cols = np.nonzero(band[:, :lim].any(0))[0]; W = cols.max() + 1          # 원문 잉크 폭
        new[r * 16:r * 16 + 16, :lim] = 0
        m = text_mask(ko)
        ys = np.nonzero(m.any(1))[0]; m = m[ys.min():ys.max() + 1]; xs = np.nonzero(m.any(0))[0]; m = m[:, xs.min():xs.max() + 1]
        body = np.zeros((16, 128), bool); oy = 2; ox = 1
        body[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
        sh = shift(body, 1, 0) & ~body
        a = body | sh
        ol = (shift(a, 1, 0) | shift(a, -1, 0) | shift(a, 0, 1) | shift(a, 0, -1)) & ~a
        blk = np.zeros((16, 128), np.uint8); blk[ol] = 8; blk[sh] = 7; blk[body] = 1
        used = np.nonzero(blk.any(0))[0].max() + 1
        assert used <= W and np.nonzero(blk.any(1))[0].max() <= 14, (ko, used, W)
        new[r * 16:r * 16 + 16, :lim] = np.where(blk[:, :lim] > 0, blk[:, :lim], 0)
        info.append((ko, '폭 %d/%d' % (used, W)))
    # ニャン次郎軍 = 1번 줄 88~127(ニャン) + 4번 줄 88~127(次郎軍) 두 조각 이음 → 음절 나눠 «냥지» + «로군»(하스피 «나머지 전부 마무리»)
    for r, ko in ((0, '냥지'), (3, '로군')):
        new[r * 16:r * 16 + 16, NYAN_X:] = 0
        m = text_mask(ko); ys = np.nonzero(m.any(1))[0]; m = m[ys.min():ys.max() + 1]; xs = np.nonzero(m.any(0))[0]; m = m[:, xs.min():xs.max() + 1]
        x0 = 127 - 1 - m.shape[1] if r == 0 else 89                 # «냥지»는 1번 줄 오른쪽 끝(127)에 붙이고 «로군»은 4번 줄 88부터 — 두 조각 이음새가 맞닿게(원문 «次»가 127|88 에서 이어짐)
        body = np.zeros((16, 128), bool); body[2:2 + m.shape[0], x0:x0 + m.shape[1]] = m
        sh = shift(body, 1, 0) & ~body; a = body | sh
        ol = (shift(a, 1, 0) | shift(a, -1, 0) | shift(a, 0, 1) | shift(a, 0, -1)) & ~a
        blk = np.zeros((16, 128), np.uint8); blk[ol] = 8; blk[sh] = 7; blk[body] = 1
        assert not blk[:, :NYAN_X].any() and np.nonzero(blk.any(0))[0].max() <= 127, ko
        new[r * 16:r * 16 + 16, NYAN_X:] = blk[:, NYAN_X:]
        info.append((ko, '냥지로군 조각'))
    return new, info


def colorize(px, CL):
    im = np.zeros(px.shape + (3,), np.uint8); im[:] = (60, 140, 60)
    for i in range(1, 16):
        c = int(CL[i]); im[px == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return Image.fromarray(im)


if __name__ == '__main__':
    d = open('work/files/DATA/FIX.BIN', 'rb').read()
    v = open('work/st/19/vram.bin', 'rb').read()
    vr = np.frombuffer(v, np.uint8).reshape(512, 2048)[384:512, 672 * 2:704 * 2].tobytes()
    assert d[OFF:OFF + 128 * 64] == vr, 'FIX 0xC000 ≠ VRAM (672,384)'
    px = unpack4(d[OFF:OFF + 128 * 64])
    new, info = build(px)
    for i in info: print(i)
    open(OUT + '/fix_C000_new.bin', 'wb').write(pack4(new))
    CL = np.frombuffer(v, '<u2').reshape(512, 1024)[255, 512:528].astype(int)
    a = colorize(px, CL).resize((512, 512), Image.NEAREST); c = colorize(new, CL).resize((512, 512), Image.NEAREST)
    s = Image.new('RGB', (1036, 512), (0, 0, 0)); s.paste(a, (0, 0)); s.paste(c, (524, 0))
    s.save(OUT + '/미리보기_글자판_왼쪽원본_오른쪽한글_v3.png'); print(OUT)
