from ..models import Note, Voice
from .scales import pitches_in_register
from .time import BAR_STEPS


def bass_pitch(pitch_class, register):
    pitches = pitches_in_register(register, (pitch_class,))
    if not pitches:
        raise ValueError(f"Chord pitch {pitch_class} cannot fit bass register {register}")
    center = sum(register) / 2
    return min(pitches, key=lambda p: (abs(p - center), p))


# (chord-core index, onset, duration), in sixteenth-note units.
BASS_TEMPLATES = (
    ((0, 0, 16),),
    ((0, 0, 8), (0, 8, 8)),
    ((0, 0, 8), (2, 8, 8)),
    ((0, 0, 8), (1, 8, 4), (2, 12, 4)),
    ((0, 0, 4), (2, 4, 4), (1, 8, 4), (2, 12, 4)),
)


def compose_bass(music, template, velocity):
    if type(template) is not int or not 0 <= template <= 4:
        raise ValueError("Bass template must be an integer from 0 to 4")
    notes = []
    for bar, chord in enumerate(music.harmony):
        for degree, onset, duration in BASS_TEMPLATES[template]:
            notes.append(Note(pitch=bass_pitch(chord.core[degree], music.bass_register),
                              onset=BAR_STEPS * bar + onset, duration=duration, velocity=velocity))
    return Voice(notes=tuple(notes))
