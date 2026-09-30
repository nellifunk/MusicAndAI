from functools import lru_cache

from .time import BAR_STEPS, PHRASE_STEPS


def rhythm_cost(onsets: tuple[int, ...], target: int) -> float:
    count = len(onsets)
    offbeats = sum(t % 4 in (2, 3) for t in onsets)
    sixteenths = sum(t % 2 for t in onsets)
    first_bar = sum(t < BAR_STEPS for t in onsets)
    adjacent = sum(b - a == 1 for a, b in zip(onsets, onsets[1:]))
    return min(1.0, 0.55 * ((offbeats - target) / 8) ** 2
               + 0.15 * (sixteenths / count) ** 2
               + 0.20 * ((2 * first_bar - count) / count) ** 2
               + 0.10 * adjacent / max(1, count - 1))


@lru_cache(maxsize=64)
def generate_rhythm(count: int, target: int) -> tuple[tuple[int, ...], float]:
    if not 4 <= count <= 14 or not 0 <= target <= 8:
        raise ValueError("Rhythm requires 4..14 onsets and 0..8 target offbeats")
    choices = tuple(t for t in range(PHRASE_STEPS) if t not in (0, BAR_STEPS))
    beam = [()]
    width = 5000
    for _ in range(count - 2):
        expanded = []
        for prefix in beam:
            for t in choices:
                if not prefix or t > prefix[-1]:
                    candidate = (*prefix, t)
                    full = tuple(sorted((0, BAR_STEPS, *candidate)))
                    expanded.append((rhythm_cost(full, target), candidate))
        beam = [candidate for _, candidate in sorted(expanded)[:width]]
    onsets = min((tuple(sorted((0, BAR_STEPS, *candidate))) for candidate in beam),
                 key=lambda s: (rhythm_cost(s, target), s))
    return onsets, rhythm_cost(onsets, target)


def lead_durations(onsets: tuple[int, ...]) -> tuple[int, ...]:
    durations = []
    for i, onset in enumerate(onsets):
        next_onset = onsets[i + 1] if i + 1 < len(onsets) else PHRASE_STEPS
        gap = min(next_onset, BAR_STEPS if onset < BAR_STEPS else PHRASE_STEPS) - onset
        durations.append(next(d for d in (8, 4, 2, 1) if d <= gap))
    return tuple(durations)
