"""Lee títulos de sección en el resumen del curso, sin abrir actividades."""
from urllib.parse import urljoin

from playwright.sync_api import Error, Page

from models import Course, Section
from .browser import check_session, navigate
from .errors import PageLoadError


def normalize_sections(rows: list[dict[str, str]], course_url: str) -> list[Section]:
    result = []
    seen = set()
    for row in rows:
        key = row["key"]
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        position = len(result) + 1
        name = " ".join(row["name"].split()) or f"Sección sin título ({position})"
        url = urljoin(course_url, row["url"]) if row["url"] else None
        result.append(Section(name, position, url))
    return result


def get_sections(page: Page, course: Course) -> list[Section]:
    navigate(page, course.url)
    try:
        content = page.locator('[role="main"] .course-content')
        content.wait_for(state="attached")
        # Tiles incluye placeholders .course-section ocultos: se omiten.
        # Se toman encabezados, nunca títulos ni enlaces de actividades.
        rows = content.locator('.course-section:visible, li.tile:visible').evaluate_all("""elements => elements.map(el => {
            const tile = el.matches('li.tile');
            const heading = tile
                ? el.querySelector('a.tile-link h3')
                : el.querySelector(':scope > h2, :scope > h3, :scope > .content > h2, :scope > .content > h3');
            const link = tile ? el.querySelector('a.tile-link') : heading?.querySelector('a[href]');
            return {
                key: el.dataset.section || el.id,
                name: heading?.textContent || '',
                url: link?.getAttribute('href') || (el.id ? '#' + el.id : '')
            };
        })""")
        return normalize_sections(rows, course.url)
    except Error as exc:
        check_session(page)
        raise PageLoadError("No se pudo leer la estructura del curso. La página no terminó de cargar o usa un formato no reconocido.") from exc
