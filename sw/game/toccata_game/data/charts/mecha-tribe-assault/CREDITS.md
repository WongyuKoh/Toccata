# Mecha-Tribe Assault

Kommisar가 작곡하고 Wyde가 StepMania 5의 `dance-single` Medium 8 채보를 제작했다. TOCCATA에는 이 채보의 탭 345개와 홀드 50개를 수록했다. 두 건반을 함께 누르는 시점은 45곳이며 지뢰는 0개다.

## 원본 파일

두 파일은 StepMania 공식 저장소의 커밋 `7cbaff8ce2dcbede32dd3d6f3f2d8fafeafd674e`에서 가져왔다. 음원은 파일명만 `original.ogg`로 바꾸었고, SSC는 다른 난이도를 포함한 원본 전체를 보존했다. [공식 수록 폴더](https://github.com/stepmania/stepmania/tree/7cbaff8ce2dcbede32dd3d6f3f2d8fafeafd674e/Songs/StepMania%205/MechaTribe%20Assault)

| 수록 파일 | 원본 SHA-256 | 다운로드 |
| --- | --- | --- |
| `original.ogg` | `6eb052cf8081ebb01d4b30e8db34e9eeca692635e2c1ed3ba7f7bd131c1b65c3` | [Mecha-Tribe Assault.ogg](https://raw.githubusercontent.com/stepmania/stepmania/7cbaff8ce2dcbede32dd3d6f3f2d8fafeafd674e/Songs/StepMania%205/MechaTribe%20Assault/Mecha-Tribe%20Assault.ogg) |
| `Mecha-Tribe Assault.ssc` | `a594bd13b0728ecb2e9eb8e56ddb0e1744c0d2eef80466a42ea299703615e426` | [Mecha-Tribe Assault.ssc](https://raw.githubusercontent.com/stepmania/stepmania/7cbaff8ce2dcbede32dd3d6f3f2d8fafeafd674e/Songs/StepMania%205/MechaTribe%20Assault/Mecha-Tribe%20Assault.ssc) |

## 이용 조건

> Any songs that are included within this repository are under the [CC-NC license](https://creativecommons.org/).

StepMania는 수록곡에 **CC-NC**(Creative Commons Non-Commercial)를 표기하며, 수록곡을 포함한 게임의 판매를 금지한다. 해당 커밋의 README에는 세부 라이선스 유형과 버전이 명시되어 있지 않다. [공식 README의 Licensing Terms](https://github.com/stepmania/stepmania/blob/7cbaff8ce2dcbede32dd3d6f3f2d8fafeafd674e/README.md#L30-L44)

## TOCCATA 변환

- 왼쪽·아래·위·오른쪽 레인을 차례로 도·레·미·파(MIDI 60·62·64·65)에 연결했다. 홀드 시작과 끝, 동시 누름, SSC의 구간 이름을 보존했다.
- 180 BPM에서 각 채보 행의 박 위치를 밀리초로 반올림했다. SSC의 `OFFSET=-0.028000`은 첫 박이 음원 시작 후 28ms에 온다는 뜻이다. TOCCATA는 노트를 읽을 때 `offset_ms`를 더하므로 이 값을 `28`로 기록했다.
- 원본 OGG 헤더에는 105초로 기록되어 있다. 끝까지 디코딩한 재생 시간은 108.012초다. 마지막 홀드는 105.361초에 끝나고, 게임은 남은 약 2.65초의 소리를 재생한 뒤 결과를 보여 준다.
- 게임의 22,050Hz 모노 SDL 믹서에서는 같은 원음을 변환한 16비트 `mixer.flac`을 사용한다. 영상은 원본 OGG의 스테레오를 사용한다.
- 재생 설정은 자유 연주(`free`), 걸음 5, `sonata`, 레벨 8, 낙하 시간 1,500ms다.

저장소 루트에서 다음 명령을 실행하면 두 원본의 SHA-256을 확인한 뒤 같은 JSON을 다시 생성한다.

```sh
python3 sw/game/tools/import_mecha_tribe.py
```

FFmpeg가 있는 환경에서 `--rebuild-audio`를 붙이면 게임용 FLAC도 원본 OGG에서 다시 만든다.
