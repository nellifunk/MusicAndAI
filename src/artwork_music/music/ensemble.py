from ..models import ComposedCell, Composition, Interpretation, Phrase
from .accompaniment import compose_accompaniment
from .bass import compose_bass
from .global_mapping import global_mapping
from .lead_composer import compose_lead_candidates
from .local_mapping import local_mapping
from .rhythm import generate_rhythm, rhythm_cost
from .character import character_constraints, character_rhythm
from .relative_features import normalize_cells
from .diversity import select_candidates
from .diagnostics import diagnose


def compose(raw, interpretation=None, tonic="D", instruments=None, character=None) -> Composition:
    interpretation = interpretation or Interpretation()
    effective, music = global_mapping(raw.raw_global_visual, interpretation, raw.artwork.music_era, tonic, instruments, character)
    ordered = sorted(raw.cells, key=lambda c: (c.row, c.column))
    relative = normalize_cells(ordered)
    prepared = []
    candidate_sets = []
    for cell in ordered:
        constraints = local_mapping(cell, music, relative[cell.row, cell.column])
        if character is not None:
            constraints = character_constraints(constraints, character, relative[cell.row, cell.column])
            onsets = character_rhythm(character, constraints.relative_lead_activity)
            score = rhythm_cost(onsets, constraints.target_offbeats)
        else:
            onsets, score = generate_rhythm(constraints.lead_note_onsets, constraints.target_offbeats)
        candidates = compose_lead_candidates(music, cell.visual, constraints, onsets)
        prepared.append((constraints, onsets, score))
        candidate_sets.append(candidates)
    selections, selection_metadata = select_candidates(ordered, relative, candidate_sets, music)
    cells = []
    for cell, (constraints, onsets, rhythm_score), candidates, chosen in zip(ordered, prepared, candidate_sets, selections):
        selected = candidates[chosen]
        phrase = Phrase(
            length_sixteenths=32,
            lead=selected.voice,
            accompaniment=compose_accompaniment(music, constraints.accompaniment_template, constraints.velocities.accompaniment),
            bass=compose_bass(music, constraints.bass_template, constraints.velocities.bass),
            lead_scale_degrees=selected.degrees, rhythm_onsets=onsets, rhythm_cost=rhythm_score,
            lead_costs=selected.costs, total_lead_cost=selected.costs.total, max_scale_step_used=selected.max_scale_step_used,
            relaxations=selected.relaxations, lead_candidates=candidates, selected_candidate_index=chosen,
        )
        cells.append(ComposedCell(row=cell.row, column=cell.column, visual=cell.visual,
                                  musical_constraints=constraints, phrase=phrase,
                                  **relative[cell.row, cell.column].model_dump()))
    return Composition(
        schema_version="1.3" if character else "1.2",
        image_sha256=raw.image_sha256, image_size=raw.image_size, artwork=raw.artwork,
        raw_global_visual=raw.raw_global_visual, interpretation=interpretation,
        effective_global_visual=effective, global_music=music, cells=tuple(cells),
        diagnostics=diagnose(cells, music), diversity_selection=selection_metadata,
    )
