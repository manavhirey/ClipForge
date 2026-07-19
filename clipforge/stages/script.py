SYSTEM_PROMPT = (
    "You turn Reddit posts into spoken-narration scripts for a short-form video. "
    "Strip Reddit-specific formatting (markdown, 'EDIT:', 'UPDATE:', flair tags like 'AITA'), "
    "and lightly adjust phrasing so it reads naturally when read aloud. "
    "Stay faithful to the original story — do not add, remove, or embellish plot details. "
    "Output only the narration script, nothing else."
)


def clean_script(title: str, body: str, llm_client) -> str:
    response = llm_client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Title: {title}\n\nBody:\n{body}"}],
    )
    if response.stop_reason == "max_tokens":
        raise ValueError("LLM response was truncated (hit max_tokens) before completing the script")
    text = next(
        (block.text for block in response.content if getattr(block, "type", None) == "text"),
        "",
    ).strip()
    if not text:
        raise ValueError("LLM returned an empty script")
    return text
