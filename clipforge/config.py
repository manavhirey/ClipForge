import os
from dataclasses import dataclass
from typing import Mapping

REQUIRED_VARS = [
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ANTHROPIC_API_KEY",
]


@dataclass
class Config:
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    anthropic_api_key: str


def load_config(env: Mapping[str, str] = os.environ) -> Config:
    missing = [name for name in REQUIRED_VARS if not env.get(name)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return Config(
        elevenlabs_api_key=env["ELEVENLABS_API_KEY"],
        elevenlabs_voice_id=env["ELEVENLABS_VOICE_ID"],
        anthropic_api_key=env["ANTHROPIC_API_KEY"],
    )
