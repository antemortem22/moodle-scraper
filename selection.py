"""Selección de modelos sin depender de consola, navegador ni GUI."""
import re

from models import Section


def parse_section_selection(value: str, sections: list[Section]) -> list[Section]:
    """Devuelve los objetos originales en orden del curso; errores como ValueError."""
    if not sections:
        raise ValueError("No hay secciones disponibles para seleccionar.")
    value = value.strip()
    if value.lower() == "all":
        return [section for section in sections if section.is_available]

    available = {section.position for section in sections}
    selected = set()
    for item in value.split(","):
        match = re.fullmatch(r"\s*([0-9]+)\s*(?:-\s*([0-9]+)\s*)?", item)
        if not match:
            raise ValueError("Entrada inválida. Usá números, rangos separados por coma o all (ejemplo: 1,3-5,7).")
        start = int(match[1])
        end = int(match[2]) if match[2] is not None else start
        if start > end:
            raise ValueError("Rango inválido: el inicio debe ser menor o igual que el final.")
        if start not in available or end not in available or end - start + 1 > len(available):
            raise ValueError("Número fuera de rango. Usá los números de las secciones listadas.")
        numbers = set(range(start, end + 1))
        if not numbers <= available:
            raise ValueError("El rango contiene números que no aparecen en la lista.")
        selected.update(numbers)
    result = [section for section in sections if section.position in selected]
    restricted = [section for section in result if not section.is_available]
    if restricted:
        names = ", ".join(f"[{section.position}] {section.name}" for section in restricted)
        raise ValueError(f"Moodle restringe estas secciones: {names}. Elegí sólo secciones disponibles.")
    return result
