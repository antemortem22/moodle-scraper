from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    id: int
    name: str
    url: str
    is_favorite: bool = False
