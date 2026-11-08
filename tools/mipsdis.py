# -*- coding: utf-8 -*-
"""PAW.EXE(MIPS R3000, 적재 0x80010010, 머리 0x800) 역어셈(capstone).  python tools/mipsdis.py 0x8005a8e0 [개수] [파일]"""
import sys, capstone
f = sys.argv[3] if len(sys.argv) > 3 else 'work/PAW.EXE'
d = open(f, 'rb').read(); a = int(sys.argv[1], 16); n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
o = a - 0x80010010 + 0x800          # t_addr 0x80010010
for i in md.disasm(d[o:o + n * 4], a): print('%08x  %s %s' % (i.address, i.mnemonic, i.op_str))
