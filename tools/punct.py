# -*- coding: utf-8 -*-
"""전프로젝트 규칙: 문장부호 바로 뒤 공백 1칸(반각·전각) 삭제. 2칸 이상 이어진 채움 공백은 둔다.
   제어 코드 <..>·줄바꿈(백슬래시 l)으로 쪼갠 조각마다 적용.  python tools/punct.py = 번역표 검사(고치기는 --fix)"""
import re, sys
PUNCT = ',.!?:;)]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥'
_R = re.compile('([' + re.escape(PUNCT) + '])[ 　](?![ 　])')
_SPLIT = re.compile('(<[0-9A-Fa-f]+>|' + re.escape(chr(92) + 'l') + ')')


def squeeze(t):
    return ''.join(p if _SPLIT.fullmatch(p) else _R.sub(r'\1', p) for p in _SPLIT.split(t))


def bad(t):
    return squeeze(t) != t


def guard():
    """빌드 시작 때 호출: 번역표에 부호 뒤 공백이 하나라도 있으면 빌드 중단."""
    bad_ = []
    for f, col in FILES.items():
        for l in open(f, encoding='utf-8'):
            if l.strip() and l[0] != '#':
                p_ = l.rstrip(chr(10)).split(chr(9))
                if bad(p_[col]): bad_.append((f, p_[0]))
    assert not bad_, ('부호 뒤 공백 남음 — python tools/punct.py --fix', bad_[:10])


FILES = {'work/text/ko_story.tsv': 1}
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    fix = '--fix' in sys.argv; tot = 0
    for f, col in FILES.items():
        L = open(f, encoding='utf-8').read().split('\n'); n = 0
        for i, l in enumerate(L):
            if not l or l[0] == '#': continue
            p = l.split('\t'); v = p[col]; s = squeeze(v)
            if s != v:
                n += 1
                if n <= 5: print(f, p[0], v[:60], '→', s[:60])
                p[col] = s; L[i] = '\t'.join(p)
        print(f, '고칠 줄', n); tot += n
        if fix and n: open(f, 'w', encoding='utf-8', newline='\n').write('\n'.join(L))
    print('합계', tot)
