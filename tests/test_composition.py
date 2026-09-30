from itertools import product

import pytest

from artwork_music.models import Interpretation
from artwork_music.music.accompaniment import chord_voicings, compose_accompaniment, valid_inversions
from artwork_music.music.bass import compose_bass
from artwork_music.music.global_mapping import global_mapping
from artwork_music.music.lead_composer import beam_search, compose_lead
from artwork_music.music.lead_costs import evaluate_lead
from artwork_music.music.local_mapping import local_mapping
from artwork_music.music.rhythm import generate_rhythm, lead_durations, rhythm_cost
from artwork_music.music.scales import pitches_in_register


def assert_lead(voice, degrees, music, constraints, onsets, used):
    assert len(voice.notes) == constraints.lead_note_onsets
    assert len(set(degrees)) >= 3
    assert all(abs(b - a) <= used for a, b in zip(degrees, degrees[1:]))
    assert not any(a == b == c for a, b, c in zip(degrees, degrees[1:], degrees[2:]))
    for note in voice.notes:
        assert music.lead_register[0] <= note.pitch <= music.lead_register[1]
        assert note.pitch % 12 in music.scale_pitch_classes
        assert note.duration in (1, 2, 4, 8)
        assert note.onset // 16 == (note.onset + note.duration - 1) // 16
    assert tuple(n.onset for n in voice.notes) == onsets
    for a, b in zip(voice.notes, voice.notes[1:]):
        assert a.onset + a.duration <= b.onset


