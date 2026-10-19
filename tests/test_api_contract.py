"""The JSON API must refuse local paths and still do its actual job."""
import unittest

from loudnessgate.core import analyze

MEASURED = {"profile": "podcast", "integrated_lufs": -18.4, "true_peak_dbtp": -2.1, "loudness_range_lu": 6.2}


class ApiContractTest(unittest.TestCase):
    def test_report_vocabulary_is_accepted(self):
        result = analyze(MEASURED)
        self.assertEqual(result["gain_needed_db"], 2.4)
        self.assertFalse(result["passed"])

    def test_ffmpeg_vocabulary_is_accepted(self):
        result = analyze({"profile": "podcast", "measurement": {"input_i": "-18.4", "input_tp": "-2.1", "input_lra": "6.2"}})
        self.assertEqual(result["gain_needed_db"], 2.4)

    def test_a_body_with_no_measurement_says_what_is_missing(self):
        # It used to fall through to measuring an empty path and answer
        # "audio file not found: ", which tells a caller nothing.
        with self.assertRaises(ValueError) as caught:
            analyze({"profile": "podcast"})
        self.assertIn("provide measured loudness", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
