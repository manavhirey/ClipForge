import json
import re
from dataclasses import dataclass
from pathlib import Path

from clipforge.stages.background import get_clip_duration_seconds, select_background
from clipforge.stages.fetch import fetch_story, fetch_story_from_text
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


def _run_pipeline_stages(
    post_id: str, fetch, output_root: Path, gameplay_library: Path, clients: Clients, force: bool
) -> Path:
    video_dir = output_root / post_id
    video_dir.mkdir(parents=True, exist_ok=True)

    story_path = video_dir / "story.json"
    if force or not story_path.exists():
        story = fetch()
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
        temp_path = video_dir / "final.tmp.mp4"
        try:
            render(
                Path(selection["clip"]), selection["offset"], selection["duration"],
                narration_path, subtitles_path, temp_path,
            )
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        temp_path.replace(final_path)
    return final_path


def run_pipeline(
    url: str, output_root: Path, gameplay_library: Path, clients: Clients, force: bool = False
) -> Path:
    post_id = extract_post_id(url)
    return _run_pipeline_stages(
        post_id, lambda: fetch_story(url, clients.reddit), output_root, gameplay_library, clients, force,
    )


def run_pipeline_from_text(
    text: str, output_root: Path, gameplay_library: Path, clients: Clients, force: bool = False
) -> Path:
    story = fetch_story_from_text(text)
    return _run_pipeline_stages(
        story["id"], lambda: story, output_root, gameplay_library, clients, force,
    )