def test_all_cells_ensemble_and_lead(composition):
    music = composition.global_music
    for cell in composition.cells:
        phrase, c = cell.phrase, cell.musical_constraints
        assert phrase.length_eighths == 16 and phrase.length_sixteenths == 32
        assert phrase.bars == 2 and phrase.time_signature == (4, 4)
        assert 0 in phrase.rhythm_onsets and 16 in phrase.rhythm_onsets
        assert_lead(phrase.lead, phrase.lead_scale_degrees, music, c, phrase.rhythm_onsets, phrase.max_scale_step_used)
        for role in ("accompaniment", "bass"):
            voice = getattr(phrase, role)
            register = getattr(music, role + "_register")
            for note in voice.notes:
                assert register[0] <= note.pitch <= register[1]
                assert note.pitch % 12 in music.harmony[note.onset // 16].core
        signatures = {tuple((n.pitch, n.onset, n.duration) for n in getattr(phrase, role).notes)
                      for role in ("lead", "accompaniment", "bass")}
        assert len(signatures) == 3
        assert max(n.onset + n.duration for n in phrase.bass.notes) == 32


@pytest.mark.parametrize("count,target", list(product(range(4, 15), range(9))))
def test_rhythm_constraints_and_deterministic(count, target):
    onsets, score = generate_rhythm(count, target)
    assert len(onsets) == count and len(set(onsets)) == count
    assert 0 in onsets and 16 in onsets
    assert all(0 <= t < 32 for t in onsets)
    assert score == pytest.approx(rhythm_cost(onsets, target))
    assert generate_rhythm(count, target) == (onsets, score)


def test_rhythm_uses_sixteenths_and_lexicographic_ties():
    assert any(t % 2 for t in generate_rhythm(14, 8)[0])
    assert generate_rhythm(4, 0)[0] == min(
        (generate_rhythm(4, 0)[0],),
        key=lambda s: (rhythm_cost(s, 0), s),
    )


def test_duration_gaps_become_rests():
    assert lead_durations((0, 3, 7, 16, 29)) == (2, 4, 8, 8, 2)


@pytest.mark.parametrize("valence,lightness,entropy,orientation", [
    (-1, 0, 0, None), (0, 0.5, 0.5, 45), (1, 1, 1, 135),
    (-1/3, 1, 0, 90), (1/3, 0, 1, 5), (0, 0, 1, 175),
])
def test_lead_extreme_contexts(raw, relative, valence, lightness, entropy, orientation):
    visual = raw.raw_global_visual.model_copy(update={"valence": valence, "lightness": lightness, "entropy": entropy})
    _, music = global_mapping(visual, Interpretation(), raw.artwork.music_era, tonic="Bb")
    local = raw.cells[-1].visual.model_copy(update={"entropy": entropy, "orientation_deg": orientation})
    cell = raw.cells[-1].model_copy(update={"visual": local})
    q = relative[cell.row, cell.column].model_copy(update={"relative_entropy": entropy, "relative_lightness": lightness})
    constraints = local_mapping(cell, music, q)
    onsets, _ = generate_rhythm(constraints.lead_note_onsets, constraints.target_offbeats)
    voice, degrees, costs, used, _ = compose_lead(music, local, constraints, onsets)
    assert_lead(voice, degrees, music, constraints, onsets, used)
    assert 0 <= costs.total <= 1


def test_lead_cost_hand_calculated(composition):
    # D major, I -> V, degrees D E F# A; final A is the dominant root.
    harmony = composition.global_music.harmony
    degrees, pitches, onsets = (0, 1, 2, 4), (62, 64, 66, 67, 69), (0, 4, 8, 12)
    # Use triads to avoid extensions changing the expected harmony cost.
    from artwork_music.music.harmony import progression
    harmony = progression((2, 4, 6, 7, 9, 11, 1), "ionian", 0)
    costs = evaluate_lead(degrees, pitches, onsets, harmony, 0, 0)
    assert costs.harmony == 0.25  # E on I; all onsets remain in the first sixteenth-note bar.
    assert costs.contour == pytest.approx(9 / 16)
    assert costs.smoothness == pytest.approx(0.2 / 3)
    assert costs.leap == 0 and costs.cadence == 0 and costs.repetition == 0
    assert costs.anchor == pytest.approx(21 / 144)
    assert costs.total == pytest.approx(0.19 * 0.25 + 0.20 * 9 / 16 + 0.13 * 0.2 / 3 + 0.17 * 21 / 144)


def test_beam_matches_exhaustive_for_small_space(composition):
    pitches, onsets = (62, 64, 66), (0, 4, 8, 12)
    harmony = composition.global_music.harmony
    legal = [s for s in product(range(3), repeat=4) if len(set(s)) >= 3
             and not any(a == b == c for a, b, c in zip(s, s[1:], s[2:]))]
    expected = min(legal, key=lambda s: (evaluate_lead(s, pitches, onsets, harmony, 0.5, 0).total, s))
    assert beam_search(pitches, onsets, harmony, 0.5, 0, 2) == expected


def test_leap_and_repetition_costs(composition):
    # Large upward leap followed by another upward step is unresolved.
    costs = evaluate_lead((0, 3, 4, 4), (62, 64, 66, 67, 69), (0, 4, 8, 12),
                          composition.global_music.harmony, 0.5, 0)
    assert costs.leap == 0.5
    assert costs.repetition == pytest.approx(1 / 3)
    assert costs.smoothness == pytest.approx((0.6 + 0 + 0.25) / 3)
    assert costs.cadence == 0  # Root A, approached by repetition.


def test_cadence_approach_penalty(composition):
    costs = evaluate_lead((1, 0, 4, 0), (69, 71, 73, 74, 76), (0, 4, 8, 12),
                          composition.global_music.harmony, 0.5, 0)
    assert costs.cadence == 0.25  # Root A, but a four-scale-step final approach.
    assert costs.leap == 1  # Opposite direction but still a large second leap.


def test_impossible_lead_and_relaxation(raw, composition, monkeypatch, caplog):
    import artwork_music.music.lead_composer as module
    cell = composition.cells[0]
    c = cell.musical_constraints.model_copy(update={"max_scale_step": 1})
    real = module.beam_candidates
    calls = []
    def fail_initial(*args, **kwargs):
        calls.append(args[-1])
        return () if args[-1] == 1 else real(*args, **kwargs)
    monkeypatch.setattr(module, "beam_candidates", fail_initial)
    result = module.compose_lead(composition.global_music, cell.visual, c, cell.phrase.rhythm_onsets)
    assert calls == [1, 2] and result[3] == 2 and result[4]
    assert "relaxed" in caplog.text
    monkeypatch.setattr(module, "beam_candidates", lambda *args, **kwargs: ())
    with pytest.raises(ValueError, match="No valid lead"):
        module.compose_lead(composition.global_music, cell.visual, c, cell.phrase.rhythm_onsets)


@pytest.mark.parametrize("template,count", [(0, 6), (1, 12), (2, 8), (3, 8), (4, 16), (5, 16)])
def test_accompaniment_patterns(composition, template, count):
    assert len(compose_accompaniment(composition.global_music, template, 75).notes) == count


def test_voicing_optimum(composition):
    music = composition.global_music
    first, second = chord_voicings(music)
    candidates = valid_inversions(music.harmony[1], music.accompaniment_register)
    assert second == min(candidates, key=lambda v: (sum(abs(a-b) for a, b in zip(v, first)), v))


@pytest.mark.parametrize("template,durations", [(0, (16,)), (1, (8, 8)), (2, (8, 8)), (3, (8, 4, 4)), (4, (4, 4, 4, 4))])
def test_bass_templates(composition, template, durations):
    bass = compose_bass(composition.global_music, template, 75)
    assert tuple(n.duration for n in bass.notes) == durations * 2
