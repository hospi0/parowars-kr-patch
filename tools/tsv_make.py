# -*- coding: utf-8 -*-
"""하스피 번역용 TSV 만들기 → my files/tsv/paro_NNN.tsv (18 KB 단위, 하스피 지시) + work/text/tsv_map.tsv(번호 → 모든 자리).
   제외: 인물·병기 이름(names_*), UI 짧은 문자열 사전(ui_dict — 직접 번역), 개발 PC 찌꺼기.
   포함: 평문 문장(work/text/jp.tsv) + 압축 덩어리 안 문장(work/unpk: 도감 P_·엔딩·국가 정보·냥TV 등).
   이야기·도감·엔딩(고정 폭 줄)은 줄 채움 전각 공백을 빼고(맨 앞 들여쓰기 하나만 남김), 덩어리 안에서 문장이 끝나지 않고 바로 다음 줄로
   이어지는 조각은 한 줄로 합친다(재삽입 때 빌더가 줄 폭으로 다시 나눔). 같은 원문은 한 번만.
   python tools/tsv_make.py"""
import os, re, sys, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import extract as X, ui_check as UC
LIMIT = 18 * 1024
OUTD = 'my files/tsv'
WRAP = re.compile(r'(/DEMO/TXT_|/ENDING/|^@DATA_P_|^@DATA_ENDING|^@DATA_DEMO_KABE|^@DATA_NYANTV)')
UD = UC.load()
UIFILES = set(l.split('\t')[0] for l in open('work/text/ui_jp.tsv', encoding='utf-8') if l[0] != '#')
names = set((l.split('\t')[1], int(l.split('\t')[2], 16)) for l in open('work/text/names_jp.tsv', encoding='utf-8') if l[0] != '#')


NOISE = re.compile('ャャ|[≠÷]|[ａ-ｚ][ャモヤ]|^[モャヤメュ]{1,3}$')


def noisy(s):
    """그림 화소가 우연히 SJIS 로 읽힌 줄(ャ·モ·ヤ = 0x83xx 화소값, ≠÷, 전각 소문자 섞임)."""
    t = s.replace('　', '')
    if NOISE.search(t): return True
    return sum(1 for c in t if c in 'ャモヤメュ＝ｃｂａｅ泣灸給垂') * 10 >= len(t) * 4


def norm(src, s):
    if WRAP.search(src):
        lead = '　' if s.startswith('　') else ''
        return lead + s.replace('　', '').strip()
    return s


MINE = set()          # 내가 직접 번역하는 위치 지정 UI(ui_ko.tsv)
for l in open('work/text/ui_ko.tsv', encoding='utf-8'):
    if l[0] != '#' and l.strip(): p = l.split('\t'); MINE.add((p[0], int(p[1], 16)))
# 눈으로 확인한 잡음(그림·코드 바이트가 우연히 글자로 읽힌 조각) — 2026-11-07
JUNK_ROWS = {'ね般', 'ｃRマンドが実行できる', 'Pロード', '香[ドしています', 'ヲ!蓮', '楓ャヶ末封粕', '垂ヰｄヰ', '″訣メ', '麻ヶ', '＜ャ氏', '渚月モ', 'リャ喝ｌ', 'ウヨ'}
rows = []            # (출처, 위치, 바이트, 원문)
for l in open('work/text/jp.tsv', encoding='utf-8'):
    if l[0] == '#': continue
    i, fn, o, n, s = l.rstrip('\n').split('\t', 4)
    if (fn, int(o, 16)) in names or (fn, int(o, 16)) in MINE or s in JUNK_ROWS: continue
    if fn in UIFILES and len(s.replace('　', '')) <= 12 and fn != '/DATA/ITEM.BIN': continue   # UI 짧은 건 직접 번역
    if s in UD and fn in UIFILES: continue
    if fn == '/PAW.EXE' and 0x93DF4 <= int(o, 16) < 0xA31D2: continue
    rows.append((fn, int(o, 16), int(n), s))
