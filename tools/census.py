# -*- coding: utf-8 -*-
"""전 파일(STR·음원 제외) Shift-JIS 문자열 총량 조사(읽기 전용).
   전각 2글자 이상 이어진 덩어리를 문자열로 본다. 출력 work/census.tsv(파일·위치·길이·문장)"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import discfs as D
BIN = r'C:\claude\roms\ps\Paro Wars (Japan)\Paro Wars (Japan).bin'
f, vol, rl, rs, ents = D.read_fs(BIN)
# 전각 SJIS 한 글자 또는 반각 ASCII/카나 일부를 허용한 덩어리
LEAD = set(range(0x81, 0xA0)) | set(range(0xE0, 0xF0))
def runs(d):
    i = 0; n = len(d)
    while i < n - 1:
        j = i; fw = 0
        while j < n - 1:
            b = d[j]
            if b in LEAD and 0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F:
                try: bytes(d[j:j + 2]).decode('cp932')
                except UnicodeDecodeError: break
                j += 2; fw += 1
            elif 0x20 <= b < 0x7F and fw: j += 1
            else: break
        if fw >= 2:
            s = bytes(d[i:j]).decode('cp932', 'replace')
            if re.search('[ぁ-んァ-ヶ一-龥]', s): yield i, j - i, s
            i = j
        else: i += 1
out = open('work/census.tsv', 'w', encoding='utf-8'); tot = collections.Counter(); cnt = collections.Counter()
for e in ents:
    if e[0].endswith(('.STR', '.VB', '.VH', '.SEQ')): continue
    d = D.sector(f, e[1], (e[2] + 2047) // 2048)[:e[2]]
    for o, n, s in runs(d):
        out.write('%s\t%X\t%d\t%s\n' % (e[0], o, n, s)); tot[e[0]] += n; cnt[e[0]] += 1
grp = collections.Counter(); gc = collections.Counter()
for k, v in tot.items():
    g = re.sub(r'\d+', '#', k); grp[g] += v; gc[g] += 1
print('파일', len(tot), '바이트', sum(tot.values()), '줄', sum(cnt.values()))
for g, v in grp.most_common(40): print('%7d' % v, gc[g], g)
