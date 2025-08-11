from typing import List, Literal, Optional, Any
from pydantic import BaseModel, Field

class IngestRequest(BaseModel):
    corpus_id: str = Field(min_length=1)
    urls: List[str] = Field(min_items=1)

class IngestResponse(BaseModel):
    corpus_id: str
    chunks_indexed: int

class QueryRequest(BaseModel):
    corpus_id: str
    question: str
    retriever: Literal["hybrid", "vector"] = "hybrid"
    k: int = 6
    max_per_url: int = 2
    alpha: float = 0.6  # hybrid mixing weight

class SourceItem(BaseModel):
    id: int
    url: str
    chunk: int
    score: float

class AnswerResponse(BaseModel):
    tldr: str
    bullets: List[str]
    sources: List[SourceItem]
    verification: Optional[List[dict]] = None

class JobSubmissionResponse(BaseModel):
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    state: Literal["PENDING","STARTED","PROGRESS","SUCCESS","FAILURE","RETRY","REVOKED"]
    progress: Optional[int] = None
    detail: Optional[str] = None
    result: Optional[Any] = None
