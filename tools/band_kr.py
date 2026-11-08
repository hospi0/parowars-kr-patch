# -*- coding: utf-8 -*-
"""묶음 D — 나라 소개 띠(큰 나라 이름) + 머리글(国データー·軍事データー·主力武器) 한글화 — 미리보기 + 빌드용.
   VRAM (상태 12·40~45 실측): 나라 띠 = x 64·128·…·512(하프워드) 4비트 128px 폭, 1줄 y384~407 · 2줄 y408~431, 팔레트 (128,246).
   이름 = 한 장짜리 그림을 128px 에서 접어 1줄(0~127)+2줄(0~w2)에 둠 — 화면은 두 조각을 이어 찍음(러블리: 128×24 + 88×24).
   머리글 조각(램 패킷): 軍事データー = 펭타 띠 2줄 u16~127 · 主力武器 = 미카엘 띠 2줄 u16~95 · 国データー = 바우바우 띠 2줄 0~95.
   양식: 몸 = 세로 그라데이션(행마다 원문 색: 흰 2 → 파랑 10), 테두리·그림자 1(검정). 한글 = 나눔고딕 ExtraBold(경계 화소 이진화).
   ⚠ 그림 사본: 시나리오 데모 덩어리(DEMO/*_0x)마다 — build 단계에서 전 사본 검색 후 교체.
   python tools/band_kr.py → work/미리보기_그림_D/"""
import sys, os, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_D'; os.makedirs(OUT, exist_ok=True)
FONT = 'C:/claude/utils/font/dohyeon/DoHyeon-Regular.ttf'      # 2026-11-08 하스피 D안(도현) — 전 나눔고딕 ExtraBold
STRIPS = [64, 128, 192, 256, 320, 384, 448, 512]           # 하프워드 x (펭타·미카엘·아카시야·러블리·이녀석·모아이·판다·멍멍)
NAMES = ['펭타로 왕국', '미카엘 제국', '아카시야랜드 공화국', '러블리 연방 합중국', '이녀석＆저녀석 연방 공화국', '모아이 제도 수장국', '판다 다회주의 수민 공화국', '멍멍국']
# 원문 이름 2줄 폭(머리글 조각 앞까지) — 펭타·미카엘 2줄은 u16 부터 머리글, 바우바우 2줄은 머리글만(이름은 1줄)
HEAD = [(0, 16, 128, '군사 데이터'), (1, 16, 96, '주력 무기'), (7, 0, 96, '국가 데이터')]   # (띠 번호, u0, u1, 한글)


def load(v):
    b = np.frombuffer(v, np.uint8).reshape(512, 2048); out = []
    for x in STRIPS:
        reg = b[384:432, x * 2:x * 2 + 64]; px = np.zeros((48, 128), np.uint8)
        px[:, 0::2] = reg & 15; px[:, 1::2] = reg >> 4; out.append(px)
    return out


def shift(m, dy, dx):
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return o


