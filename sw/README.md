# Toccata USB MIDI 개발 환경

이 폴더는 RP2040 USB MIDI 건반을 라즈베리파이에 연결해 입력을 확인하고 FluidSynth 피아노 음원을 실행하는 시작점입니다. 옥타브 기판 펌웨어는 [firmware/README.md](../firmware/README.md)에 있고, 터치 메뉴와 리듬게임은 이후 구현합니다.

MIDI 건반과 USB 오디오 동글은 **라즈베리파이 USB에 연결**합니다. SSH는 명령과 개발용이며, 맥에 꽂은 MIDI 장치나 라즈베리파이 소리를 자동으로 전달하지 않습니다.

## 처음 설치

현재 사용하는 브랜치는 `design/v3-fastener-changes`입니다.

```bash
git clone --branch design/v3-fastener-changes --single-branch https://github.com/WongyuKoh/Toccata.git
cd Toccata
sudo apt-get install --no-install-recommends fluidsynth alsa-utils timgm6mb-soundfont libasound2-dev python3-venv
./sw/setup-midi.sh
```

설치기는 프로젝트의 `.venv`에 고정 버전의 Mido/RtMidi를 설치하고 `config/midi.json`을 만듭니다. 기존 설정 파일은 보존합니다. 음원은 Debian의 TimGM6mb SF2를 사용하며, 원하는 피아노 SF2로 교체할 수 있습니다.

Debian FluidSynth 패키지가 기본 사용자 서비스를 자동 실행하도록 등록했다면, 선택 실행을 유지하려면 아래 명령으로 끕니다. 프로젝트 CLI는 계속 사용할 수 있습니다. 현재 라즈베리파이에는 이미 적용했습니다.

```bash
sudo systemctl --global disable fluidsynth.service
```

라즈베리파이의 실제 위치는 `/home/autodriver/Desktop/Toccata`입니다. 맥에서는 `ssh pi-toccata` 또는 `ssh -p 2226 autodriver@64.176.232.102`로 이 폴더에 들어갑니다.

## 1. 연결과 MIDI 입력 확인

```bash
./sw/toccata-midi list
aconnect -l
amidi -l
aplay -l
./sw/toccata-midi monitor
```

건반을 누르면 `note_on`, 떼면 `note_off`, 페달은 `control_change`가 보입니다. 모니터는 입력을 관찰하며 음원으로 재전송하지 않습니다. 장치가 없으면 연결을 기다리고, 연결이 바뀌면 다시 탐색합니다. 종료는 `Ctrl+C`입니다.

특정 이름의 입력만 보고 싶으면 다음처럼 이름 일부를 지정합니다.

```bash
./sw/toccata-midi monitor --input 'Toccata O1' --input 'Toccata PED'
./sw/toccata-midi monitor --duration 10
```

기본 모니터에서는 System·PipeWire·Midi Through 같은 가상 포트를 제외합니다. 가상 포트로 개발 시험을 할 때는 `--input`으로 그 이름을 직접 지정하세요.

## 2. 피아노 음원 실행

먼저 `aplay -l`과 `aplay -L`에서 **실제로 연결한 USB 오디오의 카드 ID**를 확인한 뒤 `config/midi.json`의 `audio_device`를 수정합니다. 예를 들어 ALSA 카드 ID가 `Device`이면 다음과 같습니다.

```json
{
  "fluidsynth": "fluidsynth",
  "soundfont": "/usr/share/sounds/sf2/TimGM6mb.sf2",
  "audio_device": "hw:CARD=Device,DEV=0",
  "sample_rate": 48000,
  "gain": 0.2,
  "polyphony": 256,
  "period_size": 128,
  "periods": 3
}
```

숫자 카드 번호는 연결 순서에 따라 바뀔 수 있어 카드 ID를 사용합니다. 기본값 `Device`는 예시이며, 현재 USB 오디오가 연결되어 있지 않으면 실제 음원 실행은 오류로 끝납니다. 코드가 준비되었다고 장치까지 연결된 것은 아닙니다.

```bash
# 실행할 명령만 확인: 장치나 소리를 열지 않음
./sw/toccata-midi synth --dry-run

# 연결한 USB MIDI 건반으로 연주, Ctrl+C로 종료
./sw/toccata-midi synth
```

48kHz ALSA `hw:` 직결로 실행하며, MIDI 입력 병합은 FluidSynth의 `midi.autoconnect=1` 한 곳에서 처리합니다. 별도 MIDI 전달 프로그램이나 중복 `aconnect` 연결을 함께 만들지 마세요. 여러 옥타브·페달 장치는 같은 음원으로 들어갑니다. 현재 데스크톱과 VNC의 오디오 서비스 설정은 유지합니다.

`gain`은 최종 스피커 출력 제한기가 아닙니다. 실제 앰프·스피커 조립 후 볼륨과 연주 지연, 끊김, 페달 동작을 확인해야 합니다.

## 3. 건반 없이 개발·검증

실제 오디오를 열지 않고 MIDI 파일과 WAV를 생성할 수 있습니다.

```bash
./sw/toccata-midi demo --output data/demo.mid
./sw/toccata-midi render data/demo.mid --output data/demo.wav
.venv/bin/python -m unittest discover -s sw/tests -v
```

생성한 파일은 `data/`에 남고 Git에는 포함되지 않습니다. 파일 렌더링 성공은 실제 USB 장치나 스피커 출력·지연 검증을 대신하지 않습니다.

## 프로젝트 관리 도구

이 라즈베리파이에서 설치기를 실행하면 `project.json`이 없을 때만 등록합니다. 기본 명령은 입력을 기다리는 `monitor`이고, 부팅 자동 실행은 꺼져 있습니다.

```bash
pi-project start Toccata
pi-project logs Toccata -f
pi-project stop Toccata
```

`run.sh`도 같은 관리 명령으로 시작합니다. 실제 피아노를 관리 서비스로 실행하려면 오디오 장치 설정을 마친 뒤 `project.json`의 `command`를 `["python3", "sw/toccata_midi.py", "synth"]`로 바꿉니다. 선택 실행 설정은 유지하고, 부팅 실행이 필요해질 때 `pi-project autostart Toccata on`을 사용하세요.

## 맥 → GitHub → 라즈베리파이 업데이트

맥의 `/Users/kwg/Desktop/mydrive/project/Toccata`에서 수정한 파일을 커밋·push합니다.

```bash
git status
git add 수정한파일
git commit -m "Describe the change"
git push origin design/v3-fastener-changes
```

라즈베리파이에서는 해당 폴더에서 가져옵니다. 실행 중인 Toccata만 먼저 멈추고, 의존성이 바뀌었다면 설치기를 다시 실행합니다.

```bash
pi-project stop Toccata
git pull --ff-only
./sw/setup-midi.sh
pi-project start Toccata
```

`git pull`이 로컬 수정 때문에 거절되면 먼저 그 수정을 보관·커밋하세요. `git reset --hard`로 덮어쓰지 않습니다. `.venv`, `config/midi.json`, `project.json`, `data/`, `logs/`, `.env`는 로컬 실행 자료로 Git에서 제외합니다. GitHub 인증 토큰이나 개인 SSH 키는 저장소에 넣지 않습니다.

## API 참고

- [Mido RtMidi backend](https://mido.readthedocs.io/en/stable/backends/rtmidi.html)
- [FluidSynth MIDI settings](https://www.fluidsynth.org/api/settings_midi.html)
- [FluidSynth audio settings](https://www.fluidsynth.org/api/settings_audio.html)
- [FluidSynth user manual](https://www.fluidsynth.org/wiki/UserManual/)
