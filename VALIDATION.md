# Validation

Completed in Python 3.12.14 on Linux, using the versions in `requirements-lock.txt`.

## Automated suite

Command: `python -m pytest -q`

Latest result after the sixteenth-note and instrument-layer revision: **230 passed in 84.00 seconds. No warnings or failures.**

Coverage includes image features, semantic schema errors, global/local mappings,
musical hard constraints, rhythm optimality, lead cost arithmetic and search,
accompaniment and bass, MIDI tracks/channels/timing, provider and playback
fallbacks, REPL commands, saving, raw-data preservation, and byte-identical
regeneration after resetting interpretation offsets.

Repeated fresh CLI analysis runs produced byte-identical analysis JSON,
composition JSON, overlay, semantic output, all 16 cell MIDI files, and overview.

## Executed demo workflow

The included `examples/demo.png` and explicitly authored semantic fixture were
analyzed through the CLI. Outputs are in `demo_output/`.

The terminal REPL was then run with:

```text
show 0 0
play 0 0
set energy 0.2
set complexity -0.1
rebuild
play 0 0
save my_interpretation
reset
quit
```

The baseline is D Ionian, Romantic instruments, 85 BPM. The saved version is
96 BPM, with offsets `delta_movement=0.2` and `delta_complexity=-0.1`.
Both contain 16 cell MIDI files and a sequential overview. The original
composition remains unchanged.

No MIDI backend was installed during the initial validation. The actual
`play` command returned an existing preview MIDI path without crashing.
Message delivery and port reset are separately tested with a fake port.

## Packaging (initial build)

`pip wheel --no-deps .` succeeded. The built wheel was imported directly outside
the source package; all seven bundled era palettes were successfully loaded
and their General MIDI names resolved.

## External integrations

OpenAI request construction, structured response handling, refusal handling,
and cache reuse were tested with a fake client. No live paid vision request
was made. A physical MIDI device and Chordcat were not connected or tested.
No accessibility or aesthetic effectiveness study was conducted.

## MIDI troubleshooting update

Installed `python-rtmidi 1.5.8` into the working Python environment. Linux's
ALSA status reports the connected Chordcat and its MIDI port. The restricted
execution environment does not expose `/dev/snd/seq`, so physical playback
cannot be verified from that environment.

The player now handles ALSA initialization `SystemError` failures gracefully,
reports the backend error with a next step, and explains a missing backend's
installation command. The CLI and REPL support `ports`; the REPL supports
`port NUMBER` to explicitly choose the instrument instead of a MIDI Through port.
Regression tests cover these failures and explicit Chordcat selection.

## Deterministic diversity revision (0.2.0 / composition schema 1.1)

All four average-tie percentile ranks, the constant-range fallback, separately
ranked raw bass activity, the new anchor cost and weights, all six accompaniment
templates and five bass templates, 20-candidate validity, exact distance formulas,
coordinate-descent convergence and tie-breaking, duplicate diagnostics, legacy
playback compatibility, and Klimt acceptance are tested.

On the historical 1.1 Klimt recomposition, unique lead pitch sequences increased from 5 to 16,
unique onset patterns from 3 to 11, accompaniment patterns from 1 to 6, and bass
patterns from 1 to 5. There are zero redundant lead sequences (previously 11;
the largest old identical group contained 9 cells). Mean pairwise musical
distance increases from 0.074891 to 0.187083 under the same new diagnostic metric.

The joint selection converges in four full passes. With the new local costs,
its objective decreases from 8.142433 for independently optimal candidates to
7.343636. Raw analysis bytes and the global musical context remain unchanged.
The old Klimt outputs are preserved in `output_klimt_kuss_v1/`.

These checks establish deterministic implementation and improved measured
diversity, not subjective listening quality or hardware playback quality.

## Sixteenth-note and layer revision (0.3.0 / composition schema 1.2)

New compositions use 32 sixteenth-note timing steps per two-bar cell. Lead
durations may now be sixteenth, eighth, quarter, or half notes. Accompaniment
and bass templates were scaled to the new timing grid, and the syncopated
accompaniment template now contains explicit sixteenth-note movement.

Instrument palettes can now give each role either one General MIDI instrument
or a list of instruments. The MIDI writer creates one track and channel per
instrument layer. The current Klimt palette renders five tracks: Flute, Violin,
Orchestral Harp, String Ensemble 1, and Cello.

On the Klimt input, the regenerated output remains deterministic and reports
16 unique lead pitch sequences, 14 unique onset patterns, 6 accompaniment
patterns, 5 bass patterns, and no duplicate lead pitch sequences.
