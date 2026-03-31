import streamlit as st
import httpx
import json

API_URL = "http://api:8000"  # service name from docker-compose

st.set_page_config(
    page_title="Financial RAG",
    page_icon="",
    layout="wide",
)

# ── helpers ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def fetch_documents():
    try:
        r = httpx.get(f"{API_URL}/documents/", timeout=5)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

def ingest_sec(cik: str, filing_type: str):
    r = httpx.post(
        f"{API_URL}/ingest/sec",
        json={"cik": cik, "filing_type": filing_type},
        timeout=120,
    )
    return r.json()

def ingest_pdf(url: str, source_name: str):
    r = httpx.post(
        f"{API_URL}/ingest/pdf",
        json={"url": url, "source_name": source_name},
        timeout=120,
    )
    return r.json()

def query(question: str, doc_ids: list[str] | None = None):
    r = httpx.post(
        f"{API_URL}/query/",
        json={"question": question, "source_filter": doc_ids or None, "top_k": 5},
        timeout=60,
    )
    return r.json()

# ── session state ─────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_chunks" not in st.session_state:
    st.session_state.last_chunks = []

# ── layout ────────────────────────────────────────────────────────────────

col_sidebar, col_chat, col_chunks = st.columns([1.2, 2.5, 1.5])

# ── sidebar ───────────────────────────────────────────────────────────────

with col_sidebar:
    st.markdown("### Financial RAG")

    docs = fetch_documents()
    if not isinstance(docs, list):
        docs = []
    doc_ids = [d["doc_id"] for d in docs if isinstance(d, dict) and "doc_id" in d]

    if docs:
        st.markdown("**Indexed documents**")
        for doc in docs:
            badge = "SEC" if doc["source_type"] == "sec_filing" else "PDF"
            st.markdown(
                f"`{badge}` **{doc['source_name']}**  \n"
                f"<span style='font-size:11px;color:gray'>{doc['chunk_count']} chunks</span>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No documents ingested yet.")

    st.divider()
    st.markdown("**Add SEC filing**")
    cik_input = st.text_input("CIK", placeholder="e.g. 0000019617")
    filing_type = st.selectbox("Filing type", ["10-K", "10-Q"])
    if st.button("Ingest SEC filing"):
        with st.spinner("Fetching and embedding..."):
            result = ingest_sec(cik_input, filing_type)
            st.success(f"{result['chunks_stored']} chunks stored")
            st.cache_data.clear()

    st.divider()
    st.markdown("**Add PDF report**")
    pdf_url = st.text_input("PDF URL")
    pdf_name = st.text_input("Source name", placeholder="e.g. Fed FSR Nov 2023")
    if st.button("Ingest PDF"):
        with st.spinner("Downloading and embedding..."):
            result = ingest_pdf(pdf_url, pdf_name)
            st.success(f"{result['chunks_stored']} chunks stored")
            st.cache_data.clear()

# ── chat ──────────────────────────────────────────────────────────────────

with col_chat:
    st.markdown("### Ask your documents")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                st.caption(" · ".join(msg["sources"]))

    if question := st.chat_input("Ask a question across your documents..."):
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving and generating..."):
                result = query(question, doc_ids if doc_ids else None)

            answer = result["answer"]
            chunks = result.get("chunks", [])
            sources = list({c["source_name"] for c in chunks})

            st.markdown(answer)
            if sources:
                st.caption(" · ".join(sources))

            st.session_state.last_chunks = chunks
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
            })

# ── chunks panel ──────────────────────────────────────────────────────────

with col_chunks:
    st.markdown("### Retrieved chunks")

    if st.session_state.last_chunks:
        for i, chunk in enumerate(st.session_state.last_chunks, 1):
            with st.expander(
                f"#{i} · {chunk['source_name']} · score {chunk['score']}"
            ):
                if chunk.get("section"):
                    st.caption(chunk["section"])
                st.markdown(chunk["text"])
    else:
        st.info("Ask a question to see retrieved chunks.")
