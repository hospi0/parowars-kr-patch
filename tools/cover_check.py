# -*- coding: utf-8 -*-
"""추출 누락 검사: census_text.tsv(넓은 그물)의 문장이 jp.tsv 범위 안에 들어 있는지 파일별로 센다.
   python tools/cover_check.py [파일 이름 일부]"""
import sys, collections, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'tools')
import extract as X
cov = collections.defaultdict(list)
for l in open('work/text/jp.tsv', encoding='utf-8'):
    if l[0] == '#': continue
    i, fn, o, n, s = l.rstrip('\n').split('\t', 4); cov[fn].append((int(o, 16), int(o, 16) + int(n)))
miss = collections.defaultdict(list)
for l in open('work/census_text.tsv', encoding='utf-8'):
    fn, o, n, s = l.rstrip('\n').split('\t', 3); o = int(o, 16)
    if X.SKIP_FILE.search(fn) or X.JUNK.search(s): continue
    if not any(a <= o < b for a, b in cov[fn]): miss[fn].append((o, s))
flt = sys.argv[1] if len(sys.argv) > 1 else ''
print('누락 파일', len(miss), '줄', sum(len(v) for v in miss.values()))
for fn, v in sorted(miss.items(), key=lambda x: -len(x[1])):
    if flt in fn: print(len(v), fn, [('%X' % o, s[:20]) for o, s in v[:5]])
