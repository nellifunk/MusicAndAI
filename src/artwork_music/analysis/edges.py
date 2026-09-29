import cv2
import numpy as np


def canny_edges(gray: np.ndarray) -> np.ndarray:
    median = float(np.median(gray))
    return cv2.Canny(gray, max(0, 0.66 * median), min(255, 1.33 * median))


def edge_density(edges: np.ndarray) -> float:
    return float(np.count_nonzero(edges) / edges.size)

