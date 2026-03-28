CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id          SERIAL PRIMARY KEY,
    doc_id      TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    section     TEXT,
    text        TEXT NOT NULL,
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS chunks_doc_id_idx
    ON chunks (doc_id);