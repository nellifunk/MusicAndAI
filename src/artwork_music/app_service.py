"""Thin stateful facade for the local NiceGUI frontend."""
from pathlib import Path

from .controller.session import InterpretationSession
from .render.midi_player import MidoOutput


class ArtworkMusicService:
    def __init__(self, composition_path: Path, player=None, use_character=True):
        self.session = InterpretationSession(composition_path, player=player or MidoOutput())
        if use_character and self.session.composition.global_music.character is None:
            try:
                self.session.enable_artwork_character()
            except Exception:
                self.session.close()
                raise
        self.selected_index: int | None = None

    def get_composition(self):
        return self.session.composition

    def play_region(self, index: int) -> str:
        if type(index) is not int or not 0 <= index < 16:
            raise ValueError("Region index must be between 0 and 15")
        self.selected_index = index
        return self.session.play(index // 4, index % 4)

    def stop_playback(self) -> None:
        self.session.player.stop()

    def rebuild_interpretation(self, valence=0.0, movement=0.0, complexity=0.0, lightness=0.0):
        self.session.set_mood(float(valence))
        for name, value in (("energy", movement), ("complexity", complexity),
                            ("brightness", lightness)):
            self.session.set_offset(name, float(value))
        return self.session.rebuild()

    def reset_interpretation(self):
        return self.session.reset_to_neutral_mood()

    def save_interpretation(self, name: str):
        return self.session.save(name)

    def get_region_info(self, index: int) -> dict:
        if type(index) is not int or not 0 <= index < 16:
            raise ValueError("Region index must be between 0 and 15")
        cell = self.session.cell(index // 4, index % 4)
        visual, constraints = cell.visual, cell.musical_constraints
        return {
            "index": index, "row": cell.row, "column": cell.column,
            "relative_entropy": cell.relative_entropy,
            "relative_movement": cell.relative_movement,
            "relative_edge_density": cell.relative_edge_density,
            "relative_lightness": cell.relative_lightness,
            "orientation_deg": visual.orientation_deg,
            "lead_note_onsets": constraints.lead_note_onsets,
            "accompaniment_template": constraints.accompaniment_template,
            "bass_template": constraints.bass_template,
        }

    def close(self):
        self.session.close()