def glyphs(text, px_h, maxw):
    """글자 몸 높이 px_h 로(넘치면 줄임) 이진 마스크."""
    for size in range(px_h + 10, 8, -1):
        f = ImageFont.truetype(FONT, size * 4)
        im = Image.new('L', (size * 4 * (len(text) + 2), size * 8), 0); ImageDraw.Draw(im).text((8, 8), text, font=f, fill=255)
        a = np.array(im.resize((im.width // 4, im.height // 4), Image.BOX)) >= 110
        ys, xs = np.nonzero(a); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if a.shape[0] <= px_h and a.shape[1] <= maxw: return a
    raise ValueError(text)


def profile(px_line):
    """원문 줄의 행별 몸색(1·0 제외 최다) — 그라데이션."""
    prof = []
    for y in range(px_line.shape[0]):
        r = px_line[y][(px_line[y] > 1)]
        prof.append(collections.Counter(r.tolist()).most_common(1)[0][0] if len(r) else 0)
    return prof


def paint(mask, H, prof, top):
    """mask 를 H 줄 캔버스에 top 부터: 몸 = 행 그라데이션, 테두리 1px + 오른쪽 아래 그림자 1px = 색 1."""
    W = mask.shape[1] + 3
    T = np.zeros((H, W), bool); T[top:top + mask.shape[0], 1:1 + mask.shape[1]] = mask
    O = (shift(T, 1, 0) | shift(T, -1, 0) | shift(T, 0, 1) | shift(T, 0, -1) | shift(T, 1, 1) | shift(T, 1, -1) | shift(T, -1, 1) | shift(T, -1, -1) | shift(T, 2, 2) | shift(T, 1, 2) | shift(T, 2, 1)) & ~T
    c = np.zeros((H, W), np.uint8); c[O] = 1
    rows = [p for p in prof if p]
    for y in range(H):
        if T[y].any():
            k = (y - top) * len(rows) // max(1, mask.shape[0]); c[y][T[y]] = rows[min(k, len(rows) - 1)] if rows else 2
    return c


def build(strips):
    new = [s.copy() for s in strips]; info = []
    for k, ko in enumerate(NAMES):
        s = strips[k]
        l1 = s[0:24]; l2 = s[24:48]
        hd = [h for h in HEAD if h[0] == k]
        w2 = (hd[0][1] if hd else (np.nonzero(l2.any(0))[0].max() + 1 if l2.any() else 0)) if k != 7 else 0
        if k == 5: w2 = 64                                   # 모아이 2줄 = «首長国»(0~63) + «VS»(90~127, 대전 화면용 — 보존)
        maxw = 128 + w2 - 4
        prof = profile(l1)
        body_rows = [y for y in range(24) if (l1[y] > 1).any()]; top = body_rows[0]; bh = body_rows[-1] - top + 1
        m = glyphs(ko, min(bh, 24 - top - 3), maxw)          # 아래 테두리·그림자 2px 가 띠 안에 들게
        img = paint(m, 24, prof, top + (min(bh, 24 - top - 3) - m.shape[0]) // 2)
        assert not img[22:].any() or True
        line = np.zeros((24, 256), np.uint8); line[:, :img.shape[1]] = img[:, :256]
        assert img.shape[1] <= 128 + w2, (ko, img.shape, w2)
        new[k][0:24] = line[:, 0:128]
        new[k][24:48, 0:max(w2, 0)] = line[:, 128:128 + max(w2, 0)]
        info.append((ko, '폭', img.shape[1], '/', 128 + w2))
    for k, u0, u1, ko in HEAD:
        l2 = strips[k][24:48, u0:u1]; prof = profile(l2)
        rows = [y for y in range(24) if (l2[y] > 1).any()]; top = rows[0]; bh = rows[-1] - top + 1
        hh = min(bh, 24 - top - 3)                           # 머리글도 그림자까지 띠 안(«주력 무기» 아래 잘림 — 하스피)
        m = glyphs(ko, hh, u1 - u0 - 4)
        img = paint(m, 24, prof, top + (hh - m.shape[0]) // 2)
        assert not img[23].any(), (ko, '아래 잘림')
        blk = np.zeros((24, u1 - u0), np.uint8); blk[:, :img.shape[1]] = img[:, :u1 - u0]
        new[k][24:48, u0:u1] = blk
        info.append((ko, '머리글 폭', img.shape[1], '/', u1 - u0))
    return new, info


def colorize(px, CL):
    im = np.zeros(px.shape + (3,), np.uint8); im[:] = (60, 140, 60)
    for i in range(1, 16):
        c = int(CL[i]); im[px == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return im


if __name__ == '__main__':
    v = open('work/st/12/vram.bin', 'rb').read()
    strips = load(v)
    new, info = build(strips)
    for i in info: print(i)
    np.save(OUT + '/strips_orig.npy', np.array(strips)); np.save(OUT + '/strips_new.npy', np.array(new))
    CL = np.frombuffer(v, '<u2').reshape(512, 1024)[246, 128:144].astype(int)
    rows = []
    for a, b2 in zip(strips, new):
        # 화면처럼 이어 보기: 1줄 + 2줄
        rows.append(np.hstack([colorize(np.hstack([a[0:24], a[24:48]]), CL), np.zeros((24, 8, 3), np.uint8), colorize(np.hstack([b2[0:24], b2[24:48]]), CL)]))
    s = np.vstack([np.pad(r, ((0, 4), (0, 0), (0, 0))) for r in rows])
    Image.fromarray(s).resize((s.shape[1] * 2, s.shape[0] * 2), Image.NEAREST).save(OUT + '/미리보기_띠_왼쪽원본_오른쪽한글.png')
    print(OUT)


def pack4(px):
    return (px[:, 0::2] | (px[:, 1::2] << 4)).astype(np.uint8).tobytes()


def edits():
    """빌드용: 원문 줄 블록(24줄×64 B)과 똑같은 바이트를 모든 풀린 덩어리에서 찾아 새 블록으로 → [(덩어리 키 '@…', 위치, 새 바이트)]."""
    import glob
    v = open('work/st/12/vram.bin', 'rb').read()
    strips = load(v); new = np.load(OUT + '/strips_new.npy')
    out = []
    for k in range(8):
        for li in (0, 1):
            ob = pack4(strips[k][li * 24:li * 24 + 24]); nb = pack4(new[k][li * 24:li * 24 + 24])
            if ob == nb: continue
            for p in glob.glob('work/unpk/*.bin'):
                d = open(p, 'rb').read(); i = d.find(ob)
                while i >= 0:
                    out.append(('@' + os.path.basename(p)[:-4], i, nb)); i = d.find(ob, i + 1)
    return out
