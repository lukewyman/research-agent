import json, textwrap
from typing import List, Tuple
from openai import OpenAI
from newsrag_core.config import OPENAI_API_KEY, LLM_MODEL
from newsrag_core.models import VerificationOutput
from pydantic import ValidationError

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM = """You verify claims against the provided evidence snippets labeled [1], [2], ...
Return STRICT JSON:
{
  "results": [
    { "claim": string, "status": "supported"|"contested"|"insufficient", "evidence_ids": [int] }
  ]
}
Adjudication rules:
- 'supported' only if at least one snippet clearly entails the claim.
- 'contested' if some snippet contradicts it.
- 'insufficient' if none clearly support it.
- Cite snippet ids via their numbers (e.g., [2, 5]).
- Be conservative: prefer 'insufficient' when unsure.
"""

def _label_context(hits: List[Tuple[dict, float]] , max_chars_per_snippet: int = 700) -> str:
    parts = []
    for i, (m, _) in enumerate(hits, 1):
        snippet = (m.get("text") or "").replace("\n"," ")
        snippet = textwrap.shorten(snippet, width=max_chars_per_snippet, placeholder="…")
        parts.append(f"[{i}] {snippet}")
    return "\n\n".join(parts)

def verify_claims(claims: List[str], hits: List[Tuple[dict, float]]) -> dict:
    if not claims:
        return {"results": []}
    labeled = _label_context(hits)
    user_payload = {"claims": claims, "evidence": labeled}

    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":json.dumps(user_payload)},
    ]

    for attempt in range(2):
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,
            response_format={"type":"json_object"},
            messages=messages,
        )
        content = resp.choices[0].message.content
        try:
            obj = VerificationOutput.model_validate_json(content)
            return obj.model_dump()
        except ValidationError as e:
            messages.append({
                "role":"system",
                "content": f"Your last JSON failed validation: {e}. "
                           f"Output valid JSON only, matching the schema exactly."
            })

    return {"error":"Failed to produce valid Verification JSON","raw":content}
