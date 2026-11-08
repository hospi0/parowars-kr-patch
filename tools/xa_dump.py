# -*- coding: utf-8 -*-
"""음성 조사 — SOUND/XA/*.STR 의 클립(서브헤더 (파일 번호, 채널) 하나 = 클립 하나, 모노 37.8 kHz 4비트)을 wav 로.
   클립 섹터만 모아 raw 2352 .str(채널 0)로 → C:/claude/utils/ps1/ffmpeg.exe(psxstr) 해독.
   python tools/xa_dump.py → work/voice/<파일>/<파일>_f<번호>_c<채널>.wav + work/voice/clips.tsv"""
import sys, os, collections, subprocess, tempfile, shutil, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discfs
sys.stdout.reconfigure(encoding='utf-8')
SRC = r'C:\claude\roms\ps\Paro Wars (Japan)\Paro Wars (Japan).bin'
FF = r'C:/claude/utils/ps1/ffmpeg.exe'
OUT = 'work/voice'
f, vol, rl, rs, ents = discfs.read_fs(SRC)
xs = sorted([e for e in ents if e[0].startswith('/SOUND/XA/') and 'MUSIC' not in e[0]], key=lambda e: e[1])
fh = open(SRC, 'rb'); tmp = tempfile.mkdtemp(); rows = []
try:
    for nm, lba, size in xs:
        base = os.path.basename(nm)[:-4]; os.makedirs(OUT + '/' + base, exist_ok=True)
        clips = collections.OrderedDict()
        for i in range((size + 2047) // 2048):
            fh.seek((lba + i) * 2352); s = bytearray(fh.read(2352))
            if not s[18] & 4: continue
            k = (s[16], s[17]); s[17] = 0; s[21] = 0
            clips.setdefault(k, []).append((i, bytes(s)))
        for (fn, c), secs in clips.items():
            p = os.path.join(tmp, 'c.str'); open(p, 'wb').write(b''.join(b for _, b in secs))
            w = '%s/%s/%s_f%d_c%02d.wav' % (OUT, base, base, fn, c)
            subprocess.run([FF, '-v', 'error', '-y', '-f', 'psxstr', '-i', p, '-ac', '1', w], check=True)
            with wave.open(w) as wv: dur = wv.getnframes() / wv.getframerate()
            rows.append((base, fn, c, secs[0][0], len(secs), round(dur, 2), w))
        print(base, len(clips))
finally:
    shutil.rmtree(tmp)
with open(OUT + '/clips.tsv', 'w', encoding='utf-8') as o:
    o.write('파일\t파일번호\t채널\t첫섹터\t섹터수\t초\twav\n')
    for r in rows: o.write('\t'.join(map(str, r)) + '\n')
print(len(rows))
