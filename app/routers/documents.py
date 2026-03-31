from fastapi import APIRouter
from app.services.vector_store import list_documents

router = APIRouter()

@router.get("/", response_model=list[dict])
async def get_documents():
    return await list_documents()
