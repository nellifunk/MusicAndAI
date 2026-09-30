"""Validated, immutable boundary objects. New music uses sixteenth-note units."""
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Unit = Annotated[float, Field(ge=0, le=1)]
SignedUnit = Annotated[float, Field(ge=-1, le=1)]
Offset = Annotated[float, Field(ge=-0.5, le=0.5)]
MidiPitch = Annotated[int, Field(ge=0, le=127, strict=True)]
GridIndex = Annotated[int, Field(ge=0, le=3, strict=True)]
Register = tuple[MidiPitch, MidiPitch]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Era(str, Enum):
    MEDIEVAL = "Medieval"
    RENAISSANCE = "Renaissance"
    BAROQUE = "Baroque"
    CLASSICAL = "Classical"
    ROMANTIC = "Romantic"
    IMPRESSIONIST = "Impressionist / Early Modern"
    MODERN = "Modern / Contemporary"


class Artwork(Model):
    title: Annotated[str, Field(min_length=1)]
    artist: Annotated[str, Field(min_length=1)]
    year: Annotated[int, Field(ge=1, le=9999, strict=True)] | None
    art_movement: Annotated[str, Field(min_length=1)]
    music_era: Era


class ColorCluster(Model):
    h: Annotated[float, Field(ge=0, lt=360)]
    s: Unit
    l: Unit
    w: Unit


class VisualFeatures(Model):
    entropy: Unit
    lightness: Unit
    edge_density: Unit
    orientation_deg: Annotated[float, Field(ge=0, lt=180)] | None
    color_clusters: tuple[ColorCluster, ColorCluster, ColorCluster]

    @model_validator(mode="after")
    def valid_colors(self):
        if abs(sum(c.w for c in self.color_clusters) - 1) > 1e-8:
            raise ValueError("Color cluster weights must sum to 1")
        if any(a.w < b.w for a, b in zip(self.color_clusters, self.color_clusters[1:])):
            raise ValueError("Color clusters must be sorted by descending weight")
        return self


class ValenceProbabilities(Model):
    negative: Unit
    neutral: Unit
    positive: Unit

    @model_validator(mode="after")
    def sum_to_one(self):
        if abs(self.negative + self.neutral + self.positive - 1) > 1e-6:
            raise ValueError("Valence probabilities must sum to 1")
        return self


class DetectedObject(Model):
    label: Annotated[str, Field(min_length=1)]
    confidence: Unit


class GlobalSemantics(Model):
    valence: ValenceProbabilities
    movement: Unit


class LocalSemantics(Model):
    row: GridIndex
    column: GridIndex
    objects: Annotated[tuple[DetectedObject, ...], Field(max_length=3)]
    movement: Unit


def require_grid(cells):
    if len(cells) != 16 or {(c.row, c.column) for c in cells} != {
        (r, c) for r in range(4) for c in range(4)
    }:
        raise ValueError("Exactly one cell at each (row, column) in the 4×4 grid is required")


class SemanticAnalysis(Model):
    global_features: GlobalSemantics
    cells: Annotated[tuple[LocalSemantics, ...], Field(min_length=16, max_length=16)]

    @model_validator(mode="after")
    def valid_grid(self):
        require_grid(self.cells)
        return self


class GlobalVisual(VisualFeatures):
    valence_probs: ValenceProbabilities
    valence: SignedUnit
    movement: Unit

    @model_validator(mode="after")
    def consistent_valence(self):
        if abs(self.valence - (self.valence_probs.positive - self.valence_probs.negative)) > 1e-8:
            raise ValueError("Valence must equal positive minus negative probability")
        return self


class LocalVisual(VisualFeatures):
    movement: Unit
    objects: Annotated[tuple[DetectedObject, ...], Field(max_length=3)]


class RawCell(Model):
    row: GridIndex
    column: GridIndex
    visual: LocalVisual


class RawAnalysis(Model):
    schema_version: Literal["1.0"] = "1.0"
    image_sha256: str
    image_size: tuple[int, int]
    artwork: Artwork
    raw_global_visual: GlobalVisual
    cells: tuple[RawCell, ...]

    @model_validator(mode="after")
    def valid_grid(self):
        require_grid(self.cells)
        return self


class Interpretation(Model):
    delta_valence: Offset = 0.0
    delta_movement: Offset = 0.0
    delta_complexity: Offset = 0.0
    delta_lightness: Offset = 0.0
    target_valence: SignedUnit | None = None


class EffectiveGlobal(Model):
    valence: SignedUnit
    movement: Unit
    entropy: Unit
    lightness: Unit


InstrumentSet = Annotated[tuple[Annotated[str, Field(min_length=1)], ...], Field(min_length=1, max_length=4)]


