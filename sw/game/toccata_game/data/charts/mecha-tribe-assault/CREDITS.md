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

Verse 2A부터 9A까지 11곳에서 건반의 울림을 서스테인 페달로 넘긴다. 목표음을 치고, 그 건반을 떼기 전에 페달을 밟는다. 홀드는 원래 길이까지 누른다. 손을 떼고 다음 음들을 연주한 뒤, 구간 끝에서 페달을 떼어 울림을 끊는다.

첫 비교 구간은 원음 **16.5–20.0초**다. 16.528초의 E♭4–B♭4는 페달 없이 짧게 친다. **16.861초**에는 C4를 여리게, B♭4를 강하게 친 뒤 왼손을 먼저 떼고 오른손 B♭4의 울림을 페달에 넘긴다. 17.195초와 17.528초의 C4–E♭4를 그 위에 연주하고 **17.861초**의 E♭4–G4에 맞춰 페달을 뗀다.

**18.695초**에는 여린 단음 C4를 같은 방식으로 남긴다. 19.195초에 처음과 같은 E♭4–B♭4 화음을 치고 **19.528초**에 페달을 떼면, 같은 화음 아래에 C4가 더해진 차이를 들을 수 있다.

| 프레이즈 | 타건 → 댐핑 (원음 초) | 페달에 넘길 건반 | 그 위에 연주할 음 |
| --- | ---: | --- | --- |
| Verse 2A | 16.861 → 17.861 | B♭4 (f) | C4–E♭4 두 번 |
| Verse 2A | 18.695 → 19.528 | C4 (p) | B♭4, E♭4–B♭4 |
| Verse 3A | 27.861 → 28.528 | C4 (p) | E♭4 두 번 |
| Verse 4A | 40.361 → 41.361 | C4 (p, 한 박 홀드) | G4, E♭4–G4 |
| Verse 4B | 45.028 → 45.695 | G4 (f, 한 박 홀드) | 왼손 C4 |
| Verse 5B | 54.528 → 55.361 | G4 (f, 한 박 홀드) | E♭4, C4 홀드 |
| Verse 6A | 62.528 → 63.195 | C4 (p) | B♭4, G4 두 번 |
| Verse 7A | 71.361 → 72.028 | B♭4 (f, 반 박 홀드) | G4, E♭4 두 번 |
| Verse 8A | 81.361 → 82.028 | E♭4 (p, 한 박 홀드)와 B♭4 (f) | G4 단음 |
| Verse 8B | 85.361 → 86.695 | C4 (p, 세 박 홀드) | G4 세 번 |
| Verse 9A | 94.361 → 95.361 | B♭4 (f) | G4, E♭4, C4, E♭4 |

Piano Hard 차트의 `resonances`에서 `t`는 목표 건반을 치는 시각, `d`는 타건부터 댐핑까지의 길이, `keys`는 그때 친 음 중 페달로 넘길 MIDI 건반 번호다. `t`와 `d`의 단위는 밀리초다. 위 표는 `t`와 `t + d`에 음원 오프셋 28ms를 더한 재생 시각이다.

## 재생성 및 확인

저장소 루트에서 다음 명령을 실행하면 두 원본의 SHA-256을 확인한 뒤 Medium과 Piano Hard JSON을 재생성한다. 두 번째 명령은 재생성 결과가 커밋된 채보와 같으면 종료 코드 0을 반환한다.

```sh
python3 sw/game/tools/import_mecha_tribe.py
git diff --exit-code HEAD -- sw/game/toccata_game/data/charts/mecha-tribe-assault*.chart.json
```

FFmpeg가 있는 환경에서 `--rebuild-audio`를 붙이면 게임용 FLAC도 원본 OGG에서 다시 만든다.
