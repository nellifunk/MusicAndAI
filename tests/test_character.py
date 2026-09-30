"""Musical invariants for the experimental character engine and v1 fallback."""
from pathlib import Path

import pytest

from artwork_music.app_service import ArtworkMusicService
from artwork_music.models import Composition, Interpretation
from artwork_music.music.character import (
    EMBRACE, TENSION, HORIZON, BREEZE, CURRENT, ORBIT, GEOMETRY, STILLNESS,
    PROCESSION, character_for_artwork, character_rhythm,
)
from artwork_music.music.ensemble import compose
from artwork_music.storage import load_composition

SOURCE = Path(__file__).parents[1] / "output_klimt_kuss/composition.json"
PROFILES = (EMBRACE, TENSION, HORIZON, BREEZE, CURRENT, ORBIT, GEOMETRY, STILLNESS, PROCESSION)


@pytest.fixture(scope="module")
def original():
    return load_composition(SOURCE)


@pytest.fixture(scope="module")
def themed(original):
    return compose(original.raw_analysis(), original.interpretation, EMBRACE.tonic,
                   original.global_music.instruments, character=EMBRACE)


@pytest.mark.parametrize("character", PROFILES, ids=lambda p: p.name)
def test_theme_survives_every_cell_with_valid_harmony_and_timing(original, character):
    result = compose(original.raw_analysis(), tonic=character.tonic, character=character)
    assert result.schema_version == "1.3"
    expected_intervals = tuple(b - a for a, b in zip(character.motif, character.motif[1:]))
    for cell in result.cells:
        phrase = cell.phrase
        assert phrase.rhythm_onsets[:4] == character.motif_onsets
        opening = phrase.lead_scale_degrees[:4]
        assert tuple(b - a for a, b in zip(opening, opening[1:])) == expected_intervals
        assert 16 in phrase.rhythm_onsets
        assert len(phrase.lead.notes) == cell.musical_constraints.lead_note_onsets
        for candidate in phrase.lead_candidates:
            assert candidate.degrees[:4] == opening  # Diversity cannot erase the theme.
            assert all(abs(b - a) <= candidate.max_scale_step_used
                       for a, b in zip(candidate.degrees, candidate.degrees[1:]))
        for role in ("lead", "accompaniment", "bass"):
            register = getattr(result.global_music, role + "_register")
            for note in getattr(phrase, role).notes:
                assert register[0] <= note.pitch <= register[1]
                assert note.pitch % 12 in result.global_music.scale_pitch_classes
                assert note.onset + note.duration <= (16 if note.onset < 16 else 32)
                if role != "lead":
                    assert note.pitch % 12 in result.global_music.harmony[note.onset // 16].core
        notes = phrase.lead.notes
        assert all(a.onset + a.duration <= b.onset for a, b in zip(notes, notes[1:]))
        assert len({n.velocity for n in notes}) > 1


def test_character_is_repeatable_and_preserves_analysis(original, themed):
    repeated = compose(original.raw_analysis(), original.interpretation, EMBRACE.tonic,
                       original.global_music.instruments, character=EMBRACE)
    assert repeated == themed
    assert themed.raw_analysis() == original.raw_analysis()
    assert Composition.model_validate_json(themed.model_dump_json()) == themed
    # The response changes between regions; the shared opening does not make all cells identical.
    assert len({c.phrase.lead_scale_degrees[4:] for c in themed.cells}) >= 4
    assert len({c.phrase.rhythm_onsets[4:] for c in themed.cells}) >= 3


@pytest.mark.parametrize("mood,mode", [(-1, "aeolian"), (0, "dorian"), (1, "ionian")])
def test_mood_changes_mode_without_losing_artwork_theme(original, mood, mode):
    result = compose(original.raw_analysis(), Interpretation(target_valence=mood),
                     EMBRACE.tonic, character=EMBRACE)
    assert result.global_music.mode == mode
    assert result.global_music.character == EMBRACE
    assert all(c.phrase.rhythm_onsets[:4] == EMBRACE.motif_onsets for c in result.cells)


def test_activity_only_densifies_answering_bar():
    for character in PROFILES:
        quiet, busy = character_rhythm(character, 0), character_rhythm(character, 1)
        assert quiet[:4] == busy[:4] == character.motif_onsets
        assert len(quiet) == 7 and len(busy) == 11
        assert len(set(busy)) == len(busy)
        assert all(16 <= t < 32 for t in busy[4:])


def test_authored_and_feature_based_profile_selection(original):
    assert character_for_artwork(original.artwork, original.raw_global_visual) == EMBRACE
    scream = original.artwork.model_copy(update={"title": "The Scream"})
    assert character_for_artwork(scream, original.raw_global_visual) == TENSION
    unknown = original.artwork.model_copy(update={"title": "Untitled"})
    flowing = original.raw_global_visual.model_copy(update={"movement": .8})
    assert character_for_artwork(unknown, flowing) == CURRENT


def test_frontend_defaults_to_theme_but_classic_preserves_saved_midi(original):
    source_bytes = SOURCE.read_bytes()
    services = [ArtworkMusicService(SOURCE), ArtworkMusicService(SOURCE, use_character=False)]
    try:
        modern, classic = services
        assert modern.get_composition().global_music.character == EMBRACE
        assert classic.get_composition() == original
        midi = SOURCE.parent / "midi/cell_0_0.mid"
        assert (classic.session.preview_directory / "midi/cell_0_0.mid").read_bytes() == midi.read_bytes()
        modern.rebuild_interpretation(valence=-1)
        assert modern.get_composition().global_music.character == EMBRACE
        modern.reset_interpretation()
        assert modern.get_composition().global_music.character == EMBRACE
        assert SOURCE.read_bytes() == source_bytes
    finally:
        for service in services:
            service.close()


def test_saved_character_survives_session_reload(tmp_path, themed):
    from artwork_music.controller.session import InterpretationSession
    from artwork_music.storage import write_composition
    write_composition(tmp_path, themed)
    with InterpretationSession(tmp_path / "composition.json") as session:
        assert session.composition == themed
        session.set_mood(0)
        rebuilt = session.rebuild()
        assert rebuilt.global_music.character == EMBRACE
        assert rebuilt.global_music.mode == "dorian"
