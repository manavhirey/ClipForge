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
