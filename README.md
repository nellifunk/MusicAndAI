# Artwork → musical interpretation → 4×4 exploration

**Musical character experiment:** this branch adds authored artwork themes to
the local frontend and CHORDCAT/terminal sessions. See
[run instructions and v1 comparison](docs/MUSICAL_CHARACTER.md).

A working Python 3.11+ terminal prototype that measures an artwork, combines those measurements with semantic vision, and composes 16 two-bar pieces for lead, accompaniment, and bass. Each cell shares a global scale, harmony, tempo, and historical instrument palette, while local visual features shape its rhythm, contour, accompaniment, and voice prominence.

The architecture separates **visual analysis → musical constraints → composition**. Color does not select notes or instruments. Object labels are stored for explanation, and do not directly affect the composition. There is no random note generation, neural music generation, GUI, or vertical-grid-position-to-pitch mapping.

Version **0.3.0 / composition schema 1.2** adds sixteenth-note timing and optional multiple instrument layers per role. It builds on the 1.1 diversity engine: within-artwork feature ranks, a local melodic anchor, six accompaniment templates, five bass templates, and deterministic joint selection from 20 lead candidates per cell. The updated Klimt example is in `output_klimt_kuss/`; the original is preserved in `output_klimt_kuss_v1/`. See [the comparison](output_klimt_kuss/DIVERSITY_COMPARISON.md).

## Quick start: no account or MIDI device needed

From this project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

python main.py analyze \
  --image examples/demo.png \
  --title "Studies in Motion" \
  --artist "Synthetic demonstration" \
  --year 1889 \
  --art-movement "Abstract study" \
  --semantic-sidecar examples/demo.semantic.json \
  --output output

python main.py interact output/composition.json
```

On Windows, activate with `.venv\Scripts\activate`. `artwork-music` is also installed as a CLI entry point. For reproducible dependency versions on the tested Python 3.12 environment, install `requirements-lock.txt` before installing the project with `pip install --no-deps -e .`. The lock includes the optional vision SDK and pytest, but no MIDI hardware backend.

The included `examples/demo.png` is a synthetic test pattern. Its sidecar was authored as a varied test fixture, **not inferred by a vision model**. Its artwork metadata is fictional. `examples/make_demo.py` recreates both files without randomness. A completed run is already included in `demo_output/`, with a saved modified interpretation under `demo_output/interpretations/`.

`demo_output/` and its personal interpretation are legacy 1.0 snapshots. Existing snapshots still load and play their original notes. Running `rebuild` or `reset` in a legacy session upgrades its preview to the current engine; it does not overwrite the loaded file. Reset recreates identical zero-offset MIDI within the same engine version, not across engine changes. To upgrade explicitly to a separate folder without image or semantic analysis:

```bash
python main.py recompose demo_output/composition.json --output demo_output_v12
```

## Analyze your own artwork

```bash
python main.py analyze \
  --image painting.jpg \
  --title "Example Painting" \
  --artist "Example Artist" \
  --year 1889 \
  --art-movement "Post-Impressionism" \
  --semantic-sidecar painting.semantic.json
```

`--semantic-sidecar` is optional if `painting.semantic.json` exists alongside `painting.jpg`, or a vision provider is configured. Sidecar data takes precedence over the API, so offline input never silently triggers a network request. No semantic values are fabricated when neither is available.

Required metadata: title, artist, and art movement. Supply either a creation year (integer 1–9999 CE) or an explicit `--music-era-override`. The year is never inferred from the image. `--tonic D` is the default; other note names, such as `F#` or `Bb`, work. `--output DIRECTORY` defaults to `output`. Running `analyze` again writes a new baseline in that directory; use separate directories to keep different artworks.

| Artwork year | Default music era |
| --- | --- |
| Before 1450 | Medieval |
| 1450–1599 | Renaissance |
| 1600–1749 | Baroque |
| 1750–1819 | Classical |
| 1820–1889 | Romantic |
| 1890–1919 | Impressionist / Early Modern |
| 1920 onward | Modern / Contemporary |

This is an approximate design convention, not a claim that art and music periods correspond perfectly. **1889 maps to Romantic**, following the specified table. To select the later palette, pass `--music-era-override 'Impressionist / Early Modern'`. Both `art_movement` and the resolved `music_era` are stored.

## Semantic vision configuration

