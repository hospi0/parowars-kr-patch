# -*- coding: utf-8 -*-
"""이야기·대사·도감·도움말 재삽입 배치 (build.py 가 부름).  python tools/story.py = 배치만 검사(디스크 안 씀)
   입력: work/text/ko_story.tsv(번호·한글), work/text/tsv_map.tsv(번호 → 파일·위치·원문 바이트).
   원문 배치 실측(2026-11-08):
     · 이야기 DEMO/TXT_*·엔딩 *_TXT: 150 B 레코드 = 25칸×3줄 격자(글자·전각 공백 모두 한 칸, 0 = 끝).
       화자 줄 «이름：「…» 은 다음 줄부터 «이름：「» 길이만큼 내어쓰기(원문 전수 일치). 줄 넘김은 전각 공백으로 채워서.
     · 도감 P_##·국가 정보 KABE: 52 B 간격 줄 칸(글자 50 B = 25칸 + 0 0). 도움말 SEL_HELP: 50 B 간격(48 B = 24칸 + 0 0).
       칸 뒤에 남의 데이터(예: 攻撃力 줄 뒤 守備力)가 있으면 그 칸은 원문 길이까지만.
     · 전투 대사 X_ 60 B·BAKU 50 B·아이템 ITEM 96 B 레코드: 제자리(＠ = 줄바꿈 원문 코드), 레코드 꼬리는 원래 0 이어야 씀.
     · 그 밖: 원문 바이트 길이 안 제자리.
   줄 나눔: 띄어쓰기·문장부호 뒤에서만 끊고(낱말 안 끊기), 안 되면 글자 단위.
   ＃(01529·01533) = 그 자리 원문의 攻撃力 숫자."""
import os, re, sys, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ko_merge as KM

FW = lambda s: ''.join('　' if c == ' ' else chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in s)
SUB = {'"': '”', "'": '’', '㎞': 'ｋｍ', '㎜': 'ｍｍ', '氣': '気', '·': '・', '〜': '～', '−': '－', '‘': '’'}
BRK_AFTER = set('、。，．,.！？!?」』）)…～・：')
SPEAKER = re.compile(r'^(　?[^「」『』　]{1,12}?：[「『])')
REC = lambda fn: 150 if ('/DEMO/TXT_' in fn or fn.endswith('TXT_END.BIN') or re.search(r'ENDING_[A-Z]+_TXT', fn)) else \
    60 if re.search(r'/X_[A-Z]+\.BIN', fn) else 50 if re.search(r'/BAKU\d*\.BIN', fn) else 96 if fn.endswith('/ITEM.BIN') else None
GRID = lambda fn: REC(fn) == 150
PFIX_A, PFIX_B = '守備力　'.encode('cp932'), '수비력　'
PATK_A, PATK_B = '攻撃力　'.encode('cp932'), '공격력　'
PSTAR_A, PSTAR_B = '　　　◆強さ５段階評価◆'.encode('cp932'), '　◆강함　５단계　평가◆'
# 도감 능력치 줄 꼬리(번역표 자리 없음, 이름표 뒤 값 부분) — (덩어리, 위치, 원문, 한글, 최대 바이트)
P_TAIL = [('@DATA_P_39.BIN@F84', 0x4828, '３（陸への攻撃は激弱）', '３（육상　공격　최약）', 22),
          ('@DATA_P_11.BIN@B0', 0x4848, '４（３に近い）', '４（３에　가까움）', 22)]
# 번역표에 없던 레코드(전수 검사 tools/leftover 식으로 찾음, 2026-11-08) — (파일 키, 위치, 원문, 한글)
_TITLE = '　' * 5 + '고양이 통조림 용기（성배）'                 # 엔딩 가운데 제목(25칸 한 줄)
REC_EXTRA = [(k, o, '　' * 8 + 'ネコ缶容器（聖盃）' + '　' * 8, _TITLE) for k, o in
             [('/DATA/ENDING/TXT_END.BIN', 0x79E)] + [('@DATA_ENDING_%s_TXT.BIN@0' % c, 0x79E) for c in ('PEN', 'PAN', 'BAU', 'BUT', 'LOV', 'MOA', 'TAK')] +
             [('@DATA_ENDING_KOI_TXT.BIN@0', 0x8CA)]] +             [('/DATA/X_BERIAL.BIN', 0x11DC, '修行不足ね', '수행 부족이네'), ('/DATA/X_MOAI.BIN', 0x4BC, 'ン～', '응～'), ('/DATA/X_MOAI.BIN', 0x570, 'ン～', '응～')]
PSTAR2_A, PSTAR2_B = '　　　　強さ５段階評価'.encode('cp932'), '　　강함　５단계　평가'    # ◆ 없는 변형(P_55 등 3곳)
SLOT = lambda fn: (50, 24) if fn.endswith('SEL_HELP.BIN') else (52, 25) if re.search(r'^@DATA_(P_|DEMO_KABE)', fn) else None


