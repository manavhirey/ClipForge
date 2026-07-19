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
