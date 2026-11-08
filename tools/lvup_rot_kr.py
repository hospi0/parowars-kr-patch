# -*- coding: utf-8 -*-
"""그림 J 회전 프레임 — 맵 레벨업 «ﾚﾍﾞﾙUP» 이 가로축으로 도는 12장(MATI.BIN 0x11728 부터 띠 3개 × 16줄 × 128열, 띠마다 4장).
   (하스피 «한글이 순간 보이다 일어가 보임, 돌아가는 프레임마다 다 있는 듯» — lvup_kr.py 는 첫 장(띠0 0~40열)만 바꿨었다)
   실측(파일 오름차순 = 똑바로): 프레임 열 범위 [3,36) [43,77) [91,125) — 80~88열 세로 막대는 다른 그림(건드리지 않음).
   기준(정면 최대) = 띠2 [43,77) 높이 14. 나머지 = 세로로 줄고 뒤집히고 뒷면(어두운 0x33~0x37)인 변형.
   한글 = 기준 상자에 맞춘 «레벨UP» 마스크(레벨·UP·그림자 3종)를 프레임마다 원본 상자 크기로 줄이고, 원본과 같은 쪽으로 뒤집고,
   색은 원본 프레임의 같은 행 왼쪽(레벨 자리)·오른쪽(UP 자리) 최다 색을 씀.
   python tools/lvup_rot_kr.py → work/미리보기_그림_J/lvup_rot_new.bin(0x11728 부터 띠 3개 6,144 B) + 미리보기"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf
sys.stdout.reconfigure(encoding='utf-8')
OUT = 'work/미리보기_그림_J'; os.makedirs(OUT, exist_ok=True)
LO = 0x11728
COLS = [(3, 40), (43, 80), (91, 128)]           # 80~88열 세로 막대는 다른 그림 — 범위 밖
GA = bdf.Font('C:/claude/utils/font/Galmuri-v2.40.3/Galmuri11-Condensed.bdf')      # 레벨 15px 폭 — 기준 상자 33px 에 줄임 없이
GB = bdf.Font('C:/claude/utils/font/Galmuri-v2.40.3/Galmuri11-Bold.bdf')


_V = np.frombuffer(open('work/st/lvup_rot/vram.bin', 'rb').read(), '<u2').reshape(512, 1024)[237, 256:512].astype(int)
LUM = np.array([((c & 31) * 3 + (c >> 5 & 31) * 6 + (c >> 10 & 31)) for c in _V])      # 밝기(팔레트 VRAM (256,237))


def mask(F, s):
    pts = []; x = 0
    for ch in s:
        p, w = F.draw(ch); pts += [(x + a, b) for a, b in p]; x += w
    xs = [a for a, b in pts]; ys = [b for a, b in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for a, b in pts: m[b - min(ys), a - min(xs)] = True
    return m


def bands(d):
    return [np.array([np.frombuffer(d[LO + 2048 * j + 128 * y:LO + 2048 * j + 128 * y + 128], np.uint8) for y in range(16)]).copy() for j in range(3)]


def frames(B):
    out = []
    for j in range(3):
        for (s, e) in COLS:
            sub = B[j][:, s:e]; rows = np.nonzero(sub[2:].any(1))[0] + 2
            if not len(rows): continue
            cols = np.nonzero(sub[2:].any(0))[0]
            out.append((j, s + cols.min(), s + cols.max() + 1, rows.min(), rows.max() + 1))
    return out


def master(W, H):
    """기준 상자 W×H 안의 «레벨UP»: 값 1 = 레벨 몸, 2 = UP 몸, 3 = 그림자(오른쪽 아래 1px)."""
    a = mask(GA, '레벨'); u = mask(GB, 'UP')
    h = max(a.shape[0], u.shape[0]); w = a.shape[1] + u.shape[1]
    M = np.zeros((h + 1, w + 2), np.uint8)
    M[h - a.shape[0]:h, 0:a.shape[1]][a] = 1
    M[h - u.shape[0]:h, a.shape[1] + 1:a.shape[1] + 1 + u.shape[1]][u] = 2
    L_ = M == 1; U = M == 2
    shL = np.zeros_like(L_); shL[1:, 1:] = L_[:-1, :-1]
    shU = np.zeros_like(U); shU[1:, 1:] = U[:-1, :-1]
    body = M > 0
    M[shL & ~body] = 3                                 # 레벨 그림자(오른쪽 아래 1px)
    M[shU & ~body] = 4                                 # UP 그림자(오른쪽 아래 1px, 원본 빨강) — 둘레 테두리는 획 사이를 메워 세로줄이 됨(하스피)
    return M


def fit(M, w, h):
    """마스크를 w×h 로 — 상자가 크거나 같으면 가운데 놓기(늘이지 않음), 작을 때만 가장 가까운 화소로 줄임(세로 회전 = 높이만 줄어듦)."""
    def one(A, n, ax):
        m = A.shape[ax]
        if n >= m:
            pad = [(0, 0), (0, 0)]; pad[ax] = ((n - m) // 2, n - m - (n - m) // 2)
            return np.pad(A, pad)
        idx = (np.arange(n) * m / n).astype(int)
        return A[idx] if ax == 0 else A[:, idx]
    return one(one(M, h, 0), w, 1)


def orient(orig_box, ref_box):
    """원본 프레임이 기준을 위아래로 뒤집은 것인지 — 기준을 같은 크기로 줄여 두 방향 비교."""
    a = orig_box > 0; r0 = fit(ref_box, a.shape[1], a.shape[0]) > 0
    return int((a == r0[::-1]).sum() > (a == r0).sum())


def build(d):
    B = bands(d); F = frames(B); N = [b.copy() for b in B]
    # 기준 = 가장 높은 프레임
    ref = max(F, key=lambda f: f[4] - f[3]); j0, x0, x1, y0, y1 = ref
    ref_box = B[j0][y0:y1, x0:x1]
    M = master(x1 - x0, y1 - y0)
    info = []
    for (j, a, b, c, e) in F:
        ob = B[j][c:e, a:b]; w, h = b - a, e - c
        fl = orient(ob, ref_box) if (j, a) != (j0, x0) else 0
        m = fit(M, w, h)
        if fl: m = m[::-1]
        upc = np.nonzero(np.isin(ob, [0x0E, 0x0F, 0x3C, 0x3D, 0x3E, 0x3F]).any(0))[0]   # 원본 UP 색이 있는 열
        mup = np.nonzero((m == 2).any(0))[0]
        split = int(upc.min()) if len(upc) else (int(mup.min()) if len(mup) else w // 2)   # 레벨|UP 경계 열(원본 기준, 없으면 한글 마스크)
        # 색: 원본 프레임 왼쪽(레벨)·오른쪽(UP) 화소를 밝기로 밝은 쪽(몸)·어두운 쪽(그림자·테두리)으로 나눔.
        #     몸 = 그 행(없으면 가까운 행)의 밝은 색 최다 — 세로 그라데이션 유지. 그림자·테두리 = 어두운 색 최다(하스피 «아래쪽 다 회색·UP 가로줄»).
        def split_cols(part):
            v = part[part > 0]
            if not len(v): return None, set(), set()
            l = LUM[v]; thr = (int(l.max()) + int(l.min())) / 2
            hi = set(int(x) for x in v if LUM[x] >= thr); lo = set(int(x) for x in v if LUM[x] < thr)
            dark = np.bincount([x for x in v if x in lo]).argmax() if lo else None
            return dark, hi, lo
        dL, hiL, _ = split_cols(ob[:, :split]); dR, hiR, _ = split_cols(ob[:, split:])
        def row_body(y, x0_, x1_, hi):
            for dy in range(h):
                for yy in (y - dy, y + dy):
                    if 0 <= yy < h:
                        v = [int(x) for x in ob[yy, x0_:x1_] if int(x) in hi]
                        if v: return np.bincount(v).argmax()
            return max(hi, key=lambda x: LUM[x]) if hi else 1
        new = np.zeros_like(ob)
        # 몸통 = 프레임 전체 밝은 색 최다 한 색(줄마다 바꾸면 가로줄 — 하스피), 획 왼쪽 가장자리 = 둘째 밝은 색(원본 3D 세로 하이라이트)
        def top2(part, hi):
            v = [int(x) for x in part[part > 0] if int(x) in hi]
            if not v: return None, None
            cnt = np.bincount(v); o = [k for k in np.argsort(-cnt) if cnt[k]]
            return o[0], (o[1] if len(o) > 1 else o[0])
        cl, cl2 = top2(ob[:, :split], hiL); cr, cr2 = top2(ob[:, split:], hiR)
        cl = 1 if cl is None else cl; cl2 = cl if cl2 is None else cl2
        if cr is None: cr, cr2 = cl, cl2
        upb = [int(x) for x in ob[ob > 0] if int(x) in (0x3C, 0x3D, 0x3E, 0x3F)]   # 원본에 UP 색이 있으면 그것만(회색·흰색이 더 많아도)
        if upb:
            cnt = np.bincount(upb); o_ = [k for k in np.argsort(-cnt) if cnt[k]]
            cr, cr2 = o_[0], (o_[1] if len(o_) > 1 else o_[0])
        upr = [int(x) for x in ob[ob > 0] if int(x) in (0x0E, 0x0F)]
        if upr: dR = np.bincount(upr).argmax()
        for y in range(h):
            new[y][m[y] == 1] = cl; new[y][m[y] == 2] = cr
            for x in range(w):
                if m[y, x] == 2 and (x == 0 or m[y, x - 1] != 2): new[y, x] = cr2
            new[y][m[y] == 3] = dL if dL is not None else cl
            new[y][m[y] == 4] = dR if dR is not None else (dL if dL is not None else cr)
        N[j][c:e, a:b] = new
        info.append((j, a, b, c, e, '뒤집힘' if fl else '', ''.join('%02x' % v for v in sorted(set(ob[ob > 0].tolist()))[:6])))
    blob = b''.join(n.tobytes() for n in N)
    return B, N, blob, info


if __name__ == '__main__':
    d = open('work/files/DATA/MATI.BIN', 'rb').read()
    B, N, blob, info = build(d)
    for i in info: print(i)
    open(OUT + '/lvup_rot_new.bin', 'wb').write(blob)
    V = np.frombuffer(open('work/st/lvup_rot/vram.bin', 'rb').read(), '<u2').reshape(512, 1024); CL = V[237, 256:512].astype(int)
    pal = np.zeros((256, 3), np.uint8)
    for i in range(256): c = int(CL[i]); pal[i] = ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)
    pal[0] = (40, 90, 40)
    rows = []
    for o, n in zip(B, N):
        rows.append(np.hstack([pal[o][:, :126], np.full((16, 6, 3), 255, np.uint8), pal[n][:, :126]]))
        rows.append(np.full((3, rows[-1].shape[1], 3), 255, np.uint8))
    g = np.vstack(rows)
    Image.fromarray(g).resize((g.shape[1] * 6, g.shape[0] * 6), Image.NEAREST).save(OUT + '/미리보기_레벨업_회전12장_왼쪽원본_오른쪽한글.png')
    print(OUT)
