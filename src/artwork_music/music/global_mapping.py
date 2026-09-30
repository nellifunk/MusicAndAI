from importlib.resources import files
from pathlib import Path

import pretty_midi
import yaml

from ..models import ColorAnchors, EffectiveGlobal, Era, GlobalMusic, Instruments
from .harmony import progression
from .scales import scale_pitch_classes


def clip(value, low=0, high=1):
    return min(high, max(low, value))


def select_mode(valence: float) -> str:
    return "aeolian" if valence < -1/3 else "dorian" if valence < 1/3 else "ionian"


def effective_values(raw, offsets) -> EffectiveGlobal:
    valence = (offsets.target_valence if offsets.target_valence is not None
               else clip(raw.valence + offsets.delta_valence, -1, 1))
    return EffectiveGlobal(
        valence=valence,
        movement=clip(raw.movement + offsets.delta_movement),
        entropy=clip(raw.entropy + offsets.delta_complexity),
        lightness=clip(raw.lightness + offsets.delta_lightness),
    )


def load_palette(era: Era, path: Path | None = None) -> Instruments:
    source = path if path else files("artwork_music").joinpath("config/instrument_palettes.yaml")
    try:
        data = yaml.safe_load(source.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid instrument palette YAML: {source}") from exc
    if not isinstance(data, dict) or era.value not in data:
        raise ValueError(f"Instrument palette is missing {era.value}")
    instruments = Instruments.model_validate(data[era.value])
    for value in instruments.model_dump().values():
        names = value if isinstance(value, (list, tuple)) else [value]
        for name in names:
            try:
                pretty_midi.instrument_name_to_program(name)
            except ValueError as exc:
                raise ValueError(f"Unknown General MIDI instrument in palette: {name}") from exc
    return instruments


def global_mapping(raw, offsets, era, tonic="D", instruments=None, character=None):
    effective = effective_values(raw, offsets)
    mode = select_mode(effective.valence)
    scale = scale_pitch_classes(tonic, mode)
    richness = 0 if effective.entropy < 0.40 else 1 if effective.entropy < 0.75 else 2
    if character is not None:
        richness = min(richness, 1)
    center = round(48 + 24 * effective.lightness)
    dark, middle, bright = sorted(raw.color_clusters, key=lambda c: (c.l, c.h, c.s, -c.w))
    return effective, GlobalMusic(
        tonic=tonic[0].upper() + tonic[1:], mode=mode,
        tempo_bpm=clip(round(65 + 55 * effective.movement) + (character.tempo_offset if character else 0), 65, 120),
        scale_pitch_classes=scale,
        lead_register=(clip(center - 7, 0, 127), clip(center + 9, 0, 127)),
        accompaniment_register=(clip(center - 15, 0, 127), clip(center - 3, 0, 127)),
        bass_register=(clip(center - 27, 0, 127), clip(center - 15, 0, 127)),
        harmony=progression(scale, mode, richness, character.harmony_degrees if character else None), harmonic_richness=richness,
        complexity_budget=effective.entropy, instruments=instruments or load_palette(era),
        color_anchors=ColorAnchors(lead=bright, accompaniment=middle, bass=dark),
        character=character,
    )
