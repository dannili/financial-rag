import uuid
import httpx
from fastapi import APIRouter, HTTPException
from bs4 import BeautifulSoup
import fitz  # pymupdf

from app.models import IngestSECRequest, IngestPDFRequest, IngestResponse
from app.services.chunker import chunk_text
from app.services.embedder import embed_texts
from app.services.vector_store import store_chunks

router = APIRouter()

EDGAR_HEADERS = {"User-Agent": "financial-rag contact@example.com"}

async def _fetch_sec_sections(cik: str, filing_type: str) -> list[dict]:
    """Fetch latest 10-K from EDGAR, extract Item 1A and Item 7 sections."""
    async with httpx.AsyncClient(headers=EDGAR_HEADERS) as client:
        # 1. get filing index
        cik_padded = cik.zfill(10)
        r = await client.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        )
        r.raise_for_status()
        data = r.json()

        filings = data["filings"]["recent"]
        forms = filings["form"]
        accessions = filings["accessionNumber"]
        primary_documents = filings["primaryDocument"]

        # find latest matching filing and its primary document
        result = next(
            (
                (accessions[i], primary_documents[i])
                for i, f in enumerate(forms)
                if f == filing_type
            ),
            None,
        )
        if not result:
            raise HTTPException(404, f"No {filing_type} found for CIK {cik}")

        accession, primary_document = result
        acc_clean = accession.replace("-", "")
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{acc_clean}/{primary_document}"
        )
        html = await client.get(doc_url)
        html.raise_for_status()

    # 2. parse sections from HTML
    soup = BeautifulSoup(html.text, "html.parser")
    full_text = soup.get_text(separator="\n")
    lines = full_text.splitlines()

    sections = {}
    current_section = None
    buffer = []

    for line in lines:
        stripped = line.strip().lower()
        if "item 1a" in stripped and "risk" in stripped:
            if current_section:
                sections[current_section] = "\n".join(buffer)
            current_section = "Item 1A · Risk Factors"
            buffer = []
        elif "item 7" in stripped and "management" in stripped:
            if current_section:
                sections[current_section] = "\n".join(buffer)
            current_section = "Item 7 · MD&A"
            buffer = []
        elif current_section:
            buffer.append(line)

    if current_section and buffer:
        sections[current_section] = "\n".join(buffer)

    return [{"text": text, "section": sec} for sec, text in sections.items()]


async def _fetch_pdf_sections(url: str) -> list[dict]:
    """Download a PDF and extract text page by page."""
    async with httpx.AsyncClient() as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()

    doc = fitz.open(stream=r.content, filetype="pdf")
    pages = []
    for i, page in enumerate(doc, 1):
        text = page.get_text()
        if text.strip():
            pages.append({"text": text, "section": f"Page {i}"})
    return pages


@router.post("/sec", response_model=IngestResponse)
async def ingest_sec(req: IngestSECRequest):
    doc_id = f"sec_{req.cik}_{req.filing_type.lower()}"
    sections = await _fetch_sec_sections(req.cik, req.filing_type)

    all_chunks = []
    for s in sections:
        all_chunks.extend(chunk_text(s["text"], section=s["section"]))

    if not all_chunks:
        raise HTTPException(422, "No text extracted from filing")

    texts = [c["text"] for c in all_chunks]
    embeddings = await embed_texts(texts)
    for chunk, emb in zip(all_chunks, embeddings):
        chunk["embedding"] = emb

    company_name = doc_id  # replaced by real name if you extend this
    await store_chunks(doc_id, company_name, "sec_filing", all_chunks)

    return IngestResponse(
        doc_id=doc_id,
        chunks_stored=len(all_chunks),
        source=doc_id,
    )


@router.post("/pdf", response_model=IngestResponse)
async def ingest_pdf(req: IngestPDFRequest):
    doc_id = str(uuid.uuid4())
    sections = await _fetch_pdf_sections(req.url)

    all_chunks = []
    for s in sections:
        all_chunks.extend(chunk_text(s["text"], section=s["section"]))

    if not all_chunks:
        raise HTTPException(422, "No text extracted from PDF")

    texts = [c["text"] for c in all_chunks]
    embeddings = await embed_texts(texts)
    for chunk, emb in zip(all_chunks, embeddings):
        chunk["embedding"] = emb

    await store_chunks(doc_id, req.source_name, req.source_type, all_chunks)

    return IngestResponse(
        doc_id=doc_id,
        chunks_stored=len(all_chunks),
        source=req.source_name,
    )
