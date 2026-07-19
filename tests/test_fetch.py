import pytest

from clipforge.stages.fetch import fetch_story, fetch_story_from_text


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


def test_fetch_story_from_text_splits_title_from_body():
    result = fetch_story_from_text("My Story\nOnce upon a time...\nThe end.")

    assert result["title"] == "My Story"
    assert result["body"] == "Once upon a time...\nThe end."
    assert result["subreddit"] is None
    assert result["url"] is None


def test_fetch_story_from_text_skips_blank_line_separator():
    result = fetch_story_from_text("My Story\n\nOnce upon a time...")

    assert result["title"] == "My Story"
    assert result["body"] == "Once upon a time..."


def test_fetch_story_from_text_id_is_deterministic_and_hash_like():
    result_a = fetch_story_from_text("My Story\nOnce upon a time...")
    result_b = fetch_story_from_text("My Story\nOnce upon a time...")
    result_c = fetch_story_from_text("A Different Story\nSomething else entirely.")

    assert result_a["id"] == result_b["id"]
    assert result_a["id"] != result_c["id"]
    assert len(result_a["id"]) == 12
    assert all(c in "0123456789abcdef" for c in result_a["id"])


def test_fetch_story_from_text_raises_on_empty_text():
    with pytest.raises(ValueError, match="empty"):
        fetch_story_from_text("")

    with pytest.raises(ValueError, match="empty"):
        fetch_story_from_text("   \n  \n")


def test_fetch_story_from_text_raises_on_title_only_no_body():
    with pytest.raises(ValueError, match="no body"):
        fetch_story_from_text("Just a title, no story")
