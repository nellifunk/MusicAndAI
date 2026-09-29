"""Deterministic row-major coordinate descent with explicit visual/music distances."""
import math
from dataclasses import dataclass

import numpy as np

from ..models import DiversitySelection
from .scales import pitches_in_register
from .time import PHRASE_STEPS

PAIR_WEIGHT = 0.25


@dataclass(frozen=True)
class MusicalSignature:
    contour: tuple[float, ...]
    onsets: tuple[int, ...]


def visual_signature(cell, relative):
    theta = math.radians(cell.visual.orientation_deg) if cell.visual.orientation_deg is not None else None
    return (relative.relative_entropy, relative.relative_edge_density,
            relative.relative_movement, relative.relative_lightness,
            math.sin(2 * theta) if theta is not None else 0.0,
            math.cos(2 * theta) if theta is not None else 0.0)


def visual_distance(a, b):
    # Preserve the requested formula: opposite orientations can make d_V > 1.
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) / math.sqrt(6)


def musical_signature(voice, music):
    allowed = pitches_in_register(music.lead_register, music.scale_pitch_classes)
    indices = {pitch: i for i, pitch in enumerate(allowed)}
    # Use a SHARED scale-degree reference, retaining local anchor differences.
    normalized = [indices[note.pitch] / max(1, len(allowed) - 1) for note in voice.notes]
    contour = tuple(float(x) for x in np.interp(np.linspace(0, 1, 8),
                                              np.linspace(0, 1, len(normalized)), normalized))
    starts = {note.onset for note in voice.notes}
    return MusicalSignature(contour=contour, onsets=tuple(int(t in starts) for t in range(PHRASE_STEPS)))


def musical_distance(a, b):
    pitch = min(1.0, sum(abs(x - y) for x, y in zip(a.contour, b.contour)) / 8)
    rhythm = sum(x != y for x, y in zip(a.onsets, b.onsets)) / len(a.onsets)
    return 0.6 * pitch + 0.4 * rhythm


def pair_penalty(visual, musical):
    return max(0.0, visual - musical) ** 2


def select_candidates(cells, relative, candidate_sets, music):
    if list(cells) != sorted(cells, key=lambda c: (c.row, c.column)):
        raise ValueError("Candidate selection requires row-major cell order")
    signatures = [visual_signature(cell, relative[(cell.row, cell.column)]) for cell in cells]
    musical = [[musical_signature(c.voice, music) for c in candidates] for candidates in candidate_sets]
    n = len(cells)
    penalties = {}
    for g in range(n):
        for h in range(g + 1, n):
            distance = visual_distance(signatures[g], signatures[h])
            penalties[g, h] = tuple(tuple(pair_penalty(distance, musical_distance(a, b)) for b in musical[h])
                                    for a in musical[g])

    def objective(selection):
        return (sum(candidate_sets[g][selection[g]].costs.total for g in range(n))
                + PAIR_WEIGHT * sum(matrix[selection[g]][selection[h]] for (g, h), matrix in penalties.items()))

    def lexical_key(selection):
        return tuple(candidate_sets[g][selection[g]].degrees for g in range(n))

    chosen = [min(range(len(candidates)), key=lambda i: (candidates[i].costs.total, candidates[i].degrees))
              for candidates in candidate_sets]
    history = [objective(chosen)]
    converged = False
    passes = 0
    for _ in range(5):
        changed = False
        for g, candidates in enumerate(candidate_sets):
            # Full objective, canonical summation order, including the current assignment.
            # This avoids subtraction drift and guarantees non-increasing objective.
            trials = [chosen[:g] + [i] + chosen[g + 1:] for i in range(len(candidates))]
            best = min(trials, key=lambda trial: (objective(trial), lexical_key(trial)))
            if best[g] != chosen[g]:
                changed = True
                chosen = best
        passes += 1
        history.append(objective(chosen))
        if not changed:
            converged = True
            break
    return tuple(chosen), DiversitySelection(passes_completed=passes, converged=converged,
                                             objective_history=tuple(history))
