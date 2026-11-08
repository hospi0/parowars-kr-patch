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
RAM(커널 빈 곳, 스테이트 58장 공통 0·코드 참조 0) 0x8000C000 섹터 / 0x8000C800 상태(+0 k, +4 s3, +8 시작, +12 쪽, +16 적재 항목) / 0x8000C840 패킷
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
SX, SY = 216, 93                  # 화면 자리(티비 창 x228~299·y12~90 아래)
CODE = 0x8005164C; CODE_WORDS = 266
HOOK_LOAD_AT = 0x8005FDA0; HOOK_DRAW_AT = 0x800118C4
ORIG_LOAD = 0x80013560; ORIG_DRAW = 0x80095D3C
BUF, ST, P = 0x8000C000, 0x8000C800, 0x8000C840
P_CLUT, P_IMG1, P_IMG2, P_SPR = P, P + 48, P + 48 + 928, P + 48 + 928 * 2


def width(s):
    return sum(F.draw(c)[1] for c in s)


def wrap(s):
    toks = []
    for wi, w in enumerate(s.split(' ')):
        parts = [x for x in re.split(r'(?<=[.,!?~…])', w) if x]
        for pi, x in enumerate(parts): toks.append((x, wi > 0 and pi == 0))
    out, cur = [], ''
    for x, sp in toks:
        t = (cur + (' ' if sp else '') + x) if cur else x
        if width(t) <= BOX_W - 2: cur = t; continue
        if cur: out.append(cur)
        cur = ''
        for ch in x:
            if width(cur + ch) > BOX_W - 2: out.append(cur); cur = ''
            cur += ch
    if cur: out.append(cur)
    return out


def page_px(lines):
    """→ 96×38 값 0/1/2 (1 글자, 2 테두리)"""
    T = np.zeros((PH, BOX_W), bool)
    for i, l in enumerate(lines):
        for c in l: assert c == ' ' or ord(c) in F.g, ('갈무리7에 없는 글자', c, l)
        pts, w = F.draw(l); ox = (BOX_W - w) // 2
        for a, b in pts:
            y = 1 + i * LH + b
            if 0 <= y < PH and 0 <= ox + a < BOX_W: T[y, ox + a] = True
    O = np.zeros_like(T)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            O |= np.roll(np.roll(T, dy, 0), dx, 1)
    px = np.zeros((PH, BOX_W), np.uint8); px[O & ~T] = 2; px[T] = 1
    return px


def pack2(px):
    f = px.reshape(-1, 4).astype(np.uint8)
    return (f[:, 0] | f[:, 1] << 2 | f[:, 2] << 4 | f[:, 3] << 6).astype(np.uint8).tobytes()


def sectors():
    # 자막은 문장이 이어지는 글이라 부호 뒤 공백을 지우지 않는다(하스피 2026-11-08, 3쪽 넘침 0 확인)
    rd = lambda n: [l.rstrip('\n').split('\t') for l in open(ROOT + '/work/voice/' + n, encoding='utf-8').readlines()[1:]]
    ko = {int(r[0]): r[1] for r in rd('nyatv_ko.tsv')}
    dur = {int(r[0]): float(r[5]) for r in rd('nyatv_map.tsv')}
    out = bytearray(); pages_all = {}
    for k in range(1, 126):
        ls = wrap(ko[k]); pgs = [ls[i:i + LINES] for i in range(0, len(ls), LINES)]
        assert len(pgs) <= 2, (k, len(pgs))
        n = [sum(len(x) for x in p) for p in pgs]; tot = sum(n); ends = []; acc = 0
        for i in range(len(pgs)):
            acc += n[i]; ends.append(0xFFFF if i == len(pgs) - 1 else int(dur[k] * 60 * acc / tot))
        sec = bytearray(2048); struct.pack_into('<HHH', sec, 0, len(pgs), *(ends + [0xFFFF])[:2])
        for i, p in enumerate(pgs):
            sec[16 + 912 * i:16 + 912 * (i + 1)] = pack2(page_px(p))
        out += sec; pages_all[k] = (pgs, ends)
    return bytes(out), pages_all


