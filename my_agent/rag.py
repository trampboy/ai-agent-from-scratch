"""P3 — RAG: chunking, embeddings, vector search."""

from __future__ import annotations

from typing import Any, List
from openai import OpenAI
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")
    if not text:
        return []
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    
    return chunks



def embed_texts(texts: List[str], model="text-embedding-3-small") -> Any:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if isinstance(texts, str):
        texts = [texts]
    
    try:
        response = client.embeddings.create(input=texts,model=model)
        return np.array([data.embedding for data in response.data])
    except Exception as e:
        raise ValueError(f"Error embedding texts: {e}")


def search_similar(query: str, chunks, chunk_embeddings, top_k: int) -> List[Any]:
    query_embedding = embed_texts([query])
    similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
    top_indices = similarities.argsort()[::-1][:top_k]
    results = []
    for index in top_indices:
        results.append({
            "chunk": chunks[index],
            "similarity": float(similarities[index])
        })
    return results