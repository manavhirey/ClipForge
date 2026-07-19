import requests

USER_AGENT = "clipforge/0.1 (personal use, non-commercial)"


def fetch_story(url: str, http_get=requests.get) -> dict:
    json_url = url.rstrip("/") + ".json"
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

    post = data[0]["data"]["children"][0]["data"]
    body = post.get("selftext", "")
    if not body:
        raise ValueError(f"Post at {url} has no text body (not a text post)")
    return {
        "id": post["id"],
        "title": post["title"],
        "body": body,
        "subreddit": post["subreddit"],
        "url": url,
    }