def _table():
    clut = ((504 << 6) | (608 >> 4))
    return ([(P_CLUT, (11 << 24) | (P_IMG1 & 0xFFFFFF)), (P_CLUT + 4, 0xA0000000), (P_CLUT + 8, (504 << 16) | 608), (P_CLUT + 12, (1 << 16) | 16),
             (P_CLUT + 16, 0x7FFF0000), (P_CLUT + 20, 0x00008000)] + [(P_CLUT + 24 + 4 * i, 0) for i in range(6)] +
            [(P_IMG1, (231 << 24) | (P_IMG2 & 0xFFFFFF)), (P_IMG1 + 4, 0xA0000000), (P_IMG1 + 8, (464 << 16) | 608), (P_IMG1 + 12, (19 << 16) | 24),
             (P_IMG2, (231 << 24) | (P_SPR & 0xFFFFFF)), (P_IMG2 + 4, 0xA0000000), (P_IMG2 + 8, (483 << 16) | 608), (P_IMG2 + 12, (19 << 16) | 24),
             (P_SPR, (7 << 24) | 0xFFFFFF), (P_SPR + 4, 0x01000000), (P_SPR + 8, 0xE1000419), (P_SPR + 12, 0xE2000000), (P_SPR + 16, 0x64808080),
             (P_SPR + 20, (SY << 16) | SX), (P_SPR + 24, (clut << 16) | (208 << 8) | 128), (P_SPR + 28, (PH << 16) | BOX_W)])


def hi(a): return ((a + 0x8000) >> 16) & 0xFFFF


def lo(a):
    v = a & 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def source(TA, NT):
    return f"""
.set noreorder
hook_load:
    addiu $sp, $sp, -40
    sw $ra, 36($sp)
    sw $a0, 32($sp)
    sw $a1, 28($sp)
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    sw $zero, 0($t2)
    lbu $t0, 0x7f7($s3)
    nop
    addiu $t1, $t0, -1
    sltiu $t1, $t1, 125
    beqz $t1, L_skip
    nop
    sw $t0, 24($sp)
    lui $t3, {hi(BUF)}
    addiu $t3, $t3, {lo(BUF)}
    sw $t3, 16($t2)
    addiu $t3, $zero, 0x800
    sw $t3, 20($t2)
    lui $t3, {(SUB0 - 1) >> 16}
    ori $t3, $t3, {(SUB0 - 1) & 0xFFFF}
    addu $t3, $t3, $t0
    sw $t3, 24($t2)
    lui $a0, 0xf200
    jal 0x80099568
    ori $a0, $a0, 3
    lui $a0, {hi(ST + 16)}
    addiu $a0, $a0, {lo(ST + 16)}
    jal 0x8002a4e8
    addiu $a1, $zero, 3
    sw $v0, 20($sp)
    lui $a0, 0xf200
    jal 0x80099534
    ori $a0, $a0, 3
L_wait:
    lw $t0, 20($sp)
    nop
    lh $t1, 6($t0)
    nop
    bnez $t1, L_done
    nop
    jal 0x80099340
    lui $a0, 0xff00
    j L_wait
    nop
L_done:
    lui $t0, {hi(TA)}
    addiu $t0, $t0, {lo(TA)}
    addiu $t1, $zero, {NT}
L_cp:
    lw $v0, 0($t0)
    lw $v1, 4($t0)
    addiu $t0, $t0, 8
    addiu $t1, $t1, -1
    bnez $t1, L_cp
    sw $v1, 0($v0)
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    addiu $t1, $zero, -1
    sw $s3, 4($t2)
    sw $t1, 8($t2)
    sw $t1, 12($t2)
    lw $t0, 24($sp)
    nop
    sw $t0, 0($t2)
L_skip:
    lw $a0, 32($sp)
    lw $a1, 28($sp)
    lw $ra, 36($sp)
    j {ORIG_LOAD}
    addiu $sp, $sp, 40
hook_draw:
    addiu $sp, $sp, -24
    sw $ra, 20($sp)
    jal {ORIG_DRAW}
    nop
    lui $t2, {hi(ST)}
    addiu $t2, $t2, {lo(ST)}
    lw $t1, 0($t2)
    lw $t3, 4($t2)
    beqz $t1, D_ret
    nop
    lbu $t4, 0x7f7($t3)
    lui $t5, 0x800b
    lbu $t5, 0x6628($t5)
    bne $t4, $t1, D_off
    lw $t6, 8($t2)
    lui $t7, 0x800c
    lw $t7, -0x3588($t7)
    addiu $t8, $zero, -1
    bne $t6, $t8, D_started
    nop
    beqz $t5, D_ret
    nop
    sw $t7, 8($t2)
    move $t6, $t7
D_started:
    beqz $t5, D_off
    nop
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
    addiu $v0, $zero, 912
    mult $t9, $v0
    mflo $v0
    addu $a1, $t0, $v0
    addiu $a1, $a1, 16
    lui $a2, {hi(P_IMG1 + 16)}
    addiu $a2, $a2, {lo(P_IMG1 + 16)}
    move $t4, $zero
    addiu $a3, $zero, 912
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
    addiu $v0, $zero, 456
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
    addiu $sp, $sp, 24
    jr $ra
    nop
D_off:
    b D_ret
    sw $zero, 0($t2)
"""


