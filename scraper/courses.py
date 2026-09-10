"""Cursos de la vista general; selectores comprobados en el Moodle real."""
from urllib.parse import parse_qs, urljoin, urlsplit

from playwright.sync_api import Error, Page

from models import Course
from .browser import BASE_URL, COURSES_URL, check_session, navigate
from .errors import PageLoadError

OVERVIEW = '[data-region="myoverview"]'
PAGING = f'{OVERVIEW} [data-region="paging-bar"][data-last-page-number]'


def wait_for_courses_page(page: Page) -> None:
    """El paginador aparece antes que los cursos: esperar el contenido real."""
    page.wait_for_function("""() => {
        const root = document.querySelector('[data-region="myoverview"]');
        const bar = root?.querySelector('[data-region="paging-bar"]');
        if (!bar) return false;
        const panel = [...root.querySelectorAll('[data-region="paged-content-page"]')]
            .find(el => el.dataset.page === bar.dataset.activePageNumber && el.getClientRects().length);
        return panel && (panel.querySelector('a.coursename') || panel.querySelector('[data-region="empty-message"]'));
    }""")


def normalize_courses(rows: list[dict]) -> list[Course]:
    """Normaliza URL, espacios y duplicados sin depender del navegador."""
    courses: dict[int, Course] = {}
    for row in rows:
        url = urlsplit(urljoin(COURSES_URL, row["url"]))
        if url.netloc != urlsplit(BASE_URL).netloc or url.path != "/course/view.php":
            continue
        value = parse_qs(url.query).get("id", [""])[0]
        if not value.isdecimal() or int(value) <= 0:
            continue
        course_id = int(value)
        name = " ".join(row["name"].split()) or f"Curso {course_id} (sin título)"
        courses.setdefault(course_id, Course(course_id, name, f"{BASE_URL}/course/view.php?id={course_id}", row.get('is_favorite') is True))
    return list(courses.values())


def get_courses(page: Page) -> list[Course]:
    """Lee Todos (excepto los eliminados de la vista), incluyendo su paginación."""
    if page.url != COURSES_URL:
        navigate(page, COURSES_URL)
    try:
        overview = page.locator(OVERVIEW)
        overview.wait_for(state="visible")
        page.locator(PAGING).wait_for(state="attached")
        wait_for_courses_page(page)
        all_filter = overview.locator('[data-filter="grouping"][data-value="all"]')
        if all_filter.get_attribute("aria-current") != "true":
            old_paging = page.locator(PAGING).element_handle()
            overview.locator("#groupingdropdown").click()
            all_filter.click()
            # Moodle sustituye el paginador al recargar el filtro.
            page.wait_for_function("old => !old.isConnected", arg=old_paging)
            page.locator(PAGING).wait_for(state="attached")
            wait_for_courses_page(page)

        rows = []
        visited_pages = set()
        while True:
            check_session(page)
            paging = page.locator(PAGING)
            number = paging.get_attribute("data-active-page-number")
            if number in visited_pages:
                raise PageLoadError("La paginación no avanzó; no se puede garantizar un listado completo.")
            visited_pages.add(number)
            rows.extend(overview.locator('a.coursename:visible').evaluate_all("""links => links.map(a => {
                const title = a.querySelector('.multiline[title]');
                const copy = a.cloneNode(true);
                copy.querySelectorAll('.sr-only, [data-region="favourite-icon"]').forEach(x => x.remove());
                // Inspected in this Moodle: non-favorites keep the star in the
                // DOM with aria-hidden="true" and class "hidden".
                const star = a.querySelector('[data-region="favourite-icon"] [data-region="is-favourite"]');
                const favorite = !!star && star.getAttribute('aria-hidden') === 'false'
                    && !star.classList.contains('hidden');
                return {url: a.href, name: title?.getAttribute('title') || copy.textContent || '', is_favorite: favorite};
            })"""))
            next_item = paging.locator('[data-control="next"]')
            if next_item.get_attribute("aria-disabled") == "true":
                break
            next_item.locator('a[data-region="page-link"]').click()
            page.wait_for_function("""previous => {
                const bar = document.querySelector('[data-region="myoverview"] [data-region="paging-bar"]');
                return bar && bar.dataset.activePageNumber !== previous;
            }""", arg=number)
            wait_for_courses_page(page)
        return normalize_courses(rows)
    except Error as exc:
        check_session(page)
        raise PageLoadError("No se pudo leer la lista completa de cursos. Moodle no terminó de cargar o cambió su estructura.") from exc
