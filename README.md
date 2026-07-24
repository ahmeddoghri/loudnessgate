# loudnessgate

**EBU R128 loudness measurement, normalization, and CI gate.**

![loudnessgate cover](demo/cover.png)

Measure integrated loudness, range, and true peak, then run deterministic two-pass FFmpeg normalization.

![loudnessgate workbench](demo/dashboard.png)

## What ships

- A deterministic domain analysis engine with explicit scope
- JSON API and responsive local browser workbench
- CLI demo and file-driven analysis
- Docker image, unit tests, and GitHub Actions matrix
- No API keys and no uploaded user data

## Run it end to end

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e .
loudnessgate demo
loudnessgate normalize input.wav mastered.wav --profile podcast
loudnessgate serve
```

Open <http://127.0.0.1:8090>. Analyze your own JSON input with `loudnessgate analyze input.json`.

## API

- `GET /api/demo` returns the committed fixture and result.
- `POST /api/analyze` runs the same engine on a JSON body.

## Current basis

- [EBU R128](https://tech.ebu.ch/loudness/)
- [FFmpeg loudnorm](https://www.ffmpeg.org/ffmpeg-filters.html#loudnorm)

## Demo result

The podcast fixture measures -18.40 LUFS against a -16 LUFS target, so the gate requests +2.40 dB while its loudness range and true peak already pass. The integration test performs real two-pass normalization and remeasures the output.

## Scope

Broadcast, podcast, and music-streaming presets are engineering defaults, not universal delivery contracts. Confirm each distributor's current target, channel layout, codec, and true-peak requirements.

## Test

```bash
python -m unittest discover -s tests -v
```

MIT licensed.
