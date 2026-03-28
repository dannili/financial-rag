from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import ingest, query
from app.services.vector_store import init_vector_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_vector_store()   # creates pgvector table on startup
    yield

app = FastAPI(title="Financial RAG API", lifespan=lifespan)
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(query.router, prefix="/query", tags=["query"])

@app.get("/health")
async def health():
    return {"status": "ok"}
