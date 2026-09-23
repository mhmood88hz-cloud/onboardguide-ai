import re
import time
from typing import List, Dict
from openai import OpenAI
from sqlalchemy.orm import Session
from app.config import OPENAI_API_KEY, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_CHUNKS
from app.models import DocumentChunk

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Embedding model – small is fast and cheap, 1536 dimensions
EMBEDDING_MODEL = "text-embedding-3-small"

# Marker, den documents.py beim PDF-Textextrahieren vor jede Seite einfügt
# (z.B. "<<<PAGE:3>>>"), damit Chunks später wissen, von welcher Seite sie
# stammen – nötig um passende Screenshots/Bilder im Chat zeigen zu können.
PAGE_MARKER_RE = re.compile(r"<<<PAGE:(\d+)>>>")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Splits text into overlapping chunks by word count.
    Words are used instead of tokens for simplicity –
    1 word ≈ 1.3 tokens, so chunk_size=400 words ≈ 520 tokens.
    """
    words  = text.split()
    chunks = []
    start  = 0

    while start < len(words):
        end   = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        # move forward by (chunk_size - overlap) to create overlap
        start += chunk_size - overlap

    return chunks


def _words_with_pages(text: str) -> tuple[List[str], List[int]]:
    """
    Strips "<<<PAGE:n>>>" markers out of the text and returns the remaining
    words together with a parallel list of which PDF page each word came from.
    Text without markers (e.g. .txt uploads) is treated as all page 1.
    """
    words, pages = [], []
    current_page = 1
    for tok in text.split():
        m = PAGE_MARKER_RE.fullmatch(tok)
        if m:
            current_page = int(m.group(1))
        else:
            words.append(tok)
            pages.append(current_page)
    return words, pages


def chunk_text_with_pages(text: str, chunk_size: int = CHUNK_SIZE,
                          overlap: int = CHUNK_OVERLAP) -> List[Dict]:
    """
    Same sliding-window chunking as chunk_text(), but also records which
    page(s) of the source PDF each chunk's words came from. Used so the chat
    can show the screenshot(s) from the page(s) a chunk was retrieved from.
    """
    words, word_pages = _words_with_pages(text)
    chunks = []
    start  = 0

    while start < len(words):
        end   = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append({
                "content": chunk,
                "pages":   sorted(set(word_pages[start:end])),
            })
        start += chunk_size - overlap

    return chunks


def create_embedding(text: str) -> List[float]:
    """
    Calls OpenAI text-embedding-3-small to convert text into a 1536-dim vector.
    This vector represents the semantic meaning of the text.
    """
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def embed_document(document_id: int, text: str, db: Session) -> Dict:
    """
    Full pipeline for one document:
    1. Split text into chunks
    2. Create embedding for each chunk
    3. Save all chunks to document_chunks table

    Returns stats for the live trace simulator.
    """
    if not client:
        return {"chunks_created": 0, "error": "OpenAI client not configured"}

    # Step 1: Split into chunks (page-aware, so images can be matched later)
    chunks = chunk_text_with_pages(text)
    if not chunks:
        return {"chunks_created": 0, "error": "No text to embed"}

    # Step 2 + 3: Embed each chunk and save to DB
    saved   = 0
    t_start = time.time()

    for i, chunk in enumerate(chunks):
        chunk_content = chunk["content"]
        embedding     = create_embedding(chunk_content)

        db_chunk = DocumentChunk(
            document_id    = document_id,
            chunk_index    = i,
            content        = chunk_content,
            embedding      = embedding,
            token_count    = len(chunk_content.split()),
            chunk_metadata = {
                "chunk_index":  i,
                "total_chunks": len(chunks),
                "word_count":   len(chunk_content.split()),
                "pages":        chunk["pages"],
            }
        )
        db.add(db_chunk)
        saved += 1

    db.commit()
    elapsed = round(time.time() - t_start, 2)

    return {
        "chunks_created":  saved,
        "embedding_model": EMBEDDING_MODEL,
        "elapsed_seconds": elapsed,
    }


def search_similar_chunks(query: str, db: Session,
                          allowed_doc_ids: List[int] = None) -> List[Dict]:
    """
    Converts the user query to a vector and finds the most similar
    chunks in pgvector using cosine distance.

    Returns top-k chunks with their similarity scores.
    These scores will be shown in the simulator.
    """
    if not client:
        return []

    # Embed the query with the same model used for documents
    query_embedding = create_embedding(query)

    # Build SQL query with pgvector cosine distance operator (<=>)
    # Lower distance = more similar
    from sqlalchemy import text
    from app.models import DocumentChunk

    if allowed_doc_ids:
        # Filter by allowed documents (role-based access)
        sql = text("""
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.token_count,
                1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity_score,
                dc.chunk_metadata
            FROM document_chunks dc
            WHERE dc.document_id = ANY(:doc_ids)
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)
        rows = db.execute(sql, {
            "embedding": str(query_embedding),
            "doc_ids":   allowed_doc_ids,
            "top_k":     TOP_K_CHUNKS
        }).fetchall()
    else:
        sql = text("""
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.token_count,
                1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity_score,
                dc.chunk_metadata
            FROM document_chunks dc
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)
        rows = db.execute(sql, {
            "embedding": str(query_embedding),
            "top_k":     TOP_K_CHUNKS
        }).fetchall()

    return [
        {
            "chunk_id":        row[0],
            "document_id":     row[1],
            "chunk_index":     row[2],
            "content":         row[3],
            "token_count":     row[4],
            "similarity_score": round(float(row[5]), 4),
            "pages":           (row[6] or {}).get("pages", []),
        }
        for row in rows
    ]
