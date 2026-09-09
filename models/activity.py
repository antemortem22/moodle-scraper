from dataclasses import dataclass

from .section import Section


@dataclass(frozen=True)
class Activity:
    id: int | None
    title: str
    url: str | None
    type: str
    section: Section
    position: int  # Orden dentro de la sección, desde 1.
    is_available: bool = True
    file_format: str | None = None