USE_LIG = False
LIG = {}                  # 합친 글자(사용자 영역 문자) → (한글 음절, 부호)
_LIGR = {}


def lig(s):
    """한글 바로 뒤 ． ， 를 그 음절 칸 오른쪽 아래(글꼴 칸 10~11열)에 찍은 «합친 글자» 하나로 —
       이 게임은 글자마다 12px 칸 하나라 부호를 따로 두면 점 뒤가 공백처럼 보인다(하스피 실기 지적)."""
    if not USE_LIG: return s                     # 하스피 2026-11-08: 합친 글자 취소 — 쉼표·마침표는 제 칸 그대로
    out = []; i = 0
    while i < len(s):
        c = s[i]
        if ('가' <= c <= '힣' or re.fullmatch('[Ａ-Ｚａ-ｚ０-９]', c)) and i + 1 < len(s) and s[i + 1] in '．，':
            k = (c, s[i + 1])
            if k not in _LIGR:
                u = chr(0xE000 + len(_LIGR)); _LIGR[k] = u; LIG[u] = k
            out.append(_LIGR[k]); i += 2; continue
        out.append(c); i += 1
    return ''.join(out)


def norm(s):
    for a, b in SUB.items(): s = s.replace(a, b)
    return lig(FW(s))


def wrap(s, widths):
    """s 를 줄 폭 목록(widths[i] = i번째 줄 폭)에 맞춰 나눔 — 낱말 가운데 끊김 수가 가장 적게(같으면 앞줄을 꽉 채움).
       띄어쓰기에서 끊으면 그 공백은 버림(둘째 줄부터 줄 머리 공백 버림). 못 넣으면 None."""
    n = len(s); R = len(widths)
    if n == 0: return ['']

    def cost(j):                                   # j 에서 끊는 값: 0 = 띄어쓰기·부호 뒤, 2 = 부호 앞(줄 머리 부호), 1 = 낱말 가운데
        if j < n and s[j - 1] in '「『（': return 3                  # 여는 괄호로 줄을 끝내지 않기
        if j >= n or s[j] == '　' or s[j - 1] == '　': return 0
        if s[j] in BRK_AFTER: return 5                     # 줄 머리 부호는 낱말 가운데 끊김보다 나쁨
        return 0 if s[j - 1] in BRK_AFTER else 1
    INF = 10 ** 9; best = {}

    def go(i, r):                                  # i 부터 r 번째 줄 → (값, 줄 목록)
        if (i, r) in best: return best[(i, r)]
        st = i
        if r:
            while st < n and s[st] == '　': st += 1
        if st >= n: return (0, [])
        if r >= R: return (INF, None)
        res = (INF, None)
        for j in range(min(n, st + widths[r]), st, -1):
            c = cost(j) if j < n else 0
            sub = go(j, r + 1)
            if sub[1] is None: continue
            v = c + sub[0]
            if v < res[0]: res = (v, [s[st:j].rstrip('　')] + sub[1])
        best[(i, r)] = res; return res
    v, L = go(0, 0)
    global LAST_COST; LAST_COST = v                 # 낱말 가운데 끊김 등 비용(0 = 띄어쓰기·부호 뒤에서만 끊음)
    return L


def grid_text(s, W=25, rows=3):
    m = SPEAKER.match(s); ind = len(m.group(1)) if m else 0
    L = wrap(s, [W] + [W - ind] * (rows - 2) + [W - ind - 1])      # 마지막 줄 = 끝 0 자리(레코드 148 B = 74칸)
    if L is None: return None
    out = ''
    for k, l in enumerate(L):
        if k: out += '　' * ind
        out += l
        if k < len(L) - 1: out += '　' * ((W - ind if k else W) - len(l))
    return out


