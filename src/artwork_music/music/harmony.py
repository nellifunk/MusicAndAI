from ..models import Chord


def progression(scale: tuple[int, ...], mode: str, richness: int, degrees=None) -> tuple[Chord, Chord]:
    if degrees is None:
        degrees, symbols = {"ionian": ((0, 4), ("I", "V")), "dorian": ((0, 3), ("i", "IV")),
                            "aeolian": ((0, 5), ("i", "VI"))}[mode]
    else:
        roman = ("I", "II", "III", "IV", "V", "VI", "VII")
        symbols = tuple(roman[d] if (scale[(d + 2) % 7] - scale[d]) % 12 == 4
                        else roman[d].lower() for d in degrees)
    return tuple(Chord(
        symbol=symbol, root=scale[degree],
        core=tuple(scale[(degree + offset) % 7] for offset in (0, 2, 4)),
        pitch_classes=tuple(scale[(degree + 2 * i) % 7] for i in range(3 + richness)),
    ) for degree, symbol in zip(degrees, symbols))

