# -*- coding: utf-8 -*-
"""빌드 전 검사: story.py 배치를 풀린 덩어리·파일에 실제로 적용한 뒤, 도감(P_)·엔딩·국가 정보 글 영역에 일본어(가나·한자)가 남은 줄을 전수 보고.
   (추출 누락 — 문단 앞·뒤 줄, 머리 변형 — 을 화면 보기 전에 잡는다.)  python tools/leftover_check.py"""
import sys, os, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import story as S
JP = re.compile('[ぁ-んァ-ヶ一-龥]')
W, bad, sk = S.plan(lambda t: t.encode('utf-16-le'))
out = collections.defaultdict(list)
for fn, ws in W.items():
    if not fn.startswith('@DATA_P_'): continue
    d = bytearray(S.data(fn)); done = set()
    for o, b in ws: done.update(range(o, o + len(b)))
    # 도감 글 영역: 원문 «強さ５段階評価» 제목부터 0x260 B(능력치 줄 + 설명·조언 8줄)
    base = S.data(fn).find('強さ５段階評価'.encode('cp932'))
    if base < 0: continue
    for so in range(base, min(len(d), base + 0x260)):
        if so in done: continue
        if not (0x81 <= d[so] <= 0x9F or 0xE0 <= d[so] <= 0xEF): continue
        e = so
        while e + 1 < len(d) and (0x81 <= d[e] <= 0x9F or 0xE0 <= d[e] <= 0xEF) and e not in done: e += 2
        try: t = bytes(d[so:e]).decode('cp932')
        except UnicodeDecodeError: continue
        if len(t) >= 2 and JP.search(t) and not re.fullmatch('[　]*◆?強さ５段階評価◆?', t):
            out[t].append((fn, hex(so)))
        for k in range(so, e): done.add(k)
for t, locs in out.items(): print(len(locs), t, locs[:2])
print('남은 일본어 줄', len(out))
