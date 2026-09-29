from ..models import Chord


def progression(scale: tuple[int, ...], mode: str, richness: int) -> tuple[Chord, Chord]:
    degrees, symbols = {"ionian": ((0, 4), ("I", "V")), "dorian": ((0, 3), ("i", "IV")),
                        "aeolian": ((0, 5), ("i", "VI"))}[mode]
    return tuple(Chord(
        symbol=symbol, root=scale[degree],
        core=tuple(scale[(degree + offset) % 7] for offset in (0, 2, 4)),
        pitch_classes=tuple(scale[(degree + 2 * i) % 7] for i in range(3 + richness)),
    ) for degree, symbol in zip(degrees, symbols))