```bash
python -m pip install -e '.[vision]'
export OPENAI_API_KEY='your-api-key'
export OPENAI_VISION_MODEL='your-vision-and-structured-output-capable-model-id'
```

Then omit `--semantic-sidecar`; optionally specify the model with `--vision-model`. The model is explicitly configurable rather than embedding an account-dependent model choice. The OpenAI implementation sends the full artwork and 16 labeled crops through the Responses API with a Pydantic structured-output schema. It requests global valence probabilities, global movement, and local physical movement and objects. It does not request musical decisions. Refusals, unavailable models, malformed responses, and connection failures produce an actionable sidecar error.

API calls are external and are **not guaranteed deterministic**, even if a provider offers temperature controls. The first result is stored in `semantic_cache.json`, keyed by normalized image content, artwork metadata, and model. A matching cache is reused, including without credentials. `--refresh-semantics` explicitly requests a new result. Copy `semantic_analysis.json` to a sidecar to reproduce an interpretation in another output directory or environment. No API calls occur when exploring or rebuilding a saved composition.

The adapter follows the official [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [image input](https://developers.openai.com/api/docs/guides/images-vision) documentation. The SDK is imported only within the optional provider.

## Semantic sidecar format

See the complete, validated example at `examples/demo.semantic.json`. The root contains:

```json
{
  "global_features": {
    "valence": {"negative": 0.15, "neutral": 0.25, "positive": 0.60},
    "movement": 0.36
  },
  "cells": [
    {
      "row": 0,
      "column": 0,
      "movement": 0.44,
      "objects": [{"label": "tree", "confidence": 0.91}]
    }
  ]
}
```

The snippet shows one cell for readability; a valid file must include **exactly 16 unique cells**, one for each `(row,column)` in `0..3`. Supply at most three objects per cell; an empty object list is valid. Probabilities, confidences, and movement must be finite values in `[0,1]`; valence probabilities must sum to one within `1e-6`. Unexpected fields, missing cells, duplicate cells, and invalid values are rejected.

Movement means visually depicted or strongly implied physical activity: static architecture is low, running people high, and turbulent water medium/high. It is separate from emotional positivity. Object labels can help the semantic provider estimate movement, but composition never reads those labels.

## Interactive exploration and personal interpretation

```text
show 0 0
play 0 0
set energy 0.2
set complexity -0.1
rebuild
play 0 0
save my_interpretation
reset
status
quit
```

| Control | Offset field | Meaning |
| --- | --- | --- |
| `set valence VALUE` | `delta_valence` | Emotional valence / mode and harmony |
| `set energy VALUE` | `delta_movement` | Global tempo |
| `set complexity VALUE` | `delta_complexity` | Harmonic extensions and melodic step budget |
| `set brightness VALUE` | `delta_lightness` | Global register |

Each offset is in `[-0.5,0.5]`. `set` stages changes; **`rebuild` applies them** to all 16 phrases. `save` refuses unapplied changes so the saved offsets always describe the actual MIDI. `reset` immediately zeros all four offsets and rebuilds. Invalid input reports an error and keeps the REPL running.

Rebuilds operate only on the immutable raw analysis embedded in `composition.json`; neither the original image nor an API key is needed. Changing only energy changes tempo, not the local notes or constraints. Other changes can alter pitches, harmony, or melodic step limits; local onset counts and rhythms still derive from the original local features.

`show ROW COL` prints raw features, detected objects, derived constraints, all seven lead costs and their weighted total, notes with timing and velocity, and instrument names. Coordinates are zero-based and row-major. There is no claim that all 16 phrases must differ for an entirely uniform artwork.

The loaded baseline file is preserved. Current MIDI previews live in a temporary session directory; a no-port message prints their paths. Use `save NAME` to keep them after exiting. Saving creates `interpretations/NAME/` beside the baseline; reopening an interpretation still saves alongside its siblings. Names accept letters, digits, underscores, and hyphens, and existing interpretations are never overwritten.

## Files and MIDI

```text
output/
  analysis_raw.json
  semantic_analysis.json
  semantic_cache.json              # Only when API semantics were used
  composition.json
  diagnostics.json
  grid_overlay.png
  midi/
    cell_0_0.mid ... cell_3_3.mid
    overview.mid
  interpretations/NAME/
    diagnostics.json
    composition.json
    midi/
      cell_0_0.mid ... cell_3_3.mid
      overview.mid
```

Each cell is exactly two bars of 4/4, eight quarter-note beats, or approximately 4.00–7.38 seconds at 120–65 BPM. New compositions use 32 sixteenth-note steps per cell. Each Standard MIDI File has one track and channel per instrument layer: a single-instrument role creates one track, while a layered role creates parallel tracks such as `lead` and `lead_2`. Tempo and meter metadata are in the first lead track, avoiding an extra conductor track. Instruments are resolved by `pretty_midi.instrument_name_to_program()`. Every voice receives pan CC 10. MIDI resolution is 480 ticks per quarter; note-offs precede new note-ons at the same tick.

`overview.mid` plays cells in row-major order, inserting one full silent bar between cells. There is no trailing spacer after the final phrase. Note timing and explicit end-of-track events preserve phrase length even when the lead finishes early.

MIDI describes notes and control events; it is not an audio recording. Open these files in a MIDI-capable DAW, synthesizer, or player to hear them. For terminal playback:

```bash
python -m pip install -e '.[playback]'
python main.py interact output/composition.json --midi-port 'Exact output port name'
```

List output names with `python main.py ports`, or use `ports` inside the REPL.
Then use `port NUMBER` to select the instrument before `play`. For example,
if `ports` lists `1: Midi Through` and `2: Chordcat ...`, enter `port 2`.
The port numbering starts at 1; grid coordinates still start at 0.

If the backend is missing, install `python-rtmidi` in the same activated Python
environment and restart the REPL. If Linux reports that `/dev/snd/seq` is
inaccessible, the program lacks access to the OS MIDI device (for example in a
restricted execution environment). Run it in a local terminal with device access.

Without `--midi-port`, the first available port is used. The optional `python-rtmidi` backend may need OS MIDI drivers/services. If unavailable, `play` returns the MIDI path without crashing; file generation has no dependency on MIDI hardware. Playback resets the port on completion or interruption to avoid hanging notes. The synth must support GM programs and CC 10 for the intended timbres and panning.

The eras' palettes are editable in `src/artwork_music/config/instrument_palettes.yaml`. A role can be a single General MIDI instrument name or a list of up to four names. `--palette PATH` loads another configuration. Instrument choices are embedded in the composition and preserved on rebuild, so later changes to a config file do not silently alter saved interpretations.

## Architecture

```text
main.py → artwork_music.cli
  analysis/    image grid, CIELAB clustering, entropy, edges, orientation,
               SemanticAnalyzer → sidecar / OpenAI implementations
  models.py    frozen Pydantic models for every stage
  music/       era, scale, harmony, global/local mappings,
               relative feature ranks, rhythm enumeration, beam-search candidates,
               cross-cell diversity selection, accompaniment, bass, diagnostics
  render/      deterministic MIDI writer, abstract MidiOutput, MidoOutput
  controller/  ControllerAdapter, shared InterpretationSession, terminal REPL
  storage.py   stable JSON and composition export
```

Composition classes have no API, image loading, keyboard, or hardware logic. The stored raw layer is immutable (frozen models and tuples). The generated composition carries enough information to load, inspect, rebuild, reset, and save without access to the initial input files.

## Mapping and search details

Quantitative descriptors are computed over every original-resolution pixel, globally and in each cell. EXIF orientation is respected; transparency is composited on white. Images must be at least 4×4. Integer split boundaries assign every pixel exactly once, even with unequal cell sizes. The debug overlay is separate from analysis and may be enlarged to make labels readable.

| Stage | Definition |
| --- | --- |
| Color | Three CIELAB k-means clusters, `random_state=0`, `n_init=10`, Lloyd algorithm; RGB-converted centroids stored as HSL plus weight |
| Fewer than three colors | Use available Lab colors and pad with zero-weight duplicates; always three entries sorted by descending weight |
| Lightness | Mean pixel HSL lightness, `(max(R,G,B)+min(R,G,B))/2`, normalized to `[0,1]` |
| Entropy | 256-bin grayscale Shannon entropy divided by 8; zero-probability bins omitted |
| Edges | Canny thresholds `max(0,0.66×median)` and `min(255,1.33×median)`; density is edge pixels / all pixels |
| Orientation | Sobel gradient directions modulo 180°, 18 magnitude-weighted bins; strongest bin center; fewer than eight usable edge pixels → `null` |
| Effective global values | Add offsets to raw values, then clip valence to `[-1,1]`, others to `[0,1]` |
| Mode | Aeolian below `−1/3`, Dorian from `−1/3` to below `1/3`, Ionian from `1/3` |
| Two-bar harmony | Ionian `I→V`; Dorian `i→IV`; Aeolian `i→VI` |
| Extensions | Effective entropy below 0.40: triads; 0.40–0.75: diatonic seventh; ≥0.75: seventh and ninth |
| Tempo | `round(65 + 55×effective_movement)` |
| Register center | `p_c = round(48 + 24×effective_lightness)` |
| Voice registers | Lead `[p_c−7,p_c+9]`; accompaniment `[p_c−15,p_c−3]`; bass `[p_c−27,p_c−15]` |
| Panning | Column `c` gives `−1+2c/3`, converted to CC 10 values `0,42,85,127` |
| Activity | `D = 0.65×local_movement + 0.35×edge_density` |
| Lead onsets | `N = 4+round(10×(0.65q_m+0.35q_E))`, target offbeat sixteenth-note positions `round(q_H×min(8,N−2))` |
| Contour | `sin(2θ)`; missing orientation gives zero |
| Maximum step | `1+floor(2κ+abs(sin θ))`, where `κ=(effective_global_entropy+q_H)/2`; missing θ gives verticality zero |

The orientation definition uses the **Sobel gradient**, not the tangent to the edge; image y coordinates increase downward. This convention is deliberate and documented because rotating a gradient into an edge tangent would change the contour mapping. The reliability threshold of eight pixels is a V1 implementation choice.

Global colors sorted by lightness anchor lead, accompaniment, and bass from bright to dark. Each local color contributes its weight to the closest anchor, using circular hue distance with weights 0.50 hue, 0.25 saturation, and 0.25 lightness. Ties use lead → accompaniment → bass. Smoothed role weights are `(q+0.10)/1.30`; velocities are `round(55+45q_lead)`, `round(45+40q_acc)`, `round(50+40q_bass)`. Here each `q` in the velocity formulas is the **smoothed** weight. Instrument identity depends only on the era palette.

Rhythm uses a deterministic bounded search over onset sets of size N in positions 0–31, requiring 0 and 16. It minimizes offbeat, sixteenth-density, bar-balance, and adjacency costs, clipped to `[0,1]`; ties choose the lexicographically smallest onset tuple. Durations choose the longest of 8, 4, 2, or 1 sixteenth-note steps that fits before the next onset and bar boundary. Remaining space is a rest.

Lead search uses exactly a **100-sequence deterministic beam**. Scale degrees index ascending in-register MIDI pitches. Hard constraints enforce maximum scale-step distance, at least three distinct pitches, and no three equal successive notes. If search fails, its maximum step increases to four, with each relaxation logged and stored. Failure after that raises an error rather than inventing notes.

The local lead objective is **0.19 harmony + 0.20 contour + 0.13 smoothness + 0.07 leap resolution + 0.16 cadence + 0.08 repetition + 0.17 anchor**. Prefix search uses available terms with full-phrase denominators; cadence is included when the phrase is complete. The anchor is `a=round(6q_L)` and its cost is `clip(mean(((d−a)/6)^2),0,1)`, a soft preference. Degree `d` is the index in the ordered global in-register scale-pitch list; it is not reduced modulo seven. Contour amplitude uses `1+2q_H`. The definitions of the original six cost terms otherwise remain unchanged.

The best 20 valid sequences surviving the beam are retained, sorted by local cost and lexicographic degree sequence. All share the cell's optimized rhythm. **Beam search is approximate**: these are the top candidates of the beam, not a guaranteed exhaustive top 20 of the full search space. The 32-step rhythm search is also bounded and deterministic. Joint selection never changes candidate notes or bypasses the original hard constraints.

Accompaniment uses root/third/fifth compact inversions, first centered in its register, then minimizing summed sorted-voice motion. Select template `round(5q_H)`:

| Index | Per-bar accompaniment pattern (L/M/H = low/middle/high chord voice) |
| --- | --- |
| 0 | Whole-bar sustained chord |
| 1 | Chord pulses on beats 1 and 3, each a half note |
| 2 | Quarter notes L, M, H, L |
| 3 | Quarter notes H, M, L, M |
| 4 | Eighth notes L, M, H, M, H, M, L, M |
| 5 | Syncopated sixteenth-note broken chord at positions 0,3,5,8,10,11,13,15, playing L,M,H,M,L,M,H,M |

Bass selects `round(4q_D)`, where `q_D` is the percentile rank of **raw** activity `D=0.65m+0.35E`, not a weighted sum of percentiles:

| Index | Per-bar bass pattern |
| --- | --- |
| 0 | Whole-note root |
| 1 | Two half-note roots |
| 2 | Half-note root → half-note fifth |
| 3 | Half-note root → quarter-note third → quarter-note fifth |
| 4 | Quarter-note root → fifth → third → fifth |

All notes use the active chord core, remain within their voice registers, and end within the current bar. Bass octaves use the nearest register center, lower pitch on a tie.

The prescribed registers overlap slightly, so strict `bass < accompaniment < lead` ordering is a preference, not an extra hard constraint. The engine preserves the given register ranges; the revised local cost and cross-cell diversity objective are explicitly stored and documented. All three voices use the global scale; accompaniment and bass use chord-core tones.

Python's deterministic `round()` (ties to even) is used wherever the brief specifies rounding. K-means has a fixed seed and runs under a single numerical thread. JSON keys and serialization, all musical tie-breaks, MIDI event ordering, and timings are stable. Identical decoded pixels, metadata, semantic data, offsets, palette, and tonic produce identical outputs in the same dependency environment. Cross-version or cross-platform floating-point library changes can affect clustering; preserve the lock and semantic sidecar for reproducible experiments.

## Relative normalization and joint musical diversity

For entropy, edge density, physical movement, and lightness, each cell receives an average-tie percentile rank `(rank−1)/15` across the 16 cells. If an entire feature's range is below `1e-6`, all its ranks are 0.5. Equal values otherwise receive the exact average rank; no epsilon jitter or randomness is added. Results are stored as `relative_entropy`, `relative_edge_density`, `relative_movement`, `relative_lightness`, and `relative_activity` directly on each composed cell. Raw visual data are unchanged.

Relative ranks drive local onset density, offbeat target, contour amplitude, complexity budget, anchor, and template selection. Absolute global measurements still determine mode, harmony, tempo, and register. The absolute activity and the relative lead-activity mixture are both stored to make the distinction inspectable.

The visual signature is `(q_H,q_E,q_m,q_L,sin(2θ),cos(2θ))`; both orientation components are zero when orientation is unavailable. Visual distance is Euclidean distance divided by `sqrt(6)`, exactly as specified. Because the orientation components span `[-1,1]`, this distance can reach `sqrt(8/6)`; it is deliberately not silently clipped.

Each candidate's musical signature uses its scale-degree indices normalized by the **shared global allowed-pitch-list span**, then linearly interpolated at eight equally spaced positions along note order. This common reference preserves differences between local melodic anchors. Per-phrase min/max normalization would erase those register differences and is not used. Rhythm is the binary 32-step onset vector. Musical distance is `0.6×mean_absolute_contour_difference + 0.4×normalized_Hamming_distance`; pitch distance is clipped to `[0,1]`.

For every pair, the diversity penalty is `max(0,d_visual−d_music)^2`. The joint objective is `sum(local_costs) + 0.25×sum(pair_penalties)`. Start from local optima, then visit cells in row-major order and test all their retained candidates against the current assignment. Choose the lowest total objective, breaking ties by the lexicographic tuple of all selected degree sequences. Stop after a full pass with no change, or after five passes. The full objective uses a fixed summation order and cannot increase at an update. Selection is approximate and need not find a global minimum.

Every new composition stores all retained candidates, their cost breakdowns, the selected index, and the objective history. `diagnostics.json` and the REPL's `diagnostics` command report unique lead, onset, accompaniment, and bass patterns; duplicates with coordinates; and pairwise distances. Reports are also printed after CLI analysis/recomposition and REPL rebuild/reset. Accompaniment/bass uniqueness compares actual `(pitch,onset,duration)` sequences, ignoring loudness/pan. Duplicate leads compare pitch sequences only, ignoring rhythm; the duplicate count is the number of redundant cells after retaining one representative per sequence (`16−unique_leads`). `largest_duplicate_group` is zero when no duplicate exists.

Identical visual signatures have zero pairwise penalty regardless of musical similarity, so visually identical regions are not forced apart. Distinctness is an objective, not a hard quota of 16 different melodies. A minimum improvement on the Klimt fixture is verified by regression tests.

## Future Chordcat adapter

`ControllerAdapter` defines `select_cell`, the four interpretation setters, and `save_interpretation`. `TerminalController` is the first implementation and delegates to `InterpretationSession`. A future Chordcat adapter can translate documented device events into those same session actions, calling `rebuild` when appropriate. Device transport belongs behind `MidiOutput`; composition does not need to change. No unknown Chordcat button mapping is guessed. The palette can be replaced with a device patch resolver when the patch specification is known.

## Tests and validation

```bash
python -m pytest -q
```

Tests cover image measures and padding, semantic validation, era and mapping boundaries, deterministic rhythm selection, lead constraints and cost calculations, voicings and all eleven accompaniment/bass templates, MIDI structure and timing, deterministic repeated CLI runs, offline/provider failures, controller errors, personal saves, and reset restoring original MIDI bytes. OpenAI request construction and caching are tested with a fake client; playback is tested with a fake MIDI port and absent-backend fallback. A live API request and physical Chordcat playback are not part of the offline validation.

The delivered build passes **165 tests**. See [VALIDATION.md](VALIDATION.md) for the executed workflow and integration limits, and [docs/SPECIFICATION.md](docs/SPECIFICATION.md) for the original implementation brief and full equations.

## Research context and limitations

Quantitative visual descriptors and cross-modal principles are inspired by prior work. **The exact mapping functions, thresholds, coefficients, and optimization weights are prototype design decisions specified for this implementation.** They are not scientifically universal truths and are not attributed to papers as experimentally established constants. User studies, including participation by intended users, would be required to validate accessibility effectiveness.

Relevant inspiration:

- Michael Banf and Volker Blanz, [“Sonification of Images for the Visually Impaired Using a Multi-Level Approach”](https://doi.org/10.1145/2459236.2459264) (2013): multi-level image sonification and exploration.
- [“A toolbox for calculating quantitative image properties in aesthetics research”](https://pmc.ncbi.nlm.nih.gov/articles/PMC11909096/) (2025): quantitative descriptors for studying images. The prototype uses grayscale intensity entropy; it does not equate this with edge-orientation entropy.
- Charles Spence, [“Crossmodal correspondences: A tutorial review”](https://ora.ox.ac.uk/objects/uuid%3Acd54c3eb-603a-4eb0-aa86-b8f392e79f7a) (2011): broader cross-modal context, including pitch associations.
- [“Interactions Between Auditory Elevation, Auditory Pitch and Visual Elevation During Multisensory Perception”](https://pmc.ncbi.nlm.nih.gov/articles/PMC7877490/): pitch/elevation research context. V1 intentionally does not map grid-row elevation to pitch.
- [“Color and tone color: audiovisual crossmodal correspondences with musical instrument timbre”](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2024.1520131/full): color/timbre research context, not a direct instrument-selection rule.
- Torsten Anders and Eduardo R. Miranda, [“Constraint programming systems for modeling music theories and composition”](https://doi.org/10.1145/1978802.1978809) (2011): constraint-based composition as a methodological inspiration.

The demo is an engineering validation, not an accessibility or perceptual study. Musical coherence is encouraged by common harmony, scale membership, distinct roles, voice leading, and melodic costs; aesthetic quality remains subjective.
# CHORDCAT hardware control

Start the existing interactive controller from the saved composition with:

```bash
python main.py chordcat output_klimt_kuss/composition.json
```

The input port is detected by a name containing `CHORDCAT` or `AlphaTheta`; use
`--midi-input 'exact port name'` when detection is ambiguous. Playback still uses
the normal output selection (`--midi-port`). The XY signatures are configured in
`src/artwork_music/controller/chordcat.py` under `XY_GRID_MAPPING`.

Use `--debug` to print grouped non-clock events and unknown signatures. MIDI
channel 5 is handled (MIDI's zero-based channel 4). Signatures shared by the XY
pad and mood keys are rejected by default because the observed messages contain
no reliable physical-source discriminator. For controlled experiments,
`--ambiguous xy` or `--ambiguous mood` selects an explicit policy.
