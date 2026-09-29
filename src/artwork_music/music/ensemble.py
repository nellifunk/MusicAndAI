from ..models import ComposedCell, Composition, Interpretation, Phrase
from .accompaniment import compose_accompaniment
from .bass import compose_bass
from .global_mapping import global_mapping
from .lead_composer import compose_lead_candidates
from .local_mapping import local_mapping
from .rhythm import generate_rhythm
from .relative_features import normalize_cells
from .diversity import select_candidates
from .diagnostics import diagnose


def compose(raw, interpretation=None, tonic="D", instruments=None) -> Composition:
    interpretation = interpretation or Interpretation()
    effective, music = global_mapping(raw.raw_global_visual, interpretation, raw.artwork.music_era, tonic, instruments)
    ordered = sorted(raw.cells, key=lambda c: (c.row, c.column))
    relative = normalize_cells(ordered)
    prepared = []
    candidate_sets = []
    for cell in ordered:
        constraints = local_mapping(cell, music, relative[cell.row, cell.column])
        onsets, rhythm_cost = generate_rhythm(constraints.lead_note_onsets, constraints.target_offbeats)
        candidates = compose_lead_candidates(music, cell.visual, constraints, onsets)
        prepared.append((constraints, onsets, rhythm_cost))
        candidate_sets.append(candidates)
    selections, selection_metadata = select_candidates(ordered, relative, candidate_sets, music)
    cells = []
    for cell, (constraints, onsets, rhythm_cost), candidates, chosen in zip(ordered, prepared, candidate_sets, selections):
        selected = candidates[chosen]
        phrase = Phrase(
            length_sixteenths=32,
            lead=selected.voice,
            accompaniment=compose_accompaniment(music, constraints.accompaniment_template, constraints.velocities.accompaniment),
            bass=compose_bass(music, constraints.bass_template, constraints.velocities.bass),
            lead_scale_degrees=selected.degrees, rhythm_onsets=onsets, rhythm_cost=rhythm_cost,
            lead_costs=selected.costs, total_lead_cost=selected.costs.total, max_scale_step_used=selected.max_scale_step_used,
            relaxations=selected.relaxations, lead_candidates=candidates, selected_candidate_index=chosen,
        )
        cells.append(ComposedCell(row=cell.row, column=cell.column, visual=cell.visual,
                                  musical_constraints=constraints, phrase=phrase,
                                  **relative[cell.row, cell.column].model_dump()))
    return Composition(
        schema_version="1.2",
        image_sha256=raw.image_sha256, image_size=raw.image_size, artwork=raw.artwork,
        raw_global_visual=raw.raw_global_visual, interpretation=interpretation,
        effective_global_visual=effective, global_music=music, cells=tuple(cells),
        diagnostics=diagnose(cells, music), diversity_selection=selection_metadata,
    )
