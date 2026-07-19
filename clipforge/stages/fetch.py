import hashlib


def fetch_story(url: str, reddit_client) -> dict:
    submission = reddit_client.submission(url=url)
    if not submission.selftext:
        raise ValueError(f"Post at {url} has no text body (not a text post)")
    return {
        "id": submission.id,
        "title": submission.title,
        "body": submission.selftext,
        "subreddit": str(submission.subreddit),
        "url": url,
    }


def fetch_story_from_text(text: str) -> dict:
    lines = text.strip().splitlines()
    if not lines:
        raise ValueError("Text is empty")

    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    if not title:
        raise ValueError("Text is empty")
    if not body:
        raise ValueError("Text has a title but no body (add at least one more line of story text)")

    story_id = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return {
        "id": story_id,
        "title": title,
        "body": body,
        "subreddit": None,
        "url": None,
    }
