# Mecha-Tribe Assault

Kommisar가 작곡하고 Wyde가 StepMania 5의 `dance-single` 채보를 제작했다. TOCCATA는 Medium 8과 Hard 10의 탭 시각, 홀드 시작·끝, 동시 누름을 옮기고, Hard 10에 양손 피아노 편곡을 더했다.

| TOCCATA 채보 | 원본 난이도 | 탭 | 홀드 | 두 음이 동시에 시작하는 곳 | 원본 지뢰 |
| --- | --- | ---: | ---: | ---: | ---: |
| `mecha-tribe-assault` | Medium 8 | 345 | 50 | 45 | 0 |
| `mecha-tribe-assault-piano-hard` | Hard 10 | 446 | 73 | 48 | 25개 모두 피아노 편곡에서 생략 |

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

- Medium은 왼쪽·아래·위·오른쪽 레인을 차례로 도·레·미·파(MIDI 60·62·64·65)에 연결했다. 두 채보 모두 SSC의 구간 이름을 보존했다.
- 180 BPM에서 각 채보 행의 박 위치를 밀리초로 반올림했다. SSC의 `OFFSET=-0.028000`은 첫 박이 음원 시작 후 28ms에 온다는 뜻이다. TOCCATA는 노트를 읽을 때 `offset_ms`를 더하므로 이 값을 `28`로 기록했다.
- 원본 OGG 헤더에는 105초로 기록되어 있다. 끝까지 디코딩한 재생 시간은 108.012초다. 마지막 홀드는 105.361초에 끝나고, 게임은 남은 약 2.65초의 소리를 재생한 뒤 결과를 보여 준다.
- 두 채보는 스테레오 원음 `original.ogg`와 게임의 22,050Hz 모노 SDL 믹서용 16비트 `mixer.flac`을 공유한다.
- 재생 설정은 자유 연주(`free`), `sonata`, 낙하 시간 1,500ms다. Medium은 걸음 5·레벨 8, Piano Hard는 걸음 6·레벨 10이다.

### Piano Hard 연주

| 원본 레인 | 건반 | MIDI | 손과 손가락 |
| --- | --- | ---: | --- |
| 왼쪽 | C4 (도) | 60 | 왼손 약지 |
| 아래 | E♭4 (미♭) | 63 | 왼손 검지 |
| 위 | G4 (솔) | 67 | 오른손 엄지 |
| 오른쪽 | B♭4 (시♭) | 70 | 오른손 중지 |

원음의 주파수 스펙트럼에서 도입부에 반복되는 A♭ 저음과 E♭, 그 위의 C·B♭를 확인했다. Verse 2A에서는 같은 뒷박에 E♭4–B♭4 완전5도를 두 번 울린다. C와 G가 두드러지는 Verse 4에서는 C4를 누른 채 G4를 친 뒤, 되풀이할 때는 G4를 길게 남긴다. Verse 5의 단음은 오른손 G4의 강세에 왼손 C4가 여리게 답한다.

519음 중 85음에 피아노 소리를 덧입힌다. 왼손의 여린 터치(`touch: "p"`)는 41음, 오른손의 강한 터치(`touch: "f"`)는 44음이다. 이 중 12곳에서 두 터치를 동시에 치며, 모두 PC 분할점인 MIDI 65를 사이에 둔다. 나머지 434음은 일반 노트로 원곡만 들린다.

서스테인 페달 11구간은 TOCCATA의 Piano Hard 편곡에 추가했다. Verse 4에서는 왼손 C4 홀드와 오른손 G4 홀드를 각각 뗀 뒤까지 페달을 유지한다. Verse 9B에서는 마지막 C4의 여운을 남긴 뒤 Fin 전에 페달을 뗀다. 차트의 `pedals` 배열에서 `t`는 건반과 같은 오프셋 적용 전 밀리초, `d`는 밟고 있는 시간(밀리초)이다.

첫 페달 녹화에는 원음 기준 **15.8–20.4초**를 권한다. **16.361초**에 밟고 16.528초에 왼손 E♭4를 여리게, 오른손 B♭4를 강하게 짧게 친다. 16.861초의 C4–B♭4도 짧게 친 뒤 **18.028초**에 페달을 떼면 손을 뗀 뒤의 울림과 발을 뗄 때의 차이가 드러난다. 1초 뒤인 **19.028초**에 다시 밟아 두 번째 E♭4–B♭4를 받는다.

반복되는 양손 화음을 함께 담으려면 원음 기준 **16.0–34.5초**를 권한다. 16.528초와 19.195초에 E♭4–B♭4 화음이, 32.528초와 33.861초에 C4–B♭4 화음이 반복된다. 두 손이 홀드를 주고받는 장면은 **40.0–55.5초**에 담을 수 있다.

## 재생성 및 확인

저장소 루트에서 다음 명령을 실행하면 두 원본의 SHA-256을 확인한 뒤 Medium과 Piano Hard JSON을 재생성한다. 두 번째 명령은 재생성 결과가 커밋된 채보와 같으면 종료 코드 0을 반환한다.

```sh
python3 sw/game/tools/import_mecha_tribe.py
git diff --exit-code HEAD -- sw/game/toccata_game/data/charts/mecha-tribe-assault*.chart.json
```

FFmpeg가 있는 환경에서 `--rebuild-audio`를 붙이면 게임용 FLAC도 원본 OGG에서 다시 만든다.
