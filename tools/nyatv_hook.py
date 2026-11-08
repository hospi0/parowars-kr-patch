# -*- coding: utf-8 -*-
r"""냥티비 음성 자막 훅(2026-11-08, 하스피 «오른쪽 상단 티비 밑에 작게»)

자료
  work/voice/nyatv_ko.tsv(번역 125줄) · nyatv_map.tsv(번호 ↔ 클립 길이)
  → 번호 k(1~125)마다 섹터 1개(디스크 끝 빈 섹터 LBA SUB0+k-1, 볼륨 안·원래 0):
     +0 u16 쪽 수 n(≤2) · +2 u16 쪽 끝 시각[2](VBlank, 마지막 = 0xFFFF) · +16 쪽 그림 2비트 96×38(912 B, 4화소/바이트 LSB 먼저, 1 = 글자 흰색, 2 = 테두리 검정)
코드(PAW.EXE 0x8005164C — 호출·포인터·외부 분기 0인 게임 함수 자리, 266워드)
  hook_load : 0x8005FDA0 «jal 0x80013560»(TV 자료 정리) 대신. k = lbu 0x7F7(s3).
              게임 적재기 0x8002A4E8({0x8000C000, 0x800, SUB0+k-1}, 3) → 완료(lh 6(h)) 까지 0x80099340 으로 양보 → 패킷·상태 초기화 → j 0x80013560.
  hook_draw : 0x800118C4 프레임 전환의 마지막 «jal 0x80095D3C»(DrawOTag) 대신. 원래 DrawOTag 뒤에,
              무장(k) && s3->0x7F7 == k && 음성 상태(0x800B6628) ≠ 0 이면 경과 VBlank(VSync 카운터 0x800BCA78)로 쪽을 골라
              바뀌었으면 2→4비트 펼침 → DrawOTag(CLUT 올림 + 그림 올림 2조각 + 캐시 비움·tpage·SPRT).
              음성 상태가 0 이 되거나 번호가 바뀌면 끔.
⚠ VBlank 에 스레드가 선점 전환됨 — 무장(k_init) 먼저, 그다음 jal 설치(반대면 그 사이 프레임이 «무장 안 됨»으로 보고 즉시 복원).
RAM(커널 빈 곳, 스테이트 58장 공통 0·코드 참조 0) 0x8000C000 섹터 / 0x8000C800 상태(+0 k, +4 s3, +8 시작, +12 쪽, +16 코드 적재 항목, +28 자료 적재 항목, +40 k, +44 ra, +48 a0, +52 a1, +56 loadone ra, +60 적재 손잡이 — ⚠양보(0x80099340) 사이에 스택 프레임이 깨짐(냥티비 크래시) → 토막은 스택을 안 씀 — ⚠한 항목 재사용 금지: 적재기가 완료 뒤 항목을 되돌려 둘째 요청이 코드 섹터를 다시 읽음) / 0x8000C840 패킷
VRAM(맵 스테이트 46장 공통 0) 그림 (608,464) 24hw×38 · CLUT (608,504) · tpage (576,256) 4비트 → u128 v208
  python tools/nyatv_hook.py → work/voice/nyatv_hook.bin · nyatv_sectors.bin · 미리보기"""
