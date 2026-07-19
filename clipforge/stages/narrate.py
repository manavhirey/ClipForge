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