def build():
    """→ (코드+표 바이트, 패치 [(주소, jal 워드)], 섹터 바이트, 쪽 정보, 라벨, 표 주소)"""
    from keystone import Ks, KS_ARCH_MIPS, KS_MODE_MIPS32, KS_MODE_LITTLE_ENDIAN
    ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN)
    table = _table(); ta = CODE + 0x300
    for _ in range(4):
        src = source(ta, len(table))
        code = bytes(ks.asm(src, CODE)[0]); want = CODE + ((len(code) + 7) // 8) * 8
        if want == ta: break
        ta = want
    assert want == ta
    blob = code + bytes(ta - CODE - len(code)) + b''.join(struct.pack('<II', a, v) for a, v in table)
    assert len(blob) <= CODE_WORDS * 4, ('코드 자리 넘침', len(blob), CODE_WORDS * 4)
    lab, n = {}, 0
    for l in src.split('\n'):
        m = re.match(r'^(\w+):\s*$', l)
        if m: lab[m.group(1)] = CODE + 4 * n
        elif l.strip() and not l.strip().startswith('.'): n += 1
    assert 4 * n == len(code), ('명령 수 셈 어긋남', n, len(code))
    jal = lambda t: 0x0C000000 | ((t >> 2) & 0x3FFFFFF)
    patches = [(HOOK_LOAD_AT, jal(lab['hook_load'])), (HOOK_DRAW_AT, jal(lab['hook_draw']))]
    sec, pages = sectors()
    return blob, patches, sec, pages, lab, ta


if __name__ == '__main__':
    import capstone
    blob, patches, sec, pages, lab, ta = build()
    open(ROOT + '/work/voice/nyatv_hook.bin', 'wb').write(blob)
    open(ROOT + '/work/voice/nyatv_sectors.bin', 'wb').write(sec)
    print('코드+표', len(blob), 'B /', CODE_WORDS * 4, '· 라벨', {k: hex(v) for k, v in lab.items() if not k.startswith(('L_', 'D_'))}, '· 표', hex(ta))
    print('패치', [(hex(a), hex(w)) for a, w in patches])
    print('섹터', len(sec) // 2048, '개 · 쪽 수', {n: sum(1 for v in pages.values() if len(v[0]) == n) for n in (1, 2)})
    if '-d' in sys.argv:
        md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
        for ins in md.disasm(blob[:ta - CODE], CODE): print(hex(ins.address)[2:], ins.mnemonic, ins.op_str)
