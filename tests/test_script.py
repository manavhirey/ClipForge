import pytest

from clipforge.stages.script import clean_script, SYSTEM_PROMPT


class FakeBlock:
    def __init__(self, type, text=None):
        self.type = type
        self.text = text


class FakeResponse:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self.response


class FakeLLMClient:
    def __init__(self, response):
        self.messages = FakeMessages(response)


def _text_response(text, stop_reason="end_turn"):
    return FakeResponse([FakeBlock("text", text)], stop_reason=stop_reason)


def test_clean_script_returns_llm_text():
    client = FakeLLMClient(_text_response("Cleaned narration text."))

    result = clean_script("My Distinctive Roommate Story", "Body text", client)

    assert result == "Cleaned narration text."
    assert "My Distinctive Roommate Story" in client.messages.last_kwargs["messages"][0]["content"]
    assert "Body text" in client.messages.last_kwargs["messages"][0]["content"]
    assert client.messages.last_kwargs["system"] == SYSTEM_PROMPT


def test_system_prompt_instructs_narrating_the_title_first():
    assert "begin the script by narrating the title" in SYSTEM_PROMPT
    assert "Do not invent your own opening hook" in SYSTEM_PROMPT


def test_system_prompt_addresses_title_flair_and_duplicate_body_line():
    assert "AITA" in SYSTEM_PROMPT
    assert "expand it naturally" in SYSTEM_PROMPT
    assert "narrate it once" in SYSTEM_PROMPT


def test_clean_script_raises_on_empty_response():
    client = FakeLLMClient(_text_response("   "))

    with pytest.raises(ValueError, match="empty script"):
        clean_script("Title", "Body text", client)


def test_clean_script_skips_leading_thinking_block():
    response = FakeResponse([
        FakeBlock("thinking", text=None),
        FakeBlock("text", text="Cleaned narration text."),
    ])
    client = FakeLLMClient(response)

    result = clean_script("Title", "Body text", client)

    assert result == "Cleaned narration text."


def test_clean_script_raises_on_max_tokens_truncation():
    client = FakeLLMClient(_text_response("Truncated mid-sent", stop_reason="max_tokens"))

    with pytest.raises(ValueError, match="truncated"):
        clean_script("Title", "Body text", client)
