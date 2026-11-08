# -*- coding: utf-8 -*-
"""압축 파일을 LZSS 변형으로 풀어 VRAM(또는 램)과 맞는 조합 찾기(읽기 전용).
   python tools/lz_vram.py 파일 상태번호 [시작]"""
import sys
sys.path.insert(0, 'tools')
from lz_try import lzss
f, st = sys.argv[1], sys.argv[2]
d = open(f, 'rb').read()
tgt = open('work/st/%s/vram.bin' % st, 'rb').read() + open('work/st/%s/ram.bin' % st, 'rb').read()
res = []
starts = [int(sys.argv[3], 16)] if len(sys.argv) > 3 else range(0, 12)
for p in starts:
    for lsb in (True, False):
        for lit1 in (True, False):
            for ref in ('okumura', 'hi', 'len_hi', 'lo'):
                for init, wpos in ((0, 0xFEE), (0, 0), (0x20, 0xFEE), (0, 0xFF0)):
                    for minm in (2, 3):
                        o = lzss(d, p, lsb, lit1, ref, init, 4096, wpos, minm, limit=4096)
                        sc = sum(1 for k in range(64, len(o) - 16, 64) if len(set(o[k:k + 16])) > 3 and o[k:k + 16] in tgt)
                        res.append((sc, p, lsb, lit1, ref, init, wpos, minm, len(o)))
res.sort(reverse=True)
for r in res[:10]: print(r)
