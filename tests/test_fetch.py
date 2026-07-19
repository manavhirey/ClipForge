import pytest

from clipforge.stages.fetch import fetch_story


class FakeSubmission:
    def __init__(self, id, title, selftext, subreddit):
        self.id = id
        self.title = title
        self.selftext = selftext
        self.subreddit = subreddit


class FakeRedditClient:
    def __init__(self, submission):
        self._submission = submission

    def submission(self, url):
        return self._submission


def test_fetch_story_returns_expected_fields():
    fake_sub = FakeSubmission(
        id="abc123", title="My Story", selftext="Once upon a time...", subreddit="AmItheAsshole"
    )
    client = FakeRedditClient(fake_sub)

    result = fetch_story("https://reddit.com/r/AmItheAsshole/comments/abc123/my_story/", client)

    assert result == {
        "id": "abc123",
        "title": "My Story",
        "body": "Once upon a time...",
        "subreddit": "AmItheAsshole",
        "url": "https://reddit.com/r/AmItheAsshole/comments/abc123/my_story/",
    }


def test_fetch_story_raises_on_no_selftext():
    fake_sub = FakeSubmission(id="abc123", title="Image post", selftext="", subreddit="pics")
    client = FakeRedditClient(fake_sub)

    with pytest.raises(ValueError, match="no text body"):
        fetch_story("https://reddit.com/r/pics/comments/abc123/img/", client)
