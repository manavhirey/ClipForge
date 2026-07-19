import base64

from elevenlabs.client import ElevenLabs


class ElevenLabsTTSClient:
    def __init__(self, api_key: str, sdk_client=None):
        self._client = sdk_client if sdk_client is not None else ElevenLabs(api_key=api_key)

    def convert_with_timestamps(self, voice_id: str, text: str) -> dict:
        result = self._client.text_to_speech.convert_with_timestamps(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        return {
            "audio_bytes": base64.b64decode(result.audio_base_64),
            "alignment": {
                "characters": result.alignment.characters,
                "character_start_times_seconds": result.alignment.character_start_times_seconds,
                "character_end_times_seconds": result.alignment.character_end_times_seconds,
            },
        }
