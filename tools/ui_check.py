# -*- coding: utf-8 -*-
"""UI 사전 검사(빌더도 같은 함수 사용).
   finalize(jp, ko): 부호 뒤 공백 지움 → 반각 전각화 → 원문이 전각 공백으로 끝나면 원문 글자 수까지 끝 공백 채움(파일 저장 때 끝 공백이 잘려도 복원).
   problems(jp, ko): ① 원문 바이트 이하 ② 자리: «：／＠» 위치 같음, «：» 바로 앞(아이콘 칸)이 공백이면 번역도 공백, 맨 앞 공백 수 같음
                     ③ 고정 용어(glossary).
   python tools/ui_check.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import punct, glossary
MARK = '：／＠'


def fw(s):
    return ''.join('　' if c == ' ' else '・' if c == '·' else chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in s)


def finalize(jp, ko):
    k = fw(punct.squeeze(ko))
    if jp.endswith('　') and len(k) < len(jp): k = k + '　' * (len(jp) - len(k))
    return k


def problems(jp, ko):
    k = finalize(jp, ko); prob = []
    if len(k) > len(jp): prob.append('길이 %d>%d자' % (len(k), len(jp)))
    lead = lambda s: len(s) - len(s.lstrip('　'))
    if jp.startswith('　') and lead(k) != lead(jp): prob.append('맨 앞 공백 %d≠%d' % (lead(k), lead(jp)))
    for i, c in enumerate(jp):
        if c in MARK:
            if i >= len(k) or k[i] != c: prob.append('%s 자리 %d' % (c, i)); break
            if i and jp[i - 1] == '　' and k[i - 1] != '　': prob.append('아이콘 칸 %d' % (i - 1)); break
    if any(c in MARK for c in k) and not any(c in MARK for c in jp): prob.append('없던 표시')
    g = glossary.check(jp, ko)
    if g: prob.append('용어 %s' % g)
    return prob


def load():
    D = {}
    for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'text', 'ui_dict.tsv'), encoding='utf-8'):
        if l[0] == '#' or not l.strip(): continue
        jp, ko = l.rstrip('\n').split('\t'); D[jp] = ko
    return D


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    D = load(); bad = 0
    for jp, ko in D.items():
        p = problems(jp, ko)
        if p: bad += 1; print(p, '|', jp, '→', ko)
    print('사전', len(D), '문제', bad)
