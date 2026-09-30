import colorsys

import cv2
import numpy as np
from sklearn.cluster import KMeans
from threadpoolctl import threadpool_limits

from ..models import ColorCluster


def mean_lightness(rgb: np.ndarray) -> float:
    pixels = rgb.astype(np.float64) / 255.0
    return float(((pixels.max(axis=2) + pixels.min(axis=2)) / 2).mean())


def color_clusters(rgb: np.ndarray) -> tuple[ColorCluster, ColorCluster, ColorCluster]:
    pixels = np.ascontiguousarray(rgb, dtype=np.float32) / 255.0
    lab = cv2.cvtColor(pixels, cv2.COLOR_RGB2LAB).reshape(-1, 3)
    distinct = np.unique(lab, axis=0)
    if len(distinct) < 3:
        centers = distinct
        labels = np.argmin(((lab[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2), axis=1)
    else:
        # Fix initialization and numerical reduction threads; use every pixel.
        with threadpool_limits(limits=1):
            km = KMeans(n_clusters=3, random_state=0, n_init=10, algorithm="lloyd").fit(lab)
        centers, labels = km.cluster_centers_, km.labels_
    weights = np.bincount(labels, minlength=len(centers)) / len(lab)
    converted = cv2.cvtColor(np.asarray(centers, dtype=np.float32)[None, :, :], cv2.COLOR_LAB2RGB)[0]
    clusters = []
    for color, weight in zip(converted, weights):
        h, l, s = colorsys.rgb_to_hls(*np.clip(color.astype(float), 0, 1))
        clusters.append(ColorCluster(h=(h * 360) % 360, s=s, l=l, w=float(weight)))
    # Meaningful anchors for a single-color image: duplicate its color with weight 0.
    while len(clusters) < 3:
        clusters.append(clusters[0].model_copy(update={"w": 0.0}))
    return tuple(sorted(clusters, key=lambda c: (-c.w, c.h, c.s, c.l)))

