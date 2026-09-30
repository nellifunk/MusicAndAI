import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from artwork_music.analysis.color_features import color_clusters, mean_lightness
from artwork_music.analysis.entropy import normalized_entropy
from artwork_music.analysis.image_grid import grid_overlay, grid_regions, load_rgb
from artwork_music.analysis.pipeline import analyze_image, visual_features
from artwork_music.models import SemanticAnalysis


def test_uniform_entropy_and_missing_orientation():
    features = visual_features(np.full((64, 64, 3), 128, dtype=np.uint8))
    assert features.entropy == pytest.approx(0)
    assert features.edge_density == 0
    assert features.orientation_deg is None
    assert features.lightness == pytest.approx(128 / 255)


def test_entropy_normalization():
    assert normalized_entropy(np.arange(256, dtype=np.uint8).reshape(16, 16)) == pytest.approx(1)
    assert normalized_entropy(np.array([[0, 255]], dtype=np.uint8)) == pytest.approx(1 / 8)


def test_checkerboard_edges():
    y, x = np.mgrid[:128, :128]
    checker = (((x // 8 + y // 8) % 2) * 255).astype(np.uint8)
    structured = visual_features(np.repeat(checker[:, :, None], 3, axis=2))
    uniform = visual_features(np.full((128, 128, 3), 128, dtype=np.uint8))
    assert structured.edge_density > uniform.edge_density
    assert structured.orientation_deg is not None
    assert structured.orientation_deg % 10 == 5


@pytest.mark.parametrize("count", [1, 2, 3])
def test_clusters_padding_and_weights(count):
    rgb = np.array([[[255, 0, 0], [0, 255, 0], [0, 0, 255]][i % count]
                    for i in range(60)], dtype=np.uint8).reshape(6, 10, 3)
    clusters = color_clusters(rgb)
    assert len(clusters) == 3
    assert sum(c.w for c in clusters) == pytest.approx(1)
    assert sum(c.w > 0 for c in clusters) == count
    assert [c.w for c in clusters] == sorted((c.w for c in clusters), reverse=True)
    assert clusters == color_clusters(rgb)
    assert all(0 <= c.h < 360 and 0 <= c.s <= 1 and 0 <= c.l <= 1 for c in clusters)


def test_hsl_lightness_not_hsv_value():
    assert mean_lightness(np.array([[[255, 0, 0], [0, 255, 0]]], dtype=np.uint8)) == 0.5


def test_odd_grid_exact_partition():
    rgb = np.arange(11 * 19 * 3).reshape(11, 19, 3)
    cells = list(grid_regions(rgb))
    assert len(cells) == 16
    assert [(r, c) for r, c, _ in cells] == [(r, c) for r in range(4) for c in range(4)]
    rebuilt = np.concatenate([np.concatenate([cells[r * 4 + c][2] for c in range(4)], axis=1)
                              for r in range(4)], axis=0)
    np.testing.assert_array_equal(rebuilt, rgb)


def test_image_errors_and_overlay(tmp_path, rgb):
    with pytest.raises(ValueError, match="does not exist"):
        load_rgb(tmp_path / "missing.png")
    Image.new("RGB", (3, 8)).save(tmp_path / "small.png")
    with pytest.raises(ValueError, match="at least"):
        load_rgb(tmp_path / "small.png")
    grid_overlay(rgb, tmp_path / "grid.png")
    with Image.open(tmp_path / "grid.png") as image:
        assert image.size == (rgb.shape[1], rgb.shape[0])


def test_analysis_determinism_and_immutable(raw, rgb, artwork, semantics):
    assert raw == analyze_image(rgb, artwork, semantics)
    assert raw.model_dump_json() == analyze_image(rgb, artwork, semantics).model_dump_json()
    with pytest.raises(ValidationError):
        raw.raw_global_visual.entropy = 0.0


def test_smallest_uniform_artwork_composes(artwork, semantics):
    from artwork_music.music.ensemble import compose
    rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    result = compose(analyze_image(rgb, artwork, semantics))
    assert len(result.cells) == 16
    assert all(c.visual.entropy == 0 and c.visual.orientation_deg is None for c in result.cells)
    assert all(len(set(n.pitch for n in c.phrase.lead.notes)) >= 3 for c in result.cells)


@pytest.mark.parametrize("mutation", ["probabilities", "duplicate", "missing", "objects", "nan", "extra"])
def test_semantic_validation(semantics, mutation):
    data = semantics.model_dump(mode="json")
    if mutation == "probabilities":
        data["global_features"]["valence"]["positive"] = 0.9
    elif mutation == "duplicate":
        data["cells"][1] = data["cells"][0]
    elif mutation == "missing":
        data["cells"].pop()
    elif mutation == "objects":
        data["cells"][0]["objects"] *= 4
    elif mutation == "nan":
        data["cells"][0]["movement"] = float("nan")
    else:
        data["global_features"]["instrument"] = "Flute"
    with pytest.raises(ValidationError):
        SemanticAnalysis.model_validate(data)
