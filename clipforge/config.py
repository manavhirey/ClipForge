import os
from dataclasses import dataclass
from typing import Mapping, Optional

ALWAYS_REQUIRED_VARS = [
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_VOICE_ID",
    "ANTHROPIC_API_KEY",
]
REDDIT_VARS = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]


@dataclass
class Config:
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    anthropic_api_key: str
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None


def load_config(env: Mapping[str, str] = os.environ, require_reddit: bool = True) -> Config:
    required = ALWAYS_REQUIRED_VARS + (REDDIT_VARS if require_reddit else [])
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    return Config(
        elevenlabs_api_key=env["ELEVENLABS_API_KEY"],
        elevenlabs_voice_id=env["ELEVENLABS_VOICE_ID"],
        anthropic_api_key=env["ANTHROPIC_API_KEY"],
        reddit_client_id=env.get("REDDIT_CLIENT_ID"),
        reddit_client_secret=env.get("REDDIT_CLIENT_SECRET"),
    )
