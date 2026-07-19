# Content-Generation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI (`clipforge run <reddit_url>`) that turns a Reddit post into a finished vertical (1080×1920) short-form video: LLM-cleaned narration read by ElevenLabs TTS, over a randomly selected local gameplay clip, with word-by-word burned-in captions.

**Architecture:** A staged pipeline. Each stage is a pure, independently-testable function taking plain data plus injected clients, so unit tests never make real network/subprocess calls. `pipeline.py` orchestrates the stages in order, persisting each stage's output into `output/<post-id>/` and skipping any stage whose output file already exists (unless `--force`) — this makes reruns cheap and avoids re-paying for ElevenLabs calls after a downstream failure.

**Tech Stack:** Python 3.11+, `praw` (Reddit), `anthropic` (script cleanup), `elevenlabs` (TTS + timestamps), `ffmpeg`/`ffprobe` (via subprocess, must be installed and on PATH), `pytest`.

## Global Constraints

- Output video: 1080×1920, MP4. No duration cap — video length equals however long the narration runs.
- Background clip audio is muted; ElevenLabs narration is the sole audio track.
- Subtitles: one word on screen at a time, bold centered, burned into the video via ffmpeg's `ass` filter.
- TTS timing comes from ElevenLabs' own alignment data — no Whisper/re-transcription step.
- Script cleanup is a light LLM pass (strip Reddit formatting, fix flow for narration) — not a rewrite for engagement.
- Story sourcing is manual: the pipeline takes one Reddit post URL per run, no auto-discovery.
- No content-moderation/policy filtering in v1.
- Pipeline stops at a rendered `final.mp4` — no upload/publishing.
- Secrets (`REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ANTHROPIC_API_KEY`) load from `.env`/environment via `config.py`, which fails fast with a clear message if any are missing.
- Each pipeline stage persists its artifact into `output/<post-id>/` and is skipped on rerun if that artifact already exists, unless `--force` is passed.
- `assets/gameplay/` is a manually populated library of `.mp4` files — the pipeline only reads from it, never downloads into it.

---

### Task 1: Project scaffolding and config loading

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `clipforge/__init__.py`
- Create: `clipforge/config.py`
- Create: `assets/gameplay/.gitkeep`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `clipforge.config.load_config(env: Mapping[str, str] = os.environ) -> Config`, where `Config` is a dataclass with fields `reddit_client_id`, `reddit_client_secret`, `elevenlabs_api_key`, `elevenlabs_voice_id`, `anthropic_api_key` (all `str`). Raises `ValueError` naming every missing variable if any required var is absent.

- [ ] **Step 1: Create the package layout and project files**

`pyproject.toml`:
```toml
[project]
name = "clipforge"
version = "0.1.0"
description = "AI pipeline converting Reddit stories into portrait short-form videos"
requires-python = ">=3.11"
dependencies = [
    "praw>=7.7",
    "anthropic>=0.40",
    "elevenlabs>=1.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
clipforge = "clipforge.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["clipforge*"]
```

`.env.example`:
```
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
ANTHROPIC_API_KEY=
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.env
output/
assets/gameplay/*
!assets/gameplay/.gitkeep
```

`clipforge/__init__.py`: empty file.

`assets/gameplay/.gitkeep`: empty file.

- [ ] **Step 2: Write `clipforge/config.py`**

```python
import os
from dataclasses import dataclass
from typing import Mapping

REQUIRED_VARS = [
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ANTHROPIC_API_KEY",
]


@dataclass
class Config:
    reddit_client_id: str
    reddit_client_secret: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    anthropic_api_key: str


def load_config(env: Mapping[str, str] = os.environ) -> Config:
    missing = [name for name in REQUIRED_VARS if not env.get(name)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return Config(
        reddit_client_id=env["REDDIT_CLIENT_ID"],
        reddit_client_secret=env["REDDIT_CLIENT_SECRET"],
        elevenlabs_api_key=env["ELEVENLABS_API_KEY"],
        elevenlabs_voice_id=env["ELEVENLABS_VOICE_ID"],
        anthropic_api_key=env["ANTHROPIC_API_KEY"],
    )
```

- [ ] **Step 3: Write the failing test**

`tests/test_config.py`:
```python
import pytest

from clipforge.config import load_config


def test_load_config_reads_all_vars():
    env = {
        "REDDIT_CLIENT_ID": "rid",
        "REDDIT_CLIENT_SECRET": "rsecret",
        "ELEVENLABS_API_KEY": "ekey",
        "ELEVENLABS_VOICE_ID": "voice1",
        "ANTHROPIC_API_KEY": "akey",
    }

    config = load_config(env)

    assert config.reddit_client_id == "rid"
    assert config.reddit_client_secret == "rsecret"
    assert config.elevenlabs_api_key == "ekey"
    assert config.elevenlabs_voice_id == "voice1"
    assert config.anthropic_api_key == "akey"


def test_load_config_raises_on_missing_vars():
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        load_config({"REDDIT_CLIENT_ID": "rid"})
```

