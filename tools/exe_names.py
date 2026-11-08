# -*- coding: utf-8 -*-
"""PAW.EXE 안 파일 이름 문자열 나열(읽기 전용).  python tools/exe_names.py [패턴]"""
import re, sys
d = open('work/PAW.EXE', 'rb').read()
pat = sys.argv[1] if len(sys.argv) > 1 else r'(?i)\.BIN|%0|TXT|cdrom'
for m in re.finditer(rb'[A-Za-z0-9_%./:\\;]{4,48}', d):
    s = m.group().decode()
    if re.search(pat, s): print(hex(m.start()), hex(m.start() - 0x800 + 0x80010000), s)
