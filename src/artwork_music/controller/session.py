import re
import shutil
import tempfile
from pathlib import Path

from ..models import Interpretation
from ..music.ensemble import compose
from ..render.midi_player import MidoOutput
from ..storage import load_composition, write_composition


class InterpretationSession:
    """Shared application actions for terminal and future hardware adapters."""
    def __init__(self, composition_path: Path, player=None, save_root: Path | None = None):
        self.source = composition_path.resolve()
        self.composition = load_composition(self.source)
        self.raw = self.composition.raw_analysis()
        self.pending = self.composition.interpretation
        self.player = player if player is not None else MidoOutput()
        parent = self.source.parent
        # Reopening a saved interpretation still saves alongside other interpretations.
        default_root = parent.parent if parent.parent.name == "interpretations" else parent / "interpretations"
        self.save_root = save_root if save_root is not None else default_root
        self._temporary = tempfile.TemporaryDirectory(prefix="artwork-music-")
        self.preview_directory = Path(self._temporary.name)
        write_composition(self.preview_directory, self.composition)

    @property
    def dirty(self):
        return self.pending != self.composition.interpretation

    def cell(self, row, col):
        if type(row) is not int or type(col) is not int or not (0 <= row < 4 and 0 <= col < 4):
            raise ValueError("Row and column must be integers from 0 to 3")
        return next(c for c in self.composition.cells if c.row == row and c.column == col)

    def set_offset(self, dimension, value):
        fields = {"valence": "delta_valence", "energy": "delta_movement",
                  "complexity": "delta_complexity", "brightness": "delta_lightness"}
        if dimension not in fields:
            raise ValueError("Dimension must be valence, energy, complexity, or brightness")
        data = self.pending.model_dump()
        # The hardware mood scale is [-1, 1], while the legacy interpretation
        # model intentionally limits manual offsets to [-0.5, 0.5]. Preserve
        # the continuous hardware control by saturating at that model limit.
        if dimension == "valence":
            value = max(-0.5, min(0.5, value))
        data[fields[dimension]] = value
        self.pending = Interpretation.model_validate(data)

    def rebuild(self):
        candidate = compose(self.raw, self.pending, self.composition.global_music.tonic,
                            self.composition.global_music.instruments)
        write_composition(self.preview_directory, candidate)
        self.composition = candidate
        return candidate

    def reset(self):
        self.pending = Interpretation()
        return self.rebuild()

    def play(self, row, col):
        self.cell(row, col)
        path = self.preview_directory / "midi" / f"cell_{row}_{col}.mid"
        message = self.player.play(path)
        if self.dirty:
            message += "\nPending offsets have not been applied; run rebuild."
        return message

    def save(self, name):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name):
            raise ValueError("Name must be 1..64 letters, digits, underscores or hyphens; start with a letter or digit")
        if self.dirty:
            raise ValueError("Pending interpretation changes: run rebuild before saving")
        self.save_root.mkdir(parents=True, exist_ok=True)
        destination = self.save_root / name
        # Exclusive directory creation prevents accidentally replacing personal versions.
        destination.mkdir(exist_ok=False)
        try:
            write_composition(destination, self.composition)
        except Exception:
            shutil.rmtree(destination)
            raise
        return destination

    def close(self):
        self._temporary.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
