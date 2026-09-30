# Artwork musical character experiment

Branch: `feat/artwork-musical-character`. The original demo remains on `main`.
No MIDI input signatures, port selection, output channel, or frontend layout were changed.

## Run and compare

Use Python 3.11 or later. From the repository directory:

```bash
python -m pip install -e '.[frontend,playback]'
python frontend.py output_klimt_kuss/composition.json --image artworks/klimt_der_kuss/der_kuss.jpg
```

The experimental frontend automatically recomposes the saved image measurements
into a **temporary preview**. It does not analyze the image again, call a vision
API, or overwrite the original composition and MIDI files. Catalog selections
also use the new preview engine after their baseline has been loaded/generated.

For CHORDCAT, append the exact same port arguments that work in the v1 demo:

```bash
python frontend.py output_klimt_kuss/composition.json --image artworks/klimt_der_kuss/der_kuss.jpg --midi-port "YOUR WORKING OUTPUT NAME" --chordcat-input "YOUR WORKING INPUT NAME"
```

For a simultaneous v1 comparison on another port, use the original baseline:

```bash
python frontend.py output_klimt_kuss/composition.json --image artworks/klimt_der_kuss/der_kuss.jpg --classic --port 8081
```

Only play one app at a time when sharing a MIDI destination. Hardware input should
be enabled in one app at a time as well. `--classic` plays the supplied saved
notes; use the original `output_klimt_kuss/composition.json`, not a newly saved
character interpretation. You can also return to `main` for the untouched demo.

Terminal and CHORDCAT CLI sessions enable the new preview by default, and accept
`--classic` to keep their supplied saved notes. Existing port arguments still work.

To export new MIDI files for listening without the frontend:

```bash
python main.py recompose output_klimt_kuss/composition.json --character --output output/klimt_character
```

`analyze` continues to generate the original baseline. `recompose --character`
explicitly exports the experiment. Plain `recompose` preserves an existing saved
character, but does not add one to an original composition.

## What changes in the music

- A four-note theme occupies the first bar of every cell. Its scale-step contour
  and onset pattern remain recognizable, while local brightness moves its register.
- The second bar answers the theme. Existing visual activity controls its density;
  melody scoring and ensemble selection still shape the response.
- Artwork families have distinct two-chord harmony, rhythm, articulation, and
  accompaniment/bass choices. They retain the shared scale and tempo across cells.
- The lead has stronger prominence, accents, and articulation. Accompaniment and
  bass velocities are lower to leave room for the theme.
- Mood controls still choose Aeolian/Dorian/Ionian. They rebuild the same artwork
  theme within the new scale rather than selecting another theme.

Examples of authored interpretations:

| Artwork | Profile | Tonic | First-bar onsets (sixteenths) |
| --- | --- | --- | --- |
| The Kiss / Der Kuss | Golden embrace | D | 0, 4, 6, 10 |
| The Scream | Fractured cry | F# | 0, 3, 6, 11 |
| Wanderer above the Sea of Fog | Distant horizon | D | 0, 6, 10, 14 |
| Woman with a Parasol | Dancing breeze | G | 0, 3, 8, 10 |
| The Great Wave | Rolling current | A | 0, 2, 6, 10 |
| The Starry Night | Luminous orbit | E | 0, 3, 6, 12 |

These are curated musical choices, not scientifically determined meanings of
paintings. Unknown artwork titles select a family from measured movement,
edge density, entropy, and lightness. Profiles live in
`src/artwork_music/music/character.py` and can be adjusted after listening.

## Compatibility and remaining limitations

Original schemas 1.0–1.2 remain readable and their saved notes are preserved.
New character exports use schema **1.3**, with their complete profile stored in
the composition. They can be reopened and rebuilt on this branch. The older
`main` code cannot read these new exports; keep the v1 files for its demo.

The transport still collapses all instrument layers onto CHORDCAT MIDI channel
6 (`mido channel=5`). This experiment does not add multitrack hardware routing
or assume General MIDI program names correspond to CHORDCAT patches. Use the
known working device setup and judge the result through its actual preset.

Other inherited behavior is unchanged: cell selection interrupts/restarts
playback, and newly analyzed catalog artworks currently use the demo semantic
sidecar. Character profiles do not validate or replace that semantic data.

## Listening check

1. Keep the CHORDCAT output port, track, preset, and headphone level identical.
2. Compare cells 1, 6, 11, and 16 in classic and character mode.
3. Check whether the first-bar theme is recognizable across cells, and whether
   the answering bar changes without burying the lead under the bass.
4. Try dark, neutral, and bright mood keys. The theme should remain recognizable.
5. Explore rapidly across XY cells to check the existing cancellation behavior.

Automated tests check motif preservation, timing/pitch constraints, deterministic
generation, variation between cells, mood changes, saved-profile reload, and
byte-for-byte preservation of the original preview MIDI. Musical quality and
CHORDCAT sound must still be judged on the connected device.
