# Build a Working Prototype: Artwork → Musical Interpretation → 4×4 Exploration

## 1. Goal

Build a complete working Python prototype that transforms an artwork into 16 short, coherent musical compositions corresponding to a 4×4 spatial grid.

The system must not simply map pixels to isolated sounds.

The intended pipeline is:

Artwork  
→ quantitative computer-vision analysis  
→ semantic visual analysis  
→ global musical interpretation  
→ local musical constraints for each of 16 grid cells  
→ deterministic rule-based / optimization-based composition  
→ three-part mini-ensemble per grid cell  
→ MIDI output  
→ interactive exploration  
→ global reinterpretation by the user  
→ save individual interpretations.

Each grid cell should produce approximately two bars / 4–8 seconds of coherent music.

Each grid cell contains three different musical voices:

1. Lead melody
2. Harmonic accompaniment
3. Bass

They must play different material but remain harmonically coherent.

The same artwork and the same interpretation parameters must always produce the same result.

Do NOT introduce random composition unless a deterministic seed is explicitly used. For V1, prefer full determinism.

---

# 2. Core Design Principle

Separate three layers:

\[
\text{Visual analysis}
\rightarrow
\text{Musical constraints}
\rightarrow
\text{Composition}
\]

Do not directly implement rules such as:

`blue -> C#`

or

`tree -> violin`.

Instead, quantitative and semantic image features define a constrained musical world, and a composer generates music inside that world.

For each grid cell \(g\),

\[
P_g=C(M_G,L_g)
\]

where:

- \(M_G\) = global musical context of the full artwork
- \(L_g\) = local musical identity of grid cell \(g\)
- \(P_g\) = final three-part phrase for grid cell \(g\)

with

\[
P_g=
(
P_g^{lead},
P_g^{acc},
P_g^{bass}
).
\]

---

# 3. Technical Stack

Use Python 3.11+.

Preferred libraries:

- numpy
- opencv-python
- scikit-learn
- Pillow
- pydantic
- pretty_midi
- mido
- python-rtmidi
- OpenAI Python SDK only behind a provider abstraction for semantic vision
- pytest

Do not build a heavy GUI.

Provide:

- CLI
- simple interactive terminal / REPL
- MIDI files
- optional real-time MIDI output if a MIDI device is connected

Design MIDI/device access behind an abstraction so the Chordcat can be connected later without rewriting the composition engine.

---

# 4. Input

The prototype must accept:

```text
image_path
title
artist
year
art_movement
optional music_era_override
```

Example CLI:

```bash
python main.py analyze \
  --image painting.jpg \
  --title "Example Painting" \
  --artist "Example Artist" \
  --year 1889 \
  --art-movement "Post-Impressionism"
```

Do NOT infer the creation year from the image.

If the year is unknown, require `music_era_override`.

---

# 5. Image Grid

Split the artwork into an exact 4×4 grid.

Use:

\[
g=(r,c),
\qquad
r,c\in\{0,1,2,3\}.
\]

This produces 16 cells.

Store row and column explicitly.

Also generate a debug image:

```text
grid_overlay.png
```

showing the 4×4 division and cell indices.

---

# 6. Quantitative Computer-Vision Features

Compute features for:

1. the complete artwork
2. each of the 16 grid cells

## 6.1 Color clustering

Use exactly 3 color clusters.

Do NOT cluster directly in raw HSL hue space because hue is circular.

Perform k-means clustering in CIELAB space.

Use:

```text
k = 3
random_state = 0
n_init = 10
```

After clustering, convert cluster centroids to HSL.

Represent each cluster as:

\[
C_k=(h_k,s_k,l_k,w_k)
\]

where:

- \(h_k\in[0,360)\)
- \(s_k\in[0,1]\)
- \(l_k\in[0,1]\)
- \(w_k\in[0,1]\)

and

\[
\sum_{k=1}^{3}w_k=1.
\]

Sort clusters by descending weight for storage.

If fewer than 3 distinct color groups exist, return the available clusters and pad remaining entries with weight 0.

---

## 6.2 Global and local lightness

Define lightness as the mean normalized HSL lightness across the corresponding pixels:

\[
L\in[0,1].
\]

---

## 6.3 Shannon entropy

Convert the corresponding image region to grayscale.

Use 256 histogram bins.

For histogram probability \(p_i\),

\[
H=
-\sum_{i=0}^{255}
p_i\log_2p_i.
\]

Ignore terms where \(p_i=0\).

Since

\[
H_{\max}=\log_2(256)=8,
\]

normalize:

\[
\boxed{
H_{\text{norm}}=\frac H8
}
\]

so that

\[
H_{\text{norm}}\in[0,1].
\]

Use this formula globally and locally.

---

## 6.4 Edge density

Use Canny edge detection.

