"""Play recorded backing audio against the game's unadjusted song clock."""
from __future__ import annotations

from array import array
import subprocess
import sys


TRACK_GAIN = 0.8125  # SDL_mixer volume 104/128, also used by the recording mix.


def _overlap_add(pcm, rate, speed):
    """Pitch-preserving fallback when ffmpeg is unavailable (mono signed 16-bit PCM)."""
    samples = array("h")
    samples.frombytes(pcm)
    length = round(len(samples) / speed)
    hop = rate // 40
    overlap = rate // 100
    search = rate // 200
    grain = hop + overlap
    samples.extend([0] * (grain + search))
    output = array("h", [0]) * (length + grain)

    output[:grain] = samples[:grain]
    for dest in range(hop, length, hop):
        source = round(dest * speed)
        # Align each grain to the previous waveform before crossfading. The
        # hop follows absolute song time so local phase choices cannot drift.
        previous = output[dest:dest + overlap:8]

        def difference(pos):
            return sum(abs(a - b) for a, b in zip(previous, samples[pos:pos + overlap:8]))

        lo, hi = max(0, source - search), source + search
        coarse = min(range(lo, hi + 1, 4), key=difference)
        source = min(range(max(lo, coarse - 3), min(hi, coarse + 3) + 1), key=difference)
        for i in range(overlap):
            output[dest + i] = (output[dest + i] * (overlap - i) + samples[source + i] * i) // overlap
        output[dest + overlap:dest + grain] = samples[source + overlap:source + grain]
    return memoryview(output)[:length]


def _practice_pcm(sound, rate, speed):
    pcm = memoryview(sound).cast("B")
    frames = round((len(pcm) // 2) / speed)
    fmt = "s16le" if sys.byteorder == "little" else "s16be"
    tempo = f"atempo={speed}" if speed >= 0.5 else f"atempo=0.5,atempo={2 * speed}"
    # Flush the final overlap window and match the game clock to the last frame.
    filters = f"apad=pad_dur=0.1,{tempo},apad=whole_len={frames},atrim=end_sample={frames}"
    try:
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-f", fmt, "-ar", str(rate), "-ac", "1",
             "-i", "pipe:0", "-af", filters, "-f", fmt, "pipe:1"],
            input=pcm, capture_output=True, check=True,
        )
    except FileNotFoundError:
        return _overlap_add(pcm, rate, speed)
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"원곡 연습 속도 변환 실패: {exc.stderr.decode(errors='replace').strip()}") from exc
    return result.stdout


class BackingTrackPlayer:
    """Prepare one run. Tick due(original_song_ms), including negative count-in.

    pause/resume freeze the current sample. stop releases the track. A restarted
    scene creates a new player, potentially at a different practice speed.
    """

    def __init__(self, pygame, path, speed=1.0):
        if not 0.25 <= speed <= 2.0:
            raise ValueError(f"speed out of range: {speed}")
        self._mixer = pygame.mixer
        spec = self._mixer.get_init()
        if spec is None or spec[1:] != (-16, 1):
            raise ValueError("원곡 재생에는 16비트 모노 믹서가 필요합니다")
        self._rate = spec[0]
        self._speed = speed
        original = self._mixer.Sound(file=path)
        frames = memoryview(original).nbytes // 2
        self.length_ms = frames * 1000 / self._rate
        self._sound = original
        if speed != 1.0 and frames:
            self._sound = self._mixer.Sound(buffer=_practice_pcm(original, self._rate, speed))
        self._sound.set_volume(TRACK_GAIN)
        self._channel = None
        self._paused = False

    def due(self, song_ms):
        if self._paused or self._sound is None or song_ms < 0:
            return
        if song_ms >= self.length_ms:
            self.stop()
            return
        if self._channel is not None:
            return
        frame = int(song_ms * self._rate / (1000 * self._speed))
        if frame:
            # The first tick may already be past the downbeat. Skip those samples
            # once, then let SDL play the rest independently of render frame rate.
            tail = memoryview(self._sound).cast("B")[frame * 2:]
            if not tail:
                self.stop()
                return
            self._sound = self._mixer.Sound(buffer=tail)
            self._sound.set_volume(TRACK_GAIN)
        # Sound.play chooses a free channel and resets its previous effect gain.
        # If every voice is busy, add a voice without cutting off a held key.
        self._channel = self._sound.play()
        if self._channel is None:
            index = self._mixer.get_num_channels()
            self._mixer.set_num_channels(index + 1)
            self._channel = self._mixer.Channel(index)
            self._channel.play(self._sound)

    def _owns_channel(self):
        return self._channel is not None and self._channel.get_sound() is self._sound

    def pause(self):
        if self._owns_channel():
            self._channel.pause()
        self._paused = True

    def resume(self):
        if self._paused and self._owns_channel():
            self._channel.unpause()
        self._paused = False

    def stop(self):
        if self._owns_channel():
            self._channel.stop()
        self._channel = None
        self._sound = None
