MODES = {"ionian": (0, 2, 4, 5, 7, 9, 11), "dorian": (0, 2, 3, 5, 7, 9, 10),
         "aeolian": (0, 2, 3, 5, 7, 8, 10)}
NATURALS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def tonic_pitch_class(tonic: str) -> int:
    if len(tonic) not in (1, 2) or tonic[0].upper() not in NATURALS:
        raise ValueError("Tonic must be a note name such as D, F#, or Bb (without octave)")
    accidental = tonic[1:]
    if accidental not in ("", "#", "b"):
        raise ValueError("Tonic accidental must be # or b")
    return (NATURALS[tonic[0].upper()] + {"": 0, "#": 1, "b": -1}[accidental]) % 12


def scale_pitch_classes(tonic: str, mode: str) -> tuple[int, ...]:
    root = tonic_pitch_class(tonic)
    return tuple((root + step) % 12 for step in MODES[mode])


def pitches_in_register(register, pitch_classes) -> tuple[int, ...]:
    return tuple(p for p in range(register[0], register[1] + 1) if p % 12 in pitch_classes)

