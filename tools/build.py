# -*- coding: utf-8 -*-
"""파로 워즈 한글 빌더 (PoC 1: 인물·병기·종류·무장 이름).
   1) 한글 음절 → «원문 어디에도 안 쓰는» JIS 1수준 한자 코드(정렬해 차례로) — work/text/kcode.tsv
   2) PAW.EXE 글꼴(0x93EC0, 12×12 1비트 18 B, 범위표 0x93DF4)의 그 칸에 갈무리11 BDF 화소를 그대로 그림(왼쪽 위 맞춤, 11×11)
   3) 이름 제자리 쓰기: UNITINFO.BIN(40 B 레코드), PAW.EXE 병기(0x46)·종류(28)·무장(28) 표. 반각 영숫자·기호는 전각으로.
      원문보다 길면 칸 여유(0 연속)−1 까지만 허용, 넘치면 빌드 실패.
   4) 디스크: 원본 BIN 복사 → 바뀐 파일의 섹터만 다시 쓰고 EDC/ECC 재계산(파일 크기 불변).
   5) 검산: 새 디스크에서 파일을 다시 읽어 «바뀐 바이트가 허용 범위 안»인지·글꼴 칸이 그린 그대로인지 확인.
   python tools/build.py [--write]"""
import sys, os, shutil, struct, glob, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import discfs as D, cdsector as CS, bdf, punct, glossary
import extract as X

SRC = r'C:\claude\roms\ps\Paro Wars (Japan)\Paro Wars (Japan).bin'
OUT = 'work/disc/Paro Wars (Japan).bin'
EXE_OFF = 0x800                       # PAW.EXE 파일 위치 → 적재 0x80010010
RANGE, FONT, NG = 0x93DF4, 0x93EC0, 3457
G9 = bdf.Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf')     # 하스피 «9로 가자» — 10줄 창(兵器情報 등)에서 안 잘림


def used_chars():
    u = set()
    for l in open('work/text/jp.tsv', encoding='utf-8'):
        if l[0] != '#': u |= set(l.rstrip('\n').split('\t')[4])
    for p in glob.glob('work/unpk/*.bin'):
        for o, raw, s in X.strings(open(p, 'rb').read()):
            if X.good(s) or 'DATA_P_' in p: u |= set(s)          # 도감은 걸러진 조각 글자도 사용 중(«強さ５段階評価»의 階 가 한글 «델»로 덮인 일)
    for l in open('work/text/names_jp.tsv', encoding='utf-8'):
        if l[0] != '#': u |= set(l.rstrip('\n').split('\t')[5])
    # 짧은 UI 칸(한 글자 지형·무기 머리 등)·후보 목록 글자도 «사용 중» — 빠뜨리면 그 한자 칸에 한글이 덮여 원문이 깨진다(岸→린·橋→번, 2026-11-08)
    for f_, col in (('work/text/ui_jp.tsv', 3), ('work/text/ui_cand.tsv', 3), ('work/text/ui_ko_add.tsv', 2)):
        for l in open(f_, encoding='utf-8'):
            f2 = l.rstrip('\n').split('\t')
            if l[0] != '#' and len(f2) > col: u |= set(f2[col])
    return u


def free_kanji(used):
    out = []
    for hi in range(0x88, 0x99):
        for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            v = hi << 8 | lo
            if not 0x889F <= v <= 0x9872: continue
            try: c = bytes([hi, lo]).decode('cp932')
            except UnicodeDecodeError: continue
            if c not in used: out.append(v)
    return out


def glyph_index(exe, code):
    ent = [struct.unpack_from('<HH', exe, RANGE + 4 * i) for i in range(51)]
    for (a, b), (c, _) in zip(ent, ent[1:]):
        if a <= code < c: return b + code - a
    raise KeyError(hex(code))


ELLIPSIS = [(1, 10), (4, 10), (7, 10)]        # 한국식 말줄임표 = 바닥선(갈무리9 마침표 자리 y10) 점 셋, 한 칸


