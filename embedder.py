# utils/embedder.py
import os
import numpy as np

# Lazy import to avoid heavy import cost at startup
_model = None
_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")

def _load_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            raise RuntimeError("Please install sentence-transformers: pip install sentence-transformers") from e
        _model = SentenceTransformer(_MODEL_NAME)
    return _model

def sentence_embed_texts(texts, normalize=True):
    """
    Accepts a list of strings and returns list of 1D float vectors.
    Uses sentence-transformers (all-MiniLM-L6-v2).
    """
    if not texts:
        return []


    if not isinstance(texts, list):
        texts = [texts]

    clean_texts = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
    if not clean_texts:
        return []
    
    model = _load_model()

    vecs = model.encode(
        clean_texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )

    if vecs.ndim == 1:
        vecs = vecs.reshape(1, -1)

    return vecs.astype(float).tolist()


def aggregate_vectors(vectors):
    if not vectors:
        return None
    arr = np.asarray(vectors, dtype=float)
    if arr.ndim == 1:
        return arr.tolist()
    return np.mean(arr, axis=0).tolist()