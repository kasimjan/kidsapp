"""Words for objects. 3D lessons draw solid toys, so they say 'ball', not 'circle'."""

SOLID_NOUN = {"circle": "ball", "square": "cube", "triangle": "cone", "star": "coin", "heart": "ball"}


def noun(shape: str, solid: bool) -> str:
    return SOLID_NOUN[shape] if solid else shape
