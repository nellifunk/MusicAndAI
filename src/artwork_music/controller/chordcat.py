"""Deterministic CHORDCAT MIDI input and signature classification."""
from __future__ import annotations

import time
import json
import threading
from dataclasses import dataclass
from pathlib import Path

# Keep physical ordering in one place so it is easy to recalibrate.
XY_GRID_MAPPING = {
    frozenset({45, 48, 52}): 0, frozenset({45, 49, 52}): 1,
    frozenset({45, 49, 52, 56}): 2, frozenset({46, 49, 52}): 3,
    frozenset({46, 49, 52, 56}): 4, frozenset({46, 49, 53}): 5,
    frozenset({47, 50, 54}): 6, frozenset({47, 51, 54}): 7,
    frozenset({48, 51, 55}): 8, frozenset({48, 51, 55, 58}): 9,
    frozenset({49, 52, 57}): 10, frozenset({49, 52, 58}): 11,
    frozenset({50, 53, 57}): 12, frozenset({50, 54, 57}): 13,
    frozenset({51, 54, 57}): 14, frozenset({51, 54, 58}): 15,
}
XY_GRID_MAPPING_BY_MOOD = {
    -1.00: {frozenset(s): i for i, s in enumerate(((44,48,51),(44,48,51,55),(45,48,51),(45,48,51,55),(45,48,52),(46,49,53),(46,50,53),(47,50,54),(47,50,54,57),(48,51,56),(48,51,57),(49,52,56),(49,53,56),(50,53,56),(50,53,57),(51,54,58)))},
    -0.83: {frozenset(s): i for i, s in enumerate(((45,48,52),(45,49,52),(45,49,52,56),(46,49,52),(46,49,52,56),(46,49,53),(47,50,54),(47,51,54),(48,51,55),(48,51,55,58),(49,52,57),(49,52,58),(50,53,57),(50,54,57),(51,54,57),(51,54,58)))},
    -0.67: {frozenset(s): i for i, s in enumerate(((45,48,52),(45,48,52,55),(46,49,53),(46,50,53),(46,50,53,57),(47,50,53),(47,50,53,57),(47,50,54),(48,51,55),(48,52,55),(49,52,56),(49,52,56,59),(50,53,58),(50,53,59),(51,54,58),(51,55,58)))},
    -0.50: {frozenset(s): i for i, s in enumerate(((44,48,51),(44,48,51,54),(44,48,51,54,58),(46,49,53),(46,49,53,56),(47,50,54),(47,51,54),(47,51,54,58),(48,51,54),(48,51,54,58),(48,51,55),(49,52,56),(49,53,56),(50,53,57),(50,53,57,60),(51,54,59)))},
    -0.33: {frozenset(s): i for i, s in enumerate(((45,48,52),(45,48,52,55),(45,49,52),(45,49,52,55),(45,49,52,55,59),(47,50,54),(47,50,54,57),(48,51,55),(48,52,55),(48,52,55,59),(49,52,55),(49,52,55,59),(49,52,56),(50,53,57),(50,54,57),(51,54,58)))},
    -0.17: {frozenset(s): i for i, s in enumerate(((46,49,53),(46,49,53,56),(46,50,53),(46,50,53,56),(46,50,53,56,60),(48,51,55),(48,51,55,58),(49,52,56),(49,53,56),(49,53,56,60),(50,53,56),(50,53,56,60),(50,53,57),(51,54,58),(51,55,58),(52,55,59)))},
    0.00: {frozenset(s): i for i, s in enumerate(((47,50,54),(47,50,54,57),(47,51,54),(47,51,54,57),(47,51,54,57,61),(49,52,56),(49,52,56,59),(50,53,57),(50,54,57),(50,54,57,61),(51,54,57),(51,54,57,61),(51,54,58),(52,55,59),(52,56,59),(53,56,60)))},
    0.17: {frozenset(s): i for i, s in enumerate(((48,51,55),(48,51,55,58),(48,52,55),(48,52,55,58),(48,52,55,58,62),(50,53,57),(50,53,57,60),(51,54,58),(51,55,58),(51,55,58,62),(52,55,58),(52,55,58,62),(52,55,59),(53,56,60),(53,57,60),(54,57,61)))},
    0.33: {frozenset(s): i for i, s in enumerate(((49,52,56),(49,52,56,59),(49,53,56),(49,53,56,59),(49,53,56,59,63),(51,54,58),(51,54,58,61),(52,55,59),(52,56,59),(52,56,59,63),(53,56,59),(53,56,59,63),(53,56,60),(54,57,61),(54,58,61),(55,58,62)))},
    0.50: {frozenset(s): i for i, s in enumerate(((50,53,57),(50,53,57,60),(50,54,57),(50,54,57,60),(50,54,57,60,64),(52,55,59),(52,55,59,62),(53,56,60),(53,57,60),(53,57,60,64),(54,57,60),(54,57,60,64),(54,57,61),(55,58,62),(55,59,62),(56,59,63)))},
    0.67: {frozenset(s): i for i, s in enumerate(((51,54,58),(51,54,58,61),(51,55,58),(51,55,58,61),(51,55,58,61,65),(53,56,60),(53,56,60,63),(54,57,61),(54,58,61),(54,58,61,65),(55,58,61),(55,58,61,65),(55,58,62),(56,59,63),(56,60,63),(57,60,64)))},
    0.83: {frozenset(s): i for i, s in enumerate(((52,55,59),(52,55,59,62),(52,56,59),(52,56,59,62),(52,56,59,62,66),(54,57,61),(54,57,61,64),(55,58,62),(55,59,62),(55,59,62,66),(56,59,62),(56,59,62,66),(56,59,63),(57,60,64),(57,61,64),(58,61,65)))},
    1.00: {frozenset(s): i for i, s in enumerate(((53,56,60),(53,56,60,63),(53,57,60),(53,57,60,63),(53,57,60,63,67),(55,58,62),(55,58,62,65),(56,59,63),(56,60,63),(56,60,63,67),(57,60,63),(57,60,63,67),(57,60,64),(58,61,65),(58,62,65),(59,62,66)))},
}
# These are the largest conflict-free subset of the 13 recorded mood states:
# physical keys 1, 7, and 13, mapped to dark, neutral, and bright.
ACTIVE_MOODS = {-1.0, 0.0, 1.0}
MOOD_CHORDS = {frozenset({n, n + 3, n + 7}): round(-1 + i / 6, 2)
               for i, n in enumerate(range(48, 61))
               if round(-1 + i / 6, 2) in ACTIVE_MOODS}