def draw(ch, pts=None):
    """갈무리9 한글 상자(x 0~8, y 2~10 고정)를 12×12 칸의 (1,1)~(9,9) 로 — 원래 한자 잉크(0~10) 가운데, 10줄 창 안."""
    if pts is None: pts, _ = G9.draw(ch)
    bits = [0] * 144
    for x, y in pts:
        xx, yy = x + 1, y - 1
        assert 0 <= xx < 11 and 0 <= yy < 10, (ch, x, y)
        bits[yy * 12 + xx] = 1
    return bytes(int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, 144, 8))


def draw_k(c):
    """한글 음절 또는 합친 글자(음절 + 칸 10~11열 부호). 부호 = 갈무리9 마침표·쉼표 화소를 음절 오른쪽 빈 열로."""
    import story
    if c not in story.LIG: return draw(c)
    syl, pu = story.LIG[c]
    if not '가' <= syl <= '힣':                                      # 전각 영문·숫자: 원래 글꼴 칸(잉크 2~8열) + 원래 부호 모양을 10열로
        def fb(ch):
            gi = glyph_index(_EXE0, int.from_bytes(ch.encode('cp932'), 'big')); b = _EXE0[FONT + gi * 18:FONT + gi * 18 + 18]
            return [int(x) for x in ''.join(format(v, '08b') for v in b)[:144]]
        a, q = fb(syl), fb(pu)
        assert not any(a[r * 12 + k] for r in range(12) for k in (10, 11)), c
        for r in range(12):
            for k in range(3):
                if q[r * 12 + k]: a[r * 12 + k + 9] = 1
        return bytes(int(''.join(map(str, a[i:i + 8])), 2) for i in range(0, 144, 8))
    pts, _ = G9.draw(syl)
    extra = [(9, 10)] if pu == '．' else [(10, 10), (9, 11)]          # (x, y) 갈무리 좌표 → 칸 (x+1, y-1): 마침표 (10,9), 쉼표 (11,9)(10,10)
    bits = [0] * 144
    for x, y in pts + extra:
        xx, yy = x + 1, y - 1
        assert 0 <= xx < 12 and 0 <= yy < 11, (c, x, y)
        bits[yy * 12 + xx] = 1
    return bytes(int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, 144, 8))


def encode(s, kmap, laid=False):
    """laid = story.py 가 이미 정규화·줄 배치한 문자열(줄 채움 공백이 부호 뒤에 올 수 있어 squeeze 금지)."""
    import story
    if not laid: s = story.norm(punct.squeeze(s))        # 전각화·대체·합친 글자(한글+．，)
    out = bytearray()
    for c in s:
        if '가' <= c <= '힣' or c in story.LIG:
            v = kmap[c]; out += bytes([v >> 8, v & 0xFF]); continue
        if c == ' ': c = '　'
        elif c == '·': c = '・'
        elif 0x21 <= ord(c) <= 0x7E: c = chr(ord(c) + 0xFEE0)
        b = c.encode('cp932')               # 못 쓰는 글자면 여기서 예외 = 빌드 실패
        if len(b) == 2: assert in_font(b[0] << 8 | b[1]), ('글꼴에 없는 글자', c, s)
        out += b
    return bytes(out)


_EXE0 = None


def in_font(code):
    """PAW.EXE 범위표(51줄, 줄 길이 = 다음 줄 칸 번호 차)에 든 코드인지."""
    ent = [struct.unpack_from('<HH', _EXE0, RANGE + 4 * i) for i in range(51)]
    for (a, b), (_, c) in zip(ent, ent[1:]):
        if a <= code < a + (c - b): return True
    return False


