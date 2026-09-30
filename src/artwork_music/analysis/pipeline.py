import hashlib

import cv2

from ..models import GlobalVisual, LocalVisual, RawAnalysis, RawCell, VisualFeatures
from .color_features import color_clusters, mean_lightness
from .edges import canny_edges, edge_density
from .entropy import normalized_entropy
from .image_grid import grid_regions
from .orientation import dominant_orientation


def visual_features(rgb) -> VisualFeatures:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = canny_edges(gray)
    return VisualFeatures(
        entropy=normalized_entropy(gray), lightness=mean_lightness(rgb),
        edge_density=edge_density(edges), orientation_deg=dominant_orientation(gray, edges),
        color_clusters=color_clusters(rgb),
    )


def analyze_image(rgb, artwork, semantics) -> RawAnalysis:
    visual = visual_features(rgb)
    global_semantics = semantics.global_features
    probs = global_semantics.valence
    semantic_cells = {(c.row, c.column): c for c in semantics.cells}
    cells = []
    for row, column, crop in grid_regions(rgb):
        semantic = semantic_cells[row, column]
        cells.append(RawCell(row=row, column=column, visual=LocalVisual(
            **visual_features(crop).model_dump(), movement=semantic.movement, objects=semantic.objects,
        )))
    return RawAnalysis(
        image_sha256=hashlib.sha256(str(rgb.shape).encode() + rgb.tobytes()).hexdigest(),
        image_size=(rgb.shape[1], rgb.shape[0]), artwork=artwork,
        raw_global_visual=GlobalVisual(
            **visual.model_dump(), valence_probs=probs, valence=probs.positive - probs.negative,
            movement=global_semantics.movement,
        ), cells=tuple(cells),
    )
