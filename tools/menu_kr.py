# -*- coding: utf-8 -*-
"""묶음 A — 메뉴 글자판(DEMO/KABE0 압축 덩어리 0x8000 쪽 = VRAM (896,0), 8비트 128×256) 한글화 — 미리보기 전용.
   구조: 제목은 낱말 조각을 이어 붙임 [レベル]+[を選んで下さ]+[い。]. 한국어는 조사를 앞 낱말에: [레벨을]+[선택해 주세]+[요.]
   색: 조각마다 팔레트가 달라 색 번호는 «역할»(글자 몸·외곽선·그림자·중간색)만 공통 → 원래 조각에서 역할 번호를 읽어 같은 번호로 그림.
   글꼴: 원본처럼 둥글고 굵은 Jua, 외곽선 1px + 오른쪽 아래 그림자 1px.
   python tools/menu_kr.py → work/미리보기_그림_A/"""
import sys, os, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding='utf-8')
FONT = r'C:\claude\utils\font\jua\Jua-Regular.ttf'
OUT = 'work/미리보기_그림_A'; os.makedirs(OUT, exist_ok=True)
# (상자 x0,y0,x1,y1 — 글자판 좌표, 한글, 설명)
# (u, v, w, h — 게임 스프라이트 사각형(work/kabe0_rects.txt, 램의 GPU 패킷), 한글, 정렬 L/R/C/J, 설명)
EDITS = [
    (0, 0, 32, 24, '결정', 'C', '버튼 決定'),
    (32, 0, 32, 24, '뒤로', 'C', '버튼 戻る'),
    (0, 24, 48, 24, '도움말', 'C', '버튼 ヘルプ'),
    (48, 24, 48, 24, '맵', 'C', '버튼 マップ'),
    (0, 48, 128, 24, '선택해 주세', 'R', '제목 공용 を選んで下さ'),
    (96, 24, 32, 24, '요.', 'L', '제목 끝 い。'),
    (0, 72, 64, 24, '모드를', 'R', '제목 モード'),
    (64, 72, 64, 24, '레벨을', 'R', '제목 レベル'),
    (0, 96, 128, 24, '캐릭터를', 'R', '제목 キャラクター'),
    (0, 128, 64, 24, '맵을', 'R', '제목 マップ'),
    (0, 152, 128, 16, '맵 스테이터스', 'R', '제목 マップステー'),
    (0, 168, 112, 16, ' 변경', 'L', '제목 タスの変更'),
    (0, 184, 48, 16, '레벨', 'C', '항목 レベル'),
    (48, 184, 80, 16, '에너지', 'C', '항목·도움말 エネルギー'),
    (0, 200, 40, 16, '시야', 'C', '항목·도움말 視界'),
    (0, 216, 64, 16, '쉬움', 'C', '선택지 やさしい'),
    (64, 216, 32, 16, '있음', 'C', '선택지 あり'),
    (96, 216, 32, 16, '없음', 'C', '선택지 なし'),
    (0, 232, 80, 16, '어려움', 'C', '선택지 むずかしい'),
]


