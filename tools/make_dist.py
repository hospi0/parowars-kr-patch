# -*- coding: utf-8 -*-
r"""파로 워즈 배포 묶음(2026-11-08, 파넬티아 tools/make_dist.py 를 옮김)
  dist/ParoWars_KR_<VER>/ : xdelta + xdelta.exe + readme.txt(CP949) + 한글패치_적용.bat(CP949) + zip
  트랙 1개(MODE2/2352) — cue 그대로.
  검증: 원본 → xdelta 적용 → md5 = 빌드(work/disc) md5.
  python tools/make_dist.py   (먼저 python tools/build.py --write)
"""
import hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

VER = 'v0.9'
XDELTA = r'C:\claude\utils\xdelta.exe'
ROM = 'Paro Wars (Japan)'
SRC = os.path.join(r'C:\claude\roms\ps', ROM, ROM + '.bin')
OUT = os.path.join(ROOT, 'work', 'disc', ROM + '.bin')
NAME = 'ParoWars_KR_' + VER
TITLE = '파로 워즈 (Paro Wars, 플레이스테이션 일본판) 한글 패치 ' + VER


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest().upper()


README = """{title}
{line}

트랙 1개로 이루어진 {rom} 의
{bin} 에 패치하시면 됩니다.

원본md5 : {o}
패치md5 : {d}

입니다.


[ 적용 방법 ]

  1) 원본 파일을 이 폴더에 복사
       "{bin}"
  2) 한글패치_적용.bat 실행 → 이름 끝에 [KR] 이 붙은 파일이 만들어집니다
  3) 만든 파일 이름을 원본 이름으로 바꿔 넣고, cue 는 원본 그대로 쓰세요

  직접 적용:
    xdelta.exe -d -s "원본 bin" "{patch}" "결과 파일"
  (Delta Patcher 같은 xdelta3 GUI 도구로 적용해도 됩니다. 원본이 다르면 xdelta 가 적용을 거부합니다.)


[ 바뀌는 것 ]

  - 이야기·이벤트 대사 전체, 엔딩 이야기
  - 메뉴·전투 화면·부대 목록·생산·옵션·메모리 카드 화면
  - 병기·인물·나라 이름, 병기 도감, 나라 정보, 도움말
  - 그림 글자: 타이틀 메뉴, 나라 이름 띠·턴 시작 나라 이름, 이벤트 큰 제목,
    세계 지도 지명, 상태 표시줄, 저장 화면, 레벨업, 말풍선, 배경 간판·현수막


[ 알려진 점 ]

  - 음성은 원본 일본어 그대로입니다.
  - 일부 고유명사(병기·인물)는 말장난을 살려 의역했습니다.
  - 엔딩 스태프 롤은 원문 그대로입니다.
  - 시험 단계 패치입니다. 잘못된 곳을 알려 주시면 고치겠습니다.
"""

BAT = r"""@echo off
chcp 949 >nul
set "XD=%~dp0xdelta.exe"
if not exist "%~dp0{bin}" (
  echo   [오류] 원본 bin 파일을 이 폴더에 넣어 주세요 - readme 참고.
  pause & exit /b 1
)
"%XD%" -d -f -s "%~dp0{bin}" "%~dp0{patch}" "%~dp0{kbin}"
if errorlevel 1 (
  echo   [오류] 패치 실패 - 원본이 다를 수 있습니다 - readme 의 원본md5 확인.
  pause & exit /b 1
)
echo   완료: "{kbin}"
pause
"""


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    d = os.path.join(ROOT, 'dist', NAME)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    b = ROM + '.bin'
    patch = NAME + '.xdelta'; pp = os.path.join(d, patch)
    subprocess.run([XDELTA, '-e', '-9', '-B', '536870912', '-f', '-s', SRC, OUT, pp], check=True)
    chk = os.path.join(d, '_check.bin')
    subprocess.run([XDELTA, '-d', '-f', '-s', SRC, pp, chk], check=True)
    o, want, got = md5(SRC), md5(OUT), md5(chk)
    os.remove(chk)
    assert got == want, ('패치 적용 결과가 빌드와 다름', got, want)
    print('원본md5 %s → 패치md5 %s · %s %d B' % (o, want, patch, os.path.getsize(pp)))
    shutil.copy2(XDELTA, os.path.join(d, 'xdelta.exe'))
    kbin = ROM + ' [KR].bin'
    readme = README.format(title=TITLE, line='=' * 60, rom=ROM, o=o, d=want, bin=b, patch=patch)
    open(os.path.join(d, 'readme.txt'), 'wb').write(readme.replace('\n', '\r\n').encode('cp949'))
    open(os.path.join(d, '한글패치_적용.bat'), 'wb').write(BAT.format(bin=b, patch=patch, kbin=kbin).replace('\n', '\r\n').encode('cp949'))
    z = os.path.join(ROOT, 'dist', NAME + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(os.listdir(d)):
            zf.write(os.path.join(d, f), NAME + '/' + f)
    print('✅', d)
    for f in sorted(os.listdir(d)):
        print('  %-56s %12d' % (f, os.path.getsize(os.path.join(d, f))))
    print('  zip %s %d B · md5 %s' % (os.path.basename(z), os.path.getsize(z), md5(z)))


if __name__ == '__main__':
    main()
