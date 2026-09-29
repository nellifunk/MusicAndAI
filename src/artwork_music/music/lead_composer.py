import logging

from ..models import LeadCandidate, Note, Voice
from .lead_costs import cost_components, evaluate_lead, weighted_cost
from .rhythm import lead_durations
from .scales import pitches_in_register

logger = logging.getLogger(__name__)


def beam_candidates(pitches, onsets, harmony, entropy, contour, max_step, beam_width=100, anchor=0, limit=20):
    if len(pitches) < 3 or beam_width < 1:
        return ()
    beam = [()]
    n = len(onsets)
    for depth in range(n):
        candidates = []
        for sequence in beam:
            allowed = range(len(pitches)) if not sequence else range(
                max(0, sequence[-1] - max_step), min(len(pitches), sequence[-1] + max_step + 1))
            for degree in allowed:
                if len(sequence) >= 2 and sequence[-2] == sequence[-1] == degree:
                    continue
                extended = (*sequence, degree)
                if len(set(extended)) + (n - depth - 1) < 3:
                    continue
                score = weighted_cost(cost_components(extended, pitches, onsets, harmony, entropy, contour, anchor))
                candidates.append((score, extended))
        if not candidates:
            return ()
        candidates.sort()  # Score, then lexicographic degree tuple.
        beam = [sequence for _, sequence in candidates[:beam_width]]
    return tuple(beam[:limit])


def beam_search(pitches, onsets, harmony, entropy, contour, max_step, beam_width=100, anchor=0):
    candidates = beam_candidates(pitches, onsets, harmony, entropy, contour, max_step, beam_width, anchor, 1)
    return candidates[0] if candidates else None


def compose_lead_candidates(music, visual, constraints, onsets):
    pitches = pitches_in_register(music.lead_register, music.scale_pitch_classes)
    if constraints.melodic_anchor is None or constraints.contour_entropy is None:
        raise ValueError("Compute relative musical constraints before composing a lead")
    relaxations = []
    for max_step in range(constraints.max_scale_step, 5):
        sequences = beam_candidates(pitches, onsets, music.harmony, constraints.contour_entropy,
                                    constraints.contour, max_step, anchor=constraints.melodic_anchor)
        if sequences:
            candidates = []
            for degrees in sequences:
                costs = evaluate_lead(degrees, pitches, onsets, music.harmony, constraints.contour_entropy,
                                      constraints.contour, constraints.melodic_anchor)
                voice = Voice(notes=tuple(Note(pitch=pitches[d], onset=t, duration=duration,
                                               velocity=constraints.velocities.lead)
                                          for d, t, duration in zip(degrees, onsets, lead_durations(onsets))))
                candidates.append(LeadCandidate(voice=voice, degrees=degrees, costs=costs,
                                                max_scale_step_used=max_step, relaxations=tuple(relaxations)))
            return tuple(candidates)
        if max_step < 4:
            message = f"Lead search relaxed maximum scale step from {max_step} to {max_step + 1}"
            logger.warning(message)
            relaxations.append(message)
    raise ValueError("No valid lead phrase found after deterministic beam search and relaxation to 4 scale steps")


def compose_lead(music, visual, constraints, onsets):
    """Convenience API for the lowest local cost; ensemble uses all 20 candidates."""
    candidate = compose_lead_candidates(music, visual, constraints, onsets)[0]
    return candidate.voice, candidate.degrees, candidate.costs, candidate.max_scale_step_used, candidate.relaxations
