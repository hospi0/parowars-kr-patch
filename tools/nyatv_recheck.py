# -*- coding: utf-8 -*-
"""냥티비 받아쓰기 재검사(2026-11-08) — work/voice/nyatv_map.tsv 125줄을
   ① 위스퍼 large-v3 + 용어 프롬프트 ② kotoba-whisper v2.0 으로 다시 받아쓰고, 처음 받아쓰기와 셋을 비교(글자 유사도) → work/voice/nyatv_recheck.tsv
   C:/claude/utils/whisper-venv/Scripts/python.exe tools/nyatv_recheck.py"""
import sys, subprocess, difflib, numpy as np
from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
PROMPT = ('にゃんテレビ、にゃんじろう、ニャン次郎、パロワールド、ペン太郎、ミカエル帝国、アカシヤランド、ラブリー連邦合衆国、'
          'こいつ＆あいつ連邦共和国、モアイ諸島首長国、パンダ茶会主義獣民共和国、バウバウ国、ニャー帝国、コナミ、制空権、都市攻略、空港、工場、戦車、ドエース、バイにゃん。')
rows = [l.rstrip('\n').split('\t') for l in open('work/voice/nyatv_map.tsv', encoding='utf-8')]
H, rows = rows[0], rows[1:]


def load(p):
    return np.frombuffer(subprocess.run(['C:/claude/utils/ps1/ffmpeg.exe', '-v', 'error', '-i', p, '-ar', '16000', '-ac', '1', '-f', 's16le', '-'],
                                        capture_output=True, check=True).stdout, '<i2').astype(np.float32) / 32768


A = {r[0]: load(r[6]) for r in rows}
res = {}
for name, kw in (('large', dict(initial_prompt=PROMPT)), ('kotoba', {})):
    m = WhisperModel('large-v3' if name == 'large' else 'kotoba-tech/kotoba-whisper-v2.0-faster', device='cuda', compute_type='float16')
    for r in rows:
        segs, _ = m.transcribe(A[r[0]], language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False, **kw)
        res[(name, r[0])] = ''.join(s.text for s in segs).strip()
    del m
    print(name, '끝')


def sim(a, b):
    n = lambda s: ''.join(ch for ch in s if ch not in '、。!！?？ ー～…・')
    return difflib.SequenceMatcher(None, n(a), n(b)).ratio()


out = ['번호\t초\t일치도\t처음\t재검(프롬프트)\tkotoba\twav']
low = 0
for r in rows:
    a, b, c = r[7], res[('large', r[0])], res[('kotoba', r[0])]
    s = min(sim(a, b), sim(b, c), sim(a, c))
    low += s < 0.8
    out.append('\t'.join([r[0], r[5], '%.2f' % s, a, b, c, r[6]]))
open('work/voice/nyatv_recheck.tsv', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('일치도 0.8 미만', low, '/', len(rows))
