# -*- coding: utf-8 -*-
"""음성 조사 — work/voice/clips.tsv 의 클립 전부 받아쓰기(위스퍼 large-v3, VAD 끔) → work/voice/clips_asr.tsv
   C:/claude/utils/whisper-venv/Scripts/python.exe tools/xa_asr.py"""
import sys, subprocess, numpy as np

from faster_whisper import WhisperModel
sys.stdout.reconfigure(encoding='utf-8')
m = WhisperModel('large-v3', device='cuda', compute_type='float16')
rows = [l.rstrip('\n').split('\t') for l in open('work/voice/clips.tsv', encoding='utf-8')]
out = open('work/voice/clips_asr.tsv', 'w', encoding='utf-8'); out.write('\t'.join(rows[0] + ['받아쓰기']) + '\n')
for i, r in enumerate(rows[1:]):
    a = np.frombuffer(subprocess.run(['C:/claude/utils/ps1/ffmpeg.exe', '-v', 'error', '-i', r[6], '-ar', '16000', '-ac', '1', '-f', 's16le', '-'], capture_output=True, check=True).stdout, '<i2').astype(np.float32) / 32768
    if len(a) < 16000: a = np.pad(a, (0, 16000 - len(a)))
    segs, _ = m.transcribe(a, language='ja', beam_size=5, condition_on_previous_text=False, vad_filter=False)
    t = ''.join(s.text for s in segs).strip()
    out.write('\t'.join(r + [t]) + '\n'); out.flush()
    if i % 100 == 0: print(i, r[0], t)
print('끝')