import sys, os, re, struct
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bdf, punct
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = bdf.Font('C:/claude/utils/font/Galmuri-v2.40.3/Galmuri7.bdf')
BOX_W, LINES, LH, PH = 96, 4, 9, 38
SUB0 = 298426                     # 마지막 파일 끝(298426) ~ 볼륨 끝(298576) 빈 섹터 150개
SX, SY = 216, 93                  # 냥티비: 티비 창 x228~299·y12~90 아래
WX, WY = 60, 166                  # 병기 해설: 상태 줄(y≈208) 바로 위 가운데(하스피) — 200×20, 두 줄(하스피 «가로로·두줄 정도»)
WW, WH, WLINES = 200, 20, 2
NW = 16; WV0 = 1062; NV0 = 1089
TMP = 0x8000D100                  # 해설 1비트 풀 자리(≤912 B)   # 해설 음성 1062+i(i 0~15, 명령 0x727+i) · 냥티비 음성 1089+k
# EXE 토막 자리 = 글꼴 한자 칸 끝 21칸(JIS 1수준 마지막 0x9872 까지)을 비워서 씀(하스피 «한자칸 비워서 써») — build.py 가 이 칸들을 한글 배정에서 뺌
_E = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'PAW.EXE'), 'rb').read()
_ENT = [struct.unpack_from('<HH', _E, 0x93DF4 + 4 * i) for i in range(51)]
def _gi(code):
    for (a, b), (c, _) in zip(_ENT, _ENT[1:]):
        if a <= code < c: return b + code - a
    raise KeyError(hex(code))
CAVE_G1 = _gi(0x9872) + 1; CAVE_G0 = CAVE_G1 - 400                     # 글리프 번호 [G0, G1)
def _kanji_codes():
    out = []
    for c in range(0x889F, 0x9873):
        if (c & 0xFF) == 0x7F or not 0x40 <= (c & 0xFF) <= 0xFC: continue
        try: bytes([c >> 8, c & 0xFF]).decode('cp932')
        except UnicodeDecodeError: continue
        out.append(c)
    return out
CAVE_CODES = [c for c in _kanji_codes() if CAVE_G0 <= _gi(c) < CAVE_G1]
assert len(CAVE_CODES) == CAVE_G1 - CAVE_G0, ('동굴에 한자 아닌 칸', len(CAVE_CODES), CAVE_G1 - CAVE_G0)
_A0 = 0x80010010 + 0x93EC0 - 0x800 + CAVE_G0 * 18; _A1 = 0x80010010 + 0x93EC0 - 0x800 + CAVE_G1 * 18
CODE = (_A0 + 3) & ~3; CODE_WORDS = (_A1 - CODE) // 4
# 코드 전체 = 한자 칸 끝 82칸에 한 덩어리(하스피 «한자칸 더 비워서») — 디스크엔 번호별 자막 섹터만(SUB0+k-1)
HOOK_LOAD_AT = 0x8005FDA0; HOOK_DRAW_AT = 0x800118C4
ORIG_LOAD = 0x80013560; ORIG_DRAW = 0x80095D3C
BUF, ST, P = 0x8000C000, 0x8000C800, 0x8000C880          # ST 128 B(아래 source 머리 설명), 패킷 P~
P_CLUT, P_IMG1, P_IMG2, P_SPR = P, P + 48, P + 48 + 928, P + 48 + 928 * 2


def width(s):
    return sum(F.draw(c)[1] for c in s)


def wrap(s, maxw=None):
    toks = []
    for wi, w in enumerate(s.split(' ')):
        parts = [x for x in re.split(r'(?<=[.,!?…])', w) if x]
        for pi, x in enumerate(parts): toks.append((x, wi > 0 and pi == 0))
    out, cur = [], ''
    for x, sp in toks:
        t = (cur + (' ' if sp else '') + x) if cur else x
        if width(t) <= (maxw or BOX_W - 2): cur = t; continue
        if cur: out.append(cur)
        cur = ''
        for ch in x:
            if width(cur + ch) > (maxw or BOX_W - 2): out.append(cur); cur = ''
            cur += ch
    if cur: out.append(cur)
    return out


def page_px(lines, W=None, H=None):
    """→ 96×38 값 0/1/2 (1 글자, 2 테두리)"""
    W = W or BOX_W; H = H or PH
    T = np.zeros((H, W), bool)
    for i, l in enumerate(lines):
        for c in l: assert c == ' ' or ord(c) in F.g, ('갈무리7에 없는 글자', c, l)
        pts, w = F.draw(l); ox = (W - w) // 2
        for a, b in pts:
            y = 1 + i * LH + b
            if 0 <= y < H and 0 <= ox + a < W: T[y, ox + a] = True
    O = np.zeros_like(T)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            O |= np.roll(np.roll(T, dy, 0), dx, 1)
    px = np.zeros((H, W), np.uint8); px[O & ~T] = 2; px[T] = 1
    return px