class Instruments(Model):
    lead: str | InstrumentSet
    accompaniment: str | InstrumentSet
    bass: str | InstrumentSet

    @model_validator(mode="after")
    def no_duplicate_layers(self):
        for role in ("lead", "accompaniment", "bass"):
            value = getattr(self, role)
            if isinstance(value, tuple) and len(set(value)) != len(value):
                raise ValueError(f"Duplicate instruments in {role} layer")
        return self


class Chord(Model):
    symbol: str
    root: int
    core: tuple[int, int, int]
    pitch_classes: tuple[int, ...]


class ColorAnchors(Model):
    lead: ColorCluster
    accompaniment: ColorCluster
    bass: ColorCluster


MotifDegree = Annotated[int, Field(ge=0, le=6)]


class MusicalCharacter(Model):
    """Authored musical interpretation; motif degrees are relative to a local anchor."""
    name: str
    tonic: str
    motif: tuple[MotifDegree, MotifDegree, MotifDegree, MotifDegree]
    motif_onsets: tuple[int, int, int, int]
    harmony_degrees: tuple[Annotated[int, Field(ge=0, le=6)], Annotated[int, Field(ge=0, le=6)]]
    accompaniment_templates: tuple[int, int, int]
    bass_templates: tuple[int, int, int]
    articulation: Annotated[float, Field(ge=0.4, le=1)]
    tempo_offset: Annotated[int, Field(ge=-15, le=15)] = 0

    @model_validator(mode="after")
    def valid_character(self):
        if (self.motif_onsets[0] != 0 or tuple(sorted(set(self.motif_onsets))) != self.motif_onsets
                or self.motif_onsets[-1] > 14):
            raise ValueError("A four-note motif must start at 0 and fit in the first bar")
        if (len(set(self.motif)) < 3 or max(self.motif) - min(self.motif) > 4
                or max(abs(b - a) for a, b in zip(self.motif, self.motif[1:])) > 4):
            raise ValueError("A motif needs three pitches and steps no greater than four")
        if any(not 0 <= t <= 5 for t in self.accompaniment_templates):
            raise ValueError("Invalid accompaniment template")
        if any(not 0 <= t <= 4 for t in self.bass_templates):
            raise ValueError("Invalid bass template")
        return self


class GlobalMusic(Model):
    tonic: str
    mode: Literal["ionian", "dorian", "aeolian"]
    tempo_bpm: Annotated[int, Field(ge=65, le=120)]
    scale_pitch_classes: tuple[int, ...]
    lead_register: Register
    accompaniment_register: Register
    bass_register: Register
    harmony: tuple[Chord, Chord]
    harmonic_richness: Literal[0, 1, 2]
    complexity_budget: Unit
    instruments: Instruments
    color_anchors: ColorAnchors
    character: MusicalCharacter | None = None


class VoiceWeights(Model):
    lead: Unit
    accompaniment: Unit
    bass: Unit


class Velocities(Model):
    lead: Annotated[int, Field(ge=1, le=127)]
    accompaniment: Annotated[int, Field(ge=1, le=127)]
    bass: Annotated[int, Field(ge=1, le=127)]


class LocalConstraints(Model):
    pan: SignedUnit
    activity: Unit
    lead_note_onsets: Annotated[int, Field(ge=4, le=14)]
    target_offbeats: Annotated[int, Field(ge=0, le=8)]
    contour: SignedUnit
    verticality: Unit
    complexity: Unit
    max_scale_step: Annotated[int, Field(ge=1, le=4)]
    voice_weights: VoiceWeights
    velocities: Velocities
    relative_lead_activity: Unit | None = None
    melodic_anchor: Annotated[int, Field(ge=0, le=6)] | None = None
    accompaniment_template: Annotated[int, Field(ge=0, le=5)] | None = None
    bass_template: Annotated[int, Field(ge=0, le=4)] | None = None
    contour_entropy: Unit | None = None


class Note(Model):
    pitch: MidiPitch
    onset: Annotated[int, Field(ge=0, le=31)]
    duration: Annotated[int, Field(ge=1, le=32)]
    velocity: Annotated[int, Field(ge=1, le=127)]

    @model_validator(mode="after")
    def within_phrase(self):
        if self.onset + self.duration > 32:
            raise ValueError("Note extends beyond the two-bar phrase")
        return self


class Voice(Model):
    notes: tuple[Note, ...]


class LeadCosts(Model):
    harmony: Unit
    contour: Unit
    smoothness: Unit
    leap: Unit
    cadence: Unit
    repetition: Unit
    total: Unit
    anchor: Unit = 0.0  # Default only for reading pre-1.1 compositions.


class LeadCandidate(Model):
    voice: Voice
    degrees: tuple[int, ...]
    costs: LeadCosts
    max_scale_step_used: Annotated[int, Field(ge=1, le=4)]
    relaxations: tuple[str, ...] = ()


