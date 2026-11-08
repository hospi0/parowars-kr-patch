# -*- coding: utf-8 -*-
"""고정 용어 규칙(하스피 지시 2026-11-07 «내가 번역한 파일에서는 장담 못 하니까 규칙으로 박아»).
   번역을 «읽는 순간» 검사한다: 원문에 고정 용어가 있으면 번역에 정해진 한글이 있어야 한다. 하나라도 어기면 적재기·빌더가 멈춘다.
   - こいつ·あいつ·そいつ·どいつ 가 «이름»으로 쓰인 경우(＆ 나라 이름·직함·화자 표시) → 이녀석·저녀석·그녀석·어느녀석
     (あいつら 같은 그냥 대명사는 대상 아님)
   - 인물 이름(names_ko.tsv 인물, 원문 3자 이상)·병기 이름(원문 4자 이상)이 대사에 나오면 그 번역 그대로
   비교 때 원문은 고정 칸 줄바꿈 채움(전각 공백)·줄바꿈 표시를 지우고, 번역은 공백·전각/반각 차이를 무시한다.
   python tools/glossary.py 번역TSV...   (열: 원문이 든 열과 번역 열을 머리줄 이름 «원문»·«번역»으로 찾음, 없으면 끝 두 열)"""
import re, sys, os, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')

NAME_USE = [   # (원문 정규식, 번역에 있어야 할 글자)
    (r'こいつ＆あいつ|コイツ＆アイツ', '이녀석＆저녀석'),
    (r'(?:こいつ|コイツ)(?=書記長|大統領|首相|国王|：|:|「)', '이녀석'),
    (r'(?:あいつ|アイツ)(?=書記長|大統領|首相|国王|：|:|「)', '저녀석'),
    (r'(?:そいつ|ソイツ)(?=書記長|大統領|首相|国王|：|:|「)', '그녀석'),
    (r'(?:どいつ|ドイツ)(?=書記長|大統領|首相|国王|：|:|「)', '어느녀석'),
]
# 나라 이름(하스피 확정 2026-11-07: 멍멍국·냥 제국, 나머지는 제안대로). 긴 이름이 먼저 걸리도록 정렬된다.
COUNTRY = [
    ('こいつ＆あいつ連邦共和国', '이녀석＆저녀석 연방 공화국'), ('こいつ＆あいつ共和国', '이녀석＆저녀석 공화국'),
    ('ペン太郎王国', '펭타로 왕국'), ('ペンタロウ王国', '펭타로 왕국'), ('ペンタ連合', '펭타 연합'), ('ペンタ国', '펭타국'),
    ('バウバウ国', '멍멍국'),
    ('パンダ茶会主義獣民共和国', '판다 다회주의 수민 공화국'), ('パンダ獣民共和国', '판다 수민 공화국'), ('パンダ国', '판다국'),
    ('モアイ諸島首長国', '모아이 제도 수장국'), ('モアイ首長国', '모아이 수장국'), ('モアイ国', '모아이국'),
    ('ミカエル帝国', '미카엘 제국'),
    ('ラブリー連邦合衆国', '러블리 연방 합중국'), ('ラブリー合衆国', '러블리 합중국'), ('ラブリー国', '러블리국'),
    ('プリンス王国', '프린스 왕국'),
    ('ニャー帝国', '냥 제국'),
    ('アラジオ連合', '아라지오 연합'),
    ('アカシヤ・パンダ連合', '아카시야·판다 연합'), ('アカシヤランド共和国', '아카시야랜드 공화국'), ('アカシヤ共和国', '아카시야 공화국'), ('アカシヤ国', '아카시야국'),
    ('チンココ＝カーン王国', '친코코=칸 왕국'),
]


def _names():
    out = []
    p = os.path.join(ROOT, 'work', 'text', 'names_ko.tsv')
    for l in open(p, encoding='utf-8'):
        if l[0] == '#': continue
        kind, jp, ko = l.rstrip('\n').split('\t')
        if jp in ('こいつ', 'あいつ', 'そいつ', 'どいつ'): continue
        jp2 = jp.replace('　', '').replace('・', '')
        if (kind == '인물' and len(jp2) >= 3) or (kind == '병기' and len(jp2) >= 4):
            if re.fullmatch('[ぁ-ん]+', jp2): continue                      # 히라가나 이름(はるか·ひかる)은 보통 낱말과 겹쳐 빼고
            pat = re.escape(jp2)
            if re.fullmatch('[ァ-ヶー]+', jp2): pat = '(?<![ァ-ヶー])' + pat + '(?![ァ-ヶー])'   # 가타카나 이름은 낱말 경계(プリン ≠ プリンセス)
            out.append((pat, ko))
    # 긴 이름부터(ペン太郎 안의 짧은 이름이 먼저 걸리지 않게)
    out.sort(key=lambda x: -len(x[0]))
    return out


TERMS = sorted([(re.escape(j.replace('・', '')), k) for j, k in COUNTRY], key=lambda x: -len(x[0])) + NAME_USE + _names()


def norm_jp(s):
    return re.sub('[　 ?？/・]|\\\\l|<[0-9A-Fa-f]+>', '', s)


def norm_ko(s):
    s = unicodedata.normalize('NFKC', s)          # 전각 → 반각
    return re.sub(r'[\s·・]', '', s)


def check(jp, ko):
    """어긴 규칙 목록 [(원문 용어, 필요한 한글)]"""
    j = norm_jp(jp); k = norm_ko(ko); bad = []
    used = j
    for pat, need in TERMS:
        if re.search(pat, used):
            if norm_ko(need) not in k: bad.append((re.sub(r'\\', '', pat)[:20], need))
            used = re.sub(pat, '', used)
    return bad


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    total = 0
    for f in sys.argv[1:]:
        rows = [l.rstrip('\n').split('\t') for l in open(f, encoding='utf-8')]
        head = rows[0] if rows and rows[0][0].startswith('#') else None
        ji = head.index('원문') if head and '원문' in head else -2
        ki = head.index('번역') if head and '번역' in head else -1
        for r in rows[1 if head else 0:]:
            if len(r) < 2 or not r[ki].strip(): continue
            b = check(r[ji], r[ki])
            if b: total += 1; print(os.path.basename(f), r[0], b, '|', r[ki][:40])
    print('규칙 어긴 줄', total)
    sys.exit(1 if total else 0)
