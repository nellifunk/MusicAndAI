import numpy as np


def normalized_entropy(gray: np.ndarray) -> float:
    histogram = np.bincount(gray.ravel(), minlength=256)
    probabilities = histogram[histogram > 0] / gray.size
    return float(np.clip(-np.sum(probabilities * np.log2(probabilities)) / 8, 0, 1))

