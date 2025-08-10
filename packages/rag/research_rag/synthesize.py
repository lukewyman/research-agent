import json
from openai import OpenAI
from research_core.config import OPENAI_API_KEY, LLM_MODEL
from research_core.models import GroundedSummary
from pydantic import ValidationError

# LangChain for schema-shaped instructions
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

client = OpenAI(api_key=OPENAI_API_KEY)

# Define the output schema for the LLM
schemas = [
    ResponseSchema(name="tldr", description="One sentence answer with [id] citations"),
    ResponseSchema(name="bullets", description="List of 3 concise bullets, each with [id] citations"),
    ResponseSchema(name="used_ids", description="Array of distinct integers for cited snippet ids"),
]
parser = StructuredOutputParser.from_response_schemas(schemas)
FORMAT_INSTRUCTIONS = parser.get_format_instructions()

SYSTEM = """You are a careful, grounded synthesizer.
You will receive a QUESTION and EVIDENCE CHUNKS labeled [1], [2], ...
Rules:
- Use ONLY the information in these chunks.
- Every factual sentence MUST include at least one bracket citation like [2].
- If something isn't supported, write 'insufficient evidence'.
Return JSON exactly matching the given format instructions.
"""

def synthesize(question: str, labeled_context: str) -> dict:
    messages = [
        {"role":"system","content":SYSTEM},
        {"role":"user","content":(
            "QUESTION:\n" + question +
            "\n\nEVIDENCE:\n" + labeled_context +
            "\n\n" + FORMAT_INSTRUCTIONS
        )},
    ]

    for attempt in range(2):
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0,
            response_format={"type":"json_object"},
            messages=messages,
        )
        content = resp.choices[0].message.content
        # First parse via LangChain (tolerant), then validate with Pydantic (strict).
        try:
            parsed = parser.parse(content)  # dict-like
            obj = GroundedSummary.model_validate(parsed)
            return obj.model_dump()
        except (ValidationError, Exception) as e:
            messages.append({
                "role":"system",
                "content": f"Your last output failed schema validation: {e}. "
                           f"Regenerate valid JSON matching the format instructions exactly."
            })

    return {"error":"Failed to produce valid GroundedSummary JSON","raw":content}
