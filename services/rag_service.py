# services/rag_service.py
# Manages Pinecone vector stores, one namespace per thread.
#
# Why Pinecone instead of FAISS?
# FAISS stored vectors in RAM — server restart wiped all uploaded PDFs.
# Pinecone stores vectors in the cloud — they persist across restarts,
# crashes, and redeployments. Nothing in the rest of the codebase changes
# because the interface (get_retriever, has_document, get_metadata) is identical.
#
# How thread isolation works:
# One Pinecone index holds all threads' data.
# namespace=thread_id partitions it — each thread only searches its own vectors.

import os
import tempfile
from typing import Optional

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

from core.config import settings

# Load .env explicitly so OS environment variables don't silently shadow it.
# pydantic-settings checks the OS environment BEFORE the .env file.
# If PINECONE_API_KEY exists in Windows env as an empty string (from a previous
# failed attempt), it would override the .env file and pass "" to Pinecone.
# override=True forces .env file values to always win over OS env vars.
load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Module-level clients — created once at startup, shared across all requests
# ---------------------------------------------------------------------------

# Read key directly from env after load_dotenv has populated it.
# Falls back to settings.pinecone_api_key as a second option.
_pinecone_api_key = os.environ.get("PINECONE_API_KEY") or settings.pinecone_api_key

if not _pinecone_api_key:
    raise RuntimeError(
        "PINECONE_API_KEY is missing or empty. "
        "Add it to your .env file: PINECONE_API_KEY=your-key-here"
    )

# Authenticate with Pinecone once — reused for every upload and query
_pc = Pinecone(api_key=_pinecone_api_key)

# Handle to the Pinecone index — all threads share this index,
# isolated by namespace (namespace = thread_id)
_index = _pc.Index(settings.pinecone_index_name)

# Lightweight metadata store — filenames and chunk counts only, RAM is fine for this
_THREAD_METADATA: dict = {}     # thread_id → {filename, documents, chunks}

# One embeddings client, created once, reused for every PDF upload and query
_embeddings = OpenAIEmbeddings(
    model=settings.embedding_model,
    api_key=settings.openai_api_key,
)


class RAGService:

    def ingest_pdf(self, file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
        """
        Full ingestion pipeline. Returns metadata dict.
        PyPDFLoader requires a real file path (not raw bytes), so we write
        to a temp file first, then delete it after ingestion is complete.
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

            # 3. Embed chunks and upload to Pinecone
            # namespace=thread_id isolates this thread's vectors from all others
            # in the same index. Uploading again to the same thread_id overwrites
            # the previous vectors (upsert behaviour).
            PineconeVectorStore.from_documents(
                documents=chunks,
                embedding=_embeddings,
                index_name=settings.pinecone_index_name,
                namespace=str(thread_id),
            )

            # 4. Save lightweight metadata to RAM
            metadata = {
                "filename": filename or os.path.basename(temp_path),
                "documents": len(docs),
                "chunks": len(chunks),
            }
            _THREAD_METADATA[str(thread_id)] = metadata
            return metadata

        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def get_retriever(self, thread_id: str):
        """
        Build and return a retriever pointing at this thread's Pinecone namespace.
        No API call happens here — only when retriever.invoke(query) is called.
        """
        if not self.has_document(str(thread_id)):
            return None

        vector_store = PineconeVectorStore(
            index=_index,
            embedding=_embeddings,
            namespace=str(thread_id),
        )
        return vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.retriever_k},
        )

    def has_document(self, thread_id: str) -> bool:
        return str(thread_id) in _THREAD_METADATA

    def get_metadata(self, thread_id: str) -> dict:
        return _THREAD_METADATA.get(str(thread_id), {})


rag_service = RAGService()
