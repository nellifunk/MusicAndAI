from artwork_music.controller.chordcat import SignatureGrouper, classify, XY_GRID_MAPPING


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