- [ ] **Step 4: Install the project and run the tests**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_config.py -v
```
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example .gitignore clipforge/__init__.py clipforge/config.py assets/gameplay/.gitkeep tests/test_config.py
git commit -m "feat: scaffold project and add config loading"
```

---

### Task 2: Fetch stage

**Files:**
- Create: `clipforge/stages/__init__.py`
- Create: `clipforge/stages/fetch.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `clipforge.stages.fetch.fetch_story(url: str, reddit_client) -> dict` returning `{"id": str, "title": str, "body": str, "subreddit": str, "url": str}`. `reddit_client` is any object exposing `.submission(url=str)` returning an object with `.id`, `.title`, `.selftext`, `.subreddit` attributes (this matches `praw.Reddit` directly — no adapter needed). Raises `ValueError` if `.selftext` is empty.

- [ ] **Step 1: Write the failing tests**

`clipforge/stages/__init__.py`: empty file.

`tests/test_fetch.py`:
```python
import pytest

from clipforge.stages.fetch import fetch_story


class FakeSubmission:
    def __init__(self, id, title, selftext, subreddit):
        self.id = id
        self.title = title
        self.selftext = selftext
        self.subreddit = subreddit


class FakeRedditClient:
    def __init__(self, submission):
        self._submission = submission

    def submission(self, url):
        return self._submission


def test_fetch_story_returns_expected_fields():
    fake_sub = FakeSubmission(
        id="abc123", title="My Story", selftext="Once upon a time...", subreddit="AmItheAsshole"
    )
    client = FakeRedditClient(fake_sub)

    result = fetch_story("https://reddit.com/r/AmItheAsshole/comments/abc123/my_story/", client)

    assert result == {
        "id": "abc123",
        "title": "My Story",
        "body": "Once upon a time...",
        "subreddit": "AmItheAsshole",
        "url": "https://reddit.com/r/AmItheAsshole/comments/abc123/my_story/",
    }


def test_fetch_story_raises_on_no_selftext():
    fake_sub = FakeSubmission(id="abc123", title="Image post", selftext="", subreddit="pics")
    client = FakeRedditClient(fake_sub)

    with pytest.raises(ValueError, match="no text body"):
        fetch_story("https://reddit.com/r/pics/comments/abc123/img/", client)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.stages.fetch'`

- [ ] **Step 3: Write `clipforge/stages/fetch.py`**

```python
def fetch_story(url: str, reddit_client) -> dict:
    submission = reddit_client.submission(url=url)
    if not submission.selftext:
        raise ValueError(f"Post at {url} has no text body (not a text post)")
    return {
        "id": submission.id,
        "title": submission.title,
        "body": submission.selftext,
        "subreddit": str(submission.subreddit),
        "url": url,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_fetch.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/stages/__init__.py clipforge/stages/fetch.py tests/test_fetch.py
git commit -m "feat: add fetch stage"
```

---

### Task 3: Script cleanup stage

**Files:**
- Create: `clipforge/stages/script.py`
- Test: `tests/test_script.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `clipforge.stages.script.clean_script(title: str, body: str, llm_client) -> str`. `llm_client` is any object exposing `.messages.create(**kwargs)` returning an object with `.content[0].text` (matches `anthropic.Anthropic` directly — no adapter needed). Raises `ValueError` if the LLM returns empty text.

- [ ] **Step 1: Write the failing tests**

`tests/test_script.py`:
```python
import pytest

from clipforge.stages.script import clean_script


class FakeContent:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeContent(text)]


class FakeMessages:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self.response_text)


class FakeLLMClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


def test_clean_script_returns_llm_text():
    client = FakeLLMClient("Cleaned narration text.")

    result = clean_script("Title", "Body text", client)

    assert result == "Cleaned narration text."
    assert "Title" in client.messages.last_kwargs["messages"][0]["content"]
    assert "Body text" in client.messages.last_kwargs["messages"][0]["content"]


def test_clean_script_raises_on_empty_response():
    client = FakeLLMClient("   ")

    with pytest.raises(ValueError, match="empty script"):
        clean_script("Title", "Body text", client)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_script.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.stages.script'`

- [ ] **Step 3: Write `clipforge/stages/script.py`**

```python
SYSTEM_PROMPT = (
    "You turn Reddit posts into spoken-narration scripts for a short-form video. "
    "Strip Reddit-specific formatting (markdown, 'EDIT:', 'UPDATE:', flair tags like 'AITA'), "
    "and lightly adjust phrasing so it reads naturally when read aloud. "
    "Stay faithful to the original story — do not add, remove, or embellish plot details. "
    "Output only the narration script, nothing else."
)


def clean_script(title: str, body: str, llm_client) -> str:
    response = llm_client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Title: {title}\n\nBody:\n{body}"}],
    )
    text = response.content[0].text.strip()
    if not text:
        raise ValueError("LLM returned an empty script")
    return text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_script.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/stages/script.py tests/test_script.py
git commit -m "feat: add script cleanup stage"
```

