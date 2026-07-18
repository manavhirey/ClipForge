# Content-Generation Pipeline — Design

**Status:** Approved
**Date:** 2026-07-18

## Purpose

Given a Reddit post URL, produce a finished, ready-to-upload vertical (1080×1920) short-form video: the story narrated by AI voice over a gameplay background clip, with word-by-word burned-in captions. The pipeline stops at a rendered MP4 — publishing/upload is out of scope for this design.

## Scope

- Input: a single Reddit post URL, supplied manually per run.
- Output: one `final.mp4` per run.
- Explicitly out of scope for v1: automated story sourcing/discovery, content moderation/policy filtering, multi-part/series splitting, duration capping, YouTube upload/publishing.

## Architecture

A Python CLI (`clipforge run <reddit_url>`) drives six sequential stages. Each stage reads/writes well-defined files inside a per-video working directory, `output/<post-id>/` (post-id = the Reddit post's ID). Before running, each stage checks whether its output file already exists — if so, it's skipped unless `--force` is passed. This makes reruns cheap and avoids re-paying for external API calls (notably ElevenLabs TTS) after a failure in a later stage.

```
output/<post-id>/
  story.json         # fetched title + body + metadata
  script.txt         # LLM-cleaned narration text
  narration.mp3       # ElevenLabs audio
  timestamps.json      # word-level timing from ElevenLabs
  subtitles.ass        # generated karaoke-style subtitle file
  final.mp4            # rendered output
```

A `pipeline.py` orchestrates the stage functions in order. Each stage lives in its own module (`fetch.py`, `script.py`, `narrate.py`, `background.py`, `subtitles.py`, `render.py`), independently testable and readable in isolation. Each stage is a plain Python function with a typed input/output contract, e.g. `narrate(script_path) -> (audio_path, timestamps_path)`.

## Stages

1. **`fetch`** — Given a Reddit URL, pull title + selftext via Reddit's API (read-only app-only auth — client ID/secret, no user login). Save to `story.json`.
2. **`script`** — Send title + body to an LLM (Claude) with a prompt to strip Reddit-isms (markdown, "EDIT:", "AITA" tags), fix flow for spoken narration, keep it faithful to the original story (light cleanup, not a rewrite). Save plain text to `script.txt`.
3. **`narrate`** — Send `script.txt` to ElevenLabs TTS. Save the returned audio to `narration.mp3` and the returned word-level alignment/timestamp data to `timestamps.json`. No re-transcription step needed — ElevenLabs returns timing for the exact script text.
4. **`background`** — Pick a random file from a local `assets/gameplay/` library, pick a random start offset such that `offset + narration_duration <= clip_duration`. Note the selection (clip + offset) for the render stage. If no clip in the library is long enough, error out clearly. Populating `assets/gameplay/` with source footage is a one-time manual setup step outside the pipeline's responsibility — the pipeline only reads from it.
5. **`subtitles`** — Convert `timestamps.json` word timings into an `.ass` subtitle file: one word on screen at a time, bold centered text, sized/positioned for 1080×1920 vertical video.
6. **`render`** — Use ffmpeg (via subprocess) to: trim the background clip to the chosen offset/duration, scale/crop to 1080×1920, mute its audio, mix in `narration.mp3` as the sole audio track, burn in `subtitles.ass`, and write `final.mp4`.

Video length is not capped — it equals however long the narration takes, matching the trimmed background clip length.

## Error handling & config

- **Secrets**: `.env` file (gitignored) holding `REDDIT_CLIENT_ID`/`SECRET`, `ELEVENLABS_API_KEY`, `ANTHROPIC_API_KEY`. `config.py` loads and validates these are present at startup, failing fast with a clear message if any are missing.
- **External call failures** (Reddit fetch, LLM cleanup, ElevenLabs TTS): each stage catches its own API errors, logs a clear message naming the stage and cause, and exits non-zero. No silent partial output. Because stages persist their artifacts, fixing the issue and re-running resumes from the failed stage.
- **Bad input URL** (deleted post, private subreddit, non-text post): `fetch` errors out immediately with a clear message; no downstream stage runs.
- **No suitable background clip**: `background` errors out with a clear message rather than silently looping/stretching a clip.
- **Logging**: simple stdout logging per stage (e.g. `[narrate] done in 8.4s`) so progress and cost-incurring steps are visible during a run.

## Testing

- Unit tests per stage module with external API calls mocked (Reddit response fixture, ElevenLabs response fixture, sample LLM completion) — verifies each stage's transformation logic without spending real API credits.
- One manual/integration smoke test: run the full CLI against a real short Reddit post end-to-end and visually check the output video. Not automated (costs real money per run), but documented as the way to validate a pipeline change before considering it done.

## Key decisions & rationale

| Decision | Choice | Why |
|---|---|---|
| Automation scope | Sourcing is manual (you supply the URL); everything from script-cleanup onward is automatic | Keeps editorial control over story selection while automating the expensive/tedious part |
| Script prep | LLM cleans/reformats, doesn't rewrite for engagement | Faithful to source, lower risk of the LLM introducing errors or tonal drift |
| TTS | ElevenLabs (paid) | Best narration quality; its built-in timestamp API also removes the need for a separate transcription/alignment step |
| Background sourcing | Local pre-downloaded library, random clip + random offset | No network dependency or licensing risk at render time; simplest v1 |
| Subtitle timing | ElevenLabs alignment data, not Whisper | Timed against the known script text — no transcription-error risk |
| Duration handling | Uncapped, video length = narration length | Simplest v1 behavior; YouTube Shorts allows up to 3 minutes so this isn't a hard constraint |
| Audio mix | Gameplay audio muted, narration only | Cleanest listening experience, avoids sound-effect clashes |
| Pipeline structure | Staged, per-video artifact folder, skip-if-exists | Resumable without re-paying for TTS after a downstream failure; not over-engineered with pluggability that isn't needed yet |
| Output boundary | Stops at `final.mp4` | Matches project's stated purpose (content generation); publishing is a separate concern |
| Moderation | None in v1 | Source URL is manually chosen, so the human is already the filter |
