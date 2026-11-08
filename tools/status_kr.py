# -*- coding: utf-8 -*-
"""묶음 C — 맵 스테이터스 줄 이름표 13개(64×14, 나뭇결 바탕) + 칸 안 나라 이름 8개(54×12) 한글화 — 미리보기 + 빌드용 npy.
   글자판 = VRAM (0,256) 8비트 128×256, 팔레트 VRAM (256,238). 두 반쪽이 따로 실림(상태 10 실측):
     위 128줄(이름표) = KABE2 풀린 0x4000 = KABE3 풀린 0xC000 / 아래 128줄(나라 칸) = KABE2 풀린 0 = KABE3 풀린 0x8000.
   지우기: 사각형 안쪽 글자색 화소만 → 그 행 바탕 최다색(이름표 = 가로 줄무늬, 칸 = 단색 104).
   글자: 갈무리 BDF 화소 그대로(보간 없음). 이름표 = 갈무리11(넘치면 같은 높이 Condensed), 글자색 193.
         칸 = 갈무리9 자간 −1, 글자 111 + 아래 1px 밝은 그림자 102(원본 양식).
   python tools/status_kr.py → work/미리보기_그림_C/"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_C'; os.makedirs(OUT, exist_ok=True)
GD = r'C:\claude\utils\font\Galmuri-v2.40.3\\'
SMALL = set()
G7 = bdf.Font(GD + 'Galmuri7.bdf')
G11, G11C, G9 = bdf.Font(GD + 'Galmuri11.bdf'), bdf.Font(GD + 'Galmuri11-Condensed.bdf'), bdf.Font(GD + 'Galmuri9.bdf')
# 이름표 (u, v, w, h, 한글, 자간 더하기) — 원본처럼 짧은 이름은 벌려 씀
LABELS = [(0, 0, 64, 14, '국명', 8), (0, 14, 64, 14, '색', 0), (0, 28, 64, 14, '동맹', 8), (0, 42, 64, 14, '플레이어', 0),
          (0, 56, 64, 14, '컨트롤러', 0), (0, 70, 64, 14, '돈', 0), (0, 84, 64, 14, '과학력', 4), (0, 98, 64, 14, '에너지', 0),
          (0, 112, 64, 14, '도시 수', 0), (64, 0, 64, 14, '공장 수', 0), (64, 14, 64, 14, '콤비나트 수', 0),
          (64, 28, 64, 14, '공항 수', 0), (64, 42, 64, 15, '항구 수', 0)]
LABEL_TXT = {193, 196}
# 나라 칸 (u, v(아래 반쪽 기준 +128), 한글) — 원본 «こいつあいつ国»도 ＆ 를 빼고 줄여 씀
CELLS = [(0, 128, '펭타 왕국'), (56, 128, '미카엘 제국'), (0, 144, '아카시야랜드'), (56, 144, '러블리 연방'),
         (0, 160, '이녀석저녀석'), (56, 160, '모아이국'), (0, 176, '판다국'), (56, 176, '멍멍국')]
CELL_W, CELL_H, CELL_BG, CELL_TXT, CELL_SH, CELL_MID = 54, 12, 104, 111, 102, 106


def text_mask(font, s, extra=0, squeeze=0):
    """BDF 화소 그대로 한 줄. extra = 글자 사이 더할 px, squeeze = 줄일 px. → bool 배열(잉크 범위로 자름)."""
    pts = []; x = 0
    for ch in s:
        p, w = font.draw(ch)
        pts += [(x + a, b) for a, b in p]
        x += w + extra - squeeze
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for a, b in pts: m[b - min(ys), a - min(xs)] = True
    return m, min(ys)


def erase(sub, txt):
    """글자색 화소 → 그 행의 글자 아닌 화소 최다색."""
    out = sub.copy()
    for y in range(sub.shape[0]):
        row = sub[y]; keep = row[~np.isin(row, list(txt))]
        if len(keep) and np.isin(row, list(txt)).any():
            out[y][np.isin(row, list(txt))] = np.bincount(keep).argmax()
    return out


def build(pg):
    new = pg.copy(); info = []
    for u, v, w, h, ko, ex in LABELS:
        sub = pg[v:v + h, u:u + w]
        inner = sub[1:h - 1, 2:w - 2].copy()                     # 나뭇결 = 행마다 한 색(실측) → 안쪽을 행 최다색으로 통째로(글자 밝은 테두리 찌꺼기까지)
        for y in range(inner.shape[0]): inner[y] = np.bincount(inner[y][~np.isin(inner[y], list(LABEL_TXT))]).argmax()
        new[v + 1:v + h - 1, u + 2:u + w - 2] = inner
        font = G11
        m, top = text_mask(font, ko, ex)
        if m.shape[1] > w - 6: font = G11C; m, top = text_mask(font, ko, ex)
        assert m.shape[1] <= w - 6 and m.shape[0] <= h - 2, (ko, m.shape)
        # 세로: 원본 글자 잉크 가운데에 맞춤(한글 상자 기준 — 줄마다 같은 높이)
        _, t2 = text_mask(font, '가'); mg, _ = text_mask(font, '한')
        oy = v + (h - mg.shape[0]) // 2 + (top - t2) + 1; ox = u + (w - m.shape[1]) // 2     # +1 = 하스피 «한 픽셀 내려줘»(2026-11-08)
        assert oy + m.shape[0] <= v + h - 1, (ko, '아래 테두리 침범')
        new[oy:oy + m.shape[0], ox:ox + m.shape[1]][m] = 193
        info.append((ko, 'G11C' if font is G11C else 'G11', m.shape))
    for u, v, ko in CELLS:
        sub = pg[v:v + CELL_H, u:u + CELL_W]
        assert set(np.unique(sub).tolist()) <= {CELL_BG, CELL_TXT, CELL_SH, CELL_MID, 108, 109, 0}, (ko, set(np.unique(sub).tolist()))
        new[v:v + CELL_H, u:u + CELL_W] = np.where(sub == 0, 0, CELL_BG)
        fnt = G7 if ko in SMALL else G9
        m, top = text_mask(fnt, ko, 0, 1 if fnt is G9 else 0)
        if m.shape[1] > CELL_W - 2: m, top = text_mask(fnt, ko, 0, 2)      # 긴 이름(6자)은 자간 −2
        assert m.shape[1] <= CELL_W - 2, (ko, m.shape)
        _, t2 = text_mask(fnt, '가'); mg, _ = text_mask(fnt, '한')
        oy = v + (CELL_H - 1 - mg.shape[0]) // 2 + (top - t2); ox = u + (CELL_W - m.shape[1]) // 2
        S = np.zeros((CELL_H, CELL_W), bool); T = np.zeros((CELL_H, CELL_W), bool)
        T[oy - v:oy - v + m.shape[0], ox - u:ox - u + m.shape[1]] = m
        S[1:] = T[:-1]; S &= ~T
        blk = new[v:v + CELL_H, u:u + CELL_W]; blk[S & (blk != 0)] = CELL_SH; blk[T] = CELL_TXT
        info.append((ko, 'G9-1', m.shape))
    return new, info


def colorize(sh, CL):
    im = np.zeros(sh.shape + (3,), np.uint8); im[:] = (60, 140, 60)
    for i in np.unique(sh):
        if i: c = int(CL[i]); im[sh == i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    return Image.fromarray(im)


if __name__ == '__main__':
    b2 = open('work/unpk/DATA_DEMO_KABE2.BIN@0.bin', 'rb').read(); b3 = open('work/unpk/DATA_DEMO_KABE3.BIN@0.bin', 'rb').read()
    top = np.frombuffer(b2[0x4000:0x8000], np.uint8).reshape(128, 128); bot = np.frombuffer(b2[0:0x4000], np.uint8).reshape(128, 128)
    assert b3[0xC000:0x10000] == b2[0x4000:0x8000] and b3[0x8000:0xC000] == b2[0:0x4000]
    pg = np.vstack([top, bot]).astype(int)
    v = np.frombuffer(open('work/st/10/vram.bin', 'rb').read(), np.uint8).reshape(512, 2048)
    assert (v[256:512, 0:128] == pg).all(), 'VRAM (0,256) ≠ 덩어리'
    new, info = build(pg)
    for d in info: print(d)
    # 비교판: 6글자 이름 — ①지금(갈무리9 자간−2) ②«아카시야국» ③갈무리7
    CELLS0 = list(CELLS)
    CELLS[2] = (0, 144, '아카시야국'); v2, _ = build(pg)
    CELLS[:] = CELLS0; SMALL.update({'아카시야랜드', '이녀석저녀석'}); v3, _ = build(pg); SMALL.clear()
    np.save(OUT + '/status_top_new.npy', new[:128].astype(np.uint8)); np.save(OUT + '/status_bot_new.npy', new[128:].astype(np.uint8))
    CL = np.frombuffer(open('work/st/10/vram.bin', 'rb').read(), '<u2').reshape(512, 1024)[238, 256:512].astype(int)
    a = colorize(pg[:208], CL).resize((512, 832), Image.NEAREST); c = colorize(new[:208], CL).resize((512, 832), Image.NEAREST)
    s = Image.new('RGB', (512 * 2 + 12, 832 + 12 + 4 * 80), (0, 0, 0)); s.paste(a, (0, 0)); s.paste(c, (524, 0))
    for k, vv in enumerate((v2, v3)):                                     # 아래: 나라 칸만 대안 두 가지(②아카시야국 ③갈무리7)
        s.paste(colorize(vv[144:176, 0:112], CL).resize((448, 128), Image.NEAREST), (k * 524, 844))
    s.save(OUT + '/미리보기_글자판_왼쪽원본_오른쪽한글.png'); print(OUT)
