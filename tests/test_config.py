import pytest

from clipforge.config import load_config


def test_load_config_reads_all_vars():
    env = {
        "REDDIT_CLIENT_ID": "rid",
        "REDDIT_CLIENT_SECRET": "rsecret",
        "ELEVENLABS_API_KEY": "ekey",
        "ELEVENLABS_VOICE_ID": "voice1",
        "ANTHROPIC_API_KEY": "akey",
    }

    config = load_config(env)

    assert config.reddit_client_id == "rid"
    assert config.reddit_client_secret == "rsecret"
    assert config.elevenlabs_api_key == "ekey"
    assert config.elevenlabs_voice_id == "voice1"
    assert config.anthropic_api_key == "akey"


def test_load_config_raises_on_missing_vars():
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        load_config({"REDDIT_CLIENT_ID": "rid"})


def test_load_config_does_not_require_reddit_vars_when_require_reddit_is_false():
    env = {
        "ELEVENLABS_API_KEY": "ekey",
        "ELEVENLABS_VOICE_ID": "voice1",
        "ANTHROPIC_API_KEY": "akey",
    }

    config = load_config(env, require_reddit=False)

    assert config.reddit_client_id is None
    assert config.reddit_client_secret is None
    assert config.elevenlabs_api_key == "ekey"


def test_load_config_still_requires_reddit_vars_by_default():
    env = {
        "ELEVENLABS_API_KEY": "ekey",
        "ELEVENLABS_VOICE_ID": "voice1",
        "ANTHROPIC_API_KEY": "akey",
    }

    with pytest.raises(ValueError, match="REDDIT_CLIENT_ID"):
        load_config(env)
