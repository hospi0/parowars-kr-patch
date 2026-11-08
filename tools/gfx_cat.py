# -*- coding: utf-8 -*-
"""그림 출처 카탈로그(읽기 전용) — 색인판(2026-11-07, 예전 판은 조각마다 수백 MB 검색이라 1시간+).
   1) 모든 스테이트 VRAM 텍스처 영역(화면 버퍼 x<640·y<256 제외)을 16×1 조각(32 B, x 16 정렬)으로 나눠
      앞 8 B(u64) → [(상태, x, y)] 색인. 무늬 없는 조각(고유 바이트 < 6)은 뺀다.
   2) 평문 파일·풀린 LZ 덩어리를 2 B 간격 u64 창으로 numpy np.isin 한 번에 훑어 후보만 32 B 전부 확인.
   3) 같은 출처에서 아랫줄(y+1) 조각 위치로 stride 를 구해, (출처, stride, 기준=위치−y·stride−x·2) 끼리 묶어 그림 사각형을 정한다.
   출력 work/gfxcat/cat.tsv (번호·출처·출처 위치·폭(16비트 px)·높이·VRAM x,y·stride·상태들) + 번호.png(VRAM 4bpp 회색)
   python tools/gfx_cat.py [상태들...]"""
import sys, os, glob, collections
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
os.makedirs('work/gfxcat', exist_ok=True)
for p in glob.glob('work/gfxcat/*'): os.remove(p)
states = sys.argv[1:] or sorted((os.path.basename(p) for p in glob.glob('work/st/*') if os.path.exists(p + '/vram.bin')),
                                key=lambda s: (not s.isdigit(), int(s) if s.isdigit() else 0))
V = {st: open('work/st/%s/vram.bin' % st, 'rb').read() for st in states}
rowmap = collections.defaultdict(list)          # 서로 다른 32 B 줄 → [(상태, x, y)]  (여러 스테이트의 같은 조각은 한 번만 찾음)
for st, v in V.items():
    for y in range(512):
        for x in range(0, 1024, 16):
            if x < 640 and y < 256: continue
            o = (y * 1024 + x) * 2; row = v[o:o + 32]
            if len(set(row)) < 6: continue
            rowmap[row].append((st, x, y))
keys = np.array(sorted(set(int.from_bytes(r[:8], 'little') for r in rowmap)), dtype=np.uint64)
print('상태', len(states), '서로 다른 조각', len(rowmap), flush=True)
srcs = []
for p in sorted(glob.glob('work/files/**/*', recursive=True)):
    if os.path.isfile(p) and not p.endswith('.STR'): srcs.append((p[len('work/files'):].replace(chr(92), '/'), p))
for p in sorted(glob.glob('work/unpk/*.bin')):
    srcs.append(('@' + os.path.basename(p)[:-4], p))
found = {}                                        # 32 B 줄 → (출처, 위치)  첫 출처만
for n, (nm, p) in enumerate(srcs):
    d = open(p, 'rb').read()
    if len(d) < 64: continue
    for par in (0, 1):
        e = len(d) - par; e -= e % 2
        a = np.frombuffer(d[par:par + e], '<u2').astype(np.uint64)
        if len(a) < 4: continue
        w = a[:-3] | a[1:-2] << np.uint64(16) | a[2:-1] << np.uint64(32) | a[3:] << np.uint64(48)
        pos = np.searchsorted(keys, w); pos[pos >= len(keys)] = 0
        for i in np.nonzero(keys[pos] == w)[0]:
            off = par + 2 * int(i); r = d[off:off + 32]
            if r in rowmap and r not in found: found[r] = (nm, off)
    if n % 1000 == 0: print(n, '/', len(srcs), '찾은 줄', len(found), flush=True)
hits = collections.defaultdict(dict)
for r, (nm, off) in found.items():
    for st, x, y in rowmap[r]: hits[st][(x, y)] = (nm, off)
groups = collections.defaultdict(lambda: [set(), set()])
for st, H in hits.items():
    for (x, y), (nm, off) in H.items():
        below = H.get((x, y + 1))
        if not below or below[0] != nm: continue
        stride = below[1] - off
        if not 0 < stride <= 4096: continue
        base = off - y * stride - x * 2
        groups[(nm, stride, base)][0].add((x, y)); groups[(nm, stride, base)][1].add(st)
rows = []
for (nm, stride, base), (tiles, sts) in groups.items():
    if len(tiles) < 8: continue
    xs = [t[0] for t in tiles]; ys = [t[1] for t in tiles]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs) + 16, max(ys) + 1
    rows.append((nm, base + y0 * stride + x0 * 2, x1 - x0, y1 - y0, x0, y0, stride, sts))
rows.sort(key=lambda r: (r[0], r[1]))
out = open('work/gfxcat/cat.tsv', 'w', encoding='utf-8')
for i, (nm, off, w, h, x0, y0, stride, sts) in enumerate(rows):
    s = sorted(sts, key=lambda s: int(s) if s.isdigit() else 999)
    v = np.frombuffer(V[s[0]], np.uint8).reshape(512, 2048)
    a = v[y0:y0 + h, x0 * 2:(x0 + w) * 2]
    g = (np.stack([a & 15, a >> 4], 2).reshape(h, w * 4) * 17).astype(np.uint8)
    Image.fromarray(g).save('work/gfxcat/%03d.png' % i)
    out.write('%03d\t%s\t%X\t%d\t%d\t%d,%d\tstride%d\t%s\n' % (i, nm, off, w, h, x0, y0, stride, ','.join(s)))
out.close(); print('그림', len(rows))
