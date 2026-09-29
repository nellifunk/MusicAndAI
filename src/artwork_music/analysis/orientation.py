import cv2
import numpy as np


def dominant_orientation(gray: np.ndarray, edges: np.ndarray) -> float | None:
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.hypot(gx, gy)
    mask = (edges > 0) & (magnitude > 0)
    # Explicit V1 reliability threshold: at least 8 usable edge pixels.
    if np.count_nonzero(mask) < 8:
        return None
    angles = np.degrees(np.arctan2(gy[mask], gx[mask])) % 180
    histogram, _ = np.histogram(angles, bins=18, range=(0, 180), weights=magnitude[mask])
    return float(10 * np.argmax(histogram) + 5)

