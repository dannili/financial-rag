import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models import QueryRequest, QueryResponse
from app.services.embedder import embed_query
from app.services.vector_store import similarity_search
from app.services.llm import stream_answer

router = APIRouter()

@router.post("/", response_model=QueryResponse)
async def query(req: QueryRequest):
    # 1. embed the question
    query_embedding = await embed_query(req.question)

    # 2. retrieve relevant chunks
    chunks = await similarity_search(
        query_embedding,
        top_k=req.top_k,
        doc_ids=req.source_filter,
    )

    if not chunks:
        return QueryResponse(answer="No relevant documents found.", chunks=[])

    # 3. stream LLM response — collect full answer for non-streaming response
    answer_parts = []
    async for token in stream_answer(req.question, chunks):
        answer_parts.append(token)

    return QueryResponse(
        answer="".join(answer_parts),
        chunks=chunks,
    )

@router.post("/stream")
async def query_stream(req: QueryRequest):
    """SSE endpoint — streams tokens, then sends chunks as final JSON event."""
    query_embedding = await embed_query(req.question)
    chunks = await similarity_search(
        query_embedding,
        top_k=req.top_k,
        doc_ids=req.source_filter,
    )

    async def event_generator():
        async for token in stream_answer(req.question, chunks):
            yield f"data: {json.dumps({'token': token})}\n\n"
        # final event carries the chunks so the UI can display them
        yield f"data: {json.dumps({'chunks': [c.model_dump() for c in chunks]})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},
    )