Use automatic thresholds based on median grayscale intensity \(m\):

\[
t_{\min}
=
\max(0,0.66m)
\]

\[
t_{\max}
=
\min(255,1.33m).
\]

Define:

\[
\boxed{
E=
\frac{\#\text{edge pixels}}
{\#\text{all pixels}}
}
\]

with

\[
E\in[0,1].
\]

---

## 6.5 Dominant edge orientation

Compute Sobel gradients.

For edge pixels, compute orientation modulo \(180^\circ\).

Create an orientation histogram on:

\[
[0^\circ,180^\circ)
\]

using 18 bins of \(10^\circ\).

Weight votes by gradient magnitude.

The center of the strongest bin is the dominant orientation:

\[
\theta_g\in[0^\circ,180^\circ).
\]

If there are too few edge pixels to estimate orientation reliably, set:

```json
"orientation_deg": null
```

and later use:

\[
c_g=0,\qquad V_g=0.
\]

---

# 7. Semantic Vision Analysis

Semantic features come from a multimodal vision model.

Implement this behind:

```python
class SemanticAnalyzer:
    ...
```

Do not couple the rest of the project to one provider.

If `OPENAI_API_KEY` is available, provide an OpenAI implementation.

If no API key exists, allow semantic analysis to be loaded from a sidecar JSON file so the rest of the program still works.

The semantic analyzer must output strict structured data.

---

## 7.1 Global semantic features

For the complete artwork return:

```json
{
  "valence": {
    "negative": 0.15,
    "neutral": 0.25,
    "positive": 0.60
  },
  "movement": 0.36
}
```

Require:

\[
q_-+q_0+q_+=1.
\]

Define global valence:

\[
\boxed{
v=q_+-q_-
}
\]

therefore:

\[
v\in[-1,1].
\]

Global movement:

\[
m_G\in[0,1].
\]

Movement means visually depicted or strongly implied physical activity, not emotional positivity.

Examples:

- static architecture → low
- still landscape → low
- running people → high
- moving vehicles → high
- turbulent water → medium/high

---

## 7.2 Local semantic features

For every cell return:

```json
{
  "objects": [
    {
      "label": "tree",
      "confidence": 0.91
    }
  ],
  "movement": 0.44
}
```

Maximum 3 dominant objects per grid cell.

Use:

\[
m_g\in[0,1].
\]

Objects MUST be stored but do NOT directly map to notes or instruments in V1.

Objects may inform the semantic model's movement estimate.

Do not implement rules such as:

```text
tree -> flute
person -> violin
```

---

# 8. Historical Musical Era

Determine a musical era from artwork metadata.

Allow explicit override.

Default mapping:

```text
year < 1450       -> Medieval
1450–1599         -> Renaissance
1600–1749         -> Baroque
1750–1819         -> Classical
1820–1889         -> Romantic
1890–1919         -> Impressionist / Early Modern
>= 1920           -> Modern / Contemporary
```

This mapping is deliberately approximate.

Do not pretend that art periods and musical periods correspond perfectly.

Store both:

```text
art_movement
music_era
```

---

# 9. Instrument Palette by Era

The musical era defines the allowed three-instrument mini-orchestra.

Use General MIDI instrument names and resolve them via `pretty_midi.instrument_name_to_program()` rather than manually hard-coding program numbers.

Use these V1 palettes:

```text
Medieval:
lead = Recorder
accompaniment = Acoustic Guitar (nylon)
bass = Cello

Renaissance:
lead = Recorder
accompaniment = Acoustic Guitar (nylon)
bass = Cello

Baroque:
lead = Flute
accompaniment = Harpsichord
bass = Cello

Classical:
lead = Clarinet
accompaniment = Acoustic Grand Piano
bass = Cello

Romantic:
lead = Violin
accompaniment = Acoustic Grand Piano
bass = Cello

Impressionist / Early Modern:
lead = Flute
accompaniment = Orchestral Harp
bass = String Ensemble 1

Modern / Contemporary:
lead = Lead 1 (square)
accompaniment = Pad 1 (new age)
bass = Synth Bass 1
```

Keep the palette in a configuration file so it can later be replaced with actual Chordcat patches.

---

# 10. Global Musical Mapping

Global raw visual/semantic data:

\[
G=
(v,m_G,H_G,L_G,C_1,C_2,C_3,e)
\]

where \(e\) is the musical era.

Produce:

\[
M_G=
(
S,
\Pi,
T,
R,
\kappa,
\mathcal I
).
\]

---

## 10.1 Mood / valence → mode

Use tonic D for V1.

Make tonic configurable, default:

```text
D
```

Define:

\[
S(v)=
\begin{cases}
\text{Aeolian}, & v<-\frac13\\
\text{Dorian}, & -\frac13\leq v<\frac13\\
\text{Ionian}, & v\geq\frac13.
\end{cases}
\]

Therefore:

D Ionian:

\[
D,E,F^\#,G,A,B,C^\#
\]

D Dorian:

\[
D,E,F,G,A,B,C
\]

D Aeolian:

\[
D,E,F,G,A,B^\flat,C.
\]

---

## 10.2 Mode → two-bar harmony

Use one chord per bar.

For two bars:

\[
\Pi(S)=
\begin{cases}
I\rightarrow V,&S=\text{Ionian}\\
i\rightarrow IV,&S=\text{Dorian}\\
i\rightarrow VI,&S=\text{Aeolian}.
\end{cases}
\]

Construct chords diatonically from the selected scale.

---

## 10.3 Global entropy → harmonic richness

Define:

\[
e_H=
\begin{cases}
0,&H_G<0.40\\
1,&0.40\leq H_G<0.75\\
2,&H_G\geq0.75.
\end{cases}
\]

If:

```text
e_H = 0
```

use diatonic triads.

If:

```text
e_H = 1
```

add the diatonic seventh.

If:

```text
e_H = 2
```

add the diatonic seventh and ninth.

Do NOT use random extensions.

---

## 10.4 Global movement → tempo

Use:

\[
\boxed{
T=65+55m_G
}
\]

and round:

\[
\boxed{
T_{\text{BPM}}
=
\operatorname{round}(65+55m_G).
}
\]

Therefore:

\[
65\leq T\leq120.
\]

---

## 10.5 Global lightness → register

Define global center MIDI pitch:

\[
\boxed{
p_c=
\operatorname{round}(48+24L_G)
}
\]

Then derive voice registers:

Lead:

\[
\boxed{
R_{lead}=[p_c-7,p_c+9]
}
\]

Accompaniment:

\[
\boxed{
R_{acc}=[p_c-15,p_c-3]
}
\]

Bass:

\[
\boxed{
R_{bass}=[p_c-27,p_c-15].
}
\]

Clip all values to MIDI range:

\[
[0,127].
\]

All generated pitches must also belong to the selected global scale.

---

## 10.6 Global entropy → complexity budget

Define:

\[
\boxed{
\kappa_G=H_G.
}
\]

This will later influence the maximum melodic interval allowed locally.

---

# 11. Global Color Anchors

Use the three global color clusters as color anchors for the three ensemble roles.

Sort the three global clusters by lightness.

Assign:

```text
brightest global cluster -> lead color anchor
middle global cluster    -> accompaniment color anchor
darkest global cluster   -> bass color anchor
```

This does NOT determine pitch or instrument identity.

The historical era still determines actual instruments.

The color anchors only influence local voice prominence / MIDI velocity.

---

# 12. User Interpretation Layer

The artwork produces an initial interpretation, but the user must be able to modify the interpretation globally.

Do NOT change the raw visual analysis.

Store four user offsets:

\[
\delta_v,\delta_m,\delta_H,\delta_L
\]

each constrained to:

\[
[-0.5,0.5].
\]

Define effective global values:

\[
\boxed{
v'=
\operatorname{clip}(v+\delta_v,-1,1)
}
\]

\[
\boxed{
m_G'=
\operatorname{clip}(m_G+\delta_m,0,1)
}
\]

\[
\boxed{
H_G'=
\operatorname{clip}(H_G+\delta_H,0,1)
}
\]

\[
\boxed{
L_G'=
\operatorname{clip}(L_G+\delta_L,0,1).
}
\]

Interpretation dimensions:

```text
delta_v -> emotional valence
delta_m -> energy / movement
delta_H -> complexity
delta_L -> brightness / register
```

Whenever these change, recompute:

- mode
- harmony
- tempo
- register
- global complexity
- all 16 phrases

but do NOT rerun visual image analysis.

Same artwork + same offsets must always produce identical MIDI.

---

# 13. Local Musical Mapping

For grid cell \(g=(r,c)\), use:

\[
L_g=
(
H_g,
E_g,
m_g,
\theta_g,
C_{g,1},
C_{g,2},
C_{g,3},
O_g,
c
).
\]

---

# 14. Horizontal Grid Position → Stereo Panning

Do NOT map vertical grid position to pitch.

Only horizontal position influences stereo location.

For column:

\[
c\in\{0,1,2,3\}
\]

define:

\[
\boxed{
\pi_g=-1+\frac{2c}{3}.
}
\]

Therefore:

```text
column 0 -> -1.000
column 1 -> -0.333
column 2 -> +0.333
column 3 -> +1.000
```

Map this to MIDI pan CC 10.

---

# 15. Local Activity → Number of Lead Note Onsets

Compute:

\[
\boxed{
D_g=
0.65m_g+0.35E_g.
}
\]

Then:

\[
\boxed{
N_g=
4+\operatorname{round}(6D_g).
}
\]

Therefore:

\[
4\leq N_g\leq10.
\]

---

# 16. Local Entropy → Target Offbeat Activity

Use a two-bar 4/4 phrase on an eighth-note grid:

\[
t\in\{0,\ldots,15\}.
\]

Define target offbeat count:

\[
\boxed{
O_g^*
=
\operatorname{round}
\left[
H_g
\min(4,N_g-2)
\right].
}
\]

---

# 17. Rhythm Generation

Represent onset locations:

\[
r_t\in\{0,1\}.
\]

Hard constraints:

\[
\sum_{t=0}^{15}r_t=N_g
\]

and:

\[
\boxed{
r_0=r_8=1.
}
\]

Both bars must begin with a note.

Define actual offbeat count:

\[
O(r)=
\sum_{\substack{t=0\\t\text{ odd}}}^{15}
r_t.
\]

Define:

\[
J_{\text{offbeat}}
=
\left(
\frac{O(r)-O_g^*}{4}
\right)^2.
\]

Let:

\[
N_1=\sum_{t=0}^{7}r_t
\]

\[
N_2=\sum_{t=8}^{15}r_t.
\]

Define bar-balance penalty:

\[
J_{\text{balance}}
=
\left(
\frac{N_1-N_2}{N_g}
\right)^2.
\]

Define adjacent-onset penalty:

\[
J_{\text{adj}}
=
\frac{
\sum_{t=0}^{14}r_tr_{t+1}
}{
\max(1,N_g-1)
}.
\]

Final rhythm cost:

\[
\boxed{
J_{\text{rhythm}}
=
\operatorname{clip}
\left(
0.70J_{\text{offbeat}}
+
0.20J_{\text{balance}}
+
0.10J_{\text{adj}},
0,1
\right).
}
\]

Enumerate valid onset sets and choose:

\[
\boxed{
r_g^*=
\arg\min_rJ_{\text{rhythm}}.
}
\]

Tie-breaking must be deterministic.

Use lexicographic order of onset-position tuples.

---

# 18. Lead Note Durations

Allowed lead note durations:

```text
1 eighth
1 quarter
1 half
```

represented as eighth-note units:

\[
\{1,2,4\}.
\]

For each onset, look at:

- next onset
- bar boundary

Choose the longest duration from:

\[
\{4,2,1\}
\]

that:

1. does not overlap the next onset
2. does not cross the current bar boundary.

Any unused gap becomes silence/rest.

---

# 19. Orientation → Melodic Contour

Convert orientation to radians:

\[
\theta_g\in[0,\pi).
\]

Define directional contour:

\[
\boxed{
c_g=\sin(2\theta_g).
}
\]

Thus:

```text
45°  -> strongly ascending tendency
135° -> strongly descending tendency
0°   -> approximately neutral
90°  -> approximately neutral
```

If orientation is unavailable:

\[
c_g=0.
\]

---

# 20. Orientation + Entropy → Maximum Melodic Step

Define verticality:

\[
\boxed{
V_g=|\sin\theta_g|.
}
\]

If orientation unavailable:

\[
V_g=0.
\]

Use effective global entropy \(H_G'\).

Define:

\[
\boxed{
\kappa_g=
\frac{H_G'+H_g}{2}.
}
\]

Then:

\[
\boxed{
J_g^{max}
=
1+
\left\lfloor
2\kappa_g+V_g
\right\rfloor.
}
\]

Typical result:

\[
J_g^{max}\in\{1,2,3,4\}.
\]

This value is measured in scale steps, not semitones.

---

# 21. Local Color Clusters → Ensemble Voice Weights

Use the three global color-role anchors defined earlier.

For hue distance:

\[
\boxed{
d_h(h_1,h_2)
=
\frac{
\min(|h_1-h_2|,360-|h_1-h_2|)
}{180}.
}
\]

For two color clusters:

\[
C=(h,s,l)
\]

and

\[
C'=(h',s',l')
\]

define:

\[
\boxed{
d(C,C')
=
0.50d_h(h,h')
+
0.25|s-s'|
+
0.25|l-l'|.
}
\]

For every local color cluster, find the closest global role anchor.

Sum its cluster weight into:

```text
q_lead
q_acc
q_bass
```

so initially:

\[
q_{lead}+q_{acc}+q_{bass}=1.
\]

To ensure all three voices remain audible, apply smoothing:

\[
\epsilon=0.10.
\]

Then:

\[
\boxed{
\tilde q_r
=
\frac{q_r+\epsilon}{1+3\epsilon}.
}
\]

Use role velocity:

Lead:

\[
\boxed{
V_{lead}
=
\operatorname{round}
(55+45\tilde q_{lead})
}
\]

Accompaniment:

\[
\boxed{
V_{acc}
=
\operatorname{round}
(45+40\tilde q_{acc})
}
\]

Bass:

\[
\boxed{
V_{bass}
=
\operatorname{round}
(50+40\tilde q_{bass}).
}
\]

Clip MIDI velocity to:

\[
[1,127].
\]

---

# 22. Objects

Store maximum 3 objects per grid cell.

Objects are semantic information.

For V1 they do NOT:

- select notes
- select instruments
- alter harmony directly.

They may indirectly influence music because the semantic model uses them when estimating movement.

Keep this intentionally simple.

---

# 23. Lead Composer

The lead melody is the only voice generated through an optimization/search procedure.

It must be deterministic.

---

# 24. Scale Representation

Create the ordered list of MIDI pitches inside:

\[
R_{lead}
\]

that belong to the selected global scale.

Represent them internally as ordered scale-degree indices:

\[
d_1,d_2,\ldots,d_N.
\]

All lead notes must come from this list.

---

# 25. Lead Hard Constraints

All notes must be inside the lead register.

All notes must belong to the global scale.

Maximum scale-step movement:

\[
\boxed{
|d_k-d_{k-1}|
\leq
J_g^{max}.
}
\]

If:

\[
N_g\geq4
\]

require at least 3 distinct pitches:

\[
\boxed{
|\{d_1,\ldots,d_{N_g}\}|\geq3.
}
\]

Never allow three identical pitches consecutively:

\[
\boxed{
\neg(d_k=d_{k+1}=d_{k+2}).
}
\]

If no valid phrase is found, increase:

\[
J_g^{max}
\]

by 1, up to maximum 4, and retry.

Log this relaxation.

---

# 26. Harmony Cost

At the onset time of note \(k\), determine the active chord.

Let:

\[
h_k=
\begin{cases}
0,&\text{note is a chord tone}\\
1,&\text{note is another scale tone}.
\end{cases}
\]

Use metric weight:

\[
w_k=
\begin{cases}
2,&\text{onset falls on a quarter-note beat}\\
1,&\text{otherwise}.
\end{cases}
\]

Then:

\[
\boxed{
J_{\text{harmony}}
=
\frac{
\sum_kw_kh_k
}{
\sum_kw_k
}.
}
\]

---

# 27. Contour Cost

Let:

\[
\tau_k=
\frac{k-1}{N_g-1}.
\]

Define:

\[
\boxed{
A_g=1+2H_g.
}
\]

Let \(d_c\) be the midpoint of the allowed lead scale-degree range.

Desired contour:

\[
\boxed{
d_k^*
=
d_c+
A_gc_g(2\tau_k-1).
}
\]

Cost:

\[
\boxed{
J_{\text{contour}}
=
\operatorname{clip}
\left[
\frac1{N_g}
\sum_k
\left(
\frac{d_k-d_k^*}{A_g+1}
\right)^2,
0,1
\right].
}
\]

---

# 28. Melodic Smoothness Cost

Define:

\[
\Delta_k=d_k-d_{k-1}.
\]

Use:

\[
\phi(|\Delta|)
=
\begin{cases}
0.25,&|\Delta|=0\\
0,&|\Delta|=1\\
0.20,&|\Delta|=2\\
0.60,&|\Delta|=3\\
1,&|\Delta|\geq4.
\end{cases}
\]

Then:

\[
\boxed{
J_{\text{smooth}}
=
\frac1{N_g-1}
\sum_{k=2}^{N_g}
\phi(|\Delta_k|).
}
\]

---

# 29. Leap Resolution Cost

Treat:

\[
|\Delta_k|\geq3
\]

as a large leap.

After a large leap, prefer a small movement in the opposite direction.

For every eligible \(k\):

\[
\ell_k=
\mathbf1_{\{|\Delta_k|\geq3\}}
\left[
\mathbf1_{\{\Delta_k\Delta_{k+1}\geq0\}}
+
\frac12
\max(0,|\Delta_{k+1}|-2)^2
\right].
\]

Then:

\[
\boxed{
J_{\text{leap}}
=
\operatorname{clip}
\left[
\frac1{\max(1,N_g-2)}
\sum_k\ell_k,
0,1
\right].
}
\]

If fewer than 3 notes exist, use:

\[
J_{\text{leap}}=0.
\]

---

# 30. Cadence Cost

Evaluate the final note against the second-bar chord.

Define:

\[
c_N=
\begin{cases}
0,&\text{root of final chord}\\
0.25,&\text{another chord tone}\\
1,&\text{otherwise}.
\end{cases}
\]

Define approach penalty:

\[
c_{\text{approach}}
=
\operatorname{clip}
\left(
\frac{
\max(0,|\Delta_N|-2)^2
}{4},
0,1
\right).
\]

Then:

\[
\boxed{
J_{\text{cadence}}
=
\operatorname{clip}
(
0.75c_N+0.25c_{\text{approach}},
0,1
).
}
\]

---

# 31. Repetition Cost

Define:

\[
\boxed{
J_{\text{repeat}}
=
\frac1{N_g-1}
\sum_{k=2}^{N_g}
\mathbf1[d_k=d_{k-1}].
}
\]

---

# 32. Final Lead Cost Function

Use:

\[
\boxed{
J_g=
0.22J_{\text{harmony}}
+
0.25J_{\text{contour}}
+
0.15J_{\text{smooth}}
+
0.08J_{\text{leap}}
+
0.20J_{\text{cadence}}
+
0.10J_{\text{repeat}}.
}
\]

Weights sum to:

\[
1.
\]

Find:

\[
\boxed{
P_g^{lead}
=
\arg\min J_g.
}
\]

---

# 33. Search Algorithm

Do NOT brute-force the entire search space.

Implement deterministic beam search.

Use:

```text
beam_width = 100
```

Build the sequence from left to right.

Use the relevant partial costs during search.

Evaluate full cost when phrase is complete.

Tie-break using lexicographic order of scale-degree sequences.

No randomness.

---

# 34. Bass Generation

Bass is deterministic and simple.

Use local activity:

\[
D_g=0.65m_g+0.35E_g.
\]

For every bar determine:

- chord root \(r_b\)
- chord fifth \(f_b\)

Choose their octaves inside:

\[
R_{bass}.
\]

If:

\[
D_g<0.60
\]

play:

\[
\boxed{
r_b
}
\]

as one whole-note bass tone per bar.

If:

\[
D_g\geq0.60
\]

play:

\[
\boxed{
r_b\rightarrow f_b
}
\]

as two half notes per bar.

Bass does not use the lead melody.

---

# 35. Accompaniment Generation

Use the chord core:

```text
root
third
fifth
```

even when the global chord also contains seventh/ninth extensions.

---

## 35.1 Chord voicing

For bar 1:

Choose the compact inversion inside:

\[
R_{acc}
\]

whose center is closest to the center of the accompaniment register.

For each subsequent bar, consider all valid inversions inside the register and choose:

\[
\boxed{
V_b^*
=
\arg\min_{V}
\sum_i
|v_i-v_{b-1,i}|.
}
\]

This creates smooth chord voice leading.

Tie-break deterministically.

---

## 35.2 Entropy → accompaniment pattern

If:

\[
H_g<0.33
\]

use one sustained chord for the complete bar.

If:

\[
0.33\leq H_g<0.66
\]

use quarter-note arpeggio:

\[
\boxed{
low\rightarrow middle\rightarrow high\rightarrow middle.
}
\]

If:

\[
H_g\geq0.66
\]

use eighth-note pattern:

\[
\boxed{
low,
middle,
high,
middle,
high,
middle,
low,
middle.
}
\]

Accompaniment and lead must therefore not simply duplicate each other.

---

# 36. Ensemble Constraints

The voices must occupy separate musical roles.

Prefer:

\[
\boxed{
p^{bass}<p^{acc}<p^{lead}.
}
\]

The predefined register ranges should already enforce this.

All voices must use the same:

- scale
- harmony
- tempo

Bass and accompaniment should use chord tones only.

Lead may use any scale tone, with harmony cost determining stability.

---

# 37. MIDI Rendering

Each grid cell must produce a MIDI file with 3 tracks / instruments:

```text
lead
accompaniment
bass
```

Use different MIDI channels.

Write:

- program change
- note events
- velocities
- tempo
- pan CC

Pan should apply consistently to the complete grid-cell ensemble.

Output:

```text
output/
    analysis_raw.json
    composition.json
    grid_overlay.png

    midi/
        cell_0_0.mid
        cell_0_1.mid
        ...
        cell_3_3.mid
        overview.mid
```

`overview.mid` should play the 16 cells sequentially in row-major order with one bar of silence between cells.

---

# 38. Main JSON Structure

Use a structure conceptually equivalent to:

```json
{
  "artwork": {
    "title": "...",
    "artist": "...",
    "year": 1889,
    "art_movement": "Post-Impressionism",
    "music_era": "Impressionist / Early Modern"
  },

  "raw_global_visual": {
    "valence_probs": {
      "negative": 0.15,
      "neutral": 0.25,
      "positive": 0.60
    },

    "valence": 0.45,
    "movement": 0.36,
    "entropy": 0.48,
    "lightness": 0.57,

    "color_clusters": []
  },

  "interpretation": {
    "delta_valence": 0.0,
    "delta_movement": 0.0,
    "delta_complexity": 0.0,
    "delta_lightness": 0.0
  },

  "effective_global_visual": {
    "valence": 0.45,
    "movement": 0.36,
    "entropy": 0.48,
    "lightness": 0.57
  },

  "global_music": {
    "tonic": "D",
    "mode": "ionian",
    "tempo_bpm": 85,

    "lead_register": [55, 71],
    "accompaniment_register": [47, 59],
    "bass_register": [35, 47],

    "harmony": [],

    "instruments": {
      "lead": "Flute",
      "accompaniment": "Orchestral Harp",
      "bass": "String Ensemble 1"
    }
  },

  "cells": []
}
```

Each cell:

```json
{
  "row": 1,
  "column": 2,

  "visual": {
    "entropy": 0.61,
    "edge_density": 0.37,
    "orientation_deg": 42,
    "movement": 0.44,

    "objects": [],

    "color_clusters": []
  },

  "musical_constraints": {
    "pan": 0.333,
    "activity": 0.4155,
    "lead_note_onsets": 6,
    "target_offbeats": 2,
    "contour": 0.995,
    "max_scale_step": 2,

    "voice_weights": {
      "lead": 0.52,
      "accompaniment": 0.29,
      "bass": 0.19
    }
  },

  "phrase": {
    "lead": {},
    "accompaniment": {},
    "bass": {},
    "total_lead_cost": 0.076
  }
}
```

Use Pydantic models instead of passing raw dictionaries throughout the code.

---

# 39. Interactive Prototype

Implement a simple terminal REPL.

Required commands:

```text
play ROW COL
```

Play a grid cell through an available MIDI output port.

If no output port exists, report the generated MIDI filepath instead of crashing.

```text
show ROW COL
```

Print its visual features, musical constraints and generated notes.

```text
set valence VALUE
set energy VALUE
set complexity VALUE
set brightness VALUE
```

Values represent interpretation offsets in:

\[
[-0.5,0.5].
\]

After changing an interpretation value:

```text
rebuild
```

recompute all global mappings and 16 musical phrases without rerunning image analysis.

Also provide:

```text
reset
```

and:

```text
save NAME
```

---

# 40. Saving Personal Interpretations

When:

```text
save NAME
```

is called, create:

```text
output/interpretations/NAME/
```

containing:

```text
composition.json
midi/cell_0_0.mid
...
midi/cell_3_3.mid
```

The saved JSON must include the four user interpretation offsets.

This implements:

Artwork  
→ initial machine interpretation  
→ user modification  
→ saved personal musical interpretation.

---

# 41. Controller Abstraction for Future Chordcat Integration

Do NOT hard-code keyboard/controller logic into composition classes.

Create an interface conceptually like:

```python
class ControllerAdapter:
    def select_cell(self, row: int, col: int): ...
    def set_valence(self, value: float): ...
    def set_energy(self, value: float): ...
    def set_complexity(self, value: float): ...
    def set_brightness(self, value: float): ...
    def save_interpretation(self, name: str): ...
```

The CLI REPL is the first implementation.

Later a:

```text
ChordcatControllerAdapter
```

will translate actual Chordcat MIDI events into the same actions.

Do not implement unknown Chordcat button mappings yet.

---

# 42. Recommended Project Structure

Use approximately:

```text
music_ai_artwork/
│
├── main.py
├── pyproject.toml
├── README.md
│
├── config/
│   └── instrument_palettes.yaml
│
├── src/
│   ├── models.py
│   │
│   ├── analysis/
│   │   ├── image_grid.py
│   │   ├── color_features.py
│   │   ├── entropy.py
│   │   ├── edges.py
│   │   ├── orientation.py
│   │   ├── semantic_base.py
│   │   ├── semantic_openai.py
│   │   └── semantic_sidecar.py
│   │
│   ├── music/
│   │   ├── eras.py
│   │   ├── scales.py
│   │   ├── harmony.py
│   │   ├── global_mapping.py
│   │   ├── local_mapping.py
│   │   ├── rhythm.py
│   │   ├── lead_costs.py
│   │   ├── lead_composer.py
│   │   ├── accompaniment.py
│   │   ├── bass.py
│   │   └── ensemble.py
│   │
│   ├── render/
│   │   ├── midi_writer.py
│   │   └── midi_player.py
│   │
│   └── controller/
│       ├── base.py
│       └── repl.py
│
└── tests/
```

Keep modules small and testable.

---

# 43. Determinism Requirement

Running the same:

```text
image
metadata
semantic analysis
interpretation offsets
```

twice must produce exactly the same:

```text
analysis JSON
musical constraints
note pitches
rhythms
MIDI files
```

Do not use unseeded randomness anywhere.

---

# 44. Required Tests

Write automated tests.

At minimum test:

### Image analysis

A uniform grayscale image must have near-zero entropy.

A checkerboard / strongly structured image must have greater edge density than a uniform image.

Three color clusters must have weights summing to 1.

---

### Global mapping

Verify:

\[
v<-1/3\rightarrow Aeolian
\]

\[
-1/3\leq v<1/3\rightarrow Dorian
\]

\[
v\geq1/3\rightarrow Ionian.
\]

Verify:

\[
m_G=0\rightarrow65\text{ BPM}
\]

\[
m_G=1\rightarrow120\text{ BPM}.
\]

---

### Panning

Verify:

```text
column 0 -> -1.0
column 1 -> approximately -0.333
column 2 -> approximately +0.333
column 3 -> +1.0
```

---

### Lead

Every lead note must:

- belong to selected scale
- lie inside lead register
- respect max scale-step constraint
- never contain 3 identical consecutive pitches
- use at least 3 distinct pitches when \(N_g\geq4\)

---

### Rhythm

Every phrase must:

- span exactly 2 bars
- use 4/4
- include onset at positions 0 and 8
- contain exactly \(N_g\) lead onsets

---

### Ensemble

Each cell must contain:

```text
lead
accompaniment
bass
```

and they must not simply duplicate the same notes.

---

### Interpretation

Changing only:

```text
delta_movement
```

must alter tempo but must not alter raw image analysis.

Changing interpretation parameters and then resetting them to zero must recreate the original MIDI exactly.

---

# 45. Error Handling

The prototype must fail clearly and gracefully.

Examples:

- missing image
- invalid year
- semantic provider unavailable
- no MIDI output port
- invalid interpretation offset
- impossible lead search

Never silently generate arbitrary values.

If semantic analysis is unavailable, instruct the user to provide semantic sidecar JSON.

---

# 46. Debugging / Explainability

For every grid cell, support:

```text
show ROW COL
```

Output something like:

```text
Cell (1,2)

Visual:
entropy = 0.61
edge density = 0.37
movement = 0.44
orientation = 42 degrees
objects = tree, sky

Derived:
activity = 0.4155
note onsets = 6
target offbeats = 2
contour = 0.995
max scale step = 2

Lead cost:
harmony = ...
contour = ...
smoothness = ...
leap = ...
cadence = ...
repetition = ...
total = ...

Ensemble:
lead = Flute
accompaniment = Harp
bass = Strings
```

The mathematical transformation must be inspectable.

---

# 47. README

The README must explain:

1. project concept
2. architecture
3. installation
4. semantic API configuration
5. sidecar semantic fallback
6. analysis command
7. interactive REPL
8. interpretation controls
9. MIDI output
10. mathematical mapping summary
11. how a future Chordcat adapter will connect

Do not describe the mappings as scientifically universal truths.

Explicitly state that:

- quantitative visual descriptors and cross-modal principles are inspired by prior work
- the exact mapping functions and weights are prototype design decisions
- user studies would be required to validate accessibility effectiveness.

---

# 48. Research Inspiration

Document these as inspiration, not as exact sources for every coefficient:

- Banf & Blanz, “Sonification of Images for the Visually Impaired Using a Multi-Level Approach”
- research on quantitative image properties including entropy, edge density and orientation
- research on cross-modal correspondences between visual lightness/elevation and pitch
- research on color–timbre correspondences
- Anders & Miranda / rule-based and constraint-based algorithmic composition literature

Do not claim that arbitrary constants in this prototype were taken from these papers unless they actually were.

---

# 49. Scope Restrictions

For V1, DO NOT add:

- scene graphs
- neural music generation
- generative MIDI language models
- random note generation
- direct object→instrument mappings
- direct object→pitch mappings
- vertical-grid-position→pitch mapping
- more than 3 ensemble voices
- complex counterpoint
- adaptive ML training
- Chordcat-specific button mappings before they are reverse engineered

Keep V1 explainable, deterministic and modular.

---

# 50. Definition of Done

The prototype is complete when this workflow works:

```bash
python main.py analyze \
    --image painting.jpg \
    --title "Example" \
    --artist "Artist" \
    --year 1889 \
    --art-movement "Post-Impressionism"
```

produces:

```text
analysis_raw.json
composition.json
grid_overlay.png
16 three-track MIDI files
overview.mid
```

and then:

```bash
python main.py interact output/composition.json
```

allows:

```text
play 0 0
show 0 0

set energy 0.2
set complexity -0.1

rebuild

play 0 0

save my_interpretation
```

The initial version and saved modified version must both be reproducible.

Before finishing, run the full automated test suite and fix all failing tests.

Do not leave placeholder functions for any core functionality described above.

If an optional external dependency prevents real-time MIDI playback, MIDI-file generation must still work completely.

The final prototype should prioritize correctness, transparency, determinism and modularity over UI polish.