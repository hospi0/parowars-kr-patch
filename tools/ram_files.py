# -*- coding: utf-8 -*-
"""스테이트 램에 통째로 올라와 있는 디스크 파일 찾기(읽기 전용) — 파일 앞 64 B(무늬 있는 것)로 검색 후 일치 길이 확인.
   python tools/ram_files.py 상태번호"""
import sys, os, glob
sys.stdout.reconfigure(encoding='utf-8')
r = open('work/st/%s/ram.bin' % sys.argv[1], 'rb').read()
for p in sorted(glob.glob('work/files/**/*', recursive=True)):
    if not os.path.isfile(p): continue
    d = open(p, 'rb').read()
    if len(d) < 256: continue
    k = d[:64]
    if len(set(k)) < 8: continue
    q = r.find(k)
    while q >= 0:
        n = 0
        while n < len(d) and q + n < len(r) and r[q + n] == d[n]: n += 1
        if n >= 256: print('0x%08X' % (0x80000000 + q), '%6d/%6d' % (n, len(d)), p[len('work/files'):])
        q = r.find(k, q + 1)
