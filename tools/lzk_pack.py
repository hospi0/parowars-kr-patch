# -*- coding: utf-8 -*-
"""파로 워즈 LZ 압축기 — tools/lzk.py(게임 0x80013CAC 해제기)의 역. 창(1 KB, 0 채움, 쓰기 0x3DE)을 해제기와 똑같이 흉내 낸다.
   항목: 원문 1 B(플래그 0) / 긴 참조 c<0x80: 창 절대 위치·길이 3~34 / 짧은 참조 0x80~0xBF: 거리 1~15·길이 2~5 / 원문 묶음 0xC0+: 8~71 B.
   탐욕 + 1칸 미리 보기. 결과는 반드시 lzk.unpack 으로 되풀어 원본과 같은지 검사한다(pack() 안에서 assert).
   python tools/lzk_pack.py 원본 [출력]  /  python tools/lzk_pack.py --selftest"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzk


def _best(win, w, data, i):
    """창에서 가장 긴 일치. 복사 중 창이 바뀌는 것(겹침)까지 흉내. (길이, 종류, 값)"""
    n = len(data); best = (0, None, 0)
    maxl = min(34, n - i)
    if maxl < 2: return best
    # 짧은 참조: 거리 1~15, 길이 2~5
    for dist in range(1, 16):
        l = 0; tmp = {}
        while l < min(5, n - i):
            pos = (w - dist + l) & 0x3FF
            x = tmp.get(pos, win[pos])
            if x != data[i + l]: break
            tmp[(w + l) & 0x3FF] = x; l += 1
        if l >= 2 and l > best[0]: best = (l, 'S', dist)
    # 긴 참조: 창 절대 위치 0~1023, 길이 3~34
    first = data[i]
    for src in range(1024):
        if win[src] != first and not (src == w): continue
        l = 0; tmp = {}
        while l < maxl:
            pos = (src + l) & 0x3FF
            x = tmp.get(pos, win[pos])
            if x != data[i + l]: break
            tmp[(w + l) & 0x3FF] = x; l += 1
        if l >= 3 and l > best[0] and (l > 5 or best[1] != 'S' or l > best[0]):
            best = (l, 'L', src)
            if l == maxl: break
    return best


def pack(data, hdr3=0, tail=None, splits=0, nomatch=frozenset(), rec=None, items_only=False):
    win = bytearray(1024); w = 0x3DE
    items = []                   # (플래그 비트, 바이트들)
    lit = bytearray()

    def flush_lit():
        nonlocal lit
        while lit:
            if len(lit) >= 8:
                k = min(71, len(lit)); items.append((1, bytes([0xC0 | (k - 8)]) + bytes(lit[:k]))); lit = lit[k:]
            else:
                for b in lit: items.append((0, bytes([b])))
                lit = bytearray()

    def put(b):
        nonlocal w
        win[w] = b; w = (w + 1) & 0x3FF

    i = 0; n = len(data)
    while i < n:
        if (tail is not None and i >= tail) or i in nomatch:
            lit.append(data[i]); put(data[i]); i += 1; continue
        l, kind, val = _best(win, w, data, i)
        if l >= 3 or (kind == 'S' and l >= 2):
            # 미리 보기: 다음 자리에서 더 길면 지금은 원문
            if l < 34 and i + 1 < n:
                save_w, save_win = w, bytes(win)
                put(data[i]); l2 = _best(win, w, data, i + 1)[0]
                w = save_w; win[:] = save_win
                if l2 > l + 1:
                    lit.append(data[i]); put(data[i]); i += 1; continue
            flush_lit()
            if rec is not None: rec.append(i)
            if kind == 'S':
                items.append((1, bytes([0x80 | ((l - 2) << 4) | val])))
            else:
                items.append((1, bytes([((l - 3) << 2) | (val >> 8), val & 0xFF])))
            for k in range(l): put(data[i + k])
            i += l
        else:
            lit.append(data[i]); put(data[i]); i += 1
    flush_lit()
    if items_only: return items
    return _assemble(data, items, hdr3, splits)


def _assemble(data, items, hdr3, splits):
    items = list(items)
    while splits:                                            # 원문 묶음 하나를 둘로(+1 B) — 정확한 길이 맞추기용
        for k, (bit, b) in enumerate(items):
            if bit and b[0] >= 0xC0 and len(b) - 1 >= 16:
                m = len(b) - 1; h = m // 2
                items[k:k + 1] = [(1, bytes([0xC0 | (h - 8)]) + b[1:1 + h]), (1, bytes([0xC0 | (m - h - 8)]) + b[1 + h:])]
                break
        else: raise ValueError('나눌 원문 묶음 없음')
        splits -= 1
    body = bytearray()
    for k in range(0, len(items), 8):
        grp = items[k:k + 8]; f = 0
        for j, (bit, _) in enumerate(grp): f |= bit << j
        body.append(f)
        for _, b in grp: body += b
    out = bytes([len(body) & 0xFF, len(body) >> 8 & 0xFF, len(body) >> 16, hdr3]) + bytes(body)
    back, used = lzk.unpack(out)
    assert back == data, ('왕복 불일치', len(back), len(data))
    return out


def pack_exact(data, size, hdr3=0):
    """압축 결과 길이(머리 4 B 포함)를 정확히 size 로 — 덩어리가 잇달아 붙은 파일(FLAG.BIN)에서 뒤 덩어리 위치·머리 길이를 그대로 두기 위해.
       앞부분은 보통 압축, tail 뒤는 원문 묶음만 + 묶음 나누기로 1 B 단위 맞춤."""
    import hashlib
    cdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'cache_lzk_exact'); os.makedirs(cdir, exist_ok=True)
    cf = os.path.join(cdir, '%s_%d_%d.bin' % (hashlib.md5(data).hexdigest(), size, hdr3))
    if os.path.exists(cf):
        o = open(cf, 'rb').read()
        if len(o) == size and lzk.unpack(o)[0] == data: return o
    o = _pack_exact(data, size, hdr3); open(cf, 'wb').write(o); return o


def _pack_exact(data, size, hdr3):
    base = pack(data, hdr3)
    if len(base) == size: return base
    assert len(base) < size, ('원래 길이보다 큼', len(base), size)
    lo, hi = 0, len(data)                                    # tail 이 작을수록 길어짐 — size 이하인 가장 작은 tail
    while lo < hi:
        mid = (lo + hi) // 2
        if len(pack(data, hdr3, tail=mid)) <= size: hi = mid
        else: lo = mid + 1

    def fit(items):
        for sp in range(0, 200):
            try: o = _assemble(data, items, hdr3, sp)
            except ValueError: return None
            if len(o) == size: return o
            if len(o) > size: return None

    nm = set(); rec = []
    items = pack(data, hdr3, tail=lo, rec=rec, items_only=True)
    cand = [p for p in reversed(rec)]
    while True:
        o = fit(items)
        if o is not None: return o
        for k, p_ in enumerate(cand):                        # 일치 하나를 원문으로 — 조금씩 늘림
            it2 = pack(data, hdr3, tail=lo, nomatch=frozenset(nm | {p_}), items_only=True)
            if len(_assemble(data, it2, hdr3, 0)) <= size:
                nm.add(p_); items = it2; cand = cand[k + 1:]; break
        else: raise ValueError(('정확한 길이 못 맞춤', size))


if __name__ == '__main__':
    if sys.argv[1] == '--selftest':
        import glob, random
        fs = ['work/unpk/DATA_ENDING_MOA_TXT.BIN@0.bin', 'work/unpk/DATA_P_00.BIN@B0.bin']
        for f in fs:
            d = open(f, 'rb').read(); p = pack(d)
            print(os.path.basename(f), len(d), '→', len(p))
    else:
        d = open(sys.argv[1], 'rb').read(); p = pack(d)
        print(len(d), '→', len(p))
        if len(sys.argv) > 2: open(sys.argv[2], 'wb').write(p)
