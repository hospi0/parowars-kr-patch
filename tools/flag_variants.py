# -*- coding: utf-8 -*-
"""턴 시작 큰 나라 이름 글꼴 비교판(2026-11-08 하스피 «예쁘게») — band_kr 글꼴만 바꿔 flag_kr 와 같은 과정으로 그림
   → work/미리보기_그림_D/미리보기_턴시작_글꼴비교.png (화면에 보이는 폭만, 원본|A~E)"""
import sys, os, shutil, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import band_kr, flag_kr
sys.stdout.reconfigure(encoding='utf-8')
FD = 'C:/claude/utils/font/'
VAR = [('A', '지금(나눔고딕 ExtraBold)', FD + 'nanum-gothic/NanumGothicExtraBold.ttf'),
       ('B', '주아(메뉴 글꼴)', FD + 'jua/Jua-Regular.ttf'),
       ('C', '검은고딕', FD + 'blackhansans/BlackHanSans-Regular.ttf'),
       ('D', '도현', FD + 'dohyeon/DoHyeon-Regular.ttf'),
       ('E', '나눔고딕 Bold', FD + 'nanum-gothic/NanumGothicBold.ttf')]
v = open('work/st/12/vram.bin', 'rb').read()
CL = np.frombuffer(v, '<u2').reshape(512, 1024)[246, 128:144].astype(int)
strips = band_kr.load(v)
tmp = tempfile.mkdtemp()
cols = []
try:
    shutil.copy(flag_kr.OUT + '/strips_orig.npy', tmp)
    orig = None
    for k, nm, font in VAR:
        band_kr.FONT = font
        new, _ = band_kr.build(strips)
        np.save(tmp + '/strips_new.npy', np.array(new))
        flag_kr.OUT = tmp
        _, pv = flag_kr.edits()
        if orig is None: orig = [a for a, b in pv]
        cols.append((k + ' ' + nm, [b for a, b in pv]))
finally:
    shutil.rmtree(tmp)


def show(x, i):
    W = 128 + flag_kr.W2[i]; c = np.hstack([x[0:24], x[24:48]])[:, :W]
    im = np.zeros((24, 256, 3), np.uint8); im[:] = (30, 30, 30); im[:, (256 - W) // 2:(256 - W) // 2 + W] = band_kr.colorize(c, CL); return im


allc = [('원본', orig)] + cols
blocks = []
for title, pics in allc:
    col = np.vstack([np.pad(show(p, i), ((0, 3), (0, 0), (0, 0))) for i, p in enumerate(pics)])
    hd = Image.new('RGB', (256, 16), (0, 0, 0)); ImageDraw.Draw(hd).text((4, 1), title, font=ImageFont.truetype(FD + 'nanum-gothic/NanumGothicBold.ttf', 12), fill=(255, 255, 255))
    blocks.append(np.vstack([np.array(hd), col]))
g = np.hstack([np.pad(b, ((0, 0), (0, 6), (0, 0))) for b in blocks[:3]])
g2 = np.hstack([np.pad(b, ((0, 0), (0, 6), (0, 0))) for b in blocks[3:]] + [np.zeros_like(np.pad(blocks[0], ((0, 0), (0, 6), (0, 0))))] * 0)
g2 = np.pad(g2, ((0, 0), (0, g.shape[1] - g2.shape[1]), (0, 0)))
s = np.vstack([g, np.zeros((8, g.shape[1], 3), np.uint8), g2])
Image.fromarray(s).resize((s.shape[1] * 2, s.shape[0] * 2), Image.NEAREST).save('work/미리보기_그림_D/미리보기_턴시작_글꼴비교.png')
print('ok')
