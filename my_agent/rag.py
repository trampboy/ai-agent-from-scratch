"""P3 — RAG: chunking, embeddings, vector search."""

from __future__ import annotations

from typing import Any, List


def chunk_text(text: str, **kwargs: Any) -> List[str]:
    raise NotImplementedError("P3: split text into chunks")


def embed_texts(texts: List[str], **kwargs: Any) -> Any:
    raise NotImplementedError("P3: create embeddings")


def search_similar(query: str, **kwargs: Any) -> List[Any]:
    raise NotImplementedError("P3: vector similarity search")