---

### Task 4: Narrate stage

**Files:**
- Create: `clipforge/stages/narrate.py`
- Test: `tests/test_narrate.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `clipforge.stages.narrate.characters_to_word_timestamps(characters: list[str], start_times: list[float], end_times: list[float]) -> list[dict]`, each dict `{"word": str, "start": float, "end": float}`.
  - `clipforge.stages.narrate.narrate(script_text: str, tts_client, voice_id: str) -> tuple[bytes, list[dict]]`. `tts_client` is any object exposing `.convert_with_timestamps(voice_id=str, text=str) -> dict` with keys `"audio_bytes"` (bytes) and `"alignment"` (dict with `"characters"`, `"character_start_times_seconds"`, `"character_end_times_seconds"`). Raises `ValueError` if no words are found.

- [ ] **Step 1: Write the failing tests**

`tests/test_narrate.py`:
```python
import pytest

from clipforge.stages.narrate import characters_to_word_timestamps, narrate


def test_characters_to_word_timestamps_groups_by_whitespace():
    characters = ["h", "i", " ", "y", "o", "u"]
    starts = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    ends = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

    result = characters_to_word_timestamps(characters, starts, ends)

    assert result == [
        {"word": "hi", "start": 0.0, "end": 0.2},
        {"word": "you", "start": 0.3, "end": 0.6},
    ]


class FakeTTSClient:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def convert_with_timestamps(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


def test_narrate_returns_audio_and_word_timestamps():
    fake_response = {
        "audio_bytes": b"FAKEAUDIO",
        "alignment": {
            "characters": ["h", "i"],
            "character_start_times_seconds": [0.0, 0.1],
            "character_end_times_seconds": [0.1, 0.2],
        },
    }
    client = FakeTTSClient(fake_response)

    audio, timestamps = narrate("hi", client, voice_id="voice123")

    assert audio == b"FAKEAUDIO"
    assert timestamps == [{"word": "hi", "start": 0.0, "end": 0.2}]
    assert client.last_kwargs == {"voice_id": "voice123", "text": "hi"}


def test_narrate_raises_when_no_words_found():
    fake_response = {
        "audio_bytes": b"FAKEAUDIO",
        "alignment": {
            "characters": [],
            "character_start_times_seconds": [],
            "character_end_times_seconds": [],
        },
    }
    client = FakeTTSClient(fake_response)

    with pytest.raises(ValueError, match="No words"):
        narrate("", client, voice_id="voice123")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_narrate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.stages.narrate'`

- [ ] **Step 3: Write `clipforge/stages/narrate.py`**

```python
def characters_to_word_timestamps(
    characters: list, start_times: list, end_times: list
) -> list:
    words = []
    current_word = ""
    word_start = None
    prev_end = None
    for char, start, end in zip(characters, start_times, end_times):
        if char.isspace():
            if current_word:
                words.append({"word": current_word, "start": word_start, "end": prev_end})
                current_word = ""
                word_start = None
        else:
            if not current_word:
                word_start = start
            current_word += char
            prev_end = end
    if current_word:
        words.append({"word": current_word, "start": word_start, "end": prev_end})
    return words


def narrate(script_text: str, tts_client, voice_id: str):
    response = tts_client.convert_with_timestamps(voice_id=voice_id, text=script_text)
    word_timestamps = characters_to_word_timestamps(
        response["alignment"]["characters"],
        response["alignment"]["character_start_times_seconds"],
        response["alignment"]["character_end_times_seconds"],
    )
    if not word_timestamps:
        raise ValueError("No words found in narration timestamps")
    return response["audio_bytes"], word_timestamps
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_narrate.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/stages/narrate.py tests/test_narrate.py
git commit -m "feat: add narrate stage"
```

---

### Task 5: Background selection stage

**Files:**
- Create: `clipforge/stages/background.py`
- Test: `tests/test_background.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `clipforge.stages.background.get_clip_duration_seconds(clip_path: Path) -> float`.
  - `clipforge.stages.background.select_background(narration_duration: float, library_dir: Path, get_duration=get_clip_duration_seconds, rng=random) -> dict` returning `{"clip": str, "offset": float, "duration": float}`. Raises `ValueError` if `library_dir` has no `.mp4` files, or none are long enough for `narration_duration`.

- [ ] **Step 1: Write the failing tests**

`tests/test_background.py`:
```python
import random
import subprocess
from pathlib import Path

import pytest

from clipforge.stages.background import get_clip_duration_seconds, select_background


def test_get_clip_duration_seconds_parses_ffprobe_output(monkeypatch):
    class FakeCompletedProcess:
        stdout = "12.345\n"

    def fake_run(cmd, capture_output, text, check):
        return FakeCompletedProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)

    duration = get_clip_duration_seconds(Path("fake.mp4"))

    assert duration == 12.345


