from urllib.parse import urlsplit, urlunsplit

import requests

USER_AGENT = "clipforge/0.1 (personal use, non-commercial)"
REMOVED_PLACEHOLDERS = {"[removed]", "[deleted]"}


def _to_json_url(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    if not path.endswith(".json"):
        path += ".json"
    return urlunsplit((parts.scheme, parts.netloc, path, "raw_json=1", ""))


def fetch_story(url: str, http_get=requests.get) -> dict:
    json_url = _to_json_url(url)
    response = http_get(json_url, headers={"User-Agent": USER_AGENT}, timeout=10)
    if response.status_code != 200:
        raise ValueError(
            f"Reddit request failed with status {response.status_code} for {url} "
            "(Reddit may be blocking automated requests from this network)"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError(
            f"Reddit did not return JSON for {url} "
            "(likely blocked/rate-limited and served an HTML page instead)"
        ) from exc

    try:
        post = data[0]["data"]["children"][0]["data"]
        body = post.get("selftext", "")
        result = {
            "id": post["id"],
            "title": post["title"],
            "body": body,
            "subreddit": post["subreddit"],
            "url": url,
        }
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError(f"Reddit returned JSON in an unexpected shape for {url}") from exc

    if not body or body in REMOVED_PLACEHOLDERS:
        raise ValueError(f"Post at {url} has no text body (not a text post, or removed/deleted)")
    return result
