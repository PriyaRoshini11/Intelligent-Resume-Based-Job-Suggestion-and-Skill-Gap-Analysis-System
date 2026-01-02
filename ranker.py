# utils/ranker.py
import numpy as np

def cos_sim_safe(a, b):
    """
    Compute cosine similarity between two vectors safely.
    Returns 0.0 if either vector is zero.
    """
    a = np.array(a, dtype=float).flatten()
    b = np.array(b, dtype=float).flatten()

    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0

    return float(np.dot(a, b) / denom)
   

def compute_final_score(
    semantic: float,
    keyword: float,
    recency: float,
    popularity: float,
    weights=None
) -> float:
    """
    Compute final job ranking score using fixed hybrid weights.

    Default weights (as per project spec):
    semantic   : 0.55
    keyword    : 0.25
    recency    : 0.10
    popularity : 0.10
    """
    if weights is None:
        weights = [0.55, 0.25, 0.10, 0.10]

    if len(weights) != 4:
        raise ValueError("weights must contain exactly 4 values")

    total = sum(weights)
    if total > 0:
        weights = [w / total for w in weights]

    semantic   = max(0.0, min(1.0, float(semantic)))
    keyword    = max(0.0, min(1.0, float(keyword)))
    recency    = max(0.0, min(1.0, float(recency)))
    popularity = max(0.0, min(1.0, float(popularity)))

    return (
        weights[0] * semantic +
        weights[1] * keyword +
        weights[2] * recency +
        weights[3] * popularity
    )
