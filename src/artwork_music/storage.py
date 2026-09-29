import json
import os
import tempfile
from pathlib import Path

from .models import Composition


def write_json(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = model.model_dump(mode="json") if hasattr(model, "model_dump") else model
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".write-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_composition(path: Path) -> Composition:
    return Composition.model_validate_json(path.read_text(encoding="utf-8"))


def write_composition(directory: Path, composition: Composition) -> None:
    from .render.midi_writer import write_midi_outputs
    directory.mkdir(parents=True, exist_ok=True)
    write_midi_outputs(directory / "midi", composition)
    write_json(directory / "composition.json", composition)
    from .music.diagnostics import diagnose
    write_json(directory / "diagnostics.json", composition.diagnostics or diagnose(composition.cells, composition.global_music))
