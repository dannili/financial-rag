from fastapi import APIRouter, HTTPException
from app.models import QueryRequest, QueryResponse

router = APIRouter()

@router.post("/", response_model=QueryResponse)
async def query(request: QueryRequest):
    raise HTTPException(status_code=501, detail="Query endpoint not implemented yet")
