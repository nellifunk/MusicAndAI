"""Within-artwork average ranks, independent of cell order and interpretation."""
import math

from ..models import RelativeFeatures, require_grid


def percentile_ranks(values):
    values = tuple(values)
    if len(values) != 16 or not all(math.isfinite(v) for v in values):
        raise ValueError("Relative normalization requires 16 finite feature values")
    if max(values) - min(values) < 1e-6:
        return (0.5,) * 16
    ranks = [0.0] * 16
    order = sorted(range(16), key=lambda i: values[i])
    start = 0
    while start < 16:
        end = start + 1
        while end < 16 and values[order[end]] == values[order[start]]:
            end += 1
        # Average of one-based ranks (start+1)..end, then (rank-1)/15.
        quantile = ((start + 1 + end) / 2 - 1) / 15
        for index in order[start:end]:
            ranks[index] = quantile
        start = end
    return tuple(ranks)


def normalize_cells(cells) -> dict[tuple[int, int], RelativeFeatures]:
    require_grid(cells)
    fields = ("entropy", "edge_density", "movement", "lightness")
    relative = {f"relative_{field}": percentile_ranks([getattr(c.visual, field) for c in cells])
                for field in fields}
    # q_D ranks the raw weighted activity; it is NOT a weighted sum of ranks.
    relative["relative_activity"] = percentile_ranks([
        0.65 * c.visual.movement + 0.35 * c.visual.edge_density for c in cells
    ])
    return {(c.row, c.column): RelativeFeatures(**{name: values[i] for name, values in relative.items()})
            for i, c in enumerate(cells)}
