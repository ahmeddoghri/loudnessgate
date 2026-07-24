import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from loudnessgate.core import DEMO, analyze, normalize


def tone(path: Path, amplitude: float = 0.1) -> None:
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        output.writeframes(b"".join(struct.pack("<h", int(amplitude * 32767 * math.sin(2 * math.pi * 440 * index / 48000))) for index in range(144000)))


class LoudnessGateTest(unittest.TestCase):
    def test_demo_fails_quiet_podcast(self):
        result = analyze(DEMO)
        self.assertFalse(result["passed"])
        self.assertEqual(result["gain_needed_db"], 2.4)

    def test_two_pass_normalization_produces_passing_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "source.wav", Path(directory) / "target.wav"
            tone(source)
            result = normalize(str(source), str(target), "podcast")
            self.assertTrue(target.exists())
            self.assertTrue(result["after"]["passed"])


if __name__ == "__main__":
    unittest.main()
