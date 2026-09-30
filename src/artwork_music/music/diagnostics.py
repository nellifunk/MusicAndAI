from collections import defaultdict
from itertools import combinations

from ..models import DiversityDiagnostics, DuplicateLead
from .diversity import musical_distance, musical_signature, pair_penalty, visual_distance, visual_signature
from .relative_features import normalize_cells


def diagnose(cells, music):
    relative = normalize_cells(cells)
    groups = defaultdict(list)
    for cell in cells:
        groups[tuple(n.pitch for n in cell.phrase.lead.notes)].append((cell.row, cell.column))
    duplicates = tuple(DuplicateLead(pitches=pitches, cells=tuple(sorted(coords)))
                       for pitches, coords in sorted(groups.items()) if len(coords) > 1)
    signatures = [visual_signature(c, relative[(c.row, c.column)]) for c in cells]
    musical = [musical_signature(c.phrase.lead, music) for c in cells]
    visual_distances, musical_distances, penalties = [], [], []
    for g, h in combinations(range(len(cells)), 2):
        dv, dm = visual_distance(signatures[g], signatures[h]), musical_distance(musical[g], musical[h])
        visual_distances.append(dv)
        musical_distances.append(dm)
        penalties.append(pair_penalty(dv, dm))
    def voice_pattern(cell, role):
        return tuple((n.pitch, n.onset, n.duration) for n in getattr(cell.phrase, role).notes)
    local_sum = sum(c.phrase.total_lead_cost for c in cells)
    pair_sum = sum(penalties)
    return DiversityDiagnostics(
        unique_lead_pitch_sequences=len(groups),
        unique_onset_patterns=len({c.phrase.rhythm_onsets for c in cells}),
        unique_accompaniment_patterns=len({voice_pattern(c, "accompaniment") for c in cells}),
        unique_bass_patterns=len({voice_pattern(c, "bass") for c in cells}),
        # Count redundant cells after keeping one representative of each pitch sequence.
        exact_duplicate_lead_sequences=len(cells) - len(groups),
        largest_duplicate_group=max((len(g.cells) for g in duplicates), default=0),
        duplicate_lead_groups=duplicates,
        mean_pairwise_visual_distance=sum(visual_distances) / len(visual_distances),
        mean_pairwise_musical_distance=sum(musical_distances) / len(musical_distances),
        mean_pairwise_penalty=pair_sum / len(penalties), local_cost_sum=local_sum,
        pairwise_penalty_sum=pair_sum, selection_objective=local_sum + 0.25 * pair_sum,
    )


def format_diagnostics(d):
    lines = [
        f"Unique lead pitch sequences: {d.unique_lead_pitch_sequences}/16",
        f"Unique onset patterns: {d.unique_onset_patterns}",
        f"Unique accompaniment patterns: {d.unique_accompaniment_patterns}",
        f"Unique bass patterns: {d.unique_bass_patterns}",
        f"Exact duplicate lead sequences (redundant cells): {d.exact_duplicate_lead_sequences}",
        f"Largest duplicate group: {d.largest_duplicate_group}",
        f"Mean pairwise visual distance: {d.mean_pairwise_visual_distance:.6f}",
        f"Mean pairwise musical distance: {d.mean_pairwise_musical_distance:.6f}",
        f"Mean pairwise diversity penalty: {d.mean_pairwise_penalty:.6f}",
        f"Selection objective: {d.selection_objective:.6f}",
    ]
    lines.extend(f"Duplicate pitches {group.pitches}: cells {group.cells}" for group in d.duplicate_lead_groups)
    if not d.duplicate_lead_groups:
        lines.append("No exact duplicate lead pitch sequences.")
    return "\n".join(lines)
