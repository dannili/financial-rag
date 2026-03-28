from openai import AsyncOpenAI
from app.config import settings
from app.models import ChunkResult
from typing import AsyncGenerator

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a financial risk analyst assistant.
Answer questions using only the provided document excerpts.
Be concise and cite which document each claim comes from.
If the excerpts don't contain enough information, say so."""

def _build_context(chunks: list[ChunkResult]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        section = f" · {c.section}" if c.section else ""
        parts.append(
            f"[{i}] {c.source_name}{section}\n{c.text}"
        )
    return "\n\n".join(parts)

async def stream_answer(
    question: str,
    chunks: list[ChunkResult],
) -> AsyncGenerator[str, None]:
    context = _build_context(chunks)
    stream = await client.chat.completions.create(
        model=settings.chat_model,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    async for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta
