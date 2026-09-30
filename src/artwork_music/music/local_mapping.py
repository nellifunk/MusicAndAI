import math

from ..models import LocalConstraints, Velocities, VoiceWeights


def pan_for_column(column: int) -> float:
    if type(column) is not int or not 0 <= column <= 3:
        raise ValueError("Column must be an integer from 0 to 3")
    return -1 + 2 * column / 3


def color_distance(a, b):
    delta = abs(a.h - b.h)
    return 0.50 * min(delta, 360 - delta) / 180 + 0.25 * abs(a.s - b.s) + 0.25 * abs(a.l - b.l)


def local_mapping(cell, music, relative) -> LocalConstraints:
    visual = cell.visual
    activity = 0.65 * visual.movement + 0.35 * visual.edge_density
    lead_activity = 0.65 * relative.relative_movement + 0.35 * relative.relative_edge_density
    onsets = 4 + round(10 * lead_activity)
    theta = math.radians(visual.orientation_deg) if visual.orientation_deg is not None else 0
    contour, verticality = math.sin(2 * theta), abs(math.sin(theta))
    complexity = (music.complexity_budget + relative.relative_entropy) / 2
    roles = ("lead", "accompaniment", "bass")
    weights = dict.fromkeys(roles, 0.0)
    for cluster in visual.color_clusters:
        # Equal distances use the stable role order: lead, accompaniment, bass.
        role = min(roles, key=lambda role: color_distance(cluster, getattr(music.color_anchors, role)))
        weights[role] += cluster.w
    weights = VoiceWeights(**{role: (weight + 0.10) / 1.30 for role, weight in weights.items()})
    return LocalConstraints(
        pan=pan_for_column(cell.column), activity=activity, lead_note_onsets=onsets,
        target_offbeats=round(relative.relative_entropy * min(8, onsets - 2)),
        contour=contour, verticality=verticality, complexity=complexity,
        max_scale_step=1 + math.floor(2 * complexity + verticality), voice_weights=weights,
        relative_lead_activity=lead_activity, melodic_anchor=round(6 * relative.relative_lightness),
        accompaniment_template=round(5 * relative.relative_entropy),
        bass_template=round(4 * relative.relative_activity), contour_entropy=relative.relative_entropy,
        velocities=Velocities(lead=round(55 + 45 * weights.lead),
                              accompaniment=round(45 + 40 * weights.accompaniment),
                              bass=round(50 + 40 * weights.bass)),
    )
