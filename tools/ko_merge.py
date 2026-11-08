# -*- coding: utf-8 -*-
"""하스피 초벌 번역 병합 → work/text/ko_story.tsv (번호·한글) + work/text/merge_report.txt
   입력: my files/번역/*.tsv (번호·출처·원문·번역). 원본 my files/tsv 와 번호·원문 대조(어긋나면 중단).
   003 두 판(paro_003.tsv = A, paro_003 (1).tsv = B): 같으면 그대로, 다르면 B 기본, B 가 용어 위반이 더 많거나 칸을 넘고 A 가 맞으면 A.
   다듬기(순서대로): ① 용어 바로잡기(정해진 표기, docs/이름_번역규칙.md·glossary.py) ② 화자 표시 «이름：「» ③ 물결 ～ 통일
     ④ 문장부호 뒤 공백 삭제(punct.squeeze) ⑤ 앞뒤 군더더기 공백 ⑥ 용어 재검사 ⑦ 칸 길이(바이트) 검사.
   python tools/ko_merge.py"""
import os, re, sys, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import punct, glossary as G

FIX = [   # (잘못된 표기, 정해진 표기) — 긴 것부터
    ('얏타바우와', '해냈다멍과'), ('얏타바우', '해냈다멍'),      # 하스피 2026-11-08 의역(ヤッターバウ)
    ('펜타로 킹 3세', '펭타로킹 3세'), ('펜타로킹 3세', '펭타로킹 3세'), ('펜타로 왕국', '펭타로 왕국'), ('펜타로', '펭타로'),
    ('펜타 연합', '펭타 연합'), ('펜타연합', '펭타 연합'), ('펜타국', '펭타국'),
    ('바우바우국', '멍멍국'), ('바우바우 국', '멍멍국'), ('바우바우군', '멍멍국군'), ('바우바우', '멍멍국'),
    ('안나 파블로와', '안나파블로바'), ('안나파블로와', '안나파블로바'), ('안나 파블로바', '안나파블로바'),
    ('이놈&저놈', '이녀석＆저녀석'), ('이놈＆저놈', '이녀석＆저녀석'), ('이녀석&저녀석', '이녀석＆저녀석'), ('이녀석 & 저녀석', '이녀석＆저녀석'),
    ('코이츠', '이녀석'), ('아이츠', '저녀석'),
    ('아카시아', '아카시야'), ('알라지오', '아라지오'),
    ('냐 제국', '냥 제국'), ('냐제국', '냥 제국'), ('제왕 냐~무', '제왕 냥 무'), ('제왕 냐 무', '제왕 냥 무'), ('냐~무', '냥 무'), ('냐·무', '냥 무'),
    ('레오나르드2', '레오나르도2'), ('키렌바', '키레룬바'), ('차회주의', '다회주의'), ('봉쥬르', '봉주르'), ('노크스', '녹스'),
    ('쁘띠쁘띠 쿠피르', '푸리푸리크피르'), ('우스시오 FC', '우스시오FC'), ('냐옹 제국', '냥 제국'), ('레오나르드 2', '레오나르도2'), ('냐 문', '냥 무'), ('냐・무', '냥 무'), ('냐·무', '냥 무'),
]
FIX += [('스캇토잇파츠는', '스커드한방은'), ('스캇토잇파츠', '스커드한방'), ('푸리푸리크피르', '탱탱크피르'), ('부타시오 mk2', '돼지소금mk2'),
        ('빈빈 더블', '팔팔더블'), ('비시바시 F1', '팍팍F1'), ('냐 대륙', '냥 대륙')]          # 하스피 2026-11-08 병기 이름 의역(이름표 names_ko 와 같게, 뒤 조사 받침 맞춤)
SPEAKER = re.compile(r'^(　?[^「」『』\s][^「」『』]{0,16}?)\s*[:：]\s*([「『])')


def load(p):
    d = {}
    for l in open(p, encoding='utf-8-sig'):
        if l.startswith('#') or not l.strip(): continue
        f = l.rstrip('\n').split('\t'); d[f[0]] = (f[1], f[2], '\t'.join(f[3:]))
    return d


