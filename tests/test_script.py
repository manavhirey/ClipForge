import pytest

from clipforge.stages.script import clean_script


class FakeContent:
    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, text):
        self.content = [FakeContent(text)]


class FakeMessages:
    def __init__(self, response_text):
        self.response_text = response_text
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self.response_text)


class FakeLLMClient:
    def __init__(self, response_text):
        self.messages = FakeMessages(response_text)


def test_clean_script_returns_llm_text():
    client = FakeLLMClient("Cleaned narration text.")

    result = clean_script("Title", "Body text", client)

    assert result == "Cleaned narration text."
    assert "Title" in client.messages.last_kwargs["messages"][0]["content"]
    assert "Body text" in client.messages.last_kwargs["messages"][0]["content"]


def test_clean_script_raises_on_empty_response():
    client = FakeLLMClient("   ")

    with pytest.raises(ValueError, match="empty script"):
        clean_script("Title", "Body text", client)
