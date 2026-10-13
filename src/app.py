"""Phase 7 tiny Streamlit chat UI for the HDFC Groww FAQ assistant."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chromadb
import streamlit as st

from generate import bind_citation, generate_answer
from guards import guard
from retrieve import (CHROMA_DIR, COLLECTION_NAME, DEFAULT_K, retrieve)

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    "What is the lock-in for HDFC ELSS Tax Saver?",
    "What is the minimum SIP for HDFC Small Cap Fund Direct Growth?",
]

MEMORY_WINDOW = 10



SCHEME_ALIASES = [
    ("balanced advantage", "HDFC Balanced Advantage Fund Direct Growth"),
    ("hybrid", "HDFC Balanced Advantage Fund Direct Growth"),
    ("small cap", "HDFC Small Cap Fund Direct Growth"),
    ("large cap", "HDFC Large Cap Fund Direct Growth"),
    ("flexi", "HDFC Flexi Cap Fund Direct Growth"),
    ("equity fund", "HDFC Flexi Cap Fund Direct Growth"),
    ("elss", "HDFC ELSS Tax Saver Direct Plan Growth"),
    ("tax saver", "HDFC ELSS Tax Saver Direct Plan Growth"),
]


def resolve_scheme(question: str, history: list[dict] | None = None) -> str | None:
    """Best-effort scheme resolution from the current or recent context."""
    texts = [question or ""]
    for message in list(history or [])[-MEMORY_WINDOW:]:
        content = message.get("content", "")
        if isinstance(content, str):
            texts.append(content)
    combined = " ".join(texts).lower()
    for alias, scheme_name in SCHEME_ALIASES:
        if alias in combined:
            return scheme_name
    return None


def chroma_status() -> tuple[bool, str, int | None]:
    if not CHROMA_DIR.exists():
        return False, "Chroma store not found at data/chroma/. Run: python src/ingest.py", None
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return False, "Chroma collection 'hdfc_mf_faq' is unavailable. Run: python src/ingest.py", None
    count = collection.count()
    if count == 0:
        return False, "Chroma collection 'hdfc_mf_faq' is empty. Run: python src/ingest.py", 0
    return True, f"Ready: {count} chunks indexed.", count


def is_pii_question(question: str) -> bool:
    try:
        return guard(question).reason == "pii"
    except Exception:
        return False


def build_retrieval_query(question: str, history: list[dict] | None = None) -> str:
    """Append the recent chat context so follow-up questions resolve."""
    history = list(history or [])[-MEMORY_WINDOW:]
    lines = []
    for message in history:
        role = "User" if message.get("role") == "user" else "Assistant"
        content = message.get("content", "")
        if isinstance(content, str) and content.strip():
            lines.append(f"{role}: {content.strip()[:800]}")
    if not lines:
        return question.strip()
    return (
        "Conversation context (most recent messages):\n"
        + "\n".join(lines)
        + "\n\nFollow-up question: "
        + question.strip()
    )


def answer_question(
    question: str,
    retrieval_question: str | None = None,
    k: int = DEFAULT_K,
    where: dict | None = None,
) -> dict:
    decision = guard(question)
    if decision.action != "allow":
        return {
            "kind": "refusal",
            "message": decision.message,
            "citation_url": decision.citation_url,
            "last_updated": None,
            "sources": [],
        }

    query_for_retrieval = retrieval_question or question
    try:
        hits = retrieve(query_for_retrieval, k, where=where)
    except Exception as exc:
        return {
            "kind": "error",
            "message": f"Retrieval failed: {exc}",
            "citation_url": None,
            "last_updated": None,
            "sources": [],
        }

    citation = bind_citation(question, hits)
    citation_url = citation.get("citation_url")
    last_updated = citation.get("ingest_ts")

    try:
        result = generate_answer(question, hits)
        return {
            "kind": "answer",
            "message": result.get("answer", ""),
            "citation_url": citation_url or result.get("citation_url"),
            "last_updated": result.get("ingest_ts") or last_updated,
            "sources": [h.get("metadata", {}).get("source_url") for h in hits],
        }
    except Exception:
        return {
            "kind": "generation_unavailable",
            "message": "Generation unavailable; retrieved facts were not guessed.",
            "citation_url": citation_url,
            "last_updated": last_updated,
            "sources": [h.get("metadata", {}).get("source_url") for h in hits],
        }


st.set_page_config(page_title="HDFC Mutual Fund FAQ", page_icon="💬", layout="centered")

st.markdown("**Facts-only. No investment advice.**")
st.title("HDFC Mutual Fund FAQ (Groww)")
st.write(
    "Welcome! I answer factual questions about five HDFC schemes from public "
    "Groww pages and always cite the source. Follow-up questions use recent chat context."
)

ready, status, count = chroma_status()
if ready:
    st.success(status)
else:
    st.error(status)
    st.info("Run `python src/ingest.py`, then refresh this page.")

st.caption("Example questions:")
cols = st.columns(3)
for col, question in zip(cols, EXAMPLE_QUESTIONS):
    if col.button(question, use_container_width=True):
        st.session_state["pending_question"] = question

if "messages" not in st.session_state:
    st.session_state.messages = []

pending = st.session_state.pop("pending_question", None)
if pending:
    prior_history = list(st.session_state.messages[-MEMORY_WINDOW:])
    if is_pii_question(pending):
        stored_user = "[Redacted request involving personal/account identifiers]"
    else:
        stored_user = pending
    st.session_state.messages.append({"role": "user", "content": stored_user})
    resolved_scheme = resolve_scheme(pending, prior_history)
    where = {"scheme_name": resolved_scheme} if resolved_scheme else None
    if where:
        retrieval_query = pending
    else:
        retrieval_query = build_retrieval_query(pending, prior_history)
    with st.spinner("Thinking..."):
        response = answer_question(
            pending,
            retrieval_query,
            where=where,
        )
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response["message"],
            "citation_url": response.get("citation_url"),
            "last_updated": response.get("last_updated"),
            "kind": response.get("kind"),
            "sources": response.get("sources"),
        }
    )
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            data = message
            if data.get("citation_url"):
                st.markdown(f"[Source]({data['citation_url']})")
            if data.get("last_updated"):
                st.caption(f"Last updated from sources: {data['last_updated']}")
            if data.get("kind") == "generation_unavailable" and data.get("sources"):
                st.caption("Retrieval ran. Top sources: " + ", ".join(data["sources"]))

if ready:
    prompt = st.chat_input("Ask a factual question...")
    if prompt:
        prior_history = list(st.session_state.messages[-MEMORY_WINDOW:])
        if is_pii_question(prompt):
            stored_user = "[Redacted request involving personal/account identifiers]"
        else:
            stored_user = prompt
        st.session_state.messages.append({"role": "user", "content": stored_user})
        resolved_scheme = resolve_scheme(prompt, prior_history)
        where = {"scheme_name": resolved_scheme} if resolved_scheme else None
        if where:
            retrieval_query = prompt
        else:
            retrieval_query = build_retrieval_query(prompt, prior_history)
        with st.spinner("Thinking..."):
            response = answer_question(
                prompt,
                retrieval_query,
                where=where,
            )
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response["message"],
                "citation_url": response.get("citation_url"),
                "last_updated": response.get("last_updated"),
                "kind": response.get("kind"),
                "sources": response.get("sources"),
            }
        )
        st.rerun()