def test_select_background_picks_long_enough_clip(tmp_path):
    (tmp_path / "clip_short.mp4").write_bytes(b"")
    (tmp_path / "clip_long.mp4").write_bytes(b"")
    durations = {
        str(tmp_path / "clip_short.mp4"): 5.0,
        str(tmp_path / "clip_long.mp4"): 120.0,
    }

    def fake_get_duration(path):
        return durations[str(path)]

    rng = random.Random(0)

    result = select_background(
        narration_duration=30.0, library_dir=tmp_path, get_duration=fake_get_duration, rng=rng
    )

    assert result["clip"] == str(tmp_path / "clip_long.mp4")
    assert result["duration"] == 30.0
    assert 0 <= result["offset"] <= 90.0


def test_select_background_raises_when_no_clip_long_enough(tmp_path):
    (tmp_path / "clip_short.mp4").write_bytes(b"")

    with pytest.raises(ValueError, match="No clip"):
        select_background(
            narration_duration=30.0, library_dir=tmp_path, get_duration=lambda p: 5.0
        )


def test_select_background_raises_when_library_empty(tmp_path):
    with pytest.raises(ValueError, match="No gameplay clips found"):
        select_background(
            narration_duration=30.0, library_dir=tmp_path, get_duration=lambda p: 100.0
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_background.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.stages.background'`

- [ ] **Step 3: Write `clipforge/stages/background.py`**

```python
import random
import subprocess
from pathlib import Path


def get_clip_duration_seconds(clip_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokeyprefix=1",
            str(clip_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def select_background(
    narration_duration: float,
    library_dir: Path,
    get_duration=get_clip_duration_seconds,
    rng=random,
) -> dict:
    clips = sorted(library_dir.glob("*.mp4"))
    if not clips:
        raise ValueError(f"No gameplay clips found in {library_dir}")

    candidates = []
    for clip in clips:
        duration = get_duration(clip)
        if duration >= narration_duration:
            candidates.append((clip, duration))
    if not candidates:
        raise ValueError(
            f"No clip in {library_dir} is long enough for a {narration_duration:.1f}s narration"
        )

    clip, duration = rng.choice(candidates)
    max_offset = duration - narration_duration
    offset = rng.uniform(0, max_offset)
    return {"clip": str(clip), "offset": offset, "duration": narration_duration}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_background.py -v`
Expected: all four tests PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/stages/background.py tests/test_background.py
git commit -m "feat: add background selection stage"
```

---

### Task 6: Subtitles stage

**Files:**
- Create: `clipforge/stages/subtitles.py`
- Test: `tests/test_subtitles.py`

**Interfaces:**
- Consumes: word-timestamp list shaped like Task 4's `narrate()` second return value (`[{"word": str, "start": float, "end": float}, ...]`).
- Produces:
  - `clipforge.stages.subtitles.format_ass_timestamp(seconds: float) -> str` (format `H:MM:SS.cc`).
  - `clipforge.stages.subtitles.build_ass(word_timestamps: list[dict]) -> str`. Raises `ValueError` if `word_timestamps` is empty.

- [ ] **Step 1: Write the failing tests**

`tests/test_subtitles.py`:
```python
import pytest

from clipforge.stages.subtitles import build_ass, format_ass_timestamp


def test_format_ass_timestamp():
    assert format_ass_timestamp(0.0) == "0:00:00.00"
    assert format_ass_timestamp(65.5) == "0:01:05.50"
    assert format_ass_timestamp(3661.25) == "1:01:01.25"


def test_build_ass_creates_dialogue_line_per_word():
    words = [
        {"word": "hi", "start": 0.0, "end": 0.2},
        {"word": "you", "start": 0.3, "end": 0.6},
    ]

    result = build_ass(words)

    assert "Dialogue: 0,0:00:00.00,0:00:00.20,Word,HI" in result
    assert "Dialogue: 0,0:00:00.30,0:00:00.60,Word,YOU" in result
    assert "[Script Info]" in result


def test_build_ass_raises_on_empty_input():
    with pytest.raises(ValueError, match="No word timestamps"):
        build_ass([])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_subtitles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.stages.subtitles'`

- [ ] **Step 3: Write `clipforge/stages/subtitles.py`**

```python
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, BorderStyle, Outline, Alignment, MarginL, MarginR, MarginV
Style: Word,Arial,90,&H00FFFFFF,&H00000000,1,1,4,5,80,80,760

[Events]
Format: Layer, Start, End, Style, Text
"""


def format_ass_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def build_ass(word_timestamps: list) -> str:
    if not word_timestamps:
        raise ValueError("No word timestamps to build subtitles from")
    lines = [ASS_HEADER]
    for entry in word_timestamps:
        start = format_ass_timestamp(entry["start"])
        end = format_ass_timestamp(entry["end"])
        text = entry["word"].upper()
        lines.append(f"Dialogue: 0,{start},{end},Word,{text}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_subtitles.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/stages/subtitles.py tests/test_subtitles.py
git commit -m "feat: add subtitles stage"
```

---

### Task 7: Render stage

**Files:**
- Create: `clipforge/stages/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (paths only).
- Produces: `clipforge.stages.render.build_ffmpeg_command(background_clip: Path, offset: float, duration: float, narration_audio: Path, subtitles_path: Path, output_path: Path) -> list[str]` and `clipforge.stages.render.render(background_clip: Path, offset: float, duration: float, narration_audio: Path, subtitles_path: Path, output_path: Path, runner=subprocess.run) -> Path`. `runner` is any callable matching `subprocess.run`'s signature `(command, capture_output, text) -> object with .returncode, .stderr`. Raises `RuntimeError` (including ffmpeg's stderr) on non-zero return code.

- [ ] **Step 1: Write the failing tests**

`tests/test_render.py`:
```python
from pathlib import Path

import pytest

from clipforge.stages.render import build_ffmpeg_command, render


def test_build_ffmpeg_command_includes_expected_flags():
    cmd = build_ffmpeg_command(
        Path("bg.mp4"), 12.5, 30.0, Path("narration.mp3"), Path("subs.ass"), Path("out.mp4")
    )

    assert cmd[0] == "ffmpeg"
    assert cmd[cmd.index("-ss") + 1] == "12.5"
    assert cmd[cmd.index("-t") + 1] == "30.0"
    assert str(Path("out.mp4")) == cmd[-1]


class FakeResult:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def test_render_returns_output_path_on_success(tmp_path):
    output = tmp_path / "final.mp4"

    def fake_runner(command, capture_output, text):
        return FakeResult(0)

    result = render(
        Path("bg.mp4"), 0.0, 10.0, Path("n.mp3"), Path("s.ass"), output, runner=fake_runner
    )

    assert result == output


def test_render_raises_on_ffmpeg_failure(tmp_path):
    def fake_runner(command, capture_output, text):
        return FakeResult(1, stderr="ffmpeg error: bad codec")

    with pytest.raises(RuntimeError, match="ffmpeg error"):
        render(
            Path("bg.mp4"), 0.0, 10.0, Path("n.mp3"), Path("s.ass"),
            tmp_path / "out.mp4", runner=fake_runner,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.stages.render'`

- [ ] **Step 3: Write `clipforge/stages/render.py`**

```python
import subprocess
from pathlib import Path


def build_ffmpeg_command(
    background_clip: Path,
    offset: float,
    duration: float,
    narration_audio: Path,
    subtitles_path: Path,
    output_path: Path,
) -> list:
    return [
        "ffmpeg", "-y",
        "-ss", str(offset), "-t", str(duration), "-i", str(background_clip),
        "-i", str(narration_audio),
        "-filter_complex",
        f"[0:v]crop=ih*9/16:ih,scale=1080:1920,ass={subtitles_path}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac", "-shortest",
        str(output_path),
    ]


def render(
    background_clip: Path,
    offset: float,
    duration: float,
    narration_audio: Path,
    subtitles_path: Path,
    output_path: Path,
    runner=subprocess.run,
) -> Path:
    command = build_ffmpeg_command(
        background_clip, offset, duration, narration_audio, subtitles_path, output_path
    )
    result = runner(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg render failed: {result.stderr}")
    return output_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/stages/render.py tests/test_render.py
git commit -m "feat: add render stage"
```

---

### Task 8: Pipeline orchestration

**Files:**
- Create: `clipforge/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `fetch_story` (Task 2), `clean_script` (Task 3), `narrate` (Task 4), `select_background` + `get_clip_duration_seconds` (Task 5), `build_ass` (Task 6), `render` (Task 7) — imported and called by name so tests can monkeypatch them on the `clipforge.pipeline` module.
- Produces:
  - `clipforge.pipeline.extract_post_id(url: str) -> str`. Raises `ValueError` if no post ID segment is found.
  - `clipforge.pipeline.Clients` dataclass: `reddit`, `llm`, `tts` (objects), `voice_id` (str).
  - `clipforge.pipeline.run_pipeline(url: str, output_root: Path, gameplay_library: Path, clients: Clients, force: bool = False) -> Path` returning the path to `final.mp4`.

- [ ] **Step 1: Write the failing tests**

`tests/test_pipeline.py`:
```python
from pathlib import Path

import pytest

from clipforge import pipeline as pipeline_module
from clipforge.pipeline import Clients, extract_post_id, run_pipeline


def test_extract_post_id_from_standard_url():
    url = "https://www.reddit.com/r/AmItheAsshole/comments/abc123/my_post_title/"
    assert extract_post_id(url) == "abc123"


def test_extract_post_id_raises_on_invalid_url():
    with pytest.raises(ValueError, match="Could not extract"):
        extract_post_id("https://example.com/not-reddit")


def test_run_pipeline_writes_all_artifacts_and_skips_on_rerun(tmp_path, monkeypatch):
    calls = {"fetch": 0, "script": 0, "narrate": 0, "background": 0, "subtitles": 0, "render": 0}

    def fake_fetch_story(url, reddit_client):
        calls["fetch"] += 1
        return {"id": "abc123", "title": "T", "body": "B", "subreddit": "s", "url": url}

    def fake_clean_script(title, body, llm_client):
        calls["script"] += 1
        return "Cleaned script."

    def fake_narrate(script_text, tts_client, voice_id):
        calls["narrate"] += 1
        return b"AUDIO", [
            {"word": "Cleaned", "start": 0.0, "end": 0.3},
            {"word": "script.", "start": 0.4, "end": 0.8},
        ]

    def fake_select_background(narration_duration, library_dir, get_duration):
        calls["background"] += 1
        return {"clip": str(library_dir / "clip.mp4"), "offset": 1.0, "duration": narration_duration}

    def fake_build_ass(word_timestamps):
        calls["subtitles"] += 1
        return "ASS CONTENT"

    def fake_render(clip, offset, duration, narration_path, subtitles_path, output_path):
        calls["render"] += 1
        output_path.write_bytes(b"VIDEO")
        return output_path

    monkeypatch.setattr(pipeline_module, "fetch_story", fake_fetch_story)
    monkeypatch.setattr(pipeline_module, "clean_script", fake_clean_script)
    monkeypatch.setattr(pipeline_module, "narrate", fake_narrate)
    monkeypatch.setattr(pipeline_module, "select_background", fake_select_background)
    monkeypatch.setattr(pipeline_module, "build_ass", fake_build_ass)
    monkeypatch.setattr(pipeline_module, "render", fake_render)

    output_root = tmp_path / "output"
    gameplay_library = tmp_path / "assets" / "gameplay"
    gameplay_library.mkdir(parents=True)
    clients = Clients(reddit=object(), llm=object(), tts=object(), voice_id="voice1")
    url = "https://www.reddit.com/r/test/comments/abc123/title/"

    result_path = run_pipeline(url, output_root, gameplay_library, clients)

    assert result_path == output_root / "abc123" / "final.mp4"
    assert result_path.read_bytes() == b"VIDEO"
    assert calls == {"fetch": 1, "script": 1, "narrate": 1, "background": 1, "subtitles": 1, "render": 1}

    result_path_2 = run_pipeline(url, output_root, gameplay_library, clients)

    assert result_path_2 == result_path
    assert calls == {"fetch": 1, "script": 1, "narrate": 1, "background": 1, "subtitles": 1, "render": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.pipeline'`

- [ ] **Step 3: Write `clipforge/pipeline.py`**

```python
import json
import re
from dataclasses import dataclass
from pathlib import Path

from clipforge.stages.background import get_clip_duration_seconds, select_background
from clipforge.stages.fetch import fetch_story
from clipforge.stages.narrate import narrate
from clipforge.stages.render import render
from clipforge.stages.script import clean_script
from clipforge.stages.subtitles import build_ass


@dataclass
class Clients:
    reddit: object
    llm: object
    tts: object
    voice_id: str


def extract_post_id(url: str) -> str:
    match = re.search(r"/comments/([a-zA-Z0-9]+)", url)
    if not match:
        raise ValueError(f"Could not extract a post ID from URL: {url}")
    return match.group(1)


def run_pipeline(
    url: str, output_root: Path, gameplay_library: Path, clients: Clients, force: bool = False
) -> Path:
    post_id = extract_post_id(url)
    video_dir = output_root / post_id
    video_dir.mkdir(parents=True, exist_ok=True)

    story_path = video_dir / "story.json"
    if force or not story_path.exists():
        story = fetch_story(url, clients.reddit)
        story_path.write_text(json.dumps(story))
    else:
        story = json.loads(story_path.read_text())

    script_path = video_dir / "script.txt"
    if force or not script_path.exists():
        script_text = clean_script(story["title"], story["body"], clients.llm)
        script_path.write_text(script_text)
    else:
        script_text = script_path.read_text()

    narration_path = video_dir / "narration.mp3"
    timestamps_path = video_dir / "timestamps.json"
    if force or not narration_path.exists() or not timestamps_path.exists():
        audio_bytes, word_timestamps = narrate(script_text, clients.tts, clients.voice_id)
        narration_path.write_bytes(audio_bytes)
        timestamps_path.write_text(json.dumps(word_timestamps))
    else:
        word_timestamps = json.loads(timestamps_path.read_text())

    background_path = video_dir / "background.json"
    if force or not background_path.exists():
        narration_duration = word_timestamps[-1]["end"]
        selection = select_background(narration_duration, gameplay_library, get_clip_duration_seconds)
        background_path.write_text(json.dumps(selection))
    else:
        selection = json.loads(background_path.read_text())

    subtitles_path = video_dir / "subtitles.ass"
    if force or not subtitles_path.exists():
        subtitles_path.write_text(build_ass(word_timestamps))

    final_path = video_dir / "final.mp4"
    if force or not final_path.exists():
        render(
            Path(selection["clip"]), selection["offset"], selection["duration"],
            narration_path, subtitles_path, final_path,
        )
    return final_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/pipeline.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestration with skip-if-exists resumability"
```

---

### Task 9: ElevenLabs client adapter

**Files:**
- Create: `clipforge/clients.py`
- Test: `tests/test_clients.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (matches the `tts_client` shape Task 4's `narrate()` expects).
- Produces: `clipforge.clients.ElevenLabsTTSClient(api_key: str, sdk_client=None)` with method `.convert_with_timestamps(voice_id: str, text: str) -> dict` (same shape Task 4 expects). `sdk_client`, if provided, replaces the real `elevenlabs.client.ElevenLabs` instance — used for testing.

- [ ] **Step 1: Write the failing test**

`tests/test_clients.py`:
```python
import base64

from clipforge.clients import ElevenLabsTTSClient


class FakeAlignment:
    def __init__(self, characters, starts, ends):
        self.characters = characters
        self.character_start_times_seconds = starts
        self.character_end_times_seconds = ends


class FakeResult:
    def __init__(self, audio_base64, alignment):
        self.audio_base64 = audio_base64
        self.alignment = alignment


class FakeTextToSpeech:
    def __init__(self, result):
        self.result = result
        self.last_kwargs = None

    def convert_with_timestamps(self, **kwargs):
        self.last_kwargs = kwargs
        return self.result


class FakeSDKClient:
    def __init__(self, result):
        self.text_to_speech = FakeTextToSpeech(result)


def test_convert_with_timestamps_decodes_audio_and_reshapes_alignment():
    audio_b64 = base64.b64encode(b"FAKEAUDIO").decode()
    fake_result = FakeResult(
        audio_base64=audio_b64,
        alignment=FakeAlignment(["h", "i"], [0.0, 0.1], [0.1, 0.2]),
    )
    sdk_client = FakeSDKClient(fake_result)
    client = ElevenLabsTTSClient(api_key="unused", sdk_client=sdk_client)

    result = client.convert_with_timestamps(voice_id="voice1", text="hi")

    assert result["audio_bytes"] == b"FAKEAUDIO"
    assert result["alignment"] == {
        "characters": ["h", "i"],
        "character_start_times_seconds": [0.0, 0.1],
        "character_end_times_seconds": [0.1, 0.2],
    }
    assert sdk_client.text_to_speech.last_kwargs == {
        "voice_id": "voice1", "text": "hi", "model_id": "eleven_multilingual_v2",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_clients.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.clients'`

- [ ] **Step 3: Write `clipforge/clients.py`**

```python
import base64

from elevenlabs.client import ElevenLabs


class ElevenLabsTTSClient:
    def __init__(self, api_key: str, sdk_client=None):
        self._client = sdk_client if sdk_client is not None else ElevenLabs(api_key=api_key)

    def convert_with_timestamps(self, voice_id: str, text: str) -> dict:
        result = self._client.text_to_speech.convert_with_timestamps(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        return {
            "audio_bytes": base64.b64decode(result.audio_base64),
            "alignment": {
                "characters": result.alignment.characters,
                "character_start_times_seconds": result.alignment.character_start_times_seconds,
                "character_end_times_seconds": result.alignment.character_end_times_seconds,
            },
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_clients.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add clipforge/clients.py tests/test_clients.py
git commit -m "feat: add ElevenLabs TTS client adapter"
```

---

### Task 10: CLI entrypoint

**Files:**
- Create: `clipforge/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config` (Task 1), `run_pipeline` + `Clients` (Task 8), `ElevenLabsTTSClient` (Task 9), plus `praw.Reddit` and `anthropic.Anthropic` constructed directly.
- Produces: `clipforge.cli.main(argv: list[str] | None = None) -> int`. Registered as the `clipforge` console script via `pyproject.toml` (Task 1).

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:
```python
from clipforge import cli as cli_module


def _set_required_env(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "rid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "rsecret")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "ekey")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "akey")


def _stub_real_clients(monkeypatch):
    monkeypatch.setattr(cli_module.praw, "Reddit", lambda **kwargs: object())
    monkeypatch.setattr(cli_module.anthropic, "Anthropic", lambda **kwargs: object())
    monkeypatch.setattr(cli_module, "ElevenLabsTTSClient", lambda **kwargs: object())


def test_main_run_prints_done_path_on_success(tmp_path, monkeypatch, capsys):
    _set_required_env(monkeypatch)
    _stub_real_clients(monkeypatch)
    expected_path = tmp_path / "final.mp4"

    def fake_run_pipeline(url, output_root, gameplay_library, clients, force=False):
        return expected_path

    monkeypatch.setattr(cli_module, "run_pipeline", fake_run_pipeline)

    exit_code = cli_module.main(["run", "https://www.reddit.com/r/test/comments/abc123/x/"])

    assert exit_code == 0
    assert f"Done: {expected_path}" in capsys.readouterr().out


def test_main_run_prints_error_and_returns_1_on_failure(monkeypatch, capsys):
    _set_required_env(monkeypatch)
    _stub_real_clients(monkeypatch)

    def fake_run_pipeline(url, output_root, gameplay_library, clients, force=False):
        raise RuntimeError("ffmpeg render failed: boom")

    monkeypatch.setattr(cli_module, "run_pipeline", fake_run_pipeline)

    exit_code = cli_module.main(["run", "https://www.reddit.com/r/test/comments/abc123/x/"])

    assert exit_code == 1
    assert "Error: ffmpeg render failed: boom" in capsys.readouterr().err


def test_main_run_returns_1_when_env_vars_missing(monkeypatch, capsys):
    for var in [
        "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "ELEVENLABS_API_KEY",
        "ELEVENLABS_VOICE_ID", "ANTHROPIC_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)

    exit_code = cli_module.main(["run", "https://www.reddit.com/r/test/comments/abc123/x/"])

    assert exit_code == 1
    assert "Missing required environment variables" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'clipforge.cli'`

- [ ] **Step 3: Write `clipforge/cli.py`**

```python
import argparse
import sys
from pathlib import Path

import anthropic
import praw

from clipforge.clients import ElevenLabsTTSClient
from clipforge.config import load_config
from clipforge.pipeline import Clients, run_pipeline

DEFAULT_OUTPUT_ROOT = Path("output")
DEFAULT_GAMEPLAY_LIBRARY = Path("assets/gameplay")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="clipforge")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Generate a video from a Reddit post URL")
    run_parser.add_argument("url")
    run_parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            config = load_config()
            reddit_client = praw.Reddit(
                client_id=config.reddit_client_id,
                client_secret=config.reddit_client_secret,
                user_agent="clipforge/0.1",
            )
            llm_client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            tts_client = ElevenLabsTTSClient(api_key=config.elevenlabs_api_key)
            clients = Clients(
                reddit=reddit_client, llm=llm_client, tts=tts_client, voice_id=config.elevenlabs_voice_id
            )
            final_path = run_pipeline(
                args.url, DEFAULT_OUTPUT_ROOT, DEFAULT_GAMEPLAY_LIBRARY, clients, force=args.force
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Done: {final_path}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: every test across all modules PASSES.

- [ ] **Step 6: Write the quickstart README**

`README.md`:
```markdown
# ClipForge

AI pipeline converting Reddit stories into portrait short-form videos (YT Shorts) with gameplay background, TTS narration, and word-by-word subtitles.

## Setup

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env` and fill in `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `ANTHROPIC_API_KEY`.
4. Install `ffmpeg` (provides both `ffmpeg` and `ffprobe`) and make sure it's on your `PATH`.
5. Drop one or more gameplay `.mp4` files into `assets/gameplay/`.

## Usage

```bash
clipforge run https://www.reddit.com/r/AmItheAsshole/comments/<id>/<slug>/
```

Output is written to `output/<post-id>/final.mp4`. Rerunning the same URL skips stages whose artifacts already exist; pass `--force` to redo every stage.

## Manual smoke test

Automated tests mock every external API. Before considering a pipeline change done, run it once against a real short Reddit post end-to-end and visually check `final.mp4` — this is the only way to catch real API/ffmpeg integration issues, and it costs real ElevenLabs credits, so don't automate it.
```

- [ ] **Step 7: Commit**

```bash
git add clipforge/cli.py tests/test_cli.py README.md
git commit -m "feat: add CLI entrypoint and quickstart docs"
```

---

## Self-Review Notes

- **Spec coverage:** fetch → Task 2; script cleanup → Task 3; narrate + ElevenLabs timestamps → Task 4 + Task 9; background selection → Task 5; subtitles → Task 6; render/audio-mix/mute → Task 7; skip-if-exists resumable orchestration → Task 8; secrets/config validation → Task 1; CLI + manual smoke-test documentation → Task 10. No spec section is uncovered.
- **Placeholder scan:** no TBD/TODO markers; every step has complete code and exact commands.
- **Type consistency:** `narrate()`'s `(bytes, list[dict])` return matches how `pipeline.py` unpacks it; `select_background()`'s `{"clip", "offset", "duration"}` dict matches what `render()` is called with in `pipeline.py`; `Clients` fields (`reddit`, `llm`, `tts`, `voice_id`) match both `test_pipeline.py`'s construction and `cli.py`'s construction.
