# services/rag_service.py
# Manages in-memory FAISS vector stores, one per thread.
#
# Important limitation: these stores live in RAM.
# Server restart = all uploaded PDFs are gone.
# Production upgrade path: swap FAISS for ChromaDB (local persistence)
# or Pinecone/Weaviate (cloud). The interface (retriever.invoke) stays the same.

import os
import tempfile
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import settings

# ---------------------------------------------------------------------------
# Module-level stores — survive for the lifetime of the running process
# ---------------------------------------------------------------------------
_THREAD_RETRIEVERS: dict = {}   # thread_id → FAISS retriever
_THREAD_METADATA: dict = {}     # thread_id → {filename, documents, chunks}

# One embeddings client, created once, reused for every PDF upload
# Creating it here (module level) means we don't recreate it per request
_embeddings = OpenAIEmbeddings(
    model=settings.embedding_model,
    api_key=settings.openai_api_key,
)


class RAGService:

    def ingest_pdf(self, file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
        """
        Full ingestion pipeline. Returns metadata dict.
        PyPDFLoader requires a real file path (not raw bytes), so we write
        to a temp file first, then delete it after FAISS has its copy.
        """
        if not file_bytes:
            raise ValueError("Empty file bytes — nothing to ingest.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(file_bytes)
            temp_path = f.name

        try:
            # 1. Load PDF pages
            loader = PyPDFLoader(temp_path)
            docs = loader.load()

            # 2. Split into overlapping chunks
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
            )
            chunks = splitter.split_documents(docs)

            # 3. Embed and build FAISS index
            vector_store = FAISS.from_documents(chunks, _embeddings)

            # 4. Wrap as retriever (similarity search, return top-k chunks)
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": settings.retriever_k},
            )
            _THREAD_RETRIEVERS[str(thread_id)] = retriever

            metadata = {
                "filename": filename or os.path.basename(temp_path),
                "documents": len(docs),
                "chunks": len(chunks),
            }
            _THREAD_METADATA[str(thread_id)] = metadata
            return metadata

        finally:
            try:
                os.remove(temp_path)   # FAISS keeps its own copy in memory
            except OSError:
                pass

    def get_retriever(self, thread_id: str):
        return _THREAD_RETRIEVERS.get(str(thread_id))

    def has_document(self, thread_id: str) -> bool:
        return str(thread_id) in _THREAD_RETRIEVERS

    def get_metadata(self, thread_id: str) -> dict:
        return _THREAD_METADATA.get(str(thread_id), {})


rag_service = RAGService()