# -*- coding: utf-8 -*-
"""그림 L — 전투 결과 큰 글자(DATA/BTLEND/WIN00~08 «かちっ!!» → «이겼다!!», LOS00~07 «まけっ!!» → «졌다!!»), 하스피 2026-11-08.
   파일: 0x200 부터 8비트 128×256 쪽(0x8000)들 + 끝 512 B 팔레트. 머리 +4 부터 조각 16 B(화면 x, y, 폭, 높이, u, v, …).
   조각 0·1(화면 x 8~136·136~264, 1쪽 v0·v128) = 글자, 조각 2(264, 48×88, 2쪽 u0) = «!!» — «!!» 는 원본 그대로.
   같은 묶음(WIN·LOS) 안 글자 쪽은 바이트까지 같다 → 한 번 그려 묶음 전체에.
   한글 = 주아(둥근 굵은 꼴), 낱말을 두 조각에 걸쳐 한 번에 렌더해 128 에서 자름. 몸 = 원본 몸 색의 세로 그라데이션(행 비율), 테두리 = 원본 테두리 색.
   python tools/btlend_kr.py → work/미리보기_그림_L/"""
import sys, os, struct, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_L'; os.makedirs(OUT, exist_ok=True)
FONT = 'C:/claude/utils/font/jua/Jua-Regular.ttf'
JOBS = {'WIN': ('이겼다', 237, 236, 'WIN00'), 'LOS': ('졌다', 241, 241, 'LOS00')}     # (한글, 테두리 안, 테두리 밖, 견본 파일)


def load(nm):
    d = open('work/files/DATA/BTLEND/%s.BIN' % nm, 'rb').read()
    n = struct.unpack_from('<H', d, 2)[0]
    pcs = [struct.unpack_from('<8H', d, 4 + 16 * i) for i in range(n)]
    pal = np.frombuffer(d[-512:], '<u2').astype(int)
    pg = np.frombuffer(d[0x200:0x8200], np.uint8).reshape(256, 128).copy()
    return d, pcs, pal, pg