def pack2(px):
    f = px.reshape(-1, 4).astype(np.uint8)
    return (f[:, 0] | f[:, 1] << 2 | f[:, 2] << 4 | f[:, 3] << 6).astype(np.uint8).tobytes()


def _pages(ko, dur):
    ls = wrap(ko); pgs = [ls[i:i + LINES] for i in range(0, len(ls), LINES)]
    n = [sum(len(x) for x in p) for p in pgs]; tot = sum(n); ends = []; acc = 0
    for i in range(len(pgs)):
        acc += n[i]; ends.append(0xFFFF if i == len(pgs) - 1 else int(dur * 60 * acc / tot))
    sec = bytearray(2048); struct.pack_into('<HHH', sec, 0, len(pgs), *(ends + [0xFFFF])[:2])
    for i, p in enumerate(pgs):
        sec[16 + 912 * i:16 + 912 * (i + 1)] = pack2(page_px(p))
    return sec, pgs, ends


def sectors():
    """냥티비 125(SUB0+k-1) + 병기 해설 16(SUB0+125+i). 자막은 부호 뒤 공백 유지(하스피)."""
    rd = lambda n: [l.rstrip(chr(10)).split(chr(9)) for l in open(ROOT + '/work/voice/' + n, encoding='utf-8').readlines()[1:]]
    ko = {int(r[0]): r[1] for r in rd('nyatv_ko.tsv')}; dur = {int(r[0]): float(r[5]) for r in rd('nyatv_map.tsv')}
    wko = {int(r[0]): r[1] for r in rd('weapon_ko.tsv')}; wdur = {int(r[0]): float(r[4]) for r in rd('weapon_map.tsv')}
    out = bytearray(); pages_all = {}
    for k in range(1, 126):
        sec, pgs, ends = _pages(ko[k], dur[k]); assert len(pgs) <= 2, ('냥티비', k, len(pgs)); out += sec; pages_all['N%d' % k] = (pgs, ends)
    assert len(out) // 2048 <= 150
    return bytes(out), pages_all


def wpayload():
    """병기 해설 16: [(쪽 수, 첫 쪽 끝 VBlank, LZ(1비트 글자 쪽들 456 B씩))] — 테두리는 실행 중 3×3 로 만듦."""
    import lzk_pack, lzk
    rd = lambda n: [l.rstrip(chr(10)).split(chr(9)) for l in open(ROOT + '/work/voice/' + n, encoding='utf-8').readlines()[1:]]
    wko = {int(r[0]): r[1] for r in rd('weapon_ko.tsv')}; wdur = {int(r[0]): float(r[4]) for r in rd('weapon_map.tsv')}
    out = []
    for i in range(NW):
        ls = wrap(wko[i], WW - 2); pgs = [ls[k:k + WLINES] for k in range(0, len(ls), WLINES)]; assert len(pgs) <= 2, ('해설', i, len(pgs))
        n = [sum(len(x) for x in p_) for p_ in pgs]; end0 = 0xFFFF if len(pgs) == 1 else int(wdur[i] * 60 * n[0] / sum(n))
        raw = b''.join(np.packbits((page_px(p_, WW, WH) == 1).astype(np.uint8), axis=1, bitorder='little').tobytes() for p_ in pgs)
        assert len(raw) == WW // 8 * WH * len(pgs)
        lz = lzk_pack.pack(raw); assert lzk.unpack(lz)[0] == raw
        out.append((len(pgs), end0, lz, pgs))
    return out


