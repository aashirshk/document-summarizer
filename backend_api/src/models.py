from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    question: str
    n_results: int = 3
    jobId: Optional[str] = None


class QueryMultiRequest(BaseModel):
    question: str
    n_results: int = 6
    max_context_chars: int = 12000
    dedupe_by_source: bool = True
    jobId: Optional[str] = None