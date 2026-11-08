# -*- coding: utf-8 -*-
"""평문 SJIS 문장 추출 → work/text/jp.tsv (번호·파일·위치·바이트 수·원문).
   문자열 = 앞이 0x00(또는 파일 처음)이고 다음 0x00 까지 cp932 로 온전히 풀리는 덩어리.
   잡음 거름: 전각 가나·한자 2자 이상, 가나·부호 비율, JIS 2수준·키릴·괘선 없음, 개발 PC 파일러 찌꺼기 낱말 제외.
   제외 파일: 압축(P_##·ENDING/*_TXT 등은 따로), DEMO 의 그림 묶음(COL_·SEQ_·KABE·BACK·<인물>#_#·PEN#_#).
   python tools/extract.py"""
import os, re, sys, glob, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'work/files'
SKIP_FILE = re.compile(r'/DATA/(P_\d+|P_[A-Z]+|BK_DT/.*|BTL/.*|ENDING/(?!TXT_END)[^/]*|DEMO/(COL_|SEQ_|KABE|BACK|[A-Z]{3}\d_\d|[A-Z]{3}\d_\d\d|PEN\d_)[^/]*|MAP\w*|OJ_\d+|PUP_\d+|OPF\d*|OP_\d+|MATI|MAPUNIT\d?|NYANTV/.*)\.BIN$')
JUNK = re.compile('ファイル|ディレクトリ|ドライブ|コマンド|ディスク|セクタ|クラスタ|バイト|エディター|スクロール|タイムスタンプ|キーを押して|Yes/No|メモリ$|ツリー|圧縮|解凍|テンポラリ|入力できません|出力できません|見つかりません|ジャンプ行|マークし|プログラムの実行|書き込み禁止|無効な')


def lvl2(c):
    try: b = c.encode('cp932')
    except Exception: return True
    if len(b) < 2: return False
    v = b[0] << 8 | b[1]
    return v >= 0x989F or 0x8440 <= v < 0x889F


def is_lead(b): return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def strings(d):
    """시작 = 파일 처음 · 앞 바이트 0 · 또는 앞이 문자열이 아닌 자리에서 전각 첫 바이트(레코드 안 이름: 앞 칸이 수치)."""
    i = 0; n = len(d)
    while i < n:
        if i and d[i - 1] != 0:
            prev_txt = i >= 2 and is_lead(d[i - 2]) and 0x40 <= d[i - 1] <= 0xFC          # 앞이 전각 글자면 문자열 중간
            if prev_txt or not (is_lead(d[i]) and i + 1 < n and 0x40 <= d[i + 1] <= 0xFC): i += 1; continue
        j = d.find(b'\0', i)
        if j < 0: j = n
        if j - i >= 4:
            raw = d[i:j]
            try: s = raw.decode('cp932')
            except UnicodeDecodeError: s = None
            if s is not None: yield i, raw, s
        i += 1


def good(s):
    t = s.replace('　', '')
    fw = re.findall('[ぁ-んァ-ヶ一-龥]', t)
    if len(fw) < 2: return False
    if any(lvl2(c) for c in t if ord(c) > 0x7F): return False
    if any(ord(c) < 0x20 for c in t): return False
    if len(re.findall('[ぁ-んァ-ヶー。、！？「」・…～]', t)) / len(t) < 0.3: return False
    return not JUNK.search(t)


def junk_corpus():
    """개발 PC 파일러 찌꺼기 모음: DEMO 그림 묶음 파일들의 섹터 여분 = 같은 찌꺼기. 여기 바이트가 들어 있는 문자열은 버린다."""
    c = []
    for p in glob.glob(ROOT + '/DATA/DEMO/*.BIN'):
        fn = p[len(ROOT):].replace(chr(92), '/')
        if SKIP_FILE.search(fn): c.append(open(p, 'rb').read())
    return c


if __name__ == '__main__':
    os.makedirs('work/text', exist_ok=True)
    JC = junk_corpus()
    out = open('work/text/jp.tsv', 'w', encoding='utf-8'); out.write('#번호\t파일\t위치\t바이트\t원문\n')
    n = 0; per = collections.Counter(); chars = 0
    for p in sorted(glob.glob(ROOT + '/**/*', recursive=True)):
        if os.path.isdir(p): continue
        fn = p[len(ROOT):].replace('\\', '/')
        if SKIP_FILE.search(fn): continue
        d = open(p, 'rb').read()
        end = -1
        for o, raw, s in strings(d):
            if o < end or not good(s): continue                 # 이미 받은 문자열 안쪽 시작은 버림
            if any(raw in c for c in JC) or (fn == '/DATA/S_AKANE.BIN' and o >= 0x9000): continue      # 파일러 찌꺼기
            if re.search(r'/TXT_[A-Z]+\d*\.BIN$', fn) and o % 150: continue                          # 이야기 = 150 B 고정 칸
            if fn == '/DATA/UNITINFO.BIN' and o % 40: continue                                        # 인물 = 40 B 레코드 맨 앞 이름
            end = o + len(raw)
            n += 1; per[fn] += 1; chars += len(s)
            out.write('%05d\t%s\t%X\t%d\t%s\n' % (n, fn, o, len(raw), s))
    out.close()
    print('줄', n, '글자', chars, '파일', len(per))
    for f, c in per.most_common(80): print('%5d %s' % (c, f))
