from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SkillStatus = Literal["on", "off"]


@dataclass(frozen=True)
class Skill:
    name: str
    status: SkillStatus
    explicit_alias: str | None
    effective_alias: str
    description: str
    path: Path | None
    managed_dir: Path
