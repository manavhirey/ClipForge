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
