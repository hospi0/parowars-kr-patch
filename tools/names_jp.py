# -*- coding: utf-8 -*-
"""이름 원본표 work/text/names_jp.tsv 만들기(읽기 전용 추출).
   인물 = UNITINFO.BIN 40 B 레코드 맨 앞(칸 30 B) · 병기 = PAW.EXE 0x8F404~ 0x46 B 레코드
   종류 = PAW.EXE 0x90B50~0x90D56 **14 B** 레코드(2026-11-07 실기: 28 B 로 읽어 절반 누락했던 것 바로잡음)
   무장 = PAW.EXE 0x90DA0~ 28 B 레코드.  열: 종류·파일·위치·원문바이트·칸여유(0 연속)·원문"""
import sys
d = open('work/files/DATA/UNITINFO.BIN', 'rb').read(); x = open('work/PAW.EXE', 'rb').read()
out = open('work/text/names_jp.tsv', 'w', encoding='utf-8'); out.write('#종류\t파일\t위치\t원문바이트\t칸여유(0 연속)\t원문\n')


def rec(kind, fn, buf, o, mx):
    e = buf.find(b'\0', o, o + mx); e = o + mx if e < 0 else e
    z = e
    while z < o + mx and buf[z] == 0: z += 1
    out.write('%s\t%s\t%X\t%d\t%d\t%s\n' % (kind, fn, o, e - o, z - o, buf[o:e].decode('cp932')))


for k in range(288): rec('인물', '/DATA/UNITINFO.BIN', d, k * 40, 30)
for o in range(0x8F404, 0x90B42, 0x46): rec('병기', '/PAW.EXE', x, o, 0x46)
for o in range(0x90B50, 0x90D56, 14): rec('종류', '/PAW.EXE', x, o, 14)
for o in range(0x90DA0, 0x914A0, 28): rec('무장', '/PAW.EXE', x, o, 28)
out.close()