def kabe4(enc, bad):
    """국가 정보 쪽 배치. 줄 = 22 B(11칸) + 0 4 B, 12칸째(24 B)는 부호·괄호로 끝날 때만(원문도 그렇게 씀)."""
    d = data('@DATA_DEMO_KABE4.BIN@0'); out = []
    pages = {}; cur = None
    for l in open('work/text/kabe4_ko.txt', encoding='utf-8'):
        l = l.rstrip(chr(10))
        if l.startswith('# '): continue
        if l.startswith('## '): cur = tuple(map(int, l[3:].split())); pages[cur] = []; continue
        if cur: pages[cur].append(l)
    assert len(pages) == 24, len(pages)
    for (k, p), L in pages.items():
        base = 0x10000 + (k - 1) * 0x35A + (p - 1) * 11 * 26
        if p == 2:
            rows = wrap(norm(''.join(L).strip(chr(10))), [11] * 10)          # 창에 보이는 건 10줄(11번째 잘림 — 하스피 실기)
            if rows is None or LAST_COST: bad.append(('KABE4 %d-%d' % (k, p), '문단 10줄 넘침 또는 낱말 가운데 끊김', ''.join(L))); continue
        else:
            while L and L[-1] == '': L.pop()
            rows = [norm(x) for x in L]
        if len(rows) > 10: bad.append(('KABE4 %d-%d' % (k, p), '10줄 넘침', rows)); continue
        rows += [''] * (11 - len(rows))
        for r, t in enumerate(rows):
            o = base + r * 26
            orig = d[o:o + 26]
            assert not any(orig[24:26]), ('KABE4 줄 끝', hex(o))
            b = enc(t) if t else '　'.encode('cp932')
            if len(b) > 24 or (len(b) > 22 and t[-1] not in '）」』！？。、．，'): bad.append(('KABE4 %d-%d-%d' % (k, p, r), '줄 넘침 %dB' % len(b), t)); continue
            out.append((o, b + bytes(26 - len(b))))
    return out


def load():
    K = {l.split('\t')[0]: l.rstrip('\n').split('\t')[1] for l in open('work/text/ko_story.tsv', encoding='utf-8') if l[0] != '#'}
    M = collections.defaultdict(list)
    for l in open('work/text/tsv_map.tsv', encoding='utf-8'):
        if l[0] == '#': continue
        i, fn, o, n = l.rstrip('\n').split('\t'); M[fn].append((int(o, 16), int(n), i))
    return K, M


def data(fn):
    return open('work/unpk/' + fn[1:] + '.bin' if fn.startswith('@') else 'work/files' + fn, 'rb').read()


