from pathlib import Path

import pytest

from artwork_music.analysis.image_grid import load_rgb
from artwork_music.analysis.pipeline import analyze_image
from artwork_music.analysis.semantic_sidecar import SidecarSemanticAnalyzer
from artwork_music.models import Artwork, Era
from artwork_music.music.ensemble import compose

PROJECT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def artwork():
    return Artwork(title="Test image", artist="Test author", year=1889,
                   art_movement="Post-Impressionism", music_era=Era.ROMANTIC)


@pytest.fixture(scope="session")
def rgb():
    return load_rgb(PROJECT / "examples/demo.png")


@pytest.fixture(scope="session")
def semantics(rgb, artwork):
    return SidecarSemanticAnalyzer(PROJECT / "examples/demo.semantic.json").analyze(rgb, artwork)


@pytest.fixture(scope="session")
def raw(rgb, artwork, semantics):
    return analyze_image(rgb, artwork, semantics)


@pytest.fixture(scope="session")
def composition(raw):
    return compose(raw)


@pytest.fixture(scope="session")
def relative(raw):
    from artwork_music.music.relative_features import normalize_cells
    return normalize_cells(raw.cells)
