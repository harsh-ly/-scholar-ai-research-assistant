"""FAISS vector store service for Scholar AI."""
import os
import json
import logging
import numpy as np
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _get_index_path(faiss_folder: str, document_id: str) -> str:
    return os.path.join(faiss_folder, f'{document_id}.index')


def _get_meta_path(faiss_folder: str, document_id: str) -> str:
    return os.path.join(faiss_folder, f'{document_id}.meta.json')


def build_index(
    embeddings: np.ndarray,
    chunk_ids: list[str],
    document_id: str,
    faiss_folder: str,
) -> int:
    """
    Build a FAISS flat L2 index for a document's embeddings.
    Saves index and metadata to disk.
    Returns number of vectors stored.
    """
    import faiss

    if embeddings.shape[0] == 0:
        raise ValueError('Cannot build FAISS index with 0 embeddings')

    dim = embeddings.shape[1]
    os.makedirs(faiss_folder, exist_ok=True)

    index = faiss.IndexFlatIP(dim)  # Inner product (cosine if normalized)
    index.add(embeddings)

    index_path = _get_index_path(faiss_folder, document_id)
    faiss.write_index(index, index_path)

    meta_path = _get_meta_path(faiss_folder, document_id)
    with open(meta_path, 'w') as f:
        json.dump({
            'document_id': document_id,
            'chunk_ids': chunk_ids,
            'dimension': dim,
            'count': len(chunk_ids),
        }, f)

    logger.info(f'FAISS index built for document {document_id}: {len(chunk_ids)} vectors, dim={dim}')
    return len(chunk_ids)


def load_index(faiss_folder: str, document_id: str):
    """Load FAISS index and metadata from disk. Returns (index, meta) or (None, None)."""
    import faiss

    index_path = _get_index_path(faiss_folder, document_id)
    meta_path = _get_meta_path(faiss_folder, document_id)

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        return None, None

    try:
        index = faiss.read_index(index_path)
        with open(meta_path, 'r') as f:
            meta = json.load(f)
        return index, meta
    except Exception as e:
        logger.error(f'Failed to load FAISS index for {document_id}: {e}')
        return None, None


def search_index(
    query_embedding: np.ndarray,
    document_id: str,
    faiss_folder: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Search FAISS index for a single document.
    Returns list of {chunk_id, score, faiss_rank} sorted by relevance descending.
    """
    index, meta = load_index(faiss_folder, document_id)
    if index is None:
        logger.warning(f'No FAISS index for document {document_id}')
        return []

    chunk_ids = meta.get('chunk_ids', [])
    if not chunk_ids:
        return []

    # Ensure 2D query
    if query_embedding.ndim == 1:
        query_embedding = query_embedding.reshape(1, -1)

    k = min(top_k, len(chunk_ids))
    scores, indices = index.search(query_embedding, k)

    results = []
    for rank, (idx, score) in enumerate(zip(indices[0], scores[0])):
        if idx < 0 or idx >= len(chunk_ids):
            continue
        results.append({
            'chunk_id': chunk_ids[idx],
            'score': float(score),
            'faiss_rank': rank,
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def search_multiple_documents(
    query_embedding: np.ndarray,
    document_ids: list[str],
    faiss_folder: str,
    top_k: int = 5,
) -> list[dict]:
    """Search across multiple documents and merge results."""
    all_results = []
    for doc_id in document_ids:
        results = search_index(query_embedding, doc_id, faiss_folder, top_k=top_k)
        for r in results:
            r['document_id'] = doc_id
        all_results.extend(results)

    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:top_k * len(document_ids)]


def delete_index(faiss_folder: str, document_id: str):
    """Delete FAISS index files for a document."""
    for path in [_get_index_path(faiss_folder, document_id),
                 _get_meta_path(faiss_folder, document_id)]:
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f'Deleted FAISS file: {path}')
            except Exception as e:
                logger.warning(f'Could not delete FAISS file {path}: {e}')


def index_exists(faiss_folder: str, document_id: str) -> bool:
    """Check if a FAISS index exists for a document."""
    return os.path.exists(_get_index_path(faiss_folder, document_id))

