from clipforge import cli as cli_module


def _set_required_env(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "rid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "rsecret")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "ekey")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "akey")


def _stub_real_clients(monkeypatch):
    monkeypatch.setattr(cli_module.praw, "Reddit", lambda **kwargs: object())
    monkeypatch.setattr(cli_module.anthropic, "Anthropic", lambda **kwargs: object())
    monkeypatch.setattr(cli_module, "ElevenLabsTTSClient", lambda **kwargs: object())


def test_main_run_prints_done_path_on_success(tmp_path, monkeypatch, capsys):
    _set_required_env(monkeypatch)
    _stub_real_clients(monkeypatch)
    expected_path = tmp_path / "final.mp4"

    def fake_run_pipeline(url, output_root, gameplay_library, clients, force=False):
        return expected_path

    monkeypatch.setattr(cli_module, "run_pipeline", fake_run_pipeline)

    exit_code = cli_module.main(["run", "https://www.reddit.com/r/test/comments/abc123/x/"])

    assert exit_code == 0
    assert f"Done: {expected_path}" in capsys.readouterr().out


def test_main_run_with_text_file_calls_run_pipeline_from_text(tmp_path, monkeypatch, capsys):
    _set_required_env(monkeypatch)
    _stub_real_clients(monkeypatch)
    text_file = tmp_path / "story.txt"
    text_file.write_text("My Story\nOnce upon a time...")
    expected_path = tmp_path / "final.mp4"
    captured = {}

    def fake_run_pipeline_from_text(text, output_root, gameplay_library, clients, force=False):
        captured["text"] = text
        return expected_path

    monkeypatch.setattr(cli_module, "run_pipeline_from_text", fake_run_pipeline_from_text)

    exit_code = cli_module.main(["run", "--text-file", str(text_file)])

    assert exit_code == 0
    assert captured["text"] == "My Story\nOnce upon a time..."
    assert f"Done: {expected_path}" in capsys.readouterr().out


def test_main_run_returns_1_when_neither_url_nor_text_file_given(monkeypatch, capsys):
    _set_required_env(monkeypatch)
    _stub_real_clients(monkeypatch)

    exit_code = cli_module.main(["run"])

    assert exit_code == 1
    assert "exactly one" in capsys.readouterr().err


def test_main_run_returns_1_when_both_url_and_text_file_given(tmp_path, monkeypatch, capsys):
    _set_required_env(monkeypatch)
    _stub_real_clients(monkeypatch)
    text_file = tmp_path / "story.txt"
    text_file.write_text("My Story\nOnce upon a time...")

    exit_code = cli_module.main([
        "run", "https://www.reddit.com/r/test/comments/abc123/x/", "--text-file", str(text_file),
    ])

    assert exit_code == 1
    assert "exactly one" in capsys.readouterr().err


def test_main_run_prints_error_and_returns_1_on_failure(monkeypatch, capsys):
    _set_required_env(monkeypatch)
    _stub_real_clients(monkeypatch)

    def fake_run_pipeline(url, output_root, gameplay_library, clients, force=False):
        raise RuntimeError("ffmpeg render failed: boom")

    monkeypatch.setattr(cli_module, "run_pipeline", fake_run_pipeline)

    exit_code = cli_module.main(["run", "https://www.reddit.com/r/test/comments/abc123/x/"])

    assert exit_code == 1
    assert "Error: ffmpeg render failed: boom" in capsys.readouterr().err


def test_main_run_returns_1_when_env_vars_missing(tmp_path, monkeypatch, capsys):
    for var in [
        "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "ELEVENLABS_API_KEY",
        "ELEVENLABS_VOICE_ID", "ANTHROPIC_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)

    exit_code = cli_module.main(["run", "https://www.reddit.com/r/test/comments/abc123/x/"])

    assert exit_code == 1
    assert "Missing required environment variables" in capsys.readouterr().err


def test_main_run_loads_dotenv_file(tmp_path, monkeypatch, capsys):
    for var in [
        "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "ELEVENLABS_API_KEY",
        "ELEVENLABS_VOICE_ID", "ANTHROPIC_API_KEY",
    ]:
        monkeypatch.setenv(var, "placeholder")
        monkeypatch.delenv(var)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "REDDIT_CLIENT_ID=rid\n"
        "REDDIT_CLIENT_SECRET=rsecret\n"
        "ELEVENLABS_API_KEY=ekey\n"
        "ELEVENLABS_VOICE_ID=voice1\n"
        "ANTHROPIC_API_KEY=akey\n"
    )
    monkeypatch.chdir(tmp_path)

    _stub_real_clients(monkeypatch)
    expected_path = tmp_path / "final.mp4"

    def fake_run_pipeline(url, output_root, gameplay_library, clients, force=False):
        return expected_path

    monkeypatch.setattr(cli_module, "run_pipeline", fake_run_pipeline)

    exit_code = cli_module.main(["run", "https://www.reddit.com/r/test/comments/abc123/x/"])

    assert exit_code == 0
    assert f"Done: {expected_path}" in capsys.readouterr().out