def _table(mode):
    """k_init 이 베끼는 (주소, 값) 표 — 모드마다 패킷 배치·VRAM·화면·쪽 크기가 다름. ST+96 = 쪽 2비트 바이트, ST+100 = 첫 올림 조각 hw."""
    clut = ((504 << 6) | (608 >> 4))
    if mode == 'N': vx, wh_, h1, sx, sy, sw, sh_, u = 608, 24, 19, SX, SY, BOX_W, PH, 128
    else:           vx, wh_, h1, sx, sy, sw, sh_, u = 576, WW // 4, WH // 2, WX, WY, WW, WH, 0
    split = wh_ * h1; total = wh_ * sh_; img2 = P_IMG1 + 16 + split * 2; spr = img2 + 16 + (total - split) * 2
    assert 3 + split // 2 <= 255 and 3 + (total - split) // 2 <= 255 and spr + 32 <= TMP, (mode, split, total, hex(spr))
    t = [(P_CLUT, (11 << 24) | (P_IMG1 & 0xFFFFFF)), (P_CLUT + 4, 0xA0000000), (P_CLUT + 8, (504 << 16) | 608), (P_CLUT + 12, (1 << 16) | 16),
         (P_CLUT + 16, 0x7FFF0000), (P_CLUT + 20, 0x00008000)] + [(P_CLUT + 24 + 4 * i, 0) for i in range(6)]
    t += [(P_IMG1, ((3 + split // 2) << 24) | (img2 & 0xFFFFFF)), (P_IMG1 + 4, 0xA0000000), (P_IMG1 + 8, (464 << 16) | vx), (P_IMG1 + 12, (h1 << 16) | wh_),
          (img2, ((3 + (total - split) // 2) << 24) | (spr & 0xFFFFFF)), (img2 + 4, 0xA0000000), (img2 + 8, ((464 + h1) << 16) | vx), (img2 + 12, ((sh_ - h1) << 16) | wh_),
          (spr, (7 << 24) | 0xFFFFFF), (spr + 4, 0x01000000), (spr + 8, 0xE1000419), (spr + 12, 0xE2000000), (spr + 16, 0x64808080),
          (spr + 20, (sy << 16) | sx), (spr + 24, (clut << 16) | (208 << 8) | u), (spr + 28, (sh_ << 16) | sw),
          (ST + 96, total), (ST + 100, split)]
    return t


def hi(a): return ((a + 0x8000) >> 16) & 0xFFFF


def lo(a):
    v = a & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


JAL_DRAW = 0x0C011111                      # 첫 어셈블용 자리표(0 이면 keystone 이 명령을 달리 냄)
ORIG_DRAW_JAL = 0x0C000000 | ((ORIG_DRAW >> 2) & 0x3FFFFFF)


HOOK_W_AT = 0x8003245C; ORIG_SND = 0x80023EBC        # 병기 해설: «jal 0x80023EBC ; addiu a0, s0, 0x727» (첫 사용 때 한 번)


def one_source(TN, TW, WDIR):
    """음성 자막 한 덩어리(한자 칸 동굴).
    ST(0x8000C800) +0 무장된 음성 ID(0=꺼짐) +4 화면 xy +8 시작 VBlank(-1) +12 지금 쪽(-1) +16 해설 적재 항목(12) +28 냥티비 적재 항목(12)
       +40 냥티비 k +44/+48/+52 load 토막 ra·a0·a1 +56 loadone ra +60 냥티비 적재 손잡이 +64 해설 대기 손잡이(0=없음)
       +68 무장 VBlank(대기 시간 재기) +72/+76 해설 토막 ra·a0 +80 해설 번호 +84 해설 대기 음성 ID
    규칙: 양보 사이 스택 금지(고정 칸) · VBlank 선점 → 무장 먼저, jal 설치 나중 · lw 바로 뒤 그 레지스터 금지."""
    return f"""
.set noreorder
stub_load:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    sw $ra, 44($t2)
    sw $a0, 48($t2)
    sw $a1, 52($t2)
    sw $zero, 0($t2)
    sw $zero, 64($t2)
    lbu $t0, 0x7f7($s3)
    nop
    addiu $t1, $t0, -1
    sltiu $t1, $t1, 125
    beqz $t1, S_skip
    sw $t0, 40($t2)
    lui $t3, {hi(BUF)}
    addiu $t3, $t3, {lo(BUF)}
    sw $t3, 28($t2)
    addiu $t3, $zero, 0x800
    sw $t3, 32($t2)
    lui $t3, {(SUB0 - 1) >> 16}
    ori $t3, $t3, {(SUB0 - 1) & 0xFFFF}
    addu $t3, $t3, $t0
    sw $t3, 36($t2)
    jal loadone
    addiu $a0, $t2, 28
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $a0, 40($t2)
    lui $a1, {hi(TN)}
    addiu $a1, $a1, {lo(TN)}
    jal k_init
    addiu $a0, $a0, {NV0}
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $t0, 0($t2)
    nop
    beqz $t0, S_skip
    nop
    jal install
    nop
S_skip:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $ra, 44($t2)
    lw $a0, 48($t2)
    lw $a1, 52($t2)
    j {ORIG_LOAD}
    nop
loadone:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    sw $ra, 56($t2)
    sw $a0, 60($t2)
    lui $a0, 0xf200
    jal 0x80099568
    ori $a0, $a0, 3
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $a0, 60($t2)
    jal 0x8002a4e8
    addiu $a1, $zero, 3
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    sw $v0, 60($t2)
    lui $a0, 0xf200
    jal 0x80099534
    ori $a0, $a0, 3
O_wait:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $t0, 60($t2)
    nop
    lh $t1, 6($t0)
    nop
    bnez $t1, O_done
    nop
    jal 0x80099340
    lui $a0, 0xff00
    j O_wait
    nop
O_done:
    lw $ra, 56($t2)
    nop
    jr $ra
    nop
install:
    lui $t0, {hi(HOOK_DRAW_AT)}
    lui $t1, {JAL_DRAW >> 16}
    ori $t1, $t1, {JAL_DRAW & 0xFFFF}
    sw $t1, {lo(HOOK_DRAW_AT)}($t0)
    addiu $t2, $zero, 0xa0
    jr $t2
    addiu $t1, $zero, 0x44
stub_weapon:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    sw $ra, 72($t2)
    sw $a0, 76($t2)
    addiu $t0, $a0, -0x727
    sltiu $t1, $t0, {NW}
    beqz $t1, W_skip
    sw $t0, 80($t2)
    sw $zero, 0($t2)
    sw $zero, 64($t2)
    lui $t1, {hi(WDIR)}
    addiu $t1, $t1, {lo(WDIR)}
    sll $t0, $t0, 3
    addu $t1, $t1, $t0
    lw $a0, 0($t1)
    lhu $t3, 4($t1)
    lhu $t4, 6($t1)
    lui $t5, {hi(BUF)}
    addiu $t5, $t5, {lo(BUF)}
    sh $t3, 0($t5)
    sh $t4, 2($t5)
    ori $t6, $zero, 0xffff
    sh $t6, 4($t5)
    sw $t3, 88($t2)
    lui $a1, {hi(TMP)}
    jal 0x80013cac
    addiu $a1, $a1, {lo(TMP)}
    jal conv
    nop
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $a0, 80($t2)
    lui $a1, {hi(TW)}
    addiu $a1, $a1, {lo(TW)}
    jal k_init
    addiu $a0, $a0, {WV0}
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $t0, 0($t2)
    nop
    beqz $t0, W_skip
    nop
    jal install
    nop
W_skip:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $ra, 72($t2)
    lw $a0, 76($t2)
    j {ORIG_SND}
    nop
conv:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    sw $ra, 92($t2)
    lw $a0, 88($t2)
    move $a3, $zero
C_page:
    beq $a3, $a0, C_done
    nop
    addiu $v0, $zero, {WW // 8 * WH}
    mult $a3, $v0
    mflo $v0
    lui $t8, {hi(TMP)}
    addiu $t8, $t8, {lo(TMP)}
    addu $t8, $t8, $v0
    addiu $v0, $zero, {WW // 4 * WH}
    mult $a3, $v0
    mflo $v0
    lui $t9, {hi(BUF + 16)}
    addiu $t9, $t9, {lo(BUF + 16)}
    addu $t9, $t9, $v0
    move $t0, $zero
C_y:
    move $t1, $zero
C_x:
    move $t2, $t1
    jal tpx
    move $t3, $t0
    bnez $t4, C_put
    addiu $t7, $zero, 1
    addiu $v0, $zero, -1
C_dy:
    addiu $v1, $zero, -1
C_dx:
    addu $t2, $t1, $v1
    jal tpx
    addu $t3, $t0, $v0
    bnez $t4, C_put
    addiu $t7, $zero, 2
    addiu $v1, $v1, 1
    slti $t5, $v1, 2
    bnez $t5, C_dx
    nop
    addiu $v0, $v0, 1
    slti $t5, $v0, 2
    bnez $t5, C_dy
    nop
    move $t7, $zero
C_put:
    addiu $t5, $zero, {WW // 4}
    mult $t0, $t5
    mflo $t5
    srl $t6, $t1, 2
    addu $t5, $t5, $t6
    addu $t5, $t5, $t9
    andi $t6, $t1, 3
    bnez $t6, C_or
    sll $t6, $t6, 1
    sb $zero, 0($t5)
C_or:
    lbu $a1, 0($t5)
    sllv $a2, $t7, $t6
    or $a1, $a1, $a2
    sb $a1, 0($t5)
    addiu $t1, $t1, 1
    slti $t5, $t1, {WW}
    bnez $t5, C_x
    nop
    addiu $t0, $t0, 1
    slti $t5, $t0, {WH}
    bnez $t5, C_y
    nop
    b C_page
    addiu $a3, $a3, 1
C_done:
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $ra, 92($t2)
    nop
    jr $ra
    nop
tpx:
    bltz $t2, T_no
    slti $t5, $t2, {WW}
    beqz $t5, T_no
    nop
    bltz $t3, T_no
    slti $t5, $t3, {WH}
    beqz $t5, T_no
    addiu $t5, $zero, {WW // 8}
    mult $t3, $t5
    mflo $t5
    srl $t6, $t2, 3
    addu $t5, $t5, $t6
    addu $t5, $t5, $t8
    lbu $t5, 0($t5)
    andi $t6, $t2, 7
    srlv $t5, $t5, $t6
    jr $ra
    andi $t4, $t5, 1
T_no:
    jr $ra
    move $t4, $zero
stub_draw:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    jal {ORIG_DRAW}
    nop
    jal k_draw
    nop
    lw $ra, 20($sp)
    nop
    jr $ra
    addiu $sp, $sp, 24
k_init:
    lw $t1, 0($a1)
    addiu $t0, $a1, 4
I_cp:
    lw $v0, 0($t0)
    lw $v1, 4($t0)
    addiu $t0, $t0, 8
    addiu $t1, $t1, -1
    bnez $t1, I_cp
    sw $v1, 0($v0)
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    addiu $t1, $zero, -1
    sw $t1, 8($t2)
    sw $t1, 12($t2)
    lui $t7, 0x800c
    lw $t7, -0x3588($t7)
    nop
    sw $t7, 68($t2)
    lui $t3, {hi(BUF)}
    lhu $t4, {lo(BUF)}($t3)
    nop
    addiu $t4, $t4, -1
    sltiu $t4, $t4, 2
    beqz $t4, I_bad
    nop
    jr $ra
    sw $a0, 0($t2)
I_bad:
    jr $ra
    sw $zero, 0($t2)
k_draw:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $t1, 0($t2)
    nop
    bnez $t1, D_armed
    nop
    lw $t0, 64($t2)
    nop
    beqz $t0, D_off
    nop
    lh $t3, 6($t0)
    nop
    beqz $t3, D_pend
    nop
    sw $zero, 64($t2)
    lw $a0, 84($t2)
    lui $a1, {hi(TW)}
    jal k_init
    addiu $a1, $a1, {lo(TW)}
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $t1, 0($t2)
    nop
    beqz $t1, D_off
    nop
D_armed:
    lui $t5, 0x800b
    lbu $t5, 0x6628($t5)
    lui $t4, 0x8014
    lw $t4, 0x6a8($t4)
    lw $t6, 8($t2)
    lui $t7, 0x800c
    lw $t7, -0x3588($t7)
    addiu $t8, $zero, -1
    bne $t6, $t8, D_started
    nop
    bne $t4, $t1, D_wait
    nop
    beqz $t5, D_wait
    nop
    sw $t7, 8($t2)
    b D_go
    move $t6, $t7
D_pend:
    lui $t7, 0x800c
    lw $t7, -0x3588($t7)
D_wait:
    lw $t0, 68($t2)
    nop
    subu $t0, $t7, $t0
    sltiu $t0, $t0, 600
    bnez $t0, D_ret
    nop
    b D_off
    nop
D_started:
    beqz $t5, D_off
    nop
    bne $t4, $t1, D_off
    nop
D_go:
    subu $t7, $t7, $t6
    lui $t0, {hi(BUF)}
    addiu $t0, $t0, {lo(BUF)}
    lhu $t4, 0($t0)
    move $t9, $zero
    addiu $t8, $t4, -1
D_find:
    slt $v0, $t9, $t8
    beqz $v0, D_have
    sll $v1, $t9, 1
    addu $v1, $v1, $t0
    lhu $v1, 2($v1)
    nop
    slt $v0, $t7, $v1
    bnez $v0, D_have
    nop
    b D_find
    addiu $t9, $t9, 1
D_have:
    lw $v0, 12($t2)
    nop
    beq $v0, $t9, D_draw
    nop
    sw $t9, 12($t2)
    lw $v0, 96($t2)
    nop
    mult $t9, $v0
    mflo $v0
    addu $a1, $t0, $v0
    addiu $a1, $a1, 16
    lui $a2, {hi(P_IMG1 + 16)}
    addiu $a2, $a2, {lo(P_IMG1 + 16)}
    move $t4, $zero
    lw $a3, 96($t2)
D_exp:
    lbu $v0, 0($a1)
    addiu $a1, $a1, 1
    andi $v1, $v0, 3
    srl $t5, $v0, 2
    andi $t5, $t5, 3
    sll $t5, $t5, 4
    or $v1, $v1, $t5
    srl $t5, $v0, 4
    andi $t5, $t5, 3
    sll $t5, $t5, 8
    or $v1, $v1, $t5
    srl $t5, $v0, 6
    sll $t5, $t5, 12
    or $v1, $v1, $t5
    sh $v1, 0($a2)
    addiu $a2, $a2, 2
    addiu $t4, $t4, 1
    lw $v0, 100($t2)
    nop
    bne $t4, $v0, D_nj
    nop
    addiu $a2, $a2, 16
D_nj:
    bne $t4, $a3, D_exp
    nop
D_draw:
    lui $a0, {hi(P)}
    jal {ORIG_DRAW}
    addiu $a0, $a0, {lo(P)}
D_ret:
    lw $ra, 20($sp)
    nop
    jr $ra
    addiu $sp, $sp, 24
D_off:
    sw $zero, 0($t2)
    sw $zero, 64($t2)
    lui $t0, {hi(HOOK_DRAW_AT)}
    lui $t1, {ORIG_DRAW_JAL >> 16}
    ori $t1, $t1, {ORIG_DRAW_JAL & 0xFFFF}
    sw $t1, {lo(HOOK_DRAW_AT)}($t0)
    addiu $t2, $zero, 0xa0
    jalr $t2
    addiu $t1, $zero, 0x44
    b D_ret
    nop
"""


JAL_DRAW = 0x0C011111                      # 첫 어셈블용 자리표(0 이면 keystone 이 명령을 달리 냄)
ORIG_DRAW_JAL = 0x0C000000 | ((ORIG_DRAW >> 2) & 0x3FFFFFF)


def _labels(src, base):
    lab, n = {}, 0
    for l in src.split('\n'):
        m = re.match(r'^(\w+):\s*$', l)
        if m: lab[m.group(1)] = base + 4 * n
        elif l.strip() and not l.strip().startswith('.set'): n += 1
    return lab, n


def build():
    """→ (EXE 한 덩어리(코드 + 표 N·W + 해설 목록 + 해설 LZ), 패치, 냥티비 자료 섹터 125, 쪽 정보, 라벨)"""
    global JAL_DRAW
    from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN
    ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN)
    tN, tW = _table('N'), _table('W'); wp = wpayload(); ta = CODE + 0x800
    for _ in range(8):
        TN = ta; TW = TN + 4 + 8 * len(tN); WDIR = TW + 4 + 8 * len(tW)
        src = one_source(TN, TW, WDIR); code = bytes(ks.asm(src, CODE)[0])
        lab, n = _labels(src, CODE); assert 4 * n == len(code), ('명령 수', n, len(code))
        JAL_DRAW = 0x0C000000 | ((lab['stub_draw'] >> 2) & 0x3FFFFFF)
        want = CODE + ((len(code) + 7) // 8) * 8
        if want == ta and one_source(TN, TW, WDIR) == src: break
        ta = want
    tabs = b''
    for t in (tN, tW): tabs += struct.pack('<I', len(t)) + b''.join(struct.pack('<II', a_, v) for a_, v in t)
    blobs = b''; ents = b''; a = WDIR + NW * 8
    for (np_, end0, lz, _) in wp:
        ents += struct.pack('<IHH', a + len(blobs), np_, end0); blobs += lz
    blob = code + bytes(ta - CODE - len(code)) + tabs + ents + blobs
    assert CODE + len(code) <= ta and len(blob) <= CODE_WORDS * 4, ('코드 자리 넘침', len(blob), CODE_WORDS * 4)
    jal = lambda t: 0x0C000000 | ((t >> 2) & 0x3FFFFFF)
    patches = [(HOOK_LOAD_AT, jal(lab['stub_load'])), (HOOK_W_AT, jal(lab['stub_weapon']))]
    data, pages = sectors()
    for i, (np_, end0, lz, pgs) in enumerate(wp): pages['W%d' % i] = (pgs, end0)
    return blob, patches, data, pages, lab


if __name__ == '__main__':
    import capstone
    stub, patches, sec, pages, lab = build()
    open(ROOT + '/work/voice/nyatv_hook.bin', 'wb').write(stub)
    open(ROOT + '/work/voice/nyatv_sectors.bin', 'wb').write(sec)
    print('EXE 한 덩어리', len(stub), 'B /', CODE_WORDS * 4, '· 자료 섹터', len(sec) // 2048)
    print('라벨', {k: hex(v) for k, v in lab.items() if k in ('stub_load', 'loadone', 'stub_draw', 'k_init', 'k_draw')})
    print('패치', [(hex(a), hex(w)) for a, w in patches], '· 쪽 수', {n: sum(1 for v in pages.values() if len(v[0]) == n) for n in (1, 2)})
    if '-d' in sys.argv:
        md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
        for ins in md.disasm(stub, CODE): print(hex(ins.address)[2:], ins.mnemonic, ins.op_str)
