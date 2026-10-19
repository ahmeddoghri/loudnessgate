from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


PROFILES = {
    "broadcast": {"integrated": -23.0, "tolerance": 1.0, "true_peak": -1.0, "lra": 20.0},
    "podcast": {"integrated": -16.0, "tolerance": 1.0, "true_peak": -1.0, "lra": 12.0},
    "music-streaming": {"integrated": -14.0, "tolerance": 1.0, "true_peak": -1.0, "lra": 18.0},
}

DEMO = {
    "profile": "podcast",
    "measurement": {"input_i": "-18.40", "input_tp": "-2.10", "input_lra": "6.20", "input_thresh": "-28.20", "target_offset": "0.05"},
}


def measure(path: str, target: dict[str, float]) -> dict[str, Any]:
    asset = Path(path)
    if not asset.is_file():
        raise ValueError(f"audio file not found: {path}")
    filter_spec = f"loudnorm=I={target['integrated']}:LRA={target['lra']}:TP={target['true_peak']}:print_format=json"
    process = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(asset), "-af", filter_spec, "-f", "null", "-"], capture_output=True, text=True)
    matches = re.findall(r"\{\s*\"input_i\".*?\}", process.stderr, flags=re.DOTALL)
    if process.returncode or not matches:
        raise ValueError("FFmpeg loudnorm measurement failed: " + process.stderr[-400:])
    return json.loads(matches[-1])


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    profile_name = str(payload.get("profile", "broadcast"))
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile: {profile_name}")
    target = PROFILES[profile_name]
    measurement = payload.get("measurement")
    if measurement is None:
        # Accept the report's own vocabulary as well as ffmpeg's raw keys, so
        # a caller can feed back the numbers this tool just printed at them.
        friendly = {
            "input_i": payload.get("integrated_lufs"),
            "input_tp": payload.get("true_peak_dbtp"),
            "input_lra": payload.get("loudness_range_lu"),
        }
        if all(value is not None for value in friendly.values()):
            measurement = friendly
        elif payload.get("path"):
            measurement = measure(str(payload["path"]), target)
        else:
            raise ValueError(
                "provide measured loudness: either measurement{input_i,input_tp,input_lra} "
                "or integrated_lufs, true_peak_dbtp and loudness_range_lu"
            )
    integrated = float(measurement["input_i"])
    peak = float(measurement["input_tp"])
    lra = float(measurement["input_lra"])
    checks = [
        {"metric": "integrated_lufs", "actual": integrated, "target": target["integrated"], "passed": abs(integrated - target["integrated"]) <= target["tolerance"]},
        {"metric": "true_peak_dbtp", "actual": peak, "maximum": target["true_peak"], "passed": peak <= target["true_peak"]},
        {"metric": "loudness_range_lu", "actual": lra, "maximum": target["lra"], "passed": lra <= target["lra"]},
    ]
    return {
        "profile": profile_name,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "gain_needed_db": round(target["integrated"] - integrated, 2),
        "measurement": measurement,
    }


def normalize(input_path: str, output_path: str, profile_name: str = "broadcast") -> dict[str, Any]:
    target = PROFILES.get(profile_name)
    if target is None:
        raise ValueError(f"unknown profile: {profile_name}")
    first = measure(input_path, target)
    spec = (
        f"loudnorm=I={target['integrated']}:LRA={target['lra']}:TP={target['true_peak']}:"
        f"measured_I={first['input_i']}:measured_LRA={first['input_lra']}:measured_TP={first['input_tp']}:"
        f"measured_thresh={first['input_thresh']}:offset={first['target_offset']}:linear=true:print_format=json"
    )
    process = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-i", input_path, "-af", spec, output_path], capture_output=True, text=True)
    if process.returncode:
        raise ValueError("FFmpeg normalization failed: " + process.stderr[-400:])
    return {"input": input_path, "output": output_path, "profile": profile_name, "before": analyze({"profile": profile_name, "measurement": first}), "after": analyze({"profile": profile_name, "path": output_path})}
