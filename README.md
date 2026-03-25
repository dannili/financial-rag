# financial-rag
A FastAPI backend that lets you ask natural language questions across SEC filings and financial reports.
It ingests documents, stores them as searchable embeddings in pgvector, and returns answers with the exact chunks of text the LLM used to generate them.
