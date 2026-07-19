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
