import json
from openai import OpenAI
from .config import OPENAI_API_KEY, LLM_MODEL
from .models import Summary
from pydantic import ValidationError

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM = """You are a careful, factual summarizer.
Return STRICT JSON:
{
  "tldr": string,
  "bullets": [string, string, string],
  "evidence": { "quote": string, "note": string } | null
}
Use only the provided text. Do not add unsupported facts.
"""

def summarize(article_text: str, *, source_url: str | None = None) -> dict:
    excerpt = article_text[:8000]
    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":f"Source URL: {source_url or 'N/A'}\n\n{excerpt}"}
    ]

    # retry-on-parse-fail once with the validation error as guidance
    for attempt in range(2):
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=messages,
        )
        content = resp.choices[0].message.content
        try:
            obj = Summary.model_validate_json(content)
            return obj.model_dump()
        except ValidationError as e:
            # Add a gentle fix-up instruction and retry once
            messages.append({
                "role":"system",
                "content": f"Your last JSON failed validation: {e}. "
                           f"Output valid JSON only, matching the schema exactly."
            })

    # last resort: return raw for visibility
    return {"error":"Failed to produce valid Summary JSON","raw":content}