@dataclass
class SignatureGrouper:
    window: float = 0.035
    _notes: set[int] | None = None
    _deadline: float = 0.0
    _active: set[int] = None

    def __post_init__(self):
        self._active = set()

    def feed(self, note: int, now: float | None = None):
        now = time.monotonic() if now is None else now
        if self._notes is None or now > self._deadline:
            result = self.flush(now)
            self._notes = {note}
        else:
            result = None
            self._notes.add(note)
        self._deadline = now + self.window
        return result

    def flush(self, now: float | None = None):
        if self._notes is None:
            return None
        now = time.monotonic() if now is None else now
        if now < self._deadline:
            return None
        result = frozenset(self._notes)
        self._notes = None
        return result

    def release(self, note: int):
        """Close a signature when its complete chord has been released."""
        self._active.discard(note)
        if not self._active and self._notes is not None:
            result = frozenset(self._notes)
            self._notes = None
            return result
        return None

    def press(self, note: int, now: float | None = None):
        self._active.add(note)
        return self.feed(note, now)


def classify(signature: frozenset[int], ambiguous: str = "xy", mood: float = 0.0):
    table = XY_GRID_MAPPING_BY_MOOD.get(round(mood, 2), XY_GRID_MAPPING)
    return classify_with_table(signature, table, ambiguous)


def classify_with_table(signature, table, ambiguous="xy"):
    xy = table.get(signature)
    mood = MOOD_CHORDS.get(signature)
    if xy is not None and mood is not None:
        if ambiguous == "xy":
            return "xy", xy
        if ambiguous == "mood":
            return "mood", mood
        return "ambiguous", None
    if xy is not None:
        return "xy", xy
    if mood is not None:
        return "mood", mood
    return "unknown", None


def input_names():
    import mido
    return tuple(mido.get_input_names())