def shift(m, dy, dx):
    """넘어가지 않는 밀기(빈자리 0). np.roll 은 조각 끝에서 반대편으로 돌아 나와 찌꺼기를 만든다(실기 «요» 오른쪽 위)."""
    o = np.zeros_like(m); H, W = m.shape
    o[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = m[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
    return o


def dil(m, r=1):
    o = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1): o |= shift(m, dy, dx)
    return o


def roles(sub):
    """원래 조각의 역할 번호: 몸(안쪽 최다), 외곽선(가장자리 최다), 그림자(오른쪽 아래 바깥), 중간색."""
    m = sub > 0
    # 글자 몸 = 투명에서 가장 먼 화소들(얇은 획도 판정되게 거리 단계로)
    dist = np.zeros(m.shape, int); cur = m.copy(); k = 0
    while cur.any() and k < 6:
        k += 1; dist[cur] = k; cur = cur & ~dil(~cur)
    inner = dist >= max(2, dist.max() - 0) if dist.max() >= 2 else m
    edge = m & (dist == 1)
    c_in = collections.Counter(sub[inner].tolist()); c_ed = collections.Counter(sub[edge].tolist())
    fill = c_in.most_common(1)[0][0]
    outl = [i for i, _ in c_ed.most_common() if i != fill][:2]
    rest = [i for i, _ in collections.Counter(sub[m].tolist()).most_common() if i not in (fill,) + tuple(outl)]
    return fill, outl[0] if outl else fill, (outl[1] if len(outl) > 1 else (rest[0] if rest else outl[0]))


def glyphs_at(text, size, SS=4):
    """고정 글꼴 크기로 한 줄(4배 그려 줄임). 높이는 글자마다 같은 기준선."""
    f = ImageFont.truetype(FONT, size * SS)
    im = Image.new('L', (size * SS * (len(text) + 2), size * SS * 2), 0); ImageDraw.Draw(im).text((SS * 2, SS * 2), text, font=f, fill=255)
    im = im.resize((im.width // SS, im.height // SS), Image.BOX)
    a = np.array(im) / 255.0; ys, xs = np.nonzero(a >= 0.12)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def render(text, w, h, justify=False):
    """글자별로 그려 칸 높이에 맞추고, justify 면 칸 너비 전체에 고르게 벌린다(이어 붙는 제목 조각)."""
    for size in range(h + 6, 6, -1):
        f = ImageFont.truetype(FONT, size)
        gl = []
        SS = 4                                               # 4배로 그려 면적 평균으로 줄임(작은 크기 뭉개짐·들쭉날쭉 방지)
        fbig = ImageFont.truetype(FONT, size * SS)
        for ch in text:
            if ch == ' ': gl.append(None); continue
            im = Image.new('L', (size * 2 * SS, size * 2 * SS), 0); ImageDraw.Draw(im).text((2 * SS, 2 * SS), ch, font=fbig, fill=255)
            im = im.resize((size * 2, size * 2), Image.BOX)
            a = np.array(im) / 255.0; ys, xs = np.nonzero(a >= 0.12)
            gl.append((a, ys, xs))
        ys_all = [g[1] for g in gl if g]; top = min(y.min() for y in ys_all); bot = max(y.max() for y in ys_all)
        H = bot - top + 1
        if H > h - (3 if h <= 16 else 6): continue                # 위아래 여유(테두리·그림자 자리)
        ws = [g[2].max() - g[2].min() + 1 if g else size // 3 for g in gl]
        gap = 1
        total = sum(ws) + gap * (len(ws) - 1)
        if total > w - 4: continue
        if justify and len(ws) > 1: gap = max(1, (w - 4 - sum(ws)) // (len(ws) - 1))
        out = np.zeros((H, sum(ws) + gap * (len(ws) - 1)), float); x = 0
        for g, wd in zip(gl, ws):
            if g:
                a, ys, xs = g; out[:, x:x + wd] = np.maximum(out[:, x:x + wd], a[top:bot + 1, xs.min():xs.max() + 1])
            x += wd + gap
        return out
    return out


BASE = 20                                                  # 24줄 제목 조각의 글자 바닥선
GROUPS = {('맵 스테이터스', ' 변경'): ('맵 스테이터스 변경', 'C'), ('선택해 주세', '요.'): ('선택해 주세요.', 'L')}   # 항상 붙어 다니는 조각: 한 줄로 그려 나눠 넣음       # 화면에서 이어 붙는 조각: 한 줄로 가운데 정렬 후 잘라 넣음


CLUT = np.frombuffer(open('work/st/5/vram.bin', 'rb').read(), '<u2').reshape(512, 1024)[238, 256:512].astype(int)


def nearest(rgb, pool):
    c = np.array([[(CLUT[i] & 31) * 8, (CLUT[i] >> 5 & 31) * 8, (CLUT[i] >> 10 & 31) * 8] for i in pool])
    return pool[int(((c - np.array(rgb)) ** 2).sum(1).argmin())]


def rgbof(i): return np.array([(CLUT[i] & 31) * 8, (CLUT[i] >> 5 & 31) * 8, (CLUT[i] >> 10 & 31) * 8])


def place(sheet, out, u, v, w, h, cov, desc):
    """cov(덮인 비율 0~1, h×w)로 그림: ≥0.5 글자 몸, 0.2~0.5 중간색(가장자리 부드럽게), 그 바깥 1px 테두리, 오른쪽 아래 1px 그림자."""
    sub = sheet[v:v + h, u:u + w]
    T = cov >= 0.5; Mid = (cov >= 0.2) & ~T; A = T | Mid
    O = dil(A) & ~A; S = shift(A | O, 1, 1) & ~(A | O)
    if desc.startswith('버튼'):
        # 바탕 = 글자판 안 버튼 띠 몸통 조각(uv 112,0 7×24) 세로 그라데이션 → 원래 글자 찌꺼기 없이 통째로 다시 깔기
        bg = sheet[0:24, 115].copy()
        new = np.repeat(bg[:h, None], w, 1)
        pool = sorted(set(bg.tolist()) | {BTN_DARK, BTN_LIGHT})
        Sb = shift(A, 1, 1) & ~A
        new[Sb] = BTN_LIGHT
        for y in range(h):
            mi = nearest((rgbof(BTN_DARK) + rgbof(bg[y])) / 2, pool)
            new[y][Mid[y]] = mi
        new[T] = BTN_DARK
        out[v:v + h, u:u + w] = new; return ('버튼', BTN_DARK, BTN_LIGHT)
    # 무리별 색 역할 고정(팔레트 VRAM 256,238 실측: 53 흰 · 54 회보라 · 55 진회청 · 56 남 · 57 검 · 85 노랑 · 86 황토 · 87 갈 · 88 진빨강)
    if desc.startswith('제목'): fill, mid, outl, shad = 53, 54, 56, 57      # 흰 글자 · 남색 테두리 · 검은 그림자
    elif desc.startswith('선택지'): fill, mid, outl, shad = 56, 55, 53, 54  # 남색 글자 · 흰 테두리
    elif desc.startswith('항목'): fill, mid, outl, shad = 85, 86, 88, 87    # 노란 글자 · 진빨강 테두리
    else:
        fill, outl, shad = roles(sub); mid = outl
    new = np.zeros((h, w), int); new[S] = shad; new[O] = outl; new[Mid] = mid; new[T] = fill
    out[v:v + h, u:u + w] = new; return (fill, outl, shad)


def build(sheet):
    global BTN_DARK, BTN_LIGHT, BTN_GLYPH
    # 버튼 글자색: 원래 決定 조각에서 바탕(몸통 세로줄)과 다른 화소 중 가장 어두운·밝은 번호
    sub = sheet[0:24, 0:32]; bgc = sheet[0:24, 115]; txt = (sub > 0) & (sub != bgc[:, None])
    cand = [i for i, _ in collections.Counter(sub[txt].tolist()).most_common(8)]
    br = lambda i: (lambda q: (q & 31) + (q >> 5 & 31) + (q >> 10 & 31))(int(CLUT[i]))
    BTN_DARK = min(cand, key=br); BTN_LIGHT = max(cand, key=br)
    # 버튼 글자 크기 통일: 글꼴 크기 하나로 모든 버튼(원본 버튼 글자 높이 ≈ 15px 이하, 각 칸 폭 안)
    btns = [(e[4], e[2]) for e in EDITS if e[6].startswith('버튼')]
    for size in range(22, 8, -1):
        gl = {ko: glyphs_at(ko, size) for ko, _ in btns}
        if all(g.shape[0] <= 15 and g.shape[1] <= w - 6 for (ko, w), g in zip(btns, gl.values())): break
    BTN_GLYPH = gl
    global BTN_SIZE; BTN_SIZE = size
    out = sheet.copy(); info = []
    E = list(EDITS); done = set()
    for (k1, k2), (full, gal) in GROUPS.items():
        a = [e for e in E if e[4] == k1][0]; b = [e for e in E if e[4] == k2][0]
        W = a[2] + b[2]; h = a[3]
        t = render(full, W - 4, h); th, tw = t.shape
        L = np.zeros((h, W), float); ox = (W - tw) // 2 if gal == 'C' else 5     # L: 앞 낱말과 한 칸 띄움
        oy = (BASE - th) if h == 24 else (h - th) // 2 - 1
        L[oy + 1:oy + 1 + th, ox:ox + tw] = t
        info.append((a[6], full, place(sheet, out, a[0], a[1], a[2], h, L[:, :a[2]], a[6])))
        info.append((b[6], full, place(sheet, out, b[0], b[1], b[2], h, L[:, a[2]:], b[6])))
        done |= {k1, k2}
    for u, v, w, h, ko, al, desc in E:
        if ko in done: continue
        sub = sheet[v:v + h, u:u + w]
        if desc.startswith('버튼'):
            t = BTN_GLYPH[ko]                                         # 버튼은 모두 같은 크기(가장 좁은 칸에 맞춘 한 크기)
        else:
            t = render(ko.strip(), w - 2, h, justify=(al == 'J'))
        th, tw = t.shape
        if al == 'R': ox = w - tw - 3
        elif al == 'L': ox = 1
        else: ox = (w - tw) // 2 - 1
        ys = np.nonzero((sub > 0).any(1))[0]; oy = ((ys.min() + ys.max()) // 2 - th // 2 - 1) if len(ys) else (h - th) // 2
        if desc.startswith('제목') and h == 24: oy = BASE - th - 1                     # 제목 조각은 같은 바닥선
        oy = max(0, min(h - th - 2, oy)); ox = max(0, min(w - tw - 2, ox))
        T = np.zeros((h, w), float); T[oy + 1:oy + 1 + th, ox + 1:ox + 1 + tw] = t
        info.append((desc, ko, place(sheet, out, u, v, w, h, T, desc)))
    return out, info


if __name__ == '__main__':
    raw = open('work/st/5/vram.bin', 'rb').read(); b = np.frombuffer(raw, np.uint8).reshape(512, 2048)
    sheet = b[0:256, 896 * 2:960 * 2].astype(int)
    # 덩어리 안 위치 검증: KABE0 풀린 덩어리 0x8000 = VRAM (896,0) 쪽
    blob = open('work/unpk/DATA_DEMO_KABE0.BIN@0.bin', 'rb').read()
    assert bytes(blob[0x8000:0x8000 + 128 * 256]) == bytes(sheet.astype(np.uint8)), '덩어리 0x8000 ≠ VRAM 쪽'
    new, info = build(sheet)
    # 둘째 쪽: KABE0·KABE1 0x24000 (VRAM 576,256) — 버튼 前頁(uv 64,168)·次頁(uv 32,168) 32×24, 같은 버튼 양식
    pg = np.frombuffer(blob[0x24000:0x24000 + 128 * 256], np.uint8).reshape(256, 128).astype(int); pg_new = pg.copy()
    for u, v, w, h, ko in ((64, 168, 32, 24, '이전'), (32, 168, 32, 24, '다음')):
        g = glyphs_at(ko, BTN_SIZE); th, tw = g.shape
        T = np.zeros((h, w), float); oy = (h - th) // 2 - 1; ox = (w - tw) // 2 - 1
        T[oy + 1:oy + 1 + th, ox + 1:ox + 1 + tw] = g
        info.append(('버튼2 ' + ko, ko, place(sheet, pg_new, u, v, w, h, T, '버튼')))
    np.save(OUT + '/page24000_new.npy', pg_new)
    # KABE1 의 같은 쪽은 다른 곳이 1만 바이트 달라 통째로 덮으면 안 됨 → 두 버튼 사각형만 옮긴 판
    blob1 = open('work/unpk/DATA_DEMO_KABE1.BIN@0.bin', 'rb').read()
    pg1 = np.frombuffer(blob1[0x24000:0x24000 + 128 * 256], np.uint8).reshape(256, 128).astype(int).copy()
    assert (pg1[168:192, 32:96] == pg[168:192, 32:96]).all()
    pg1[168:192, 32:96] = pg_new[168:192, 32:96]
    np.save(OUT + '/page24000_kabe1_new.npy', pg1)
    np.save(OUT + '/sheet_new.npy', new)
    for d in info: print(d)
    # 미리보기: 역할별 대표색(제목=흰·남·검, 항목=노랑 — 레벨 화면에서 읽은 색)
    P = np.load('work/pal_kabe0.npy').astype(int)
    TITLE = {53: 0x7FFF, 54: 0x5E94, 56: 0x2000, 57: 0x0000}
    def colorize(sh):
        im = np.zeros(sh.shape + (3,), np.uint8); im[:] = (120, 150, 120)       # 투명 = 연녹색
        for i in np.unique(sh):
            if i == 0: continue
            c = int(CLUT[i])                                   # 실제 팔레트 VRAM (256,238)
            im[sh == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
        return Image.fromarray(im)
    a = colorize(sheet).resize((512, 1024), Image.NEAREST); c = colorize(new).resize((512, 1024), Image.NEAREST)
    s = Image.new('RGB', (512 * 2 + 12, 1024), (0, 0, 0)); s.paste(a, (0, 0)); s.paste(c, (524, 0))
    s.save(OUT + '/미리보기_글자판_왼쪽원본_오른쪽한글.png')
    print(OUT)
