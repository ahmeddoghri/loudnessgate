import json
import socket
import threading
import time
import unittest
import urllib.error
import urllib.request

from loudnessgate.server import serve


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class ServerPathExposureTest(unittest.TestCase):
    """do_POST forwarded the raw JSON body straight into analyze(), which
    falls back to measure(payload["path"], ...) -- running ffmpeg directly
    against that filesystem path -- whenever "measurement" was absent.
    That let any unauthenticated remote caller make the server run ffmpeg
    against an arbitrary local file (an existence/readability oracle at
    minimum, and a way to pull loudness data out of files the caller has
    no business touching). The JSON API must only ever operate on
    pre-measured values; local-file measurement stays CLI-only."""

    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.thread = threading.Thread(target=serve, args=("127.0.0.1", cls.port), daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    def _post(self, body):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/analyze",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_path_field_is_rejected_over_the_network_api(self):
        status, body = self._post({"profile": "podcast", "path": "/etc/hosts"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_path_field_is_rejected_even_for_a_nonexistent_file(self):
        """The rejection must happen before any filesystem check, so the
        response can't be used as an existence oracle either."""
        status, body = self._post({"profile": "podcast", "path": "/definitely/does/not/exist.wav"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_pre_measured_values_still_work_over_the_network_api(self):
        status, body = self._post(
            {
                "profile": "podcast",
                "measurement": {
                    "input_i": "-18.40",
                    "input_tp": "-2.10",
                    "input_lra": "6.20",
                    "input_thresh": "-28.20",
                    "target_offset": "0.05",
                },
            }
        )
        self.assertEqual(status, 200)
        self.assertFalse(body["passed"])
        self.assertEqual(body["gain_needed_db"], 2.4)


if __name__ == "__main__":
    unittest.main()
