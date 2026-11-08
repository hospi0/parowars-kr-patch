# -*- coding: utf-8 -*-
"""디스크 전 파일(STR 제외)에서 화면에 보인 일본어 문구를 Shift-JIS 로 검색(읽기 전용).
   python tools/sjis_scan.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')
import discfs as D
BIN = r'C:\claude\roms\ps\Paro Wars (Japan)\Paro Wars (Japan).bin'
f, vol, rl, rs, ents = D.read_fs(BIN)
WORDS = ['移動の時', '燃料', 'ロードするスロット', '選んで', 'ステータスを変更', '画面回転', '決定', '戻る', 'ヘルプ',
         'ゾーン', '視界', 'むずかしい', 'ラブリー', 'パンダ国', '都市の数', 'ゲーム開始', '次頁', 'マップ']
def read(e):
    return D.sector(f, e[1], (e[2] + 2047) // 2048)[:e[2]]
hits = {}
for e in ents:
    if e[0].endswith(('.STR', '.VB', '.VH', '.SEQ')): continue
    d = read(e)
    for w in WORDS:
        b = w.encode('cp932'); q = d.find(b)
        if q >= 0: hits.setdefault(w, []).append((e[0], hex(q), d.count(b)))
for w in WORDS:
    h = hits.get(w, [])
    print(w, len(h), h[:6])
