from pydantic import BaseModel
from enum import Enum
from typing import Literal

class SourceType(str, Enum):
    sec_filing = "sec_filing"
    pdf_report = "pdf_report"

class IngestSECRequest(BaseModel):
    cik: str                        # e.g. "0000070858" for JPMorgan
    filing_type: str = "10-K"

class IngestPDFRequest(BaseModel):
    url: str                        # direct PDF URL
    source_name: str                # e.g. "Fed FSR Nov 2023"
    source_type: SourceType = SourceType.pdf_report

class IngestResponse(BaseModel):
    doc_id: str
    chunks_stored: int
    source: str

class QueryRequest(BaseModel):
    question: str
    source_filter: list[str] | None = None   # optional: filter by doc_id
    top_k: int = 5

class ChunkResult(BaseModel):
    doc_id: str
    source_name: str
    section: str | None
    text: str
    score: float

class QueryResponse(BaseModel):
    answer: str
    chunks: list[ChunkResult]
    