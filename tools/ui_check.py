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
# 글자 수로 가운데 정렬하는 맵 메뉴 칸 — 원문 앞뒤 공백(가운데 맞춤용)을 따르지 않고 번역 글자 수 그대로(하스피 «국가정보·행동종료 줄맞추기»)
CENTERED = {'　国情報　'}
# 게임이 «문자열 끝에서 N칸 앞»에 숫자를 써 넣는 칸 — 번역이 짧으면 끝을 전각 공백으로 원문 길이까지 채움(TSV 끝 공백은 편집 중 잘리기 쉬움)
#   («　機スタック»: 0x80075EA4 가 끝 −5칸 자리에 숫자 → 6칸이어야 맨 앞 칸에 들어감. 5칸이면 문자열 앞 데이터를 덮음 — 하스피 «숫자 안 나옴»)
PAD_TO_LEN = {'　機スタック'}


def fw(s):
    return ''.join('　' if c == ' ' else '・' if c == '·' else chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in s)


def finalize(jp, ko):
    k = fw(punct.squeeze(ko))
    if jp.endswith('　') and len(k) < len(jp) and jp not in CENTERED: k = k + '　' * (len(jp) - len(k))
    if jp in PAD_TO_LEN and len(k) < len(jp): k = k + '　' * (len(jp) - len(k))
    return k


def problems(jp, ko):
    k = finalize(jp, ko); prob = []
    if len(k) > len(jp): prob.append('길이 %d>%d자' % (len(k), len(jp)))
    lead = lambda s: len(s) - len(s.lstrip('　'))
    if jp.startswith('　') and jp not in CENTERED and lead(k) != lead(jp): prob.append('맨 앞 공백 %d≠%d' % (lead(k), lead(jp)))
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
