import math

import pytest

from artwork_music.models import ColorCluster, Era, Interpretation
from artwork_music.music.eras import music_era
from artwork_music.music.global_mapping import global_mapping, load_palette, select_mode
from artwork_music.music.local_mapping import color_distance, local_mapping, pan_for_column
from artwork_music.music.scales import scale_pitch_classes
from artwork_music.render.midi_writer import pan_cc


@pytest.mark.parametrize("value,mode", [(-1, "aeolian"), (-0.334, "aeolian"), (-1/3, "dorian"),
                                      (0, "dorian"), (0.333, "dorian"), (1/3, "ionian"), (1, "ionian")])
def test_mode_boundaries(value, mode):
    assert select_mode(value) == mode


@pytest.mark.parametrize("target,mode", [(-1.0, "aeolian"), (0.0, "dorian"), (1.0, "ionian")])
def test_absolute_mood_target_overrides_artwork_valence(raw, target, mode):
    effective, music = global_mapping(
        raw.raw_global_visual,
        Interpretation(target_valence=target),
        raw.artwork.music_era,
    )
    assert effective.valence == target
    assert music.mode == mode


@pytest.mark.parametrize("movement,bpm", [(0, 65), (1, 120), (0.36, 85)])
def test_tempo(raw, movement, bpm):
    visual = raw.raw_global_visual.model_copy(update={"movement": movement})
    _, music = global_mapping(visual, Interpretation(), raw.artwork.music_era)
    assert music.tempo_bpm == bpm


@pytest.mark.parametrize("year,era", [(1449, Era.MEDIEVAL), (1450, Era.RENAISSANCE),
    (1599, Era.RENAISSANCE), (1600, Era.BAROQUE), (1749, Era.BAROQUE), (1750, Era.CLASSICAL),
    (1819, Era.CLASSICAL), (1820, Era.ROMANTIC), (1889, Era.ROMANTIC),
    (1890, Era.IMPRESSIONIST), (1919, Era.IMPRESSIONIST), (1920, Era.MODERN)])
def test_era_boundaries(year, era):
    assert music_era(year) == era


def test_era_override_and_invalid_years():
    assert music_era(1889, Era.IMPRESSIONIST) == Era.IMPRESSIONIST
    assert music_era(None, Era.BAROQUE) == Era.BAROQUE
    for year in [None, 0, -1, 10000, True, 1889.5, "1889"]:
        with pytest.raises(ValueError):
            music_era(year)


@pytest.mark.parametrize("column,pan,cc", [(0, -1, 0), (1, -1/3, 42), (2, 1/3, 85), (3, 1, 127)])
def test_pan(column, pan, cc):
    assert pan_for_column(column) == pytest.approx(pan)
    assert pan_cc(pan_for_column(column)) == cc


@pytest.mark.parametrize("mode,scale", [("ionian", (2, 4, 6, 7, 9, 11, 1)),
                                     ("dorian", (2, 4, 5, 7, 9, 11, 0)),
                                     ("aeolian", (2, 4, 5, 7, 9, 10, 0))])
def test_scales(mode, scale):
    assert scale_pitch_classes("D", mode) == scale
    assert len(scale_pitch_classes("Bb", mode)) == 7


@pytest.mark.parametrize("entropy,size", [(0.39, 3), (0.4, 4), (0.749, 4), (0.75, 5)])
def test_richness(raw, entropy, size):
    raw_global = raw.raw_global_visual.model_copy(update={"entropy": entropy})
    _, music = global_mapping(raw_global, Interpretation(), raw.artwork.music_era)
    assert all(len(chord.pitch_classes) == size for chord in music.harmony)
    assert all(set(chord.pitch_classes) <= set(music.scale_pitch_classes) for chord in music.harmony)


def test_offsets_clipping_and_registers(raw):
    visual = raw.raw_global_visual.model_copy(update={"movement": 0.9, "lightness": 0.9, "entropy": 0.1})
    effective, music = global_mapping(visual, Interpretation(delta_movement=0.5, delta_lightness=0.5,
        delta_complexity=-0.5), raw.artwork.music_era)
    assert effective.movement == 1 and effective.lightness == 1 and effective.entropy == 0
    assert music.lead_register == (65, 81)
    assert music.accompaniment_register == (57, 69)
    assert music.bass_register == (45, 57)
    assert music.complexity_budget == 0


@pytest.mark.parametrize("orientation,contour,verticality", [(None, 0, 0), (0, 0, 0),
    (45, 1, math.sqrt(0.5)), (90, 0, 1), (135, -1, math.sqrt(0.5))])
def test_orientation(raw, composition, relative, orientation, contour, verticality):
    visual = raw.cells[0].visual.model_copy(update={"orientation_deg": orientation})
    cell = raw.cells[0].model_copy(update={"visual": visual})
    constraints = local_mapping(cell, composition.global_music, relative[cell.row, cell.column])
    assert constraints.contour == pytest.approx(contour)
    assert constraints.verticality == pytest.approx(verticality)


def test_hue_distance_wraps():
    a = ColorCluster(h=359, s=0.5, l=0.5, w=1)
    b = a.model_copy(update={"h": 1})
    assert color_distance(a, b) == pytest.approx(0.5 * 2 / 180)


def test_local_formulas_and_weights(raw, composition, relative):
    for cell in raw.cells:
        q = relative[cell.row, cell.column]
        c = local_mapping(cell, composition.global_music, q)
        assert c.activity == pytest.approx(0.65 * cell.visual.movement + 0.35 * cell.visual.edge_density)
        assert c.relative_lead_activity == pytest.approx(0.65 * q.relative_movement + 0.35 * q.relative_edge_density)
        assert c.lead_note_onsets == 4 + round(10 * c.relative_lead_activity)
        assert c.target_offbeats == round(q.relative_entropy * min(8, c.lead_note_onsets - 2))
        assert c.complexity == pytest.approx((composition.global_music.complexity_budget + q.relative_entropy) / 2)
        assert c.melodic_anchor == round(6 * q.relative_lightness)
        assert c.accompaniment_template == round(5 * q.relative_entropy)
        assert c.bass_template == round(4 * q.relative_activity)
        assert c.max_scale_step == 1 + math.floor(2 * c.complexity + c.verticality)
        assert sum(c.voice_weights.model_dump().values()) == pytest.approx(1)
        assert min(c.voice_weights.model_dump().values()) >= 0.1 / 1.3 - 1e-12
        assert c.velocities.lead == round(55 + 45 * c.voice_weights.lead)


def test_rows_and_object_labels_do_not_map_to_music(raw, composition, relative):
    from artwork_music.models import DetectedObject
    source = raw.cells[0]
    moved = source.model_copy(update={"row": 3, "visual": source.visual.model_copy(update={
        "objects": (DetectedObject(label="person", confidence=1),)})})
    q = relative[source.row, source.column]
    assert local_mapping(source, composition.global_music, q) == local_mapping(moved, composition.global_music, q)


@pytest.mark.parametrize("era", list(Era))
def test_all_palettes_resolve(era):
    assert len(load_palette(era).model_dump()) == 3


def test_invalid_palette_is_actionable(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("Romantic: [unclosed")
    with pytest.raises(ValueError, match="Invalid instrument palette"):
        load_palette(Era.ROMANTIC, path)
