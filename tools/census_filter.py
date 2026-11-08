# -*- coding: utf-8 -*-
"""census.tsv → 진짜 문장 후보만(census_text.tsv). 기준: 전각 3자 이상, 가나·부호 비율 0.35 이상,
   JIS 2수준 한자·키릴·괘선·원문자 없음(그림 데이터 우연 일치 제거). 파일 묶음별 글자 수 출력."""
import re, collections, sys
sys.stdout.reconfigure(encoding='utf-8')
def lvl2(c):
    try: b = c.encode('cp932')
    except Exception: return True
    if len(b) < 2: return False
    v = b[0] << 8 | b[1]
    return v >= 0x989F or 0x8440 <= v < 0x889F and not (0x8740 <= v < 0x8780 and False)
tot = collections.Counter(); ch = collections.Counter(); keep = []
for l in open('work/census.tsv', encoding='utf-8'):
    fn, o, n, s = l.rstrip('\n').split('\t', 3)
    t = s.replace('　', '')
    if len(t) < 3: continue
    if len(re.findall('[ぁ-んァ-ヶー。、！？「」・…～]', t)) / len(t) < 0.35: continue
    if any(lvl2(c) for c in t if ord(c) > 0x7F): continue
    g = re.sub(r'\d+', '#', fn); tot[g] += 1; ch[g] += len(t); keep.append(l)
open('work/census_text.tsv', 'w', encoding='utf-8').writelines(keep)
print('줄', sum(tot.values()), '글자', sum(ch.values()))
for g, v in ch.most_common(70): print('%7d' % v, tot[g], g)
