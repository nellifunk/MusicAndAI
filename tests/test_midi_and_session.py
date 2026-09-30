import io
from pathlib import Path

import mido
import pytest

from artwork_music.controller.repl import TerminalController
from artwork_music.controller.session import InterpretationSession
from artwork_music.models import Instruments, Interpretation
from artwork_music.music.ensemble import compose
from artwork_music.render.midi_player import MidoOutput
from artwork_music.render.midi_writer import build_midi, pan_cc, write_midi_outputs
from artwork_music.storage import load_composition, write_composition


def midi_bytes(composition, cells=None, overview=False):
    buffer = io.BytesIO()
    build_midi(composition, cells, overview).save(file=buffer)
    return buffer.getvalue()


def events(track):
    tick = 0
    for message in track:
        tick += message.time
        yield tick, message


def test_three_tracks_channels_program_pan_tempo(composition):
    for cell in composition.cells:
        midi = mido.MidiFile(file=io.BytesIO(midi_bytes(composition, [cell])))
        assert len(midi.tracks) == 3
        for channel, (track, role) in enumerate(zip(midi.tracks, ("lead", "accompaniment", "bass"))):
            assert track.name == role
            assert {m.channel for m in track if not m.is_meta} == {channel}
            assert sum(m.type == "program_change" for m in track) == 1
            assert [m.value for m in track if m.type == "control_change" and m.control == 10] == [pan_cc(cell.musical_constraints.pan)]
            assert sum(m.time for m in track) == 16 * 240
            active = set()
            for _, message in events(track):
                if message.type == "note_on":
                    assert message.note not in active
                    active.add(message.note)
                elif message.type == "note_off":
                    assert message.note in active
                    active.remove(message.note)
            assert not active
        tempo = [m.tempo for t in midi.tracks for m in t if m.type == "set_tempo"]
        assert tempo == [mido.bpm2tempo(composition.global_music.tempo_bpm)]
        assert midi.length == pytest.approx(8 * 60 / composition.global_music.tempo_bpm, abs=1e-5)
        assert 4 <= midi.length <= 8


def test_instrument_layers_create_parallel_tracks(composition):
    layered = composition.model_copy(update={
        "global_music": composition.global_music.model_copy(update={
            "instruments": Instruments(
                lead=("Flute", "Violin"),
                accompaniment=("Orchestral Harp", "String Ensemble 1"),
                bass="Cello",
            )
        })
    })
    midi = mido.MidiFile(file=io.BytesIO(midi_bytes(layered, [layered.cells[0]])))
    assert [track.name for track in midi.tracks] == ["lead", "lead_2", "accompaniment", "accompaniment_2", "bass"]
    assert [{m.channel for m in track if not m.is_meta} for track in midi.tracks] == [{0}, {1}, {2}, {3}, {4}]


def test_overview_silence_order_and_duration(composition):
    midi = build_midi(composition, overview=True)
    assert sum(m.time for m in midi.tracks[0]) == (15 * 24 + 16) * 240
    markers = [(t, m.text) for t, m in events(midi.tracks[0]) if m.type == "marker"]
    assert markers == [(i * 24 * 240, f"cell_{i // 4}_{i % 4}") for i in range(16)]
    for track in midi.tracks:
        for tick, message in events(track):
            if message.type == "note_on":
                assert tick % (24 * 240) < 16 * 240


def test_midi_reproducible(raw, composition):
    repeated = compose(raw)
    assert repeated == composition
    for original, duplicate in zip(composition.cells, repeated.cells):
        assert midi_bytes(composition, [original]) == midi_bytes(repeated, [duplicate])
    assert midi_bytes(composition, overview=True) == midi_bytes(repeated, overview=True)


def test_energy_changes_only_tempo_and_not_raw(raw, composition):
    modified = compose(raw, Interpretation(delta_movement=0.2))
    assert modified.raw_analysis() == raw
    assert modified.global_music.tempo_bpm != composition.global_music.tempo_bpm
    assert modified.cells == composition.cells


def test_session_rebuild_reset_save_no_visual_analysis(tmp_path, raw, composition, monkeypatch):
    write_composition(tmp_path, composition)
    original = {p.name: p.read_bytes() for p in (tmp_path / "midi").glob("*.mid")}
    source_json = (tmp_path / "composition.json").read_bytes()
    import artwork_music.analysis.pipeline as pipeline
    monkeypatch.setattr(pipeline, "analyze_image", lambda *a: pytest.fail("Visual analysis must not run"))
    monkeypatch.setattr(pipeline, "visual_features", lambda *a: pytest.fail("Visual features must not run"))
    with InterpretationSession(tmp_path / "composition.json") as session:
        for dimension, value in [("energy", 0.2), ("complexity", -0.1), ("valence", -0.5), ("brightness", 0.2)]:
            session.set_offset(dimension, value)
        assert session.dirty
        with pytest.raises(ValueError, match="rebuild"):
            session.save("pending")
        session.rebuild()
        assert not session.dirty and session.composition.raw_analysis() == raw
        saved = session.save("my_interpretation")
        assert len(list((saved / "midi").glob("cell_*.mid"))) == 16
        restored = load_composition(saved / "composition.json")
        assert restored == session.composition
        assert restored.interpretation.delta_movement == 0.2
        assert restored.interpretation.delta_complexity == -0.1
        session.reset()
        assert session.composition == composition
        assert {p.name: p.read_bytes() for p in (session.preview_directory / "midi").glob("*.mid")} == original
        assert session.composition.raw_analysis() == raw
        with pytest.raises(FileExistsError):
            session.save("my_interpretation")
        for name in ["../escape", "", "/tmp/oops", "a/b", ".", "..", "has spaces"]:
            with pytest.raises(ValueError):
                session.save(name)
    assert (tmp_path / "composition.json").read_bytes() == source_json
    assert {p.name: p.read_bytes() for p in (tmp_path / "midi").glob("*.mid")} == original
    with InterpretationSession(saved / "composition.json") as session:
        assert session.save_root == tmp_path / "interpretations"


