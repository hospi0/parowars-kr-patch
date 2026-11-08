# -*- coding: utf-8 -*-
"""파로 워즈 LZ 풀기 — PAW.EXE 0x80013CAC 그대로 옮김.
   머리: u24 압축 길이(LE) + 1 B, 이어서 자료. 창 1,024 B(0 으로 채움), 쓰기 위치 0x3DE 부터.
   플래그 바이트(LSB 먼저): 0 = 원문 1바이트 / 1 = 명령 바이트 c
     c < 0x80        : 다음 바이트 b, 창 위치 = (c&3)<<8 | b (절대), 길이 = (c>>2) + 3
     0x80 ≤ c < 0xC0 : 거리 = c&0xF (현재 위치에서 뒤로), 길이 = ((c>>4)&3) + 2
     c ≥ 0xC0        : 원문 묶음 (c&0x3F) + 8 바이트
   끝 = 읽는 위치가 머리 뒤 + 압축 길이를 넘을 때.
   python tools/lzk.py 파일 [출력]"""
import sys


def unpack(d, off=0):
    n = d[off] | d[off + 1] << 8 | d[off + 2] << 16
    p = off + 4; end = p + n
    win = bytearray(1024); w = 0x3DE; out = bytearray(); flags = 0
    while True:
        flags >>= 1
        if not flags & 0x100:
            if p >= end: break
            flags = d[p] | 0xFF00; p += 1
        if not flags & 1:
            if p >= end: break
            c = d[p]; p += 1; out.append(c); win[w] = c; w = (w + 1) & 0x3FF
            continue
        if p >= end: break
        c = d[p]; p += 1
        if c < 0x80:
            if p >= end: break
            b = d[p]; p += 1
            src = (c & 3) << 8 | b; ln = (c >> 2) + 3
            for k in range(ln):
                x = win[(src + k) & 0x3FF]; out.append(x); win[w] = x; w = (w + 1) & 0x3FF
        elif c < 0xC0:
            dist = c & 0xF; ln = ((c >> 4) & 3) + 2
            for k in range(ln):
                x = win[(w - dist) & 0x3FF]; out.append(x); win[w] = x; w = (w + 1) & 0x3FF
        else:
            ln = (c & 0x3F) + 8
            for k in range(ln):
                if p >= end: break
                x = d[p]; p += 1; out.append(x); win[w] = x; w = (w + 1) & 0x3FF
    return bytes(out), p - off


if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    o, used = unpack(d)
    print('압축', used, '→ 풀림', len(o))
    if len(sys.argv) > 2: open(sys.argv[2], 'wb').write(o)
