import psycopg
from pgvector.psycopg import register_vector_async
from psycopg_pool import AsyncConnectionPool
from app.config import settings
from app.models import ChunkResult

_pool: AsyncConnectionPool | None = None

async def init_vector_store():
    global _pool
    _pool = AsyncConnectionPool(
        settings.database_url,
        min_size=2,
        max_size=10,
        open=False,
    )
    await _pool.open()
    async with _pool.connection() as conn:
        await register_vector_async(conn)
        await conn.execute(open("app/db/init.sql").read())
        await conn.commit()

async def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Vector store not initialised")
    return _pool

async def store_chunks(
    doc_id: str,
    source_name: str,
    source_type: str,
    chunks: list[dict],  # each: {text, embedding, section}
):
    pool = await get_pool()
    async with pool.connection() as conn:
        await register_vector_async(conn)
        for chunk in chunks:
            await conn.execute(
                """
                INSERT INTO chunks (doc_id, source_name, source_type, section, text, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_id,
                    source_name,
                    source_type,
                    chunk.get("section"),
                    chunk["text"],
                    chunk["embedding"],
                ),
            )
        await conn.commit()

async def similarity_search(
    query_embedding: list[float],
    top_k: int = 5,
    doc_ids: list[str] | None = None,
) -> list[ChunkResult]:
    pool = await get_pool()
    async with pool.connection() as conn:
        await register_vector_async(conn)

        if doc_ids:
            # with doc_ids filter
            rows = await conn.execute(
                """
                SELECT DISTINCT ON (text) doc_id, source_name, section, text,
                    1 - (embedding <=> %s::vector) AS score
                FROM chunks
                WHERE doc_id = ANY(%s)
                ORDER BY text, embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, doc_ids, query_embedding, top_k),
            )
        else:
            # without filter
            rows = await conn.execute(
                """
                SELECT DISTINCT ON (text) doc_id, source_name, section, text,
                    1 - (embedding <=> %s::vector) AS score
                FROM chunks
                ORDER BY text, embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, top_k),
            )

        return [
            ChunkResult(
                doc_id=row[0],
                source_name=row[1],
                section=row[2],
                text=row[3],
                score=round(row[4], 4),
            )
            for row in await rows.fetchall()
        ]
    
async def list_documents() -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        rows = await conn.execute(
            """
            SELECT doc_id, source_name, source_type,
                   COUNT(*) as chunk_count,
                   MIN(created_at) as ingested_at
            FROM chunks
            GROUP BY doc_id, source_name, source_type
            ORDER BY ingested_at DESC
            """
        )
        return [
            {
                "doc_id": row[0],
                "source_name": row[1],
                "source_type": row[2],
                "chunk_count": row[3],
                "ingested_at": row[4].isoformat(),
            }
            for row in await rows.fetchall()
        ]
