# ClipForge

AI pipeline converting Reddit stories into portrait short-form videos (YT Shorts) with gameplay background, TTS narration, and word-by-word subtitles.

## Setup

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env` and fill in `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ANTHROPIC_API_KEY`. `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` are only required if you're running with a Reddit URL — skip them entirely if you'll only ever use `--text-file`.
4. Install `ffmpeg` (provides both `ffmpeg` and `ffprobe`) and make sure it's on your `PATH`.
5. Drop one or more gameplay `.mp4` files into `assets/gameplay/`.

## Usage

```bash
clipforge run https://www.reddit.com/r/AmItheAsshole/comments/<id>/<slug>/
```

Or, to skip Reddit entirely (no `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET` needed) and supply the story yourself, save it to a text file (first line = title, the rest = body) and run:

```bash
clipforge run --text-file story.txt
```

Provide exactly one of the URL or `--text-file` — not both, not neither. Output is written to `output/<id>/final.mp4` (the Reddit post ID for URL runs, or a content hash of the text for `--text-file` runs — so re-running the exact same text reuses the same output directory). Rerunning skips stages whose artifacts already exist; pass `--force` to redo every stage.

## Manual smoke test

Automated tests mock every external API. Before considering a pipeline change done, run it once against a real short Reddit post end-to-end and visually check `final.mp4` — this is the only way to catch real API/ffmpeg integration issues, and it costs real ElevenLabs credits, so don't automate it.
