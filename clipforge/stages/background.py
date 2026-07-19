import random
import subprocess
from pathlib import Path


def get_clip_duration_seconds(clip_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
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
