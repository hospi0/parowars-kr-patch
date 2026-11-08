# -*- coding: utf-8 -*-
"""문장 파일 형식 판정(읽기 전용): 파일 묶음마다 문자열 시작 간격(고정 줄?)·끝 표시·가리키는 포인터 종류.
   python tools/fmt_probe.py  → work/fmt.tsv"""
import sys, os, re, struct, collections
sys.stdout.reconfigure(encoding='utf-8')
rows = collections.defaultdict(list)
for l in open('work/census_text.tsv', encoding='utf-8'):
    fn, o, n, s = l.rstrip('\n').split('\t', 3); rows[fn].append((int(o, 16), int(n)))
grp = collections.defaultdict(list)
for fn in rows: grp[re.sub(r'\d+', '#', fn)].append(fn)
out = open('work/fmt.tsv', 'w', encoding='utf-8')
for g, fs in sorted(grp.items(), key=lambda x: -sum(len(rows[f]) for f in x[1])):
    fn = fs[0]; d = open('work/files' + fn, 'rb').read(); R = sorted(rows[fn])
    # 문자열 진짜 시작(앞쪽 0 아닌 데까지) 과 끝 바이트
    starts = []
    for o, n in R:
        a = o
        while a >= 2 and d[a - 2] >= 0x81 and d[a - 1] >= 0x40 and d[a - 2] != 0: a -= 2
        starts.append(a)
    gaps = collections.Counter(b - a for a, b in zip(starts, starts[1:]))
    term = collections.Counter(d[o + n:o + n + 2].hex() for o, n in R)
    p16 = sum(1 for a in starts if a < 65536 and struct.pack('<H', a) in d[:min(a, 0x4000)])
    p32 = sum(1 for a in starts if struct.pack('<I', a) in d)
    out.write('%s\t%d파일\t%d줄\t간격%s\t끝%s\tu16포인터%d\tu32포인터%d\n' % (g, len(fs), len(R), gaps.most_common(3), term.most_common(3), p16, p32))
out.close(); print(open('work/fmt.tsv', encoding='utf-8').read()[:6000])
