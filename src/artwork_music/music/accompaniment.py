from itertools import combinations

from ..models import Note, Voice
from .scales import pitches_in_register
from .time import BAR_STEPS


def valid_inversions(chord, register):
    pitches = pitches_in_register(register, chord.core)
    voicings = tuple(v for v in combinations(pitches, 3)
                     if len({p % 12 for p in v}) == 3 and v[-1] - v[0] < 12)
    if not voicings:
        raise ValueError(f"No compact chord inversion fits accompaniment register {register}")
    return voicings


def chord_voicings(music):
    center = sum(music.accompaniment_register) / 2
    first = min(valid_inversions(music.harmony[0], music.accompaniment_register),
                key=lambda v: (abs(sum(v) / 3 - center), v))
    second = min(valid_inversions(music.harmony[1], music.accompaniment_register),
                 key=lambda v: (sum(abs(a - b) for a, b in zip(v, first)), v))
    return first, second


TEMPLATE_NAMES = (
    "sustained chord", "half-note chord pulses", "quarter upward arpeggio",
    "quarter down-up arpeggio", "eighth rolling arpeggio", "syncopated broken chord",
)


def accompaniment_pattern(template, voicing):
    if type(template) is not int or not 0 <= template <= 5:
        raise ValueError("Accompaniment template must be an integer from 0 to 5")
    if template == 0:
        return tuple((pitch, 0, 16) for pitch in voicing)
    if template == 1:
        return tuple((pitch, onset, 8) for onset in (0, 8) for pitch in voicing)
    if template == 2:
        return tuple((voicing[i], 4 * k, 4) for k, i in enumerate((0, 1, 2, 0)))
    if template == 3:
        return tuple((voicing[i], 4 * k, 4) for k, i in enumerate((2, 1, 0, 1)))
    if template == 4:
        return tuple((voicing[i], 2 * k, 2) for k, i in enumerate((0, 1, 2, 1, 2, 1, 0, 1)))
    return tuple((voicing[i], onset, 1) for onset, i in (
        (0, 0), (3, 1), (5, 2), (8, 1), (10, 0), (11, 1), (13, 2), (15, 1),
    ))


def compose_accompaniment(music, template, velocity):
    notes = []
    for bar, voicing in enumerate(chord_voicings(music)):
        pattern = accompaniment_pattern(template, voicing)
        notes.extend(Note(pitch=pitch, onset=BAR_STEPS * bar + onset, duration=duration, velocity=velocity)
                     for pitch, onset, duration in pattern)
    return Voice(notes=tuple(notes))
