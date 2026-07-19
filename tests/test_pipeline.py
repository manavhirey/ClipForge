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