def find_input(requested: str | None = None):
    names = input_names()
    if requested:
        if requested in names:
            return requested
        raise ValueError(f"MIDI input {requested!r} is unavailable. Available: {names}")
    matches = [n for n in names if "chordcat" in n.lower() or "alpha" in n.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(names) == 1:
        return names[0]
    raise ValueError("CHORDCAT MIDI input not uniquely detected; use --midi-input with the exact port name")


def calibrate(port_name=None, output_path=None):
    """Capture the three conflict-free mood tables in physical cell order."""
    import mido
    name = find_input(port_name)
    moods = [(-1.0, 1), (0.0, 7), (1.0, 13)]
    captured = {}
    print(f"Calibration input: {name}")
    with mido.open_input(name) as port:
        for mood, key in moods:
            input(f"Press mood key {key}, then press Enter here to begin 16 XY cells...")
            # The mood chord itself may still be queued when Enter is pressed.
            # Drain it so cell 1 can only come from the next physical XY action.
            time.sleep(0.08)
            for _ in port.iter_pending():
                pass
            groups = []
            grouper = SignatureGrouper()
            print(f"Mood {mood:+.2f}: touch XY cells 1 through 16 in order.")
            while len(groups) < 16:
                for message in port.iter_pending():
                    if message.type == "clock" or getattr(message, "channel", None) != 5:
                        continue
                    if message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                        signature = grouper.release(message.note)
                        if signature is not None:
                            groups.append(sorted(signature))
                            print(f"  cell {len(groups):2d}: {sorted(signature)}")
                    elif message.type == "note_on":
                        grouper.press(message.note)
                time.sleep(0.002)
            captured[str(mood)] = groups
    if output_path:
        Path(output_path).write_text(json.dumps(captured, indent=2), encoding="utf-8")
        print(f"Saved calibration: {output_path}")
    return {float(k): {frozenset(s): i for i, s in enumerate(v)} for k, v in captured.items()}


def run(session, port_name=None, debug=False, ambiguous="reject", xy_mapping=None,
        on_region_selected=None, on_mood_changed=None, on_composition_rebuilt=None,
        stop_event=None, background_playback=False):
    """Block while translating CHORDCAT events into session actions.

    Optional callbacks receive high-level events after classification. They are
    deliberately separate from the musical actions so a UI can mirror the
    hardware without triggering a second playback or rebuild.
    """
    import mido
    name = find_input(port_name)
    print(f"Listening for CHORDCAT on {name}")
    grouper = SignatureGrouper()
    stop_event = stop_event or threading.Event()
    # No cell is selected until the first physical XY touch.
    last_cell = None
    current_mood = 0.0
    with mido.open_input(name) as port:
        def handle(signature):
            nonlocal last_cell, current_mood
            if signature is None:
                return
            if xy_mapping is not None:
                table = xy_mapping.get(round(current_mood, 2), XY_GRID_MAPPING)
                kind, value = classify_with_table(signature, table, ambiguous)
            else:
                kind, value = classify(signature, ambiguous, current_mood)
            if kind == "xy":
                row, col = divmod(value, 4)
                if value != last_cell:
                    print(f"XY signature: {sorted(signature)} -> grid cell {value + 1}")
                    if on_region_selected is not None:
                        on_region_selected(value)
                    if background_playback:
                        session.player.stop()

                        def play_cell(row=row, col=col):
                            try:
                                print(session.play(row, col))
                            except Exception as exc:  # pragma: no cover - hardware dependent
                                print(f"Playback error: {exc}")

                        threading.Thread(target=play_cell, name="chordcat-playback", daemon=True).start()
                    else:
                        print(session.play(row, col))
                    last_cell = value
            elif kind == "mood":
                print(f"Mood signature: {sorted(signature)} -> mood {value:+.2f}")
                current_mood = value
                session.player.stop()
                session.set_mood(value)
                if on_mood_changed is not None:
                    on_mood_changed(value)
                session.rebuild()
                if on_composition_rebuilt is not None:
                    on_composition_rebuilt(session.composition)
                # The regenerated phrases are different even when the next
                # physical selection is the same grid cell.
                last_cell = None
                print("Mood updated; waiting for the next XY-cell selection.")
            elif kind == "ambiguous":
                print(f"Ambiguous signature: {sorted(signature)}; it matches both XY and mood controls. Ignored. Use --ambiguous xy or --ambiguous mood after calibration.")
            elif debug:
                print(f"{kind.title()} MIDI signature: {sorted(signature)}")

        while not stop_event.is_set():
            for message in port.iter_pending():
                if message.type == "clock":
                    continue
                if debug:
                    print(f"MIDI: {message}")
                # The physical device reports channel=5 through mido.  This is
                # intentionally kept explicit because channel numbering differs
                # between MIDI documentation (1-based) and some APIs (0-based).
                if message.channel != 5:
                    continue
                if message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
                    handle(grouper.release(message.note))
                    continue
                if message.type != "note_on":
                    continue
                grouper.press(message.note)
            signature = grouper.flush()
            handle(signature)
            time.sleep(0.002)
