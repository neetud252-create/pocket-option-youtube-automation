"""Protect fallback routing and narration timing during the Piper upgrade."""
import os
import unittest
from unittest.mock import patch

from app import voice


class VoiceQualityTests(unittest.TestCase):
    def test_fallback_returns_actual_lossless_file(self):
        with patch.dict(os.environ, ELEVENLABS_API_KEY="test"), \
                patch.object(voice, "elevenlabs_tts", side_effect=RuntimeError("quota")), \
                patch.object(voice, "piper_tts", return_value="narration_piper.wav"), \
                patch.object(voice, "safe_remove"):
            self.assertEqual(voice.generate_raw_segment("Hello.", "narration.mp3"),
                             ("piper", "narration_piper.wav"))

    def test_elevenlabs_success_and_strict_requirement_are_preserved(self):
        with patch.dict(os.environ, ELEVENLABS_API_KEY="test"), \
                patch.object(voice, "elevenlabs_tts"), \
                patch.object(voice, "piper_tts") as piper:
            self.assertEqual(voice.generate_raw_segment("Hello.", "narration.mp3"),
                             ("elevenlabs", "narration.mp3"))
            piper.assert_not_called()
        with patch.dict(os.environ, ELEVENLABS_API_KEY=""), \
                patch.object(voice, "piper_tts") as piper:
            with self.assertRaises(RuntimeError):
                voice.generate_raw_segment("Hello.", "narration.mp3", require_elevenlabs=True)
            piper.assert_not_called()

    def test_piper_prefers_natural_speed_without_slowdown(self):
        for duration in (15.0, 18.0, 20.0, 23.0, 27.3):
            with self.subTest(duration=duration):
                for selector in (min, max):
                    with patch.object(voice.random, "randint", side_effect=lambda a, b: selector(a, b)):
                        target = voice.choose_main_duration(duration, "piper")
                    self.assertGreaterEqual(target, 15)
                    self.assertLessEqual(target, 21)
                    self.assertGreaterEqual(duration / target, 1)
                    self.assertLessEqual(duration / target, 1.30 + 1e-9)
                    if duration <= 23.1:
                        self.assertLessEqual(duration / target, 1.10 + 1e-9)
                    else:
                        self.assertEqual(target, 21)

    def test_out_of_range_speech_still_fails_before_upload(self):
        for duration in (14.9, 27.4):
            with self.assertRaises(RuntimeError):
                voice.choose_main_duration(duration, "piper")


if __name__ == "__main__":
    unittest.main()
