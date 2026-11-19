"""Embedding service using Sentence Transformers."""
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

_model_cache: dict = {}


def get_embedding_model(model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
    """Load and cache the embedding model."""
    if model_name not in _model_cache:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f'Loading embedding model: {model_name}')
            model = SentenceTransformer(model_name)
            _model_cache[model_name] = model
            logger.info(f'Embedding model loaded: {model_name}')
        except Exception as e:
            logger.error(f'Failed to load embedding model {model_name}: {e}')
            raise
    return _model_cache[model_name]


def embed_texts(
    texts: list[str],
    model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
    normalize: bool = True,
    batch_size: int = 32,
) -> np.ndarray:
    """
    Generate embeddings for a list of texts.
    Returns a float32 numpy array of shape (n, dim).
    """
    if not texts:
        raise ValueError('texts list is empty')

    model = get_embedding_model(model_name)

    # Preprocess: strip empty strings and truncate very long texts
    processed = [t[:8000] if t else ' ' for t in texts]

    embeddings = model.encode(
        processed,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=normalize,
        convert_to_numpy=True,
    )
    return embeddings.astype(np.float32)


def embed_query(
    query: str,
    model_name: str = 'sentence-transformers/all-MiniLM-L6-v2',
    normalize: bool = True,
) -> np.ndarray:
    """Embed a single query string. Returns shape (1, dim)."""
    return embed_texts([query], model_name=model_name, normalize=normalize)


def get_embedding_dimension(model_name: str = 'sentence-transformers/all-MiniLM-L6-v2') -> int:
    """Return the embedding dimension for the given model."""
    model = get_embedding_model(model_name)
    return model.get_sentence_embedding_dimension()

