# -*- coding: utf-8 -*-
"""UI 짧은 문자열 전수 추출(하스피: TSV 말고 직접 번역) → work/text/ui_jp.tsv (파일·위치·바이트·원문).
   대상: 오버레이·메뉴 파일 + PAW.EXE(글꼴·범위표·이름 표 제외). 이야기·대사 파일은 제외(TSV 쪽).
   조건: 앞 바이트 0(또는 파일 처음)·시작 4 B 정렬·0 으로 끝남·cp932 로 온전히 풀림·전각 가나/한자 1자 이상·
         JIS 2수준/외자 없음·제어문자 없음·공백 뺀 길이 12자 이하·개발 PC 찌꺼기 아님.
   이미 처리한 칸(이름 표 names_jp.tsv)은 뺀다.  python tools/ui_extract.py"""
import os, re, sys, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import extract as X
STORY = re.compile(r'/(DEMO/|ENDING/|X_[A-Z]+\.BIN|S_[A-Z]+\.BIN|BAKU\d*\.BIN|UNITINFO|LOCS_OV|BK_DT/|BTL/|NYANTV/|P_\w+\.BIN|MAP\w*\.BIN|OJ_|PUP_|OPF|OP_|H_\d|HK_)')
SKIP_EXE = [(0x93DF4, 0xA31D2), (0x8F404, 0x90B42), (0x90B50, 0x90D56), (0x90DA0, 0x914A0)]
done = set()
for l in open('work/text/names_jp.tsv', encoding='utf-8'):
    if l[0] != '#': p = l.split('\t'); done.add((p[1], int(p[2], 16)))
JC = X.junk_corpus()
out = open('work/text/ui_jp.tsv', 'w', encoding='utf-8'); out.write('#파일\t위치\t바이트\t원문\n')
paths = [('/PAW.EXE', 'work/PAW.EXE')] + [(p[len('work/files'):].replace('\\', '/'), p) for p in sorted(glob.glob('work/files/DATA/**/*.BIN', recursive=True))]
n = 0; per = collections.Counter(); uniq = set()
for fn, p in paths:
    if STORY.search(fn): continue
    d = open(p, 'rb').read()
    for i in range(0, len(d) - 2, 4):
        if i and d[i - 1] != 0: continue
        if not (0x81 <= d[i] <= 0x9F or 0xE0 <= d[i] <= 0xEF or 0x20 <= d[i] < 0x7F): continue
        j = d.find(b'\0', i)
        if j < 0 or j == i: continue
        raw = d[i:j]
        try: s = raw.decode('cp932')
        except UnicodeDecodeError: continue
        if fn == '/PAW.EXE' and any(a <= i < b for a, b in SKIP_EXE): continue
        if (fn, i) in done: continue
        t = s.replace('　', '')
        if not t or len(t) > 12: continue
        if not re.search('[ぁ-んァ-ヶ一-龥]', t): continue
        if any(ord(c) < 0x20 for c in s) or any(X.lvl2(c) for c in t if ord(c) > 0x7F): continue
        if any(raw in c for c in JC) or X.JUNK.search(t): continue
        # 반각 글자 섞인 건 짧은 잡음일 가능성 — 반각이 절반 넘으면 버림
        if sum(1 for c in s if ord(c) < 0x80) * 2 > len(s): continue
        out.write('%s\t%X\t%d\t%s\n' % (fn, i, len(raw), s)); n += 1; per[fn] += 1; uniq.add(s)
out.close()
print('칸', n, '고유', len(uniq), '글자', sum(len(s.replace('　', '')) for s in uniq))
for f, c in per.most_common(60): print('%4d %s' % (c, f))