def plan(enc):
    """enc(문자열) → 바이트. 반환: {파일키: [(위치, 새 바이트)]}, 문제 목록. 파일키 '@…' = 압축 덩어리(풀린 바이트 기준)."""
    K, M = load()
    src = {}
    import glob
    for p in sorted(glob.glob('my files/tsv/paro_*.tsv')):
        for i, v in KM.load(p).items(): src[i] = v
    KM.SRC.update({i: v[1] for i, v in src.items()})
    W = collections.defaultdict(list); bad = []

    def put(fn, off, b): W[fn].append((off, b))

    def text(d, o, n, i):
        ko = K[i]
        if '＃' in ko:
            m = re.match('攻撃力　([０-９]+)', d[o:o + n].decode('cp932')); assert m, (i, hex(o))
            ko = ko.replace('＃', m.group(1))
        return norm(ko)
    skipped = []
    for fn, L in M.items():
        if 'KABE4' in fn:                          # 국가 정보 = 나라 8 × 3쪽 × 11줄(26 B 간격) — work/text/kabe4_ko.txt 쪽 단위(아래 kabe4())
            for o_, b_ in kabe4(enc, bad): put(fn, o_, b_)
            continue
        d = data(fn); L.sort()
        for f_, o_, jp_, ko_ in REC_EXTRA:
            if f_ == fn:
                jb = jp_.encode('cp932'); rec_ = REC(fn)
                assert d[o_:o_ + len(jb)] == jb and not any(d[o_ + len(jb):o_ + rec_]), (fn, hex(o_))
                b_ = enc(norm(ko_)); assert len(b_) <= rec_ - 2, (ko_, len(b_)); put(fn, o_, b_ + bytes(rec_ - len(b_)))
        for f_, o_, jp_, ko_, room_ in P_TAIL:
            if f_ == fn:
                jb = jp_.encode('cp932'); assert d[o_:o_ + len(jb)] == jb and not any(d[o_ + len(jb):o_ + room_ + 2]), (fn, hex(o_))
                b_ = enc(norm(ko_)); assert len(b_) <= room_, (ko_, len(b_)); put(fn, o_, b_ + bytes(room_ - len(b_)))
        if fn.startswith('@DATA_P_'):              # 도감 고정 머리(번역표에 없음): 守備力 줄 이름·強さ 평가 제목
            for a, b in ((PFIX_A, PFIX_B), (PATK_A, PATK_B), (PSTAR_A, PSTAR_B), (PSTAR2_A, PSTAR2_B)):
                k = d.find(a)
                while k >= 0:
                    if not any(o <= k < o + n for o, n, _ in L): put(fn, k, enc(b))     # 번역표 자리면 그쪽이 씀
                    k = d.find(a, k + 1)
        rec = REC(fn); sl = SLOT(fn); done = set()
        for k0, (o, n, i) in enumerate(L):
            if (o, i) in done: continue
            s = text(d, o, n, i)
            if rec:
                assert not any(d[o + n:o + rec]), ('레코드 꼬리에 데이터', fn, hex(o), i)
                if GRID(fn):
                    assert o % rec == 0, ('레코드 시작 아님', fn, hex(o), i)
                    g = grid_text(s)
                    if g is None or len(g) > (rec - 2) // 2:
                        bad.append((i, fn, '3줄 넘침', s)); continue
                    s = g
                b = enc(s)
                if len(b) > rec - 2: bad.append((i, fn, '%dB>%d' % (len(b), rec - 2), s)); continue
                put(fn, o, b + bytes(rec - len(b)))
                continue
            if sl:
                # 자리별 문단 묶음(ko_merge.budget 과 같은 규칙, 단 파일·자리 단위)
                stride, w = sl
                if fn.endswith('SEL_HELP.BIN'):                            # 도움말 = 5줄 상자 3개(에너지·시야·Z.O.C.) — 상자 단위로만
                    bx = o // (stride * 5)
                    mem = [x for x in L if x[0] // (stride * 5) == bx]
                    slots = [(so, 2 * w, d[so:so + 2 * w]) for so in range(bx * stride * 5, (bx + 1) * stride * 5, stride)]
                    txt = ''.join(text(d, oo, nn, ii) for oo, nn, ii in mem)
                    Lw = wrap(txt, [w] * 5)
                    if Lw is None:
                        bad.append((','.join(m[2] for m in mem), fn, '도움말 상자 5줄 넘침(%d칸)' % len(txt), txt)); done.update((m[0], m[2]) for m in mem); continue
                    for q, (so, capb, seg) in enumerate(slots):
                        b = enc(Lw[q]) if q < len(Lw) else '　'.encode('cp932')
                        put(fn, so, b + bytes(capb - len(b)))
                    done.update((m[0], m[2]) for m in mem)
                    continue
                para = fn.startswith('@DATA_P_')
                star = lambda ii: '★' in KM.SRC.get(ii, '')
                mem = [(o, n, i)]; end = o + ((n + stride - 1) // stride) * stride; k = k0
                while para and not star(i) and k + 1 < len(L) and L[k + 1][0] == end and not star(L[k + 1][2]):
                    k += 1; mem.append(L[k]); end += ((L[k][1] + stride - 1) // stride) * stride
                nxt = L[k + 1][0] if k + 1 < len(L) else len(d); ex = 0
                blank = lambda x: not any(x.replace(bytes([0x81, 0x40]), bytes(2)))
                while end + stride <= nxt and ex < 3 and blank(d[end:end + stride]): end += stride; ex += 1
                slots = []
                for so in range(o, end, stride):
                    seg = d[so:so + 2 * w]; u = len(seg)
                    for q in range(0, len(seg), 2):
                        if seg[q:q + 2] == bytes(2): u = q; break
                    capb = 2 * w if not any(seg[u:]) else u                  # 칸 뒤에 남의 데이터 → 원문 길이까지
                    slots.append((so, capb, seg))
                txt = ''
                for oo, nn, ii in mem:                                     # 도감 조각 잇기: 한글·」 뒤 한글·「 면 띄어쓰기(「없음」|모드, 인접해서|보급)
                    t2 = text(d, oo, nn, ii)
                    if txt and t2 and re.match('[가-힣」-]', txt[-1]) and re.match('[가-힣「]', t2[0]): txt += '　'
                    txt += t2
                Lw = wrap(txt, [c // 2 for _, c, _ in slots])
                if Lw is None: bad.append((','.join(m[2] for m in mem), fn, '줄 칸 넘침(%d칸)' % len(slots), txt)); continue
                for q, (so, capb, seg) in enumerate(slots):
                    if q < len(Lw):
                        b = enc(Lw[q]); assert len(b) <= capb
                        put(fn, so, b + bytes(capb - len(b)))
                    elif any(seg[:capb].replace(bytes([0x81, 0x40]), bytes(2))):
                        put(fn, so, '　'.encode('cp932') + bytes(capb - 2))       # 원래 글자 있던 칸 = 빈 줄(전각 공백)
                done.update((m[0], m[2]) for m in mem)
                continue
            b = enc(s)
            if len(b) > n: bad.append((i, fn, '%dB>%d' % (len(b), n), s)); continue
            put(fn, o, b + bytes(n - len(b)))
    # 겹침 검사
    for fn, ws in W.items():
        ws.sort()
        for (a, x), (c, y) in zip(ws, ws[1:]):
            assert a + len(x) <= c or (a == c and x == y), ('겹쳐 씀', fn, hex(a), hex(c))
    return W, bad, skipped


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    enc = lambda s: bytes(len(s) * 2)
    W, bad, sk = plan(enc)
    print('보류', sk)
    print('파일', len(W), '쓰기', sum(len(v) for v in W.values()), '문제', len(bad))
    for b in bad: print(' ', b)