def test_absolute_mood_state_and_legacy_valence_offset(tmp_path, composition):
    write_composition(tmp_path, composition)
    with InterpretationSession(tmp_path / "composition.json") as session:
        session.set_mood(-1)
        assert session.pending.target_valence == -1
        assert session.pending.delta_valence == 0
        session.set_offset("valence", 0.25)
        assert session.pending.target_valence is None
        assert session.pending.delta_valence == 0.25
        with pytest.raises(ValueError, match="exactly -1, 0, or \\+1"):
            session.set_mood(0.5)


@pytest.mark.parametrize("value", [-0.51, 0.51, float("nan"), float("inf")])
def test_offset_validation(value):
    with pytest.raises(ValueError):
        Interpretation(delta_movement=value)


def test_no_port_and_missing_backend_fallback(tmp_path, monkeypatch):
    path = tmp_path / "cell_0_0.mid"
    monkeypatch.setattr(mido, "get_output_names", lambda: [])
    assert str(path) in MidoOutput().play(path)
    def unavailable():
        raise ImportError("No python-rtmidi")
    monkeypatch.setattr(mido, "get_output_names", unavailable)
    message = MidoOutput().play(path)
    assert str(path) in message
    assert "python -m pip install python-rtmidi" in message


def test_alsa_initialization_system_error_falls_back(tmp_path, monkeypatch):
    from artwork_music.render.midi_player import MidiUnavailable
    def unavailable():
        raise SystemError("MidiInAlsa::initialize: error creating ALSA sequencer client object.")
    monkeypatch.setattr(mido, "get_output_names", unavailable)
    path = tmp_path / "cell.mid"
    assert str(path) in MidoOutput().play(path)
    assert "ALSA sequencer" in MidoOutput().play(path)
    with pytest.raises(MidiUnavailable):
        MidoOutput().output_names()


def test_repl_selects_chordcat_instead_of_midi_through(tmp_path, composition, monkeypatch):
    write_composition(tmp_path, composition)
    monkeypatch.setattr(mido, "get_output_names", lambda: ["Midi Through", "Chordcat MIDI 1"])
    output = io.StringIO()
    with InterpretationSession(tmp_path / "composition.json") as session:
        repl = TerminalController(session, stdin=io.StringIO(), stdout=output)
        repl.onecmd("ports")
        repl.onecmd("port 2")
        assert session.player.port_name == "Chordcat MIDI 1"
        repl.onecmd("port 0")
        assert session.player.port_name == "Chordcat MIDI 1"
    assert "2: Chordcat MIDI 1" in output.getvalue()
    assert "Invalid port number" in output.getvalue()


def test_playback_sends_and_resets(tmp_path, composition, monkeypatch):
    write_midi_outputs(tmp_path, composition)
    messages = []
    class Port:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def send(self, message): messages.append(message)
        def reset(self): messages.append("reset")
    monkeypatch.setattr(mido, "get_output_names", lambda: ["Test MIDI"])
    monkeypatch.setattr(mido, "open_output", lambda name: Port())
    monkeypatch.setattr(mido.MidiFile, "play", lambda self: (m for m in mido.merge_tracks(self.tracks) if not m.is_meta))
    assert "Played" in MidoOutput().play(tmp_path / "cell_0_0.mid")
    assert messages[-1] == "reset"
    assert any(m.type == "note_on" for m in messages[:-1])
    assert "unavailable" in MidoOutput("Not connected").play(tmp_path / "cell_0_0.mid")


def test_repl_commands_and_errors(tmp_path, composition, monkeypatch):
    write_composition(tmp_path, composition)
    monkeypatch.setattr(mido, "get_output_names", lambda: [])
    commands = "show 0 0\nplay 0 0\nset energy 0.2\nset complexity -0.1\nrebuild\nsave terminal_version\nset energy 2\nshow 4 0\nreset\nstatus\nquit\n"
    output = io.StringIO()
    with InterpretationSession(tmp_path / "composition.json") as session:
        TerminalController(session, stdin=io.StringIO(commands), stdout=output).cmdloop()
    text = output.getvalue()
    assert "lead_costs" in text and "voice_weights" in text and "MIDI file:" in text
    assert "Rebuilt 16 cells" in text and "Error:" in text and "reset to zero" in text
    assert (tmp_path / "interpretations/terminal_version/composition.json").is_file()
