from fastapi import APIRouter, HTTPException
from app.models import IngestSECRequest, IngestPDFRequest, IngestResponse

router = APIRouter()

@router.post("/sec", response_model=IngestResponse)
async def ingest_sec(request: IngestSECRequest):
    raise HTTPException(status_code=501, detail="SEC ingest endpoint not implemented yet")

@router.post("/pdf", response_model=IngestResponse)
async def ingest_pdf(request: IngestPDFRequest):
    raise HTTPException(status_code=501, detail="PDF ingest endpoint not implemented yet")
