# -*- coding: utf-8 -*-
"""이름 번역 검사: names_ko.tsv 를 names_jp.tsv 와 순서·원문으로 맞추고
   ① 원문 일치 ② 부호 뒤 공백(punct.squeeze) ③ 길이(한 글자 2바이트, 원문 바이트·칸 여유) ④ 글꼴로 찍을 수 없는 글자 를 본다.
   python tools/names_check.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import punct
J = [l.rstrip('\n').split('\t') for l in open('work/text/names_jp.tsv', encoding='utf-8') if l[0] != '#']
K = [l.rstrip('\n').split('\t') for l in open('work/text/names_ko.tsv', encoding='utf-8') if l[0] != '#']
assert len(J) == len(K), (len(J), len(K))
over = []; bad = 0
for j, k in zip(J, K):
    kind, fn, off, nb, room, jp = j
    assert k[0] == kind and k[1] == jp, (j, k)
    ko = k[2]
    if punct.squeeze(ko) != ko: print('부호 뒤 공백', kind, jp, ko); bad += 1
    b = 2 * len(ko)
    if b > int(nb): over.append((kind, off, jp, ko, b, int(nb), int(room)))
print('항목', len(K), '부호 문제', bad, '원문보다 긺', len(over))
for o in over: print('  %s %s %s → %s  %dB (원문 %d, 칸 여유 %d)%s' % (o[0], o[1], o[2], o[3], o[4], o[5], o[6], '  ⛔칸 초과' if o[4] > o[6] - 2 else ''))
