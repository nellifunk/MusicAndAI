"""Exact full costs and compatible prefix costs with full-phrase denominators."""
from ..models import LeadCosts

from .time import BAR_STEPS

WEIGHTS = (0.19, 0.20, 0.13, 0.07, 0.16, 0.08, 0.17)
SMOOTH = (0.25, 0.0, 0.20, 0.60, 1.0)


def cost_components(degrees, pitches, onsets, harmony, entropy, contour, anchor=0):
    n = len(onsets)
    weights = tuple(2 if t % 4 == 0 else 1 for t in onsets)
    harmony_cost = sum(weights[k] * (pitches[d] % 12 not in harmony[onsets[k] // BAR_STEPS].pitch_classes)
                       for k, d in enumerate(degrees)) / sum(weights)
    amplitude = 1 + 2 * entropy
    center = (len(pitches) - 1) / 2
    contour_cost = min(1.0, sum(
        ((d - (center + amplitude * contour * (2 * k / (n - 1) - 1))) / (amplitude + 1)) ** 2
        for k, d in enumerate(degrees)
    ) / n)
    deltas = tuple(b - a for a, b in zip(degrees, degrees[1:]))
    smooth_cost = sum(SMOOTH[min(abs(delta), 4)] for delta in deltas) / (n - 1)
    leap_cost = min(1.0, sum(
        (int(a * b >= 0) + 0.5 * max(0, abs(b) - 2) ** 2)
        for a, b in zip(deltas, deltas[1:]) if abs(a) >= 3
    ) / max(1, n - 2))
    cadence_cost = 0.0
    if len(degrees) == n:
        pitch_class = pitches[degrees[-1]] % 12
        chord = harmony[1]
        ending = 0 if pitch_class == chord.root else 0.25 if pitch_class in chord.pitch_classes else 1
        approach = min(1.0, max(0, abs(deltas[-1]) - 2) ** 2 / 4)
        cadence_cost = min(1.0, 0.75 * ending + 0.25 * approach)
    repetition = sum(delta == 0 for delta in deltas) / (n - 1)
    anchor_cost = min(1.0, sum(((degree - anchor) / 6) ** 2 for degree in degrees) / n)
    return harmony_cost, contour_cost, smooth_cost, leap_cost, cadence_cost, repetition, anchor_cost


def weighted_cost(components):
    return sum(weight * value for weight, value in zip(WEIGHTS, components))


def evaluate_lead(degrees, pitches, onsets, harmony, entropy, contour, anchor=0) -> LeadCosts:
    if len(degrees) != len(onsets):
        raise ValueError("Full lead evaluation requires one pitch for every onset")
    values = cost_components(degrees, pitches, onsets, harmony, entropy, contour, anchor)
    return LeadCosts(**dict(zip(("harmony", "contour", "smoothness", "leap", "cadence", "repetition", "anchor"), values)),
                     total=weighted_cost(values))
