"""Create a synthetic test artwork and explicitly authored semantic fixture.

This is not automatic semantic inference, and the metadata is fictional.
Run from the project root: python examples/make_demo.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image


def make_demo(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    height, width = 256, 320
    y, x = np.mgrid[:height, :width]
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    palettes = [(37, 60, 94), (100, 145, 146), (221, 177, 108), (231, 217, 181)]
    for row in range(4):
        for col in range(4):
            ys, xs = slice(row * 64, (row + 1) * 64), slice(col * 80, (col + 1) * 80)
            xx, yy = x[ys, xs], y[ys, xs]
            base = np.asarray(palettes[col], dtype=float)
            if row == 0:
                variation = np.zeros_like(xx)
            elif row == 1:
                variation = 35 * np.sin((xx + yy) / 9)
            elif row == 2:
                variation = 40 * (((xx // 8 + yy // 8) % 2) * 2 - 1)
            else:
                variation = 50 * np.sin(xx / 4) * np.cos(yy / 6)
            rgb[ys, xs] = np.clip(base + variation[:, :, None], 0, 255).astype(np.uint8)
    Image.fromarray(rgb).save(directory / "demo.png")
    sidecar = {
        "global_features": {"valence": {"negative": 0.15, "neutral": 0.25, "positive": 0.60}, "movement": 0.36},
        "cells": [{"row": r, "column": c, "movement": round((r * 4 + c) / 15, 4),
                   "objects": [{"label": "abstract pattern", "confidence": 1.0}]}
                  for r in range(4) for c in range(4)],
    }
    (directory / "demo.semantic.json").write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    make_demo(Path(__file__).parent)
