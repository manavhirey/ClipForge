# ClipForge

AI pipeline converting Reddit stories into portrait short-form videos (YT Shorts) with gameplay background, TTS narration, and word-by-word subtitles.

## Setup

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env` and fill in `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ANTHROPIC_API_KEY`. No Reddit credentials needed — posts are fetched from Reddit's public `.json` endpoint, unauthenticated.
4. Install `ffmpeg` (provides both `ffmpeg` and `ffprobe`) and make sure it's on your `PATH`.
5. Drop one or more gameplay `.mp4` files into `assets/gameplay/`.

## Usage

```bash
clipforge run https://www.reddit.com/r/AmItheAsshole/comments/<id>/<slug>/
```

Output is written to `output/<post-id>/final.mp4`. Rerunning the same URL skips stages whose artifacts already exist; pass `--force` to redo every stage.

**Note on fetching:** the `fetch` stage uses Reddit's unauthenticated public JSON endpoint rather than the OAuth API. This has no setup cost, but Reddit can rate-limit or block automated requests to it (more likely from datacenter/cloud IPs than a home connection) without notice — if `clipforge run` fails at the fetch step with a 403 or "did not return JSON" error, that's Reddit blocking the request, not a bug to debug locally.

## Manual smoke test

Automated tests mock every external API. Before considering a pipeline change done, run it once against a real short Reddit post end-to-end and visually check `final.mp4` — this is the only way to catch real API/ffmpeg integration issues, and it costs real ElevenLabs credits, so don't automate it.