def _data(fn):
    p = 'work/unpk/' + fn[1:] + '.bin' if fn.startswith('@') else 'work/files' + fn
    return open(p, 'rb').read()


SRC = {}


def budget():
    """번호 → 칸(바이트). 메모리 규칙(원문 길이 버퍼 복사 위험): 고정 레코드만 레코드 크기, 나머지는 원문 길이.
       고정 레코드: 이야기 TXT_·엔딩 *_TXT 150 B, 인물 대사 X_ 60, BAKU 50, 아이템 설명 ITEM 96 (칸 − 2).
       고정 폭 줄 문단: 도움말 SEL_HELP 50 B 줄, 도감 P_·국가 정보 KABE 52 B 줄 — 이어진 줄은 문단 하나로 합산(빌더가 줄 폭으로 다시 나눔),
       뒤쪽 빈 줄 칸(0 만 있는 칸)은 문단 칸에 더함.
       반환: (번호→칸, 번호→문단 묶음 키)"""
    cap = {}; grp = {}
    rows = collections.defaultdict(list)
    for l in open('work/text/tsv_map.tsv', encoding='utf-8'):
        if l[0] == '#': continue
        i, fn, o, n = l.rstrip('\n').split('\t'); rows[fn].append((int(o, 16), int(n), i))
    for fn, L in rows.items():
        L.sort()
        rec = 150 if ('/DEMO/TXT_' in fn or fn.endswith('TXT_END.BIN') or re.search(r'ENDING_[A-Z]+_TXT', fn)) else 60 if re.search(r'/X_[A-Z]+\.BIN', fn) \
            else 50 if re.search(r'/BAKU\d*\.BIN', fn) else 96 if fn.endswith('/ITEM.BIN') else None
        line = 50 if fn.endswith('SEL_HELP.BIN') else 52 if re.search(r'^@DATA_(P_|DEMO_KABE)', fn) else None
        if rec:
            for o, n, i in L: cap[i] = min(cap.get(i, rec - 2), rec - 2)
            continue
        if line:
            d = _data(fn); k = 0
            while k < len(L):
                o0 = L[k][0]; members = [L[k]]; end = o0 + ((L[k][1] + line - 1) // line) * line
                para = fn.endswith('SEL_HELP.BIN') or fn.startswith('@DATA_P_')       # 도움말·도감: 바로 이어지는 줄 = 같은 글상자 문단
                while para and '★' not in SRC.get(L[k][2], '') and k + 1 < len(L) and L[k + 1][0] == end and '★' not in SRC.get(L[k + 1][2], ''):
                    k += 1; members.append(L[k]); end += ((L[k][1] + line - 1) // line) * line
                nxt = L[k + 1][0] if k + 1 < len(L) else len(d)
                extra = 0
                blank = lambda s: not any(s.replace(bytes([0x81, 0x40]), bytes(2)))   # 0 이나 전각 공백만 = 빈 줄
                while end + line <= nxt and extra < 3 and blank(d[end:end + line]): end += line; extra += 1
                total = (end - o0) // line * (line - 2)
                key = (fn, o0)
                for o, n, i in members:
                    grp[i] = key; cap[i] = min(cap.get(i, total), total)
                k += 1
            continue
        for o, n, i in L: cap[i] = min(cap.get(i, n), n)
    return cap, grp


def nbytes(s):
    return sum(1 if ord(c) < 0x80 and c != ' ' else 2 for c in UCfw(s))


def UCfw(s):
    return ''.join('　' if c == ' ' else chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in s)


def polish(ko):
    s = ko
    for a, b in FIX: s = s.replace(a, b)
    s = SPEAKER.sub(lambda m: m.group(1).rstrip() + '：' + m.group(2), s)
    s = s.replace('~', '～').replace('〜', '～')
    s = re.sub(r'(?:[…⋯]|・{2,}|\.{3}|‥)+', '…', s)              # 한국식 말줄임표 한 칸(전프로젝트 규칙) — 글꼴 … 칸은 빌더가 바닥선 점 셋으로
    s = punct.squeeze(s)
    s = re.sub(r'^(공격력|수비력)(?=[０-９0-9＃])', lambda m: m.group(1) + '　', s)      # 도감 능력치 줄: 원문처럼 이름 뒤 전각 공백(공격력 줄과 열 맞춤 — 하스피 실기)
    s = re.sub(' {2,}', ' ', s).rstrip()
    return s


if __name__ == '__main__':
    src = {}
    for p in sorted(glob.glob('my files/tsv/paro_*.tsv')):
        for i, v in load(p).items(): src[i] = v
    got = {}; a = b = None
    for p in sorted(glob.glob('my files/번역/*.tsv')):
        nm = os.path.basename(p); d = load(p)
        for i, (s, jp, ko) in d.items(): assert i in src and src[i][1] == jp, ('원문 불일치', nm, i)
        if nm == 'paro_003.tsv': a = d
        elif nm == 'paro_003 (1).tsv': b = d
        else: got.update({i: v[2] for i, v in d.items()})
    SRC.update({i: v[1] for i, v in src.items()})
    cap, grp = budget(); rep = []
    pick = collections.Counter()
    for i in a:
        ka, kb = polish(a[i][2]), polish(b[i][2]); jp = src[i][1]
        if ka == kb: got[i] = a[i][2]; pick['같음'] += 1; continue
        va, vb = len(G.check(jp, ka)), len(G.check(jp, kb))
        fa, fb = nbytes(ka) <= cap.get(i, 9999), nbytes(kb) <= cap.get(i, 9999)
        if (vb > va) or (not fb and fa): got[i] = a[i][2]; pick['A'] += 1
        else: got[i] = b[i][2]; pick['B'] += 1
    assert set(got) == set(src), (len(got), len(src))
    # 칸 넘침 다듬기·개별 수정(work/text/ko_override.tsv) — 병합 뒤 덮어씀
    ov = {}
    for l in open('work/text/ko_override.tsv', encoding='utf-8'):
        if l[0] == '#' or not l.strip(): continue
        i, k = l.rstrip(chr(10)).split(chr(9), 1); assert i in src, i; ov[i] = k
    got.update(ov)
    EXEMPT = {'01275'}    # ホイコーロー = 요리(회과육) 말장난, 인물 이름 아님
    out = {}; viol = []; over = []
    for i in sorted(got):
        k = polish(got[i])
        if 'チキィン' in src[i][1]: k = k.replace('치킨', '치키인')         # 점술사 チキィン 표기 통일(치키인 7곳 · 치킨 3곳)
        j = src[i][1]                                                        # 원문 괄호 토큰 따르기
        if '『' not in j and '「' in j: k = k.replace('『', '「').replace('』', '」')
        if '”' in j and '「' not in j: k = re.sub('「([^」]*)」', lambda m: '”' + m.group(1) + '”', k)
        out[i] = k
        g = [] if i in EXEMPT else G.check(src[i][1], k)
        if g: viol.append((i, g, k))
        if i not in grp and nbytes(k) > cap.get(i, 9999): over.append((i, nbytes(k), cap[i], src[i][0], k))
    # 문단 묶음은 합산으로 검사
    gs = collections.defaultdict(list)
    for i, key in grp.items(): gs[key].append(i)
    for key, ids in gs.items():
        tot = sum(nbytes(out[i]) for i in ids)
        if tot > cap[ids[0]]: over.append((','.join(sorted(ids)), tot, cap[ids[0]], src[ids[0]][0], ' / '.join(out[i] for i in sorted(ids))))
    with open('work/text/ko_story.tsv', 'w', encoding='utf-8', newline='\n') as f:
        f.write('#번호\t한글\n')
        for i in sorted(out): f.write('%s\t%s\n' % (i, out[i]))
    with open('work/text/merge_report.txt', 'w', encoding='utf-8') as f:
        f.write('003 고름 %s\n용어 위반 %d\n' % (dict(pick), len(viol)))
        for v in viol: f.write('  %s %s | %s\n' % v)
        f.write('칸 넘침 %d\n' % len(over))
        for o in over: f.write('  %s %dB>%dB %s | %s\n' % o)
    print('병합', len(out), '003', dict(pick), '용어 위반', len(viol), '칸 넘침', len(over))
    print(collections.Counter(o[3].split('_')[0][:5] for o in over).most_common(10))
