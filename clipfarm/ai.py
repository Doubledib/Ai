"""Titles and captions. Uses Claude when credentials exist; otherwise a plain template."""
from __future__ import annotations

import json

MODEL = "claude-opus-5-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "caption": {"type": "string"},
        "keep": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["title", "caption", "keep", "reason"],
    "additionalProperties": False,
}

PROMPT = """You package short-form gaming clips for the channel "{brand}" (angle: {angle}).
The clip is from {credit}'s stream "{video_title}". Transcript of the moment:

<transcript>
{text}
</transcript>

Write a title (max 60 characters, no clickbait the clip doesn't deliver, no ALL CAPS) and a
1-2 sentence caption that credits {credit} and ends with 3-4 relevant hashtags.
Set keep=false if the transcript shows nothing a viewer would care about, contains slurs or
harassment, or spoils a story ending/cutscene (publisher policy removes those); explain in reason."""


def fallback(credit: str, video_title: str) -> dict:
    who = credit or "the stream"
    return {"title": f"{who}: {video_title}"[:60], "keep": True, "reason": "no-llm",
            "caption": f"From {who}'s stream. #gta6 #gta #gaming #clips"}


def package(text: str, credit: str, video_title: str, brand: str = "", angle: str = "") -> dict:
    if not text.strip():
        return fallback(credit, video_title)
    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",   # reroute instead of failing if a classifier declines
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": PROMPT.format(
                brand=brand, angle=angle, credit=credit or "the streamer",
                video_title=video_title, text=text)}],
        )
        if resp.stop_reason != "end_turn":
            return fallback(credit, video_title)
        return json.loads(next(b.text for b in resp.content if b.type == "text"))
    except Exception as e:  # no credentials, no network, SDK missing: stay operational
        print(f"[ai] template fallback: {type(e).__name__}")
        return fallback(credit, video_title)
