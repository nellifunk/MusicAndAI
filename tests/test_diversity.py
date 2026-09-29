import io
import json
from itertools import combinations
from pathlib import Path

import pytest

from artwork_music.models import Composition, Note, RelativeFeatures, Voice
from artwork_music.music.accompaniment import compose_accompaniment
from artwork_music.music.bass import compose_bass
from artwork_music.music.diagnostics import diagnose, format_diagnostics
from artwork_music.music.diversity import (
    MusicalSignature, musical_distance, musical_signature, pair_penalty,
    select_candidates, visual_distance, visual_signature,
)
from artwork_music.music.ensemble import compose
from artwork_music.music.lead_costs import WEIGHTS, evaluate_lead
from artwork_music.music.relative_features import normalize_cells, percentile_ranks
from artwork_music.music.scales import pitches_in_register
from artwork_music.render.midi_writer import build_midi
from artwork_music.storage import load_composition

PROJECT = Path(__file__).resolve().parents[1]


def test_percentiles_exact_average_ties():
    assert percentile_ranks(range(16)) == pytest.approx([i / 15 for i in range(16)])
    values = (0, 0, 0, 1, 2, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    result = percentile_ranks(values)
    assert result[:3] == pytest.approx((1 / 15,) * 3)
    assert result[4:6] == pytest.approx((4.5 / 15,) * 2)
    assert result[-1] == 1


@pytest.mark.parametrize("values", [(5,) * 16, tuple(i * 1e-8 for i in range(16))])
def test_percentile_constant_range_fallback(values):
    assert percentile_ranks(values) == (0.5,) * 16


def test_percentile_epsilon_boundary():
    assert percentile_ranks((0,) * 15 + (1e-6,))[-1] == 1
    for values in ((0,) * 15, (0,) * 15 + (float("nan"),)):
        with pytest.raises(ValueError):
            percentile_ranks(values)


def test_relative_values_raw_preservation_and_ranked_activity(raw, composition):
    before = raw.model_dump_json()
    q = normalize_cells(raw.cells)
    assert q == normalize_cells(tuple(reversed(raw.cells)))
    activity = percentile_ranks([0.65 * c.visual.movement + 0.35 * c.visual.edge_density for c in raw.cells])
    for i, cell in enumerate(composition.cells):
        assert cell.relative_activity == activity[i]
        assert {name: getattr(cell, name) for name in RelativeFeatures.model_fields} == q[cell.row, cell.column].model_dump()
    assert composition.raw_analysis() == raw
    assert raw.model_dump_json() == before


def test_anchor_and_weight_formula(composition):
    assert sum(WEIGHTS) == pytest.approx(1)
    music = composition.global_music
    cell = composition.cells[0]
    pitches = pitches_in_register(music.lead_register, music.scale_pitch_classes)
    for candidate in cell.phrase.lead_candidates:
        a = cell.musical_constraints.melodic_anchor
        expected = min(1, sum(((d - a) / 6) ** 2 for d in candidate.degrees) / len(candidate.degrees))
        costs = candidate.costs
        assert costs.anchor == pytest.approx(expected)
        assert costs.total == pytest.approx(
            .19 * costs.harmony + .20 * costs.contour + .13 * costs.smoothness + .07 * costs.leap
            + .16 * costs.cadence + .08 * costs.repetition + .17 * costs.anchor)
        assert evaluate_lead(candidate.degrees, pitches, cell.phrase.rhythm_onsets, music.harmony,
            cell.relative_entropy, cell.musical_constraints.contour, a) == costs


def test_all_twenty_candidates_preserve_hard_constraints(composition):
    music = composition.global_music
    for cell in composition.cells:
        candidates = cell.phrase.lead_candidates
        assert len(candidates) == 20
        assert len({candidate.degrees for candidate in candidates}) == 20
        assert list(candidates) == sorted(candidates, key=lambda c: (c.costs.total, c.degrees))
        for candidate in candidates:
            degrees, notes = candidate.degrees, candidate.voice.notes
            assert len(notes) == cell.musical_constraints.lead_note_onsets
            assert len(set(degrees)) >= 3
            assert all(abs(b - a) <= candidate.max_scale_step_used for a, b in zip(degrees, degrees[1:]))
            assert not any(a == b == c for a, b, c in zip(degrees, degrees[1:], degrees[2:]))
            for note in notes:
                assert music.lead_register[0] <= note.pitch <= music.lead_register[1]
                assert note.pitch % 12 in music.scale_pitch_classes
                assert note.duration in (1, 2, 4, 8)
                assert note.onset // 16 == (note.onset + note.duration - 1) // 16
        chosen = candidates[cell.phrase.selected_candidate_index]
        assert cell.phrase.lead == chosen.voice
        assert cell.phrase.lead_costs == chosen.costs


def test_six_accompaniment_and_five_bass_templates_distinct_and_chordal(composition):
    music = composition.global_music
    for composer, count, register in ((compose_accompaniment, 6, music.accompaniment_register),
                                      (compose_bass, 5, music.bass_register)):
        signatures = set()
        for index in range(count):
            voice = composer(music, index, 80)
            signatures.add(tuple((n.pitch, n.onset, n.duration) for n in voice.notes))
            for note in voice.notes:
                assert register[0] <= note.pitch <= register[1]
                assert note.pitch % 12 in music.harmony[note.onset // 16].core
                assert note.onset // 16 == (note.onset + note.duration - 1) // 16
        assert len(signatures) == count
        for index in (-1, count, 0.5):
            with pytest.raises(ValueError):
                composer(music, index, 80)


def test_visual_signature_and_exact_distance(raw, relative):
    cell = raw.cells[0]
    missing = cell.model_copy(update={"visual": cell.visual.model_copy(update={"orientation_deg": None})})
    z = visual_signature(missing, relative[0, 0])
    assert z[-2:] == (0, 0)
    assert visual_distance(z, z) == 0
    assert visual_distance((0, 0, 0, 0, 1, 0), (1, 1, 1, 1, -1, 0)) == pytest.approx((8 / 6) ** 0.5)


def test_musical_distance_interpolation_and_anchor_retention(composition):
    music = composition.global_music
    pitches = pitches_in_register(music.lead_register, music.scale_pitch_classes)
    def voice(indices):
        return Voice(notes=tuple(Note(pitch=pitches[i], onset=k * 4, duration=2, velocity=80)
                                 for k, i in enumerate(indices)))
    a = musical_signature(voice((0, 1, 2, 3)), music)
    b = musical_signature(voice((1, 2, 3, 4)), music)
    assert len(a.contour) == 8 and len(a.onsets) == 32
    assert a.contour[0] == 0 and a.contour[-1] == pytest.approx(3 / (len(pitches) - 1))
    assert musical_distance(a, b) == pytest.approx(.6 / (len(pitches) - 1))
    assert musical_distance(a, a) == 0
    reversed_onsets = MusicalSignature(a.contour, tuple(1 - t for t in a.onsets))
    assert musical_distance(a, reversed_onsets) == pytest.approx(.4)
    assert pair_penalty(.8, .3) == pytest.approx(.25)
    assert pair_penalty(.2, .3) == 0


def test_coordinate_descent_objective_and_determinism(raw, composition):
    selection = composition.diversity_selection
    assert 1 <= selection.passes_completed <= 5
    assert len(selection.objective_history) == selection.passes_completed + 1
    assert all(b <= a for a, b in zip(selection.objective_history, selection.objective_history[1:]))
    assert selection.objective_history[-1] == pytest.approx(composition.diagnostics.selection_objective)
    assert compose(raw) == composition
    assert compose(raw.model_copy(update={"cells": tuple(reversed(raw.cells))})) == composition


def test_ties_choose_lexicographic_candidates_independent_of_candidate_order(raw, composition):
    # Visually identical cells => pairwise penalties exactly zero for every candidate.
    cells = [c.model_copy(update={"visual": raw.cells[0].visual}) for c in raw.cells]
    relative = normalize_cells(cells)
    base = composition.cells[0].phrase.lead_candidates[:2]
    base = tuple(c.model_copy(update={"costs": c.costs.model_copy(update={"total": 0.5})}) for c in base)
    candidates = [tuple(reversed(base)) for _ in cells]
    chosen, metadata = select_candidates(cells, relative, candidates, composition.global_music)
    expected = min(c.degrees for c in base)
    assert all(candidates[i][index].degrees == expected for i, index in enumerate(chosen))
    assert metadata.converged


def test_legacy_load_keeps_midi_and_reports_duplicates():
    legacy = load_composition(PROJECT / "output_klimt_kuss_v1/composition.json")
    assert legacy.schema_version == "1.0"
    diagnostics = diagnose(legacy.cells, legacy.global_music)
    assert diagnostics.unique_lead_pitch_sequences == 5
    assert diagnostics.exact_duplicate_lead_sequences == 11
    assert diagnostics.largest_duplicate_group == 9
    text = format_diagnostics(diagnostics)
    assert "Duplicate pitches" in text and "(0, 2)" in text
    for cell in legacy.cells:
        output = io.BytesIO()
        build_midi(legacy, [cell]).save(file=output)
        assert output.getvalue() == (PROJECT / f"output_klimt_kuss_v1/midi/cell_{cell.row}_{cell.column}.mid").read_bytes()


@pytest.fixture(scope="module")
def klimt():
    legacy = load_composition(PROJECT / "output_klimt_kuss_v1/composition.json")
    return compose(legacy.raw_analysis()), legacy


def test_klimt_acceptance_and_visual_distance_relationship(klimt):
    current, legacy = klimt
    d = current.diagnostics
    assert current.raw_analysis() == legacy.raw_analysis()
    assert d.unique_lead_pitch_sequences >= 12
    assert d.largest_duplicate_group <= 3
    assert d.unique_accompaniment_patterns == 6
    assert d.unique_bass_patterns == 5
    before = diagnose(legacy.cells, legacy.global_music)
    assert d.mean_pairwise_musical_distance > before.mean_pairwise_musical_distance
    q = normalize_cells(current.cells)
    visual = [visual_signature(c, q[c.row, c.column]) for c in current.cells]
    musical = [musical_signature(c.phrase.lead, current.global_music) for c in current.cells]
    pairs = sorted((visual_distance(visual[g], visual[h]), musical_distance(musical[g], musical[h]))
                   for g, h in combinations(range(16), 2))
    assert sum(m for _, m in pairs[-30:]) > sum(m for _, m in pairs[:30])


def test_klimt_all_selected_notes_and_rebuilt_midi(klimt):
    current, legacy = klimt
    rebuilt = compose(legacy.raw_analysis())
    for first, second in zip(current.cells, rebuilt.cells):
        for role in ("lead", "accompaniment", "bass"):
            register = getattr(current.global_music, role + "_register")
            for note in getattr(first.phrase, role).notes:
                assert register[0] <= note.pitch <= register[1]
                assert note.pitch % 12 in current.global_music.scale_pitch_classes
                if role != "lead":
                    assert note.pitch % 12 in current.global_music.harmony[note.onset // 16].core
        a, b = io.BytesIO(), io.BytesIO()
        build_midi(current, [first]).save(file=a)
        build_midi(rebuilt, [second]).save(file=b)
        assert a.getvalue() == b.getvalue()


def test_version_11_rejects_missing_relative_data(composition):
    data = composition.model_dump(mode="json")
    data["cells"][0]["relative_lightness"] = None
    with pytest.raises(ValueError):
        Composition.model_validate(data)