JC = X.junk_corpus()
for p in sorted(glob.glob('work/unpk/*.bin')):
    nm = '@' + os.path.basename(p)[:-4]
    if not re.search(r'^@DATA_(P_|ENDING_|DEMO_KABE|NYANTV|PUP_)', nm): continue
    d = open(p, 'rb').read(); end = -1; prev = None
    for o, raw, s in X.strings(d):
        if o < end or not X.good(s) or any(raw in c for c in JC): continue
        end = o + len(raw)
        # 이어지는 줄 합치기: 앞 문자열 끝 직후(0 패딩 ≤ 8 B) 시작 + 앞 줄이 문장 끝 부호로 안 끝남
        if prev and prev[0] == nm and o - (prev[1] + prev[2]) <= 8 and not re.search('[。！？」』…）]$', prev[3].rstrip('　')):
            prev[2] = o + len(raw) - prev[1]; prev[3] += s; continue
        prev = [nm, o, len(raw), s]; rows.append(prev)
# 같은 원문 묶기
grp = collections.OrderedDict()
for r in rows:
    fn, o, n, s = r
    t = norm(fn, s)
    if not t.replace('　', '') or noisy(t) or t in JUNK_ROWS: continue
    grp.setdefault(t, []).append((fn, o, n))
order = lambda fn: (0 if '/DEMO/TXT_' in fn else 1 if re.search(r'/X_|/BAKU|/LOCS_OV|/S_AKANE', fn) else 2 if 'ENDING' in fn else 3 if '@DATA_P_' in fn else 4 if 'KABE' in fn or 'NYANTV' in fn else 5)
items = sorted(grp.items(), key=lambda kv: (order(kv[1][0][0]), kv[1][0][0], kv[1][0][1]))
os.makedirs(OUTD, exist_ok=True)
for p in glob.glob(OUTD + '/paro_*.tsv'): os.remove(p)
mp = open('work/text/tsv_map.tsv', 'w', encoding='utf-8'); mp.write('#번호\t파일\t위치\t바이트\n')
HEAD = '#번호\t출처\t원문\t번역\n'
chunks, cur, size = [], [], len(HEAD.encode('utf-8'))
for k, (t, locs) in enumerate(items, 1):
    src = locs[0][0].split('/')[-1].replace('@DATA_', '').split('@')[0]
    line = '%05d\t%s\t%s\t\n' % (k, src, t.replace('\t', ' '))
    for fn, o, n in locs: mp.write('%05d\t%s\t%X\t%d\n' % (k, fn, o, n))
    b = len(line.encode('utf-8'))
    if cur and size + b > LIMIT: chunks.append(cur); cur, size = [], len(HEAD.encode('utf-8'))
    cur.append(line); size += b
if cur: chunks.append(cur)
# 자투리(마지막이 작으면 앞과 합칠 수 있을 때만)
if len(chunks) >= 2:
    last = chunks.pop()
    if sum(len(x.encode('utf-8')) for x in chunks[-1] + last) + len(HEAD.encode('utf-8')) <= LIMIT: chunks[-1] += last
    else: chunks.append(last)
mp.close()
total = 0
for i, c in enumerate(chunks, 1):
    path = '%s/paro_%03d.tsv' % (OUTD, i)
    open(path, 'w', encoding='utf-8', newline='\n').write(HEAD + ''.join(c)); total += len(c)
    print(path, len(c), '줄', round(os.path.getsize(path) / 1024, 1), 'KB')
assert total == len(items)
nums = [int(l.split('\t')[0]) for i in range(1, len(chunks) + 1) for l in open('%s/paro_%03d.tsv' % (OUTD, i), encoding='utf-8') if l[0] != '#']
assert nums == list(range(1, len(items) + 1)), '번호 연속 아님'
print('합계', total, '줄 / 파일', len(chunks))
