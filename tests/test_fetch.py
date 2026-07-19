import pytest

from clipforge.stages.fetch import fetch_story


class FakeResponse:
    def __init__(self, status_code, json_data=None, raise_on_json=False):
        self.status_code = status_code
        self._json_data = json_data
        self._raise_on_json = raise_on_json

    def json(self):
        if self._raise_on_json:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._json_data


def _reddit_payload(id="abc123", title="My Story", selftext="Once upon a time...", subreddit="AmItheAsshole"):
    return [
        {"data": {"children": [{"data": {
            "id": id, "title": title, "selftext": selftext, "subreddit": subreddit,
        }}]}},
        {"data": {"children": []}},
    ]


def test_fetch_story_returns_expected_fields():
    captured = {}

    def fake_http_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse(200, _reddit_payload())

    url = "https://www.reddit.com/r/AmItheAsshole/comments/abc123/my_story/"
    result = fetch_story(url, http_get=fake_http_get)

    assert result == {
        "id": "abc123",
        "title": "My Story",
        "body": "Once upon a time...",
        "subreddit": "AmItheAsshole",
        "url": url,
    }
    assert captured["url"] == url.rstrip("/") + ".json"
    assert "User-Agent" in captured["headers"]


def test_fetch_story_strips_trailing_slash_before_appending_json():
    def fake_http_get(url, headers, timeout):
        assert url == "https://www.reddit.com/r/test/comments/abc123/x.json"
        return FakeResponse(200, _reddit_payload())

    fetch_story("https://www.reddit.com/r/test/comments/abc123/x/", http_get=fake_http_get)


def test_fetch_story_raises_on_no_selftext():
    def fake_http_get(url, headers, timeout):
        return FakeResponse(200, _reddit_payload(selftext=""))

    with pytest.raises(ValueError, match="no text body"):
        fetch_story("https://reddit.com/r/pics/comments/abc123/img/", http_get=fake_http_get)


def test_fetch_story_raises_on_non_200_status():
    def fake_http_get(url, headers, timeout):
        return FakeResponse(403)

    with pytest.raises(ValueError, match="403"):
        fetch_story("https://reddit.com/r/test/comments/abc123/x/", http_get=fake_http_get)


def test_fetch_story_raises_on_non_json_response():
    def fake_http_get(url, headers, timeout):
        return FakeResponse(200, raise_on_json=True)

    with pytest.raises(ValueError, match="did not return JSON"):
        fetch_story("https://reddit.com/r/test/comments/abc123/x/", http_get=fake_http_get)
