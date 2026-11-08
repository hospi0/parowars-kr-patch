# -*- coding: utf-8 -*-
"""LZSS 변형 맞춰 보기(읽기 전용): 여러 시작 위치·플래그 비트 순서·참조 꼴로 풀어 SJIS 가나 비율이 높은 조합을 찾는다.
   python tools/lz_try.py work/files/DATA/P_00.BIN"""
import sys, re


def lzss(d, p, lsb=True, lit1=True, ref='okumura', init=0, wsize=4096, wpos=0xFEE, minm=3, limit=200000):
    win = bytearray([init]) * wsize; r = wpos; out = bytearray(); flags = 0; nb = 0
    try:
        while p < len(d) and len(out) < limit:
            if nb == 0: flags = d[p]; p += 1; nb = 8
            bit = (flags & 1) if lsb else (flags >> 7 & 1)
            flags = flags >> 1 if lsb else (flags << 1) & 0xFF; nb -= 1
            if bit == (1 if lit1 else 0):
                c = d[p]; p += 1; out.append(c); win[r] = c; r = (r + 1) % wsize
            else:
                a, b = d[p], d[p + 1]; p += 2
                if ref == 'okumura': off = a | (b & 0xF0) << 4; ln = (b & 0xF) + minm
                elif ref == 'hi': off = (a << 4) | (b >> 4); ln = (b & 0xF) + minm
                elif ref == 'len_hi': off = (a & 0xF) << 8 | b; ln = (a >> 4) + minm
                else: off = (b & 0xF) << 8 | a; ln = (b >> 4) + minm
                for k in range(ln):
                    c = win[(off + k) % wsize]; out.append(c); win[r] = c; r = (r + 1) % wsize
    except IndexError: pass
    return bytes(out)


def score(o):
    s = o.decode('cp932', 'ignore')
    return len(re.findall('[ぁ-んァ-ヶ。、]', s))


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read(); best = []
    for p in range(0, 0x40):
        for lsb in (True, False):
            for lit1 in (True, False):
                for ref in ('okumura', 'hi', 'len_hi', 'lo'):
                    for init, wpos in ((0, 0xFEE), (0x20, 0xFEE), (0, 0)):
                        o = lzss(d, p, lsb, lit1, ref, init, 4096, wpos, limit=20000)
                        best.append((score(o), p, lsb, lit1, ref, init, wpos))
    best.sort(reverse=True)
    for b in best[:8]: print(b)
