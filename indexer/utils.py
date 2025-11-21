import re
import os
from typing import Optional


def extract_scene_id(filename: str) -> Optional[int]:
    """Extract a numeric scene id from a frame filename.

    Returns integer scene id if found, otherwise None.
    Examples matched: "movie_001_scene_123.jpg", "frame_scene_45.png"
    """
    m = re.search(r"_scene_(\d+)", filename)
    if not m:
        return None
    try:
        return int(m.group(1))
    except (ValueError, TypeError):
        return None


def validate_paths(*paths: str) -> bool:
    """Return True if all supplied filesystem paths exist.

    This helper keeps path checks in one place and is trivial to unit-test.
    """
    return all(os.path.exists(p) for p in paths)
