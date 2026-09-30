"""Render one MIDI track/channel per instrument layer."""
from pathlib import Path

import mido
import pretty_midi

from artwork_music.music.time import OVERVIEW_GAP_STEPS

TICKS_PER_BEAT = 480
TICKS_PER_STEP = TICKS_PER_BEAT // 4
ROLES = ("lead", "accompaniment", "bass")


def pan_cc(pan: float) -> int:
    return max(0, min(127, round((pan + 1) * 127 / 2)))


def instrument_layers(instruments, role):
    value = getattr(instruments, role)
    return value if isinstance(value, tuple) else (value,)


def build_midi(composition, cells=None, overview=False) -> mido.MidiFile:
    selected = sorted(cells if cells is not None else composition.cells, key=lambda c: (c.row, c.column))
    if not selected:
        raise ValueError("At least one cell is required for MIDI rendering")
    if len(selected) > 1 and not overview:
        raise ValueError("Multiple cells require sequential overview mode")
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    phrase_steps = selected[0].phrase.length_sixteenths
    step_ticks = TICKS_PER_STEP if phrase_steps == 32 else TICKS_PER_BEAT // 2
    total_steps = (len(selected) - 1) * (phrase_steps + OVERVIEW_GAP_STEPS) + phrase_steps
    channel = 0
    for role in ROLES:
        for layer, instrument in enumerate(instrument_layers(composition.global_music.instruments, role)):
            if channel > 15:
                raise ValueError("MIDI rendering supports at most 16 instrument layers")
            events = []
            def add(tick, priority, message):
                events.append((tick, priority, len(events), message))
            track_name = role if layer == 0 else f"{role}_{layer + 1}"
            add(0, 0, mido.MetaMessage("track_name", name=track_name))
            if channel == 0:
                add(0, 0, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(composition.global_music.tempo_bpm)))
                add(0, 0, mido.MetaMessage("time_signature", numerator=4, denominator=4))
            program = pretty_midi.instrument_name_to_program(instrument)
            add(0, 1, mido.Message("program_change", channel=channel, program=program))
            for index, cell in enumerate(selected):
                start = index * (phrase_steps + OVERVIEW_GAP_STEPS) * step_ticks
                add(start, 2, mido.Message("control_change", channel=channel, control=10,
                                           value=pan_cc(cell.musical_constraints.pan)))
                if channel == 0:
                    add(start, 0, mido.MetaMessage("marker", text=f"cell_{cell.row}_{cell.column}"))
                for note in getattr(cell.phrase, role).notes:
                    add(start + note.onset * step_ticks, 4,
                        mido.Message("note_on", channel=channel, note=note.pitch, velocity=note.velocity))
                    add(start + (note.onset + note.duration) * step_ticks, 3,
                        mido.Message("note_off", channel=channel, note=note.pitch, velocity=0))
            add(total_steps * step_ticks, 9, mido.MetaMessage("end_of_track"))
            track = mido.MidiTrack()
            previous = 0
            for tick, _, _, message in sorted(events):
                track.append(message.copy(time=tick - previous))
                previous = tick
            midi.tracks.append(track)
            channel += 1
    return midi


def write_midi_outputs(directory: Path, composition) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for cell in composition.cells:
        build_midi(composition, [cell]).save(str(directory / f"cell_{cell.row}_{cell.column}.mid"))
    build_midi(composition, overview=True).save(str(directory / "overview.mid"))
