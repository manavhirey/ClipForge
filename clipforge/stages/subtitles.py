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
