"""
Shared schema helpers:
- SlugStr   — validated slug field type
- StatusStr — publish status literal
"""
from typing import Annotated
import re
from pydantic import AfterValidator


def _validate_slug(v: str) -> str:
    if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
        raise ValueError("slug must be lowercase alphanumeric with hyphens only")
    return v


SlugStr = Annotated[str, AfterValidator(_validate_slug)]
