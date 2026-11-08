# -*- coding: utf-8 -*-
"""PAW.EXE 에서 LZ 풀기 함수 후보 찾기(읽기 전용): 짧은 구간(48명령) 안에 lbu·sb 가 여럿 + 비트 검사(andi 1 / 0x80) + 시프트 1 + 뒤로 가는 분기(루프).
   python tools/find_lz.py [파일 적재주소]"""
import sys, capstone, struct
f = sys.argv[1] if len(sys.argv) > 1 else 'work/PAW.EXE'
base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x80010010
d = open(f, 'rb').read(); hdr = 0x800 if d[:8] == b'PS-X EXE' else 0
md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
ins = []
for o in range(hdr, len(d) - 3, 4):
    w = d[o:o + 4]
    try: i = next(md.disasm(w, base + o - hdr))
    except StopIteration: ins.append(None); continue
    ins.append((i.address, i.mnemonic, i.op_str))
res = []
N = 48
for k in range(0, len(ins) - N, 8):
    win = [x for x in ins[k:k + N] if x]
    lbu = sum(1 for a, m, s in win if m == 'lbu'); sb = sum(1 for a, m, s in win if m == 'sb')
    bit = sum(1 for a, m, s in win if m == 'andi' and (s.endswith(', 1') or s.endswith(', 0x80')))
    sh1 = sum(1 for a, m, s in win if m in ('srl', 'sll', 'sra') and s.endswith(', 1'))
    back = sum(1 for a, m, s in win if m.startswith('b') and m != 'break' and s.split(', ')[-1].startswith('0x') and int(s.split(', ')[-1], 16) < a)
    if lbu >= 2 and sb >= 1 and bit >= 1 and sh1 >= 1 and back >= 1:
        res.append((lbu + sb + 2 * bit + 2 * sh1, win[0][0]))
seen = set()
for sc, a in sorted(res, reverse=True)[:40]:
    if a // 0x100 in seen: continue
    seen.add(a // 0x100); print(hex(a), sc)