def render(text, W, H):
    for size in range(H * 2, 20, -2):
        f = ImageFont.truetype(FONT, size * 4)
        im = Image.new('L', (size * 4 * (len(text) + 2), size * 8), 0); ImageDraw.Draw(im).text((16, 16), text, font=f, fill=255)
        a = np.array(im.resize((im.width // 4, im.height // 4), Image.BOX)) >= 120
        ys, xs = np.nonzero(a); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        if a.shape[0] <= H and a.shape[1] <= W: return a
    raise ValueError(text)


def dil(m, r):
    """둥근 팽창 — 감아 돌지 않게(np.roll 은 아래 그림자가 맨 위로 넘어감)."""
    H, W = m.shape; P = np.pad(m, r); o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy * dy + dx * dx <= r * r + 1: o |= P[r - dy:r - dy + H, r - dx:r - dx + W]
    return o


def build(kind):
    text, c_in, c_out, sample = JOBS[kind]
    d, pcs, pal, pg = load(sample)
    p0, p1 = pcs[0], pcs[1]
    # 원본 몸 색(테두리·흰 바탕 제외) 행별 최다 → 위→아래 그라데이션 목록
    body = []
    for (sx, sy, w, h, u, v, _, _) in (p0, p1):
        for y in range(h):
            r = pg[v + y, u:u + w]; r = r[(r != 0) & (r != 192) & (r != 16) & (r != c_in) & (r != c_out)]
            if len(r): body.append((sy + y, collections.Counter(r.tolist()).most_common(1)[0][0]))
    ys0 = sorted(set(y for y, _ in body)); grad = [collections.Counter(c for y2, c in body if y2 == y).most_common(1)[0][0] for y in ys0]
    # 몸 색 = 밝은 색만(어두운 테두리·그림자 계열 제외), 밝기 순(위 밝음 → 아래 어두움) — 되돌아가는 색이 가로 줄무늬(하스피 «가로줄»)
    lum = lambda c: ((pal[c] & 31) * 3 + (pal[c] >> 5 & 31) * 6 + (pal[c] >> 10 & 31))
    cnt = collections.Counter()
    for (sx, sy, w, h, u, v, _, _) in (p0, p1):
        r = pg[v:v + h, u:u + w].ravel(); cnt.update(r[(r != 0) & (r != 192) & (r != 16) & (r != c_in) & (r != c_out)].tolist())
    R_ = lambda c: (pal[c] & 31) << 3; G_ = lambda c: (pal[c] >> 5 & 31) << 3; B_ = lambda c: (pal[c] >> 10 & 31) << 3
    if kind == 'WIN': grad = sorted([c for c in cnt if R_(c) >= 240 and B_(c) <= 16 and G_(c) >= 96], key=lambda c: -G_(c))     # 노랑 → 주황
    else:             grad = sorted([c for c in cnt if B_(c) >= 240 and G_(c) <= 16 and R_(c) >= 96], key=lambda c: -R_(c))     # 자홍 → 보라
    assert len(grad) >= 3, (kind, grad)
    # 두 조각 합친 화면 상자(세로 = 두 조각 겹치는 범위)
    X0, X1 = p0[0], p1[0] + p1[2]; Y0 = max(p0[1], p1[1]); Y1 = min(p0[1] + p0[3], p1[1] + p1[3])
    W, H = X1 - X0, Y1 - Y0
    # «!!» 조각(원본 그대로) 아래끝에 글자 테두리 아래끝을 맞춤(하스피 «느낌표가 아래에 붙음»)
    d2_ = open('work/files/DATA/BTLEND/%s.BIN' % sample, 'rb').read(); pg2_ = np.frombuffer(d2_[0x8200:0x10200], np.uint8).reshape(256, 128)
    ex = pcs[2]; eb = pg2_[ex[5]:ex[5] + ex[3], ex[4] - 128:ex[4] - 128 + ex[2]]
    exb = ex[1] + int(np.nonzero(((eb != 0) & (eb != 192) & (eb != 16)).any(1))[0].max())     # 화면 y
    tb = exb - 3                                                   # 글자 몸 아래끝(테두리 3px 위)
    m = render(text, W - 10, min(H - 12, tb - Y0 - 3))
    T = np.zeros((H, W), bool); oy = tb - Y0 - m.shape[0] + 1; ox = (W - m.shape[1]) // 2
    assert oy >= 3, (kind, oy)
    if kind == 'LOS': ox = W - m.shape[1] - 6                       # «졌다» 는 짧아 «!!» 쪽으로 붙임
    T[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
    ring1 = dil(T, 2) & ~T; ring2 = dil(T, 3) & ~T & ~ring1
    sh = np.zeros_like(T); sh[3:] = dil(T, 2)[:-3]; sh &= ~(T | ring1 | ring2)                  # 아래 그림자
    can = np.zeros((H, W), np.uint8)
    can[sh] = c_out; can[ring2] = c_out; can[ring1] = c_in
    rows = np.nonzero(T.any(1))[0]; t0, t1 = rows.min(), rows.max()
    for y in range(H):
        if T[y].any():
            k = int((y - t0) * (len(grad) - 1) / max(1, t1 - t0)); can[y][T[y]] = grad[k]
    new = pg.copy()
    for (sx, sy, w, h, u, v, _, _) in (p0, p1):
        new[v:v + h, u:u + w] = 0
        for y in range(h):
            Y = sy + y - Y0
            if 0 <= Y < H: new[v + y, u:u + w] = can[Y, sx - X0:sx - X0 + w]
    pg2 = np.frombuffer(d[0x8200:0x10200], np.uint8).reshape(256, 128).copy(); new2 = pg2.copy()
    sx, sy, w, h, u, v, _, _ = pcs[2]; uu = u - 128
    blk = new2[v:v + h, uu:uu + w]; ink = (blk != 0) & (blk != 192) & (blk != 16)
    seen = np.zeros_like(ink); nrm = 0
    for y0 in range(h):
        if not ink[y0, 0] or seen[y0, 0]: continue
        st = [(y0, 0)]; seen[y0, 0] = True; comp = []
        while st:
            a, b = st.pop(); comp.append((a, b))
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                na, nb = a + da, b + db
                if 0 <= na < h and 0 <= nb < w and ink[na, nb] and not seen[na, nb]: seen[na, nb] = True; st.append((na, nb))
        for a, b in comp: blk[a, b] = 0
        nrm += len(comp)
    return pg, new, pal, pcs, (X0, Y0, can), pg2, new2, nrm


def compose(pg, pal, pcs, d2=None):
    """화면처럼(조각 0·1 + «!!» 조각 2) 합성 — 미리보기."""
    P = np.stack([(pal & 31) << 3, (pal >> 5 & 31) << 3, (pal >> 10 & 31) << 3], 1).astype(np.uint8)
    scr = np.zeros((150, 320, 3), np.uint8); scr[:] = (60, 110, 60)
    pg2 = d2
    for k, (sx, sy, w, h, u, v, _, _) in enumerate(pcs[:3]):
        src = pg if k < 2 else pg2
        uu = u if k < 2 else u - 128                                  # «!!» 는 둘째 쪽(u 128 = 그 쪽 0열)
        blk = src[v:v + h, uu:uu + w]; reg = scr[sy:sy + h, sx:sx + w]
        msk = (blk != 0) & (blk != 192)
        reg[msk] = P[blk][msk]
    return scr


if __name__ == '__main__':
    for kind in JOBS:
        pg, new, pal, pcs, _, pg2, new2, nrm = build(kind)
        a = compose(pg, pal, pcs, pg2); b = compose(new, pal, pcs, new2)
        np.save(OUT + '/%s_page2_new.npy' % kind, new2); print(kind, '«!!» 조각 왼쪽 찌꺼기 지움', nrm)
        s = np.vstack([a, np.zeros((4, 320, 3), np.uint8), b])
        Image.fromarray(s).resize((640, s.shape[0] * 2), Image.NEAREST).save(OUT + '/미리보기_%s_위원본_아래한글.png' % kind)
        np.save(OUT + '/%s_page1_new.npy' % kind, new)
        print(kind, OUT)
