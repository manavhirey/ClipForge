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
