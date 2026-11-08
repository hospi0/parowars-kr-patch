# -*- coding: utf-8 -*-
"""전 파일에서 LZ 덩어리 찾기 → work/unpk/<파일>@<위치>.bin + work/lz_index.tsv(파일·위치·압축 길이·풀린 길이).
   후보 위치 = 0, 파일 앞 0x200 안의 u32 값(파일 안쪽 짝수 위치). 받는 조건: 머리 u24 길이가 파일 안이고,
   덩어리 끝(위치+4+길이)이 파일 끝·0 채움·다른 후보 위치와 맞고, 풀린 길이 ≥ 압축 길이.
   python tools/lz_scan.py"""
import sys, os, glob, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import lzk
os.makedirs('work/unpk', exist_ok=True)
idx = open('work/lz_index.tsv', 'w', encoding='utf-8')
tot = 0; nf = 0
for p in sorted(glob.glob('work/files/**/*', recursive=True)):
    if not os.path.isfile(p): continue
    fn = p[len('work/files'):].replace('\\', '/')
    d = open(p, 'rb').read(); L = len(d)
    cand = {0}
    for k in range(0, min(0x200, L - 3), 4):
        v = struct.unpack_from('<I', d, k)[0]
        if 4 <= v < L - 8 and v % 2 == 0: cand.add(v)
    got = []
    for off in sorted(cand):
        n = d[off] | d[off + 1] << 8 | d[off + 2] << 16
        e = off + 4 + n
        if not (8 <= n and e <= L): continue
        tail_ok = e == L or not any(d[e:min(L, e + 16)]) or e in cand or (e + 3) & ~3 in cand
        try: o, used = lzk.unpack(d, off)
        except IndexError: continue
        if len(o) < n: continue
        if not tail_ok and not (off == 0 and len(o) >= n * 1.2): continue      # 파일 맨 앞 덩어리는 뒤가 찌꺼기여도(데모 섹터 여분)
        got.append((off, n, len(o)))
        name = fn.strip('/').replace('/', '_') + '@%X.bin' % off
        open('work/unpk/' + name, 'wb').write(o)
        idx.write('%s\t%X\t%d\t%d\n' % (fn, off, n, len(o)))
    if got: nf += 1; tot += len(got)
idx.close(); print('압축 덩어리', tot, '파일', nf)
