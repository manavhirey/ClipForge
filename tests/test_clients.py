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