class Phrase(Model):
    bars: Literal[2] = 2
    time_signature: tuple[Literal[4], Literal[4]] = (4, 4)
    length_eighths: Literal[16] = 16
    length_sixteenths: Annotated[int, Field(ge=16, le=32)] = 16
    lead: Voice
    accompaniment: Voice
    bass: Voice
    lead_scale_degrees: tuple[int, ...]
    rhythm_onsets: tuple[int, ...]
    rhythm_cost: Unit
    lead_costs: LeadCosts
    total_lead_cost: Unit
    max_scale_step_used: Annotated[int, Field(ge=1, le=4)]
    relaxations: tuple[str, ...] = ()
    lead_candidates: tuple[LeadCandidate, ...] = ()
    selected_candidate_index: Annotated[int, Field(ge=0, le=19)] = 0


class RelativeFeatures(Model):
    relative_entropy: Unit
    relative_edge_density: Unit
    relative_movement: Unit
    relative_lightness: Unit
    relative_activity: Unit


class ComposedCell(RawCell):
    musical_constraints: LocalConstraints
    phrase: Phrase
    # Legacy JSON can still be played without changing its original notes.
    relative_entropy: Unit | None = None
    relative_edge_density: Unit | None = None
    relative_movement: Unit | None = None
    relative_lightness: Unit | None = None
    relative_activity: Unit | None = None


class DuplicateLead(Model):
    pitches: tuple[MidiPitch, ...]
    cells: tuple[tuple[GridIndex, GridIndex], ...]


class DiversityDiagnostics(Model):
    unique_lead_pitch_sequences: int
    unique_onset_patterns: int
    unique_accompaniment_patterns: int
    unique_bass_patterns: int
    exact_duplicate_lead_sequences: int
    largest_duplicate_group: int
    duplicate_lead_groups: tuple[DuplicateLead, ...]
    mean_pairwise_visual_distance: Annotated[float, Field(ge=0)]
    mean_pairwise_musical_distance: Unit
    mean_pairwise_penalty: Annotated[float, Field(ge=0)]
    local_cost_sum: Annotated[float, Field(ge=0)]
    pairwise_penalty_sum: Annotated[float, Field(ge=0)]
    selection_objective: Annotated[float, Field(ge=0)]


class DiversitySelection(Model):
    candidate_limit: Literal[20] = 20
    beam_width: Literal[100] = 100
    pair_weight: Literal[0.25] = 0.25
    passes_completed: Annotated[int, Field(ge=0, le=5)]
    converged: bool
    objective_history: tuple[float, ...]


class Composition(Model):
    schema_version: Literal["1.0", "1.1", "1.2", "1.3"] = "1.0"
    image_sha256: str
    image_size: tuple[int, int]
    artwork: Artwork
    raw_global_visual: GlobalVisual
    interpretation: Interpretation
    effective_global_visual: EffectiveGlobal
    global_music: GlobalMusic
    cells: tuple[ComposedCell, ...]
    diagnostics: DiversityDiagnostics | None = None
    diversity_selection: DiversitySelection | None = None

    @model_validator(mode="after")
    def valid_grid(self):
        require_grid(self.cells)
        if self.schema_version == "1.3" and self.global_music.character is None:
            raise ValueError("Version 1.3 requires an artwork musical character")
        if self.schema_version in ("1.1", "1.2", "1.3"):
            if self.diagnostics is None or self.diversity_selection is None:
                raise ValueError("Version 1.1 requires diversity diagnostics and selection metadata")
            for cell in self.cells:
                RelativeFeatures.model_validate({k: getattr(cell, k) for k in RelativeFeatures.model_fields})
                constraints = cell.musical_constraints
                if any(getattr(constraints, field) is None for field in (
                    "relative_lead_activity", "melodic_anchor", "accompaniment_template", "bass_template", "contour_entropy"
                )):
                    raise ValueError("Version 1.1 requires all relative musical constraints")
                phrase = cell.phrase
                if self.schema_version in ("1.2", "1.3") and phrase.length_sixteenths != 32:
                    raise ValueError("Version 1.2 requires sixteenth-note phrase timing")
                if not 1 <= len(phrase.lead_candidates) <= 20 or phrase.selected_candidate_index >= len(phrase.lead_candidates):
                    raise ValueError("Version 1.1 requires a valid selected lead candidate")
                selected = phrase.lead_candidates[phrase.selected_candidate_index]
                if (phrase.lead != selected.voice or phrase.lead_scale_degrees != selected.degrees
                        or phrase.lead_costs != selected.costs or phrase.total_lead_cost != selected.costs.total):
                    raise ValueError("Selected lead candidate does not match the rendered phrase")
        return self

    def raw_analysis(self) -> RawAnalysis:
        return RawAnalysis(
            image_sha256=self.image_sha256, image_size=self.image_size,
            artwork=self.artwork, raw_global_visual=self.raw_global_visual,
            cells=tuple(RawCell(row=c.row, column=c.column, visual=c.visual) for c in self.cells),
        )
