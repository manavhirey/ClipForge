import pytest

from clipforge.config import load_config


def test_load_config_reads_all_vars():
    env = {
        "ELEVENLABS_API_KEY": "ekey",
        "ELEVENLABS_VOICE_ID": "voice1",
        "ANTHROPIC_API_KEY": "akey",
    }

    config = load_config(env)

    assert config.elevenlabs_api_key == "ekey"
    assert config.elevenlabs_voice_id == "voice1"
    assert config.anthropic_api_key == "akey"


def test_load_config_raises_on_missing_vars():
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        load_config({"ELEVENLABS_API_KEY": "ekey"})
