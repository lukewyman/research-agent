from typing import List, Literal
from pydantic import BaseModel, Field

class Summary(BaseModel):
    tldr: str
    bullets: List[str] = Field(min_items=3, max_items=3)
    evidence: dict | None = None  # {"quote": str, "note": str} if present

class GroundedSummary(BaseModel):
    # Used by the Phase-2 synthesis that cites [ids]
    tldr: str
    bullets: List[str] = Field(min_items=3, max_items=3)
    used_ids: List[int] = Field(default_factory=list)

class VerificationResult(BaseModel):
    claim: str
    status: Literal["supported", "contested", "insufficient"]
    evidence_ids: List[int] = Field(default_factory=list)

class VerificationOutput(BaseModel):
    results: List[VerificationResult]
