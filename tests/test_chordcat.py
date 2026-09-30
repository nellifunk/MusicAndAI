import threading

import mido

from artwork_music.controller import chordcat
from artwork_music.controller.chordcat import SignatureGrouper, classify, run, XY_GRID_MAPPING


def test_signature_grouping_collects_notes_and_debounces():
    g = SignatureGrouper(window=.05)
    assert g.feed(53, 0.0) is None
    assert g.feed(56, 0.01) is None
    assert g.feed(60, 0.02) is None
    assert g.flush(.08) == frozenset({53, 56, 60})


def test_mapping_and_ambiguous_collision_are_explicit():
    sig = frozenset({48, 51, 55})
    assert sig in XY_GRID_MAPPING
    assert classify(sig, "reject", mood=0.17)[0] == "ambiguous"
    assert classify(sig, "xy", mood=0.17) == ("xy", 0)
    assert classify(sig, "mood", mood=0.17)[0] == "mood"


def test_active_mood_buttons_map_to_logical_minus_one_zero_plus_one():
    assert classify(frozenset({48, 51, 55}), "reject", mood=0.0) == ("mood", -1.0)
    assert classify(frozenset({54, 57, 61}), "reject", mood=-1.0) == ("mood", 0.0)
    assert classify(frozenset({60, 63, 67}), "reject", mood=0.0) == ("mood", 1.0)


def test_run_emits_mood_and_region_events_without_duplicate_region_action(monkeypatch, capsys):
    mood = [mido.Message("note_on", channel=5, note=n, velocity=100) for n in (48, 51, 55)]
    mood += [mido.Message("note_off", channel=5, note=n, velocity=0) for n in (48, 51, 55)]
    region = [mido.Message("note_on", channel=5, note=n, velocity=100) for n in (44, 48, 51, 55)]
    region += [mido.Message("note_off", channel=5, note=n, velocity=0) for n in (44, 48, 51, 55)]

    class Port:
        def __init__(self):
            self.batches = iter([mood, region])
            self.stop_event = None

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def iter_pending(self):
            try:
                return iter(next(self.batches))
            except StopIteration:
                self.stop_event.set()
                return iter(())

    port = Port()
    monkeypatch.setattr(mido, "get_input_names", lambda: ("Chordcat MIDI",))
    monkeypatch.setattr(mido, "open_input", lambda name: port)

    class Session:
        player = type("Player", (), {"stop": lambda self: None})()
        composition = "rebuilt"

        def __init__(self):
            self.moods = []
            self.rebuilds = 0
            self.played = []

        def set_mood(self, value):
            self.moods.append(value)

        def rebuild(self):
            self.rebuilds += 1
            return self.composition

        def play(self, row, col):
            self.played.append((row, col))
            return "played"

    session = Session()
    stop_event = threading.Event()
    port.stop_event = stop_event
    events = []
    run(session, on_region_selected=lambda index: events.append(("region", index)),
        on_mood_changed=lambda value: events.append(("mood", value)),
        on_composition_rebuilt=lambda value: events.append(("composition", value)),
        stop_event=stop_event)

    assert session.moods == [-1.0]
    assert session.rebuilds == 1
    assert session.played == [(0, 1)]
    assert events == [("mood", -1.0), ("composition", "rebuilt"), ("region", 1)]
    capsys.readouterr()


def test_find_input_tolerates_changed_alsa_address(monkeypatch):
    monkeypatch.setattr(
        chordcat,
        "input_names",
        lambda: ("Midi Through:Midi Through Port-0 14:0", "Chordcat:Chordcat MIDI 1 24:0"),
    )

    assert chordcat.find_input("Chordcat:Chordcat MIDI 1 20:0") == "Chordcat:Chordcat MIDI 1 24:0"
    assert chordcat.find_input("Chordcat") == "Chordcat:Chordcat MIDI 1 24:0"