def main():
    write = '--write' in sys.argv
    f, vol, rl, rs, ents = D.read_fs(SRC); E = {e[0]: e for e in ents}
    rd = lambda n: D.sector(f, E[n][1], (E[n][2] + 2047) // 2048)[:E[n][2]]
    FILES = {}                                                # 고칠 파일: 이름 → [새, 원본]

    def buf(fn):
        if fn not in FILES: b = rd(fn); FILES[fn] = [bytearray(b), bytes(b)]
        return FILES[fn][0]
    exe = buf('/PAW.EXE')
    global _EXE0; _EXE0 = bytes(exe)
    punct.guard()                                            # 번역표 부호 뒤 공백 = 빌드 중단
    import story
    SK = [l.rstrip(chr(10)).split(chr(9))[1] for l in open('work/text/ko_story.tsv', encoding='utf-8') if l[0] != '#']
    J = [l.rstrip('\n').split('\t') for l in open('work/text/names_jp.tsv', encoding='utf-8') if l[0] != '#']
    K = [l.rstrip('\n').split('\t') for l in open('work/text/names_ko.tsv', encoding='utf-8') if l[0] != '#']
    U = [l.rstrip('\n').split('\t') for f_ in ('work/text/ui_ko.tsv', 'work/text/ui_ko_add.tsv') for l in open(f_, encoding='utf-8') if l[0] != '#' and l.strip()]
    assert len({(u[0], u[1]) for u in U}) == len(U), '위치 지정 UI 중복'
    # UI 사전(ui_dict.tsv): ui_jp.tsv 의 같은 원문 칸 전부에. 위치 지정(ui_ko.tsv)이 먼저.
    import ui_check as UC
    UD = UC.load(); have = {(u[0], u[1]) for u in U}
    for l in open('work/text/ui_jp.tsv', encoding='utf-8'):
        if l[0] == '#': continue
        fn_, off_, nb_, jp_ = l.rstrip('\n').split('\t')
        if jp_ in UD and (fn_, off_) not in have: U.append([fn_, off_, jp_, UD[jp_]]); have.add((fn_, off_))
    for u in U:
        pr = UC.problems(u[2], u[3])
        if len(u) > 4: pr = [x for x in pr if not x.startswith('길이')]          # 다섯째 열 = 칸 간격 안 최대 바이트(길이는 아래서 바이트로 검사)
        assert not pr, ('UI 규칙', u, pr)
        u[3] = UC.finalize(u[2], u[3])
    assert len(J) == len(K)
    # 1) 코드표(이름 + UI 고정 칸)
    isk = lambda c: '가' <= c <= '힣' or c in story.LIG
    syl = sorted(set(c for t in [k[2] for k in K] + [u[3] for u in U] + SK for c in story.norm(punct.squeeze(t)) if isk(c)))
    free = free_kanji(used_chars())
    assert len(syl) <= len(free), (len(syl), len(free))
    kmap = dict(zip(syl, free))
    with open('work/text/kcode.tsv', 'w', encoding='utf-8') as o:
        for c in syl: o.write('%s\t%04X\n' % (c, kmap[c]))
    # 2) 글꼴
    allow = []                                               # (파일, 시작, 끝) 허용 범위
    for c in syl:
        gi = glyph_index(exe, kmap[c]); assert gi < NG
        p = FONT + gi * 18; exe[p:p + 18] = draw_k(c); allow.append(('/PAW.EXE', p, p + 18))
    gi = glyph_index(exe, 0x8163); p = FONT + gi * 18                 # … 칸 = 바닥선 점 셋
    exe[p:p + 18] = draw('…', ELLIPSIS); allow.append(('/PAW.EXE', p, p + 18))
    # 3) 이름
    for j, k in zip(J, K):
        kind, fn, off, nb, room, jp = j; off = int(off, 16); nb = int(nb); room = int(room)
        assert k[1] == jp
        b = encode(k[2], kmap)
        lim = nb if len(b) <= nb else room - 1
        assert len(b) <= lim, ('칸 초과', kind, jp, k[2], len(b), room)
        bb = buf(fn); span = max(nb, len(b) + 1)
        bb[off:off + span] = b + bytes(span - len(b))
        allow.append((fn, off, off + span))
    # 3b) UI 고정 칸: 원문 바이트 확인 후 원문 길이 안에 제자리(남는 바이트 0)
    for u in U:
        fn, off, jp, ko = u[:4]
        off = int(off, 16); bb = buf(fn); jb = jp.encode('cp932')
        assert bytes(bb[off:off + len(jb)]) == jb and bb[off + len(jb)] == 0, ('UI 원문 불일치', fn, hex(off), jp)
        room = len(jb)
        if len(u) > 4:                                       # 표 칸 간격 안으로 늘림: 원문 뒤 room+1 바이트까지 원래 0 이어야(끝 0 포함)
            room = int(u[4]); assert not any(FILES[fn][1][off + len(jb):off + room + 1]), ('UI 늘릴 자리에 데이터', fn, hex(off), jp)
        b = encode(ko, kmap)
        assert len(b) <= room, ('UI 칸 초과', fn, jp, ko, len(b), room)
        bb[off:off + room] = b + bytes(room - len(b))
        allow.append((fn, off, off + room))
    # 3c) 압축 그림 교체: (파일, 덩어리 위치, [(풀린 덩어리 안 위치, 새 바이트 파일)]) — 풀기→바꾸기→다시 압축(왕복 검사)→원래 칸 안
    import lzk, lzk_pack
    import numpy as _np
    GFX = [('/DATA/DEMO/KABE0.BIN', 0, [(0x8000, 'work/미리보기_그림_A/sheet_new.npy'),          # 묶음 A 메뉴 글자판(VRAM 896,0)
                                        (0x24000, 'work/미리보기_그림_A/page24000_new.npy'),     # 前頁·次頁 버튼 쪽(VRAM 576,256)
                                        (0x10000, 'work/미리보기_그림_B/mode_new_A.npy')]),       # 묶음 B 모드 큰 글씨(VRAM 768,0) — 하스피 «A 주아»
           ('/DATA/DEMO/KABE3.BIN', 0, [(0, 'work/미리보기_그림_B/mode_new_A.npy'),                 # 같은 그림 사본
                                        (0xC000, 'work/미리보기_그림_C/status_top_new.npy'),    # 묶음 C 맵 스테이터스 이름표(사본)
                                        (0x8000, 'work/미리보기_그림_C/status_bot_new.npy')]),  # 묶음 C 나라 칸(사본)
           ('/DATA/DEMO/BACK10A.BIN', 0, [(0, 'work/미리보기_그림_K/BACK10A_new.bin')]),   # 보류 ① 체스 간판(파운드 포 파운드 in 체스)
           ('/DATA/DEMO/BACK11A.BIN', 0, [(0, 'work/미리보기_그림_K/BACK11A_new.bin')]),   # 보류 ② 댄스 대회 현수막
           ('/DATA/DEMO/BACK13A.BIN', 0, [(0, 'work/미리보기_그림_K/BACK13A_new.bin')]),   # 보류 ③ 판다 궁전 간판(다회주의, tools/sign13_kr.py)
           ('/DATA/DEMO/BACK13B.BIN', 0, [(0, 'work/미리보기_그림_K/BACK13B_new.bin')]),   # 보류 ③ 같은 간판(입 벌린 장면)
           ('/DATA/DEMO/PEN4_01.BIN', 0, [(0x4000, 'work/미리보기_그림_K/pen4_01_4000_new.bin')]),   # 보류 ④ 말풍선(우스시오FC·파로냥코호)
           ('/DATA/DEMO/WMAP0.BIN', 0, [(0, 'work/미리보기_그림_E/wmap_0_new.bin')]),        # 묶음 E 세계지도 지명 21개(VRAM 768,0 8비트)
           ('/DATA/DEMO/KABE2.BIN', 0, [(0x4000, 'work/미리보기_그림_C/status_top_new.npy'),    # 묶음 C 이름표(VRAM 0,256 위 반)
                                        (0, 'work/미리보기_그림_C/status_bot_new.npy')]),       # 묶음 C 나라 칸(아래 반)
           ('/DATA/DEMO/KABE1.BIN', 0, [(0x24000, 'work/미리보기_그림_A/page24000_kabe1_new.npy')])]  # 같은 버튼 사본(두 사각형만)
    # 3d) 이야기·대사·도감·도움말(tools/story.py 배치) — 평문 파일은 바로, 압축 덩어리(@파일@위치)는 3c 와 같이 풀기→쓰기→다시 압축
    SW, sbad, sskip = story.plan(lambda t: encode(t, kmap, laid=True))
    assert not sbad, ('이야기 배치 실패', sbad[:5])
    print('이야기 보류(따로 처리):', sskip)
    disk = {fn.replace('/', '_')[1:]: fn for fn in E}
    gfx = {(fn, coff): edits for fn, coff, edits in GFX}
    for key, ws in SW.items():
        if key.startswith('@'):
            nm, co = key[1:].rsplit('@', 1); fn = disk[nm]
            gfx.setdefault((fn, int(co, 16)), []).extend((o, b) for o, b in ws)
            continue
        bb = buf(key)
        for o, b in ws:
            assert not any(f_ == key and a < o + len(b) and o < c for f_, a, c in allow), ('이름·UI 칸과 겹침', key, hex(o))
        for o, b in ws:
            bb[o:o + len(b)] = b; allow.append((key, o, o + len(b)))
    import band_kr                                           # 묶음 D 나라 띠·머리글: 데모 덩어리 40개 사본 전부(원문 블록 바이트 일치만)
    for key, o, b in band_kr.edits():
        nm, co = key[1:].rsplit('@', 1); fn = disk[nm]
        gfx.setdefault((fn, int(co, 16)), []).append((o, b))
    import flag_kr                                           # 턴 시작 큰 나라 이름(FLAG.BIN 덩어리 9개 — 모아이 VS 없음·판다 순서 다름·냥 제국)
    for co, o, b in flag_kr.edits()[0]:
        gfx.setdefault(('/DATA/FLAG.BIN', co), []).append((o, b))
    GFX = [(fn, coff, ed) for (fn, coff), ed in gfx.items()]
    for fn, coff, edits in GFX:
        bb = buf(fn)
        raw, used = lzk.unpack(bytes(bb), coff); raw = bytearray(raw)
        for off, src in edits:
            if isinstance(src, (bytes, bytearray)): data = src
            else: data = _np.load(src).astype(_np.uint8).tobytes() if src.endswith('.npy') else open(src, 'rb').read()
            raw[off:off + len(data)] = data
        if fn == '/DATA/FLAG.BIN': pk = lzk_pack.pack_exact(bytes(raw), used, hdr3=bb[coff + 3])   # 잇달아 붙은 덩어리 — 길이 그대로(뒤 위치·머리 길이 보존)
        else: pk = lzk_pack.pack(bytes(raw), hdr3=bb[coff + 3])
        room = len(bb) - coff if not any(bb[coff + used:]) else used     # 덩어리 뒤에 다른 바이트(KABE0·3 섹터 여분 등)가 있으면 원래 압축 길이까지만
        assert len(pk) <= room, ('압축 그림 칸 넘침', fn, len(pk), room)
        bb[coff:coff + len(pk)] = pk
        allow.append((fn, coff, coff + len(pk)))
        print(fn, '그림 다시 압축', used, '→', len(pk), '(칸', room, ')')
    # 3e) 평문 그림 교체(압축 아님): (파일, 위치, 새 바이트 파일) — 크기 그대로 제자리
    PLAIN = [('/DATA/FIX.BIN', 0xC000, 'work/미리보기_그림_G/fix_C000_new.bin'),       # 묶음 G 상태 줄 나라 이름(VRAM 672,384 4비트)
             ('/DATA/MCWGRPH.BIN', 0xC000, 'work/미리보기_그림_H/mcw_C000_new.bin'),   # 묶음 H 세이브 칸 라벨(VRAM 928,0 4비트)
             ('/DATA/MATI.BIN', 0x11728, 'work/미리보기_그림_J/mati_lvup_new.bin'),        # 그림 J 레벨업(행 순서 거꾸로 저장, 정방향 16줄×128 B)
             ] + [('/DATA/MTIT/MTIT%d.BIN' % k, 0, 'work/미리보기_그림_F/MTIT%d_new.BIN' % k) for k in range(1, 13)]   # 묶음 F 이벤트 제목(그림+배치표 통째)
    for fn, off, src in PLAIN:
        bb = buf(fn); data = open(src, 'rb').read()
        bb[off:off + len(data)] = data; allow.append((fn, off, off + len(data)))
        print(fn, '평문 그림', hex(off), len(data))
    # 그림 J 둘째 사본(MATI.BIN, 행 순서 반대 — 0x127A8 에서 행마다 −128): 맵에서 처음 도는 레벨업(하스피 «레벨업이 두벌»)
    _lv = open('work/미리보기_그림_J/mati_lvup_new.bin', 'rb').read(); bb = buf('/DATA/MATI.BIN')
    for r in range(2, 16):
        o = 0x127A8 - 128 * r
        assert bytes(bb[o:o + 40]) == FILES['/DATA/MATI.BIN'][1][0x11728 + 128 * r:0x11728 + 128 * r + 40], ('레벨업 둘째 사본 원본 아님', r)
        bb[o:o + 40] = _lv[128 * r:128 * r + 40]; allow.append(('/DATA/MATI.BIN', o, o + 40))
    # 3f) 냥티비 음성 자막 훅(tools/nyatv_hook.py): 안 쓰는 함수 0x8005164C 자리에 코드 + jal 두 곳
    import nyatv_hook as NH
    nblob, npatch, nsec, _, _, _ = NH.build()
    bb = buf('/PAW.EXE'); EA = lambda a: a - 0x80010010 + 0x800
    o = EA(NH.CODE); assert bytes(bb[o:o + 8]) == bytes.fromhex('c8ffbd272400b3af'), '자막 코드 자리 원본 아님'
    bb[o:o + len(nblob)] = nblob; allow.append(('/PAW.EXE', o, o + len(nblob)))
    for adr, w in npatch:
        o = EA(adr); old = struct.unpack_from('<I', bb, o)[0]
        assert old in (0x0C004D58, 0x0C02574F), ('자막 훅 자리 원본 아님', hex(adr), hex(old))
        struct.pack_into('<I', bb, o, w); allow.append(('/PAW.EXE', o, o + 4))
    print('냥티비 자막 훅', len(nblob), 'B · 섹터', len(nsec) // 2048)
    # 4) 범위 밖 변경 0 검사
    for fn, (new, old) in FILES.items():
        assert len(new) == len(old)
        rng = [(a, b) for f_, a, b in allow if f_ == fn]
        bad = [i for i in range(len(new)) if new[i] != old[i] and not any(a <= i < b for a, b in rng)]
        assert not bad, (fn, '허용 밖 변경', [hex(x) for x in bad[:8]])
        print(fn, '바뀐 바이트', sum(1 for i in range(len(new)) if new[i] != old[i]))
    print('음절', len(syl), '이름', len(K), 'UI', len(U), '이야기 쓰기', sum(len(v) for v in SW.values()))
    if not write: return
    # 5) 디스크
    os.makedirs(os.path.dirname(OUT), exist_ok=True); shutil.copyfile(SRC, OUT)
    with open(OUT, 'r+b') as g:
        for fn, (data, _) in FILES.items():
            lba, size = E[fn][1], E[fn][2]
            for s in range((size + 2047) // 2048):
                g.seek((lba + s) * 2352); sec = bytearray(g.read(2352))
                chunk = data[s * 2048:(s + 1) * 2048]
                if sec[24:24 + len(chunk)] == chunk: continue
                sec[24:24 + len(chunk)] = chunk; CS.fix_sector(sec)
                g.seek((lba + s) * 2352); g.write(sec)
        for i in range(len(nsec) // 2048):                       # 냥티비 자막 섹터 = 디스크 끝 빈 섹터(볼륨 안)
            g.seek((NH.SUB0 + i) * 2352); sec = bytearray(g.read(2352))
            assert sec[15] == 2 and not any(sec[24:2072]), ('자막 섹터 자리가 비어 있지 않음', NH.SUB0 + i)
            sec[16:24] = bytes([0, 0, 8, 0, 0, 0, 8, 0]); sec[24:2072] = nsec[i * 2048:(i + 1) * 2048]; CS.fix_sector(sec)
            g.seek((NH.SUB0 + i) * 2352); g.write(sec)
    # 6) 되읽기 검산
    f2, _, _, _, ents2 = D.read_fs(OUT); E2 = {e[0]: e for e in ents2}
    for fn, (data, _) in FILES.items():
        back = D.sector(f2, E2[fn][1], (E2[fn][2] + 2047) // 2048)[:E2[fn][2]]
        assert back == bytes(data), fn
    with open(OUT, 'rb') as g:
        for i in range(len(nsec) // 2048):
            g.seek((NH.SUB0 + i) * 2352 + 24); assert g.read(2048) == nsec[i * 2048:(i + 1) * 2048], ('자막 섹터 되읽기', i)
    print('완료', OUT)


if __name__ == '__main__':
    main()
