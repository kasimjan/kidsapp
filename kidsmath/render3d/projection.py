"""World -> screen projection matching ManimGL 1.7's vertex shader.

The shader computes  v = view @ [p, 1];  w = 1 - v.z * scale / focal_distance;
screen = v.xy / w  (in default-frame units).  Fixed-in-frame mobjects skip the
view matrix, so a HUD badge placed at this screen point appears glued to the
3D object, however the camera moves.
"""
from __future__ import annotations

import numpy as np


def project_point(view: np.ndarray, frame_scale: float, focal_distance: float,
                  point) -> tuple[float, float]:
    v = np.asarray(view, dtype=float) @ np.array([point[0], point[1], point[2], 1.0])
    w = 1.0 - v[2] * frame_scale / focal_distance
    return float(v[0] / w), float(v[1] / w)
