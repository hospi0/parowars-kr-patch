# -*- coding: utf-8 -*-
"""VRAM 칸 → 디스크 출처(읽기 전용). VRAM 을 64×8 하프워드 조각으로 나눠 무늬 있는 줄(16 B)을 전 파일에서 찾는다.
   python tools/vram_src.py 상태번호 [x0 y0 x1 y1 (16비트 좌표)]  → 출처별 조각 수"""
import sys, os, glob, collections
sys.stdout.reconfigure(encoding='utf-8')
st = sys.argv[1]
x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6]) if len(sys.argv) > 5 else (0, 0, 1024, 512)
v = open('work/st/%s/vram.bin' % st, 'rb').read()
files = {}
for p in glob.glob('work/files/**/*', recursive=True):
    if os.path.isfile(p): files[p[len('work/files'):].replace('\\', '/')] = open(p, 'rb').read()
files['/PAW.EXE'] = open('work/PAW.EXE', 'rb').read()
for p in glob.glob('work/unpk/*.bin'): files['@' + os.path.basename(p)] = open(p, 'rb').read()
hit = collections.Counter(); where = {}; miss = 0
for y in range(y0, y1, 8):
    for x in range(x0, x1, 16):
        o = (y * 1024 + x) * 2; row = v[o:o + 32]
        if len(set(row)) < 6: continue
        found = None
        for fn, d in files.items():
            q = d.find(row)
            if q >= 0: found = fn; where.setdefault((fn), (x, y, q)); break
        if found: hit[found] += 1
        else: miss += 1
print('못 찾은 조각', miss)
for fn, c in hit.most_common(40): print(c, fn, '첫 자리 VRAM(%d,%d) 파일 0x%X' % where[fn])
