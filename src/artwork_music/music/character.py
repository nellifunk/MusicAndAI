"""Small authored themes, varied by the existing measured image features.

These profiles are musical interpretations, not claims about objective meaning.
The first bar states the artwork's theme; the second answers it using local activity.
"""
import unicodedata

from ..models import MusicalCharacter


def profile(name, tonic, motif, onsets, harmony, accompaniment, bass, articulation, tempo=0):
    return MusicalCharacter(name=name, tonic=tonic, motif=motif, motif_onsets=onsets,
                            harmony_degrees=harmony, accompaniment_templates=accompaniment,
                            bass_templates=bass, articulation=articulation, tempo_offset=tempo)


EMBRACE = profile("Golden embrace", "D", (0, 2, 1, 4), (0, 4, 6, 10), (0, 3), (0, 2, 4), (0, 0, 2), .95, -3)
TENSION = profile("Fractured cry", "F#", (0, 1, 4, 1), (0, 3, 6, 11), (0, 1), (1, 3, 5), (1, 3, 4), .55, 10)
HORIZON = profile("Distant horizon", "D", (0, 4, 3, 2), (0, 6, 10, 14), (0, 5), (0, 0, 2), (0, 0, 2), 1., -8)
BREEZE = profile("Dancing breeze", "G", (0, 2, 4, 3), (0, 3, 8, 10), (0, 3), (2, 3, 4), (0, 2, 3), .85, 3)
CURRENT = profile("Rolling current", "A", (4, 3, 1, 0), (0, 2, 6, 10), (0, 6), (2, 4, 5), (1, 2, 4), .85, 5)
ORBIT = profile("Luminous orbit", "E", (0, 3, 2, 4), (0, 3, 6, 12), (0, 5), (2, 4, 4), (0, 2, 3), .9, 0)
GEOMETRY = profile("Measured shapes", "C", (0, 3, 1, 2), (0, 4, 7, 12), (0, 3), (1, 3, 5), (1, 3, 4), .6, 5)
STILLNESS = profile("Quiet interior", "Bb", (2, 1, 0, 3), (0, 6, 8, 12), (0, 3), (0, 1, 2), (0, 0, 1), .95, -5)
PROCESSION = profile("Suspended procession", "C", (0, 1, 3, 2), (0, 4, 10, 12), (0, 5), (0, 1, 3), (0, 1, 3), .8, -2)


def character_for_artwork(artwork, visual):
    title = "".join(c for c in unicodedata.normalize("NFKD", artwork.title.casefold())
                    if not unicodedata.combining(c))
    authored = (
        (("the kiss", "der kuss"), EMBRACE),
        (("scream", "schrei"), TENSION),
        (("wanderer", "fog"), HORIZON),
        (("parasol", "venus", "meadow", "red trees"), BREEZE),
        (("wave", "raft", "medusa"), CURRENT),
        (("starry",), ORBIT),
        (("composition viii", "composition 8", "boogie", "senecio", "black square", "geometric", "adulthood"), GEOMETRY),
        (("pitcher", "arnolfini"), STILLNESS),
        (("matthew", "earthly delights", "creation of adam"), PROCESSION),
        (("blue horse",), CURRENT),
    )
    for names, character in authored:
        if any(name in title for name in names):
            return character
    # Untitled/custom works receive a feature-based family, never a random theme.
    if visual.movement > .55:
        return CURRENT
    if visual.edge_density > .25 and visual.entropy > .65:
        return GEOMETRY
    if visual.lightness > .55:
        return BREEZE
    return STILLNESS


def motif_indices(pitches, character, anchor):
    """Translate the same scale-step contour without clipping individual notes."""
    motif = tuple(d - min(character.motif) for d in character.motif)
    room = len(pitches) - 1 - max(motif)
    if room < 0:
        raise ValueError("Lead register is too narrow for the artwork motif")
    base = max(0, min(room, round(anchor - sum(motif) / len(motif))))
    return tuple(base + d for d in motif)


def character_rhythm(character, activity):
    # Keep the theme intact. Density changes only the answering bar.
    count = 7 + round(4 * activity)
    response = {16 + t for t in character.motif_onsets}
    if count == 7:
        response.remove(16 + character.motif_onsets[1])
    else:
        # Add clear pulses before finer subdivisions; never overlap onsets.
        for onset in (24, 20, 28, 22, 26, 18, 30, 19, 23, 27, 29, 31, 17, 21, 25):
            if len(response) == count - 4:
                break
            response.add(onset)
    return tuple(character.motif_onsets) + tuple(sorted(response))


def character_constraints(constraints, character, relative):
    rhythm = character_rhythm(character, constraints.relative_lead_activity)
    density = min(2, round(2 * relative.relative_entropy))
    activity = min(2, round(2 * relative.relative_activity))
    velocities = constraints.velocities.model_copy(update={
        "lead": max(82, constraints.velocities.lead),
        "accompaniment": max(35, round(.72 * constraints.velocities.accompaniment)),
        "bass": max(32, round(.65 * constraints.velocities.bass)),
    })
    return constraints.model_copy(update={
        "lead_note_onsets": len(rhythm),
        "max_scale_step": max(constraints.max_scale_step,
                              max(abs(b - a) for a, b in zip(character.motif, character.motif[1:]))),
        "accompaniment_template": character.accompaniment_templates[density],
        "bass_template": character.bass_templates[activity],
        "velocities": velocities,
    })
