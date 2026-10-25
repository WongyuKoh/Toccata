"""Run with: python -m unittest discover -s sw/tests -v."""
import importlib.util
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import toccata_midi as midi


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "config").mkdir()
        self.path = self.root / "config/midi.json"

    def load(self, values):
        self.path.write_text(json.dumps(values))
        return midi.load_config(root=self.root)

    def test_default_settings_and_repo_relative_soundfont(self):
        config = self.load({"soundfont": "sounds/piano.sf2"})
        self.assertEqual(config.soundfont, str(self.root / "sounds/piano.sf2"))
        self.assertEqual(config.sample_rate, 48000)
        self.assertEqual(config.audio_device, "hw:CARD=Device,DEV=0")

    def test_default_example_used_only_when_no_project_config(self):
        self.assertEqual(midi.load_config(root=self.root).gain, 0.2)
        self.load({"gain": 0.15})
        self.assertEqual(midi.load_config(root=self.root).gain, 0.15)

    def test_explicit_missing_or_invalid_config_does_not_silently_fallback(self):
        with self.assertRaises(midi.MidiError):
            midi.load_config(self.root / "missing.json")
        self.path.write_text("{")
        with self.assertRaises(midi.MidiError):
            midi.load_config(root=self.root)

    def test_reject_invalid_types_ranges_and_unknown_options(self):
        cases = [[], {"shell": "sh"}, {"sample_rate": True}, {"sample_rate": 0},
                 {"gain": float("nan")}, {"gain": float("inf")}, {"gain": False},
                 {"gain": 1.1}, {"period_size": 127}, {"periods": 1},
                 {"polyphony": 0}, {"soundfont": 5}, {"fluidsynth": "x\ny"}]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(midi.MidiError):
                self.load(values)

    def test_reject_audio_options_that_change_driver_or_inject_commands(self):
        for value in ("default", "hw:0", "hw:CARD=Device,DEV=0;touch /tmp/x", "-s", ""):
            with self.subTest(value=value), self.assertRaises(midi.MidiError):
                self.load({"audio_device": value})


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.sf = self.root / "piano; echo injected.sf2"
        self.sf.write_bytes(b"soundfont-fixture")
        self.input = self.root / "-notes.mid"
        self.input.write_bytes(b"midi-fixture")
        self.config = midi.Config(soundfont=str(self.sf))
        self.binary = patch.object(midi, "fluidsynth_binary", return_value="/usr/bin/fluidsynth")
        self.binary.start()
        self.addCleanup(self.binary.stop)

    def test_synth_uses_one_midi_merger_and_no_shell_or_server(self):
        args = midi.synth_argv(self.config)
        self.assertEqual(args[0], "/usr/bin/fluidsynth")
        self.assertEqual(args[-1], str(self.sf))
        self.assertEqual(args.count("midi.autoconnect=1"), 1)
        self.assertIn("audio.alsa.device=hw:CARD=Device,DEV=0", args)
        self.assertIn("audio.period-size=128", args)
        self.assertIn("synth.polyphony=256", args)
        self.assertIn("midi.alsa_seq.id=Toccata synth", args)
        self.assertNotIn("-s", args)
        self.assertNotIn("-n", args)
        self.assertNotIn("shell=True", args)
        self.assertIn("-i", args)

    def test_render_is_offline_and_option_like_path_is_absolute(self):
        args = midi.render_argv(self.config, self.input, self.root / "demo.wav")
        self.assertIn("-ni", args)
        self.assertNotIn("alsa_seq", args)
        self.assertNotIn("-a", args)
        self.assertEqual(args[-2:], [str(self.sf), str(self.input)])
        self.assertEqual(args[args.index("-F") + 1], str(self.root / "demo.wav"))

    def test_missing_soundfont_or_midi_returns_actionable_error(self):
        with self.assertRaisesRegex(midi.MidiError, "MIDI"):
            midi.render_argv(self.config, self.root / "absent.mid", self.root / "test.wav")
        self.sf.unlink()
        with self.assertRaisesRegex(midi.MidiError, "SoundFont"):
            midi.synth_argv(self.config)

    def test_render_rejects_input_overwrite_and_missing_output_directory(self):
        for output in (self.input, self.sf, self.root / "missing/test.wav"):
            with self.subTest(output=output), self.assertRaises(midi.MidiError):
                midi.render_argv(self.config, self.input, output)

    def test_alsa_card_id_discovery_uses_c_locale_without_shell(self):
        result = type("Result", (), {"stdout": "card 0: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM\ncard 2: Device [USB Audio], device 0: USB Audio\n"})()
        with patch.object(midi.shutil, "which", return_value="/usr/bin/aplay"), patch.object(midi.subprocess, "run", return_value=result) as run:
            self.assertEqual(midi.alsa_playback_devices(), {"hw:CARD=vc4hdmi0,DEV=0", "hw:CARD=Device,DEV=0"})
            self.assertEqual(run.call_args.args[0], ["/usr/bin/aplay", "-l"])
            self.assertEqual(run.call_args.kwargs["env"]["LC_ALL"], "C")
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_dry_run_does_not_open_hardware_or_execute(self):
        with redirect_stdout(io.StringIO()), patch.object(midi, "load_config", return_value=self.config), patch.object(midi, "alsa_playback_devices", side_effect=AssertionError("opened audio")), patch.object(midi.os, "execv", side_effect=AssertionError("executed")):
            self.assertEqual(midi.main(["synth", "--dry-run"]), 0)

    def test_synth_missing_usb_audio_does_not_execute(self):
        with redirect_stderr(io.StringIO()), patch.object(midi, "load_config", return_value=self.config), patch.object(midi, "alsa_playback_devices", return_value={"hw:CARD=vc4hdmi0,DEV=0"}), patch.object(midi.os, "execv", side_effect=AssertionError("executed")):
            self.assertEqual(midi.main(["synth"]), 1)


class Clock:
    now = 0.0
    def __call__(self):
        return self.now
    def sleep(self, duration):
        self.now += duration


class DependencyTests(unittest.TestCase):
    def test_missing_mido_explains_project_requirements(self):
        with patch.dict(sys.modules, {"mido": None}), self.assertRaisesRegex(midi.MidiError, "requirements-midi.txt"):
            midi.load_mido()

    def test_help_and_parser_do_not_import_mido(self):
        with patch.object(midi, "load_mido", side_effect=AssertionError("dependency imported")):
            args = midi.build_parser().parse_args(["monitor", "--input", "O1", "--input", "O2", "--duration", "2.5"])
            self.assertEqual(args.input, ["O1", "O2"])
            self.assertEqual(args.duration, 2.5)

    def test_duration_rejects_nan_infinity_zero_negative(self):
        for value in ("nan", "inf", "0", "-2"):
            with self.subTest(value=value), self.assertRaises(midi.argparse.ArgumentTypeError):
                midi.positive_duration(value)


class Input:
    def __init__(self):
        self.closed = False
        self.messages = ["note_on channel=0 note=60 velocity=72"]
    def iter_pending(self):
        messages, self.messages = self.messages, []
        return iter(messages)
    def close(self):
        self.closed = True
    def send(self, *_args):
        raise AssertionError("monitor must never forward a MIDI message")


class MonitorTests(unittest.TestCase):
    def test_filter_excludes_system_virtual_ports_unless_explicit(self):
        names = ["System 0:0", "Midi Through 14:0", "PipeWire-System", "Toccata synth 128:0", "Toccata O1 20:0"]
        self.assertEqual(midi.selected_input_names(names), [names[-1]])
        self.assertEqual(midi.selected_input_names(names, ["MIDI THROUGH"]), [names[1]])
        self.assertEqual(midi.selected_input_names(names, [" O1", " O2"]), [names[-1]])

    def test_wait_hotplug_disconnect_reconnect_and_no_forwarding(self):
        clock = Clock()
        ports = []
        messages = []
        class Backend:
            def get_input_names(self):
                return ["Toccata O1"] if 1 <= clock.now < 2 or clock.now >= 3 else []
            def open_input(self, _name):
                port = Input()
                ports.append(port)
                return port
            def open_output(self, *_args):
                raise AssertionError("monitor opened output")
        midi.monitor(Backend(), duration=3.2, clock=clock, sleep=clock.sleep, emit=lambda s, **kw: messages.append(s))
        self.assertEqual(len(ports), 2)
        self.assertTrue(all(port.closed for port in ports))
        self.assertTrue(any("기다립니다" in value for value in messages))
        self.assertEqual(sum("note_on" in value for value in messages), 2)
        self.assertAlmostEqual(clock.now, 3.2)

    def test_signal_cleanup_closes_all_inputs(self):
        ports = []
        class Backend:
            def get_input_names(self):
                return ["Toccata O1", "Toccata O2"]
            def open_input(self, _name):
                port = Input()
                ports.append(port)
                return port
        def stop(_duration):
            raise midi.Interrupted(signal.SIGTERM)
        with self.assertRaises(midi.Interrupted):
            midi.monitor(Backend(), sleep=stop, emit=lambda *args, **kw: None)
        self.assertEqual(len(ports), 2)
        self.assertTrue(all(port.closed for port in ports))

    def test_main_sigterm_is_successful_shutdown_and_closes_input(self):
        port = Input()
        class Backend:
            def get_input_names(self):
                return ["Toccata O1"]
            def open_input(self, _name):
                return port
        original_monitor = midi.monitor
        previous = signal.getsignal(signal.SIGTERM)
        def send_sigterm(_duration):
            signal.raise_signal(signal.SIGTERM)
        def run_monitor(backend, selectors, duration):
            original_monitor(backend, selectors, duration, sleep=send_sigterm, emit=lambda *args, **kw: None)
        with patch.object(midi, "midi_backend", return_value=Backend()), patch.object(midi, "monitor", side_effect=run_monitor):
            self.assertEqual(midi.main(["monitor"]), 0)
        self.assertTrue(port.closed)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)


@unittest.skipUnless(importlib.util.find_spec("mido"), "Install sw/requirements-midi.txt to test real MIDI files")
class DemoTests(unittest.TestCase):
    def test_real_smf_timing_releases_and_sustain_without_device_io(self):
        import mido
        with tempfile.TemporaryDirectory() as temp, patch.object(mido, "open_output", side_effect=AssertionError("opened hardware")):
            output = midi.write_demo(Path(temp) / "demo.mid", mido)
            song = mido.MidiFile(output)
            self.assertEqual(song.type, 0)
            self.assertAlmostEqual(song.length, 2.5)
            notes_on = [m.note for m in song.tracks[0] if m.type == "note_on"]
            notes_off = [m for m in song.tracks[0] if m.type == "note_off"]
            self.assertEqual(notes_on, [60, 64, 67, 60, 64, 67])
            self.assertEqual([m.note for m in notes_off], notes_on)
            self.assertTrue(all(m.velocity >= 5 for m in notes_off))
            pedal = [m.value for m in song.tracks[0] if m.type == "control_change" and m.control == 64]
            self.assertEqual(pedal, [0, 127, 0])


if __name__ == "__main__":
    unittest.main()
