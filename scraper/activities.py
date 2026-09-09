"""Descubre elementos del resumen de las secciones elegidas; no abre recursos."""
import re
from urllib.parse import parse_qs, urldefrag, urljoin, urlsplit

from playwright.sync_api import Error, Page

from models import Activity, Course, Section
from .browser import check_session, navigate
from .errors import MoodleError, PageLoadError

TYPES = {"resource", "page", "assign", "url", "folder", "forum", "quiz", "book", "h5pactivity", "label"}


def classify_activity(modtype: str, classes: str, url: str | None) -> str:
    """Metadatos Moodle primero; URL del módulo como alternativa."""
    candidates = [modtype.split("_", 1)[0]]
    candidates.extend(c.removeprefix("modtype_") for c in classes.split() if c.startswith("modtype_"))
    if url:
        match = re.fullmatch(r"/mod/([^/]+)/[^/]+", urlsplit(url).path)
        if match:
            candidates.append(match[1])
    return next((value for value in candidates if value in TYPES), "other")


def normalize_activities(rows: list[dict], section: Section, base_url: str) -> list[Activity]:
    activities = []
    seen = set()
    for row in rows:
        url = urljoin(base_url, row["url"]) if row.get("url") else None
        if url and urlsplit(url).scheme not in {"http", "https"}:
            url = None
        modtype = row.get("modtype", "")
        kind = classify_activity(modtype, row.get("classes", ""), url)
        raw_id = row.get("id", "")
        if not raw_id and url and urlsplit(url).path.startswith("/mod/"):
            raw_id = parse_qs(urlsplit(url).query).get("id", [""])[0]
        activity_id = int(raw_id) if str(raw_id).isdigit() else None
        if activity_id is not None:
            if activity_id in seen:
                continue
            seen.add(activity_id)
        title = " ".join(row.get("title", "").split())
        text = " ".join(row.get("text", "").split())
        if not title:
            title = text[:200] if kind == "label" else ""
        if not title:
            title = f"{kind.upper()} sin título ({len(activities) + 1})"
        available = section.is_available and not row.get("restricted", False) and (bool(url) or kind == "label")
        pdf = modtype == "resource_pdf" or "resourcetype_pdf" in row.get("classes", "").split()
        activities.append(Activity(activity_id, title, url, kind, section, len(activities) + 1,
                                   available, "pdf" if kind == "resource" and pdf else None,
                                   row.get("html") if kind == "label" else None))
    return activities


def section_target(course: Course, section: Section) -> tuple[str, str]:
    """Acepta sólo enlaces de sección del curso, nunca enlaces de recursos."""
    if not section.is_available:
        raise MoodleError(f"La sección {section.name} está restringida; no se abrirá.")
    if not section.url:
        raise MoodleError(f"La sección {section.name} no tiene una URL de sección reconocible.")
    url = urlsplit(section.url)
    origin = urlsplit(course.url)
    query = parse_qs(url.query)
    if (url.scheme, url.netloc, url.path) != (origin.scheme, origin.netloc, "/course/view.php") or query.get("id") != [str(course.id)]:
        raise MoodleError("La URL de sección no pertenece al curso seleccionado.")
    number = query.get("section", [""])[0]
    if not number:
        match = re.fullmatch(r"section-([0-9]+)", url.fragment)
        number = match[1] if match else ""
    if not re.fullmatch(r"[0-9]+", number):
        raise MoodleError(f"No se pudo identificar el contenedor de {section.name}.")
    return section.url, f'[role="main"] .course-content .course-section#section-{number}'


def get_activities(page: Page, course: Course, sections: list[Section]) -> list[Activity]:
    """Devuelve modelos ordenados; recorre exclusivamente las secciones recibidas."""
    # Validar todo antes de navegar, incluso si una llamada omite el parser de UI.
    targets = [(s, *section_target(course, s)) for s in sorted(sections, key=lambda s: s.position)]
    result = []
    seen = set()
    for section, url, selector in targets:
        if selector in seen:
            continue
        seen.add(selector)
        # General usa un ancla en la página ya abierta; una navegación sólo
        # de fragmento no tiene respuesta HTTP y no necesita recargar Moodle.
        target_page = urldefrag(url).url
        if not urlsplit(url).fragment or urldefrag(page.url).url != target_page:
            navigate(page, target_page)
        try:
            root = page.locator(selector)
            root.wait_for(state="visible")
            restricted = root.evaluate('''el => [...el.querySelectorAll('.availabilityinfo.isrestricted')]
                .some(info => !info.closest('.activity') && info.closest('.course-section') === el)''')
            if restricted:
                raise MoodleError(f"Moodle ahora muestra {section.name} como restringida. Volvé a leer las secciones.")
            rows = root.evaluate(r'''root => {
                const rows = [];
                const candidates = root.querySelectorAll('.activity, :scope > .content > .summary');
                for (const el of candidates) {
                    if (!el.checkVisibility() || el.matches('.spacer, [aria-hidden="true"]') ||
                        el.closest('.course-section') !== root || el.parentElement.closest('.activity')) continue;
                    const summary = el.matches('.summary');
                    const copy = el.cloneNode(true);
                    copy.querySelectorAll('script,style,button,.completioncheckbox,.availabilityinfo,.sr-only,.photo-overlay,.tileiconcontainer').forEach(x => x.remove());
                    const text = copy.textContent.trim();
                    if (summary && !text) continue;
                    const link = summary ? null : el.querySelector('a.cm-link[href], .activityname a[href]');
                    const name = el.querySelector('.activityname');
                    const nameCopy = name?.cloneNode(true);
                    nameCopy?.querySelectorAll('.sr-only').forEach(x => x.remove());
                    rows.push({
                        id: summary ? '' : el.dataset.cmid || el.id.match(/^module-(\d+)$/)?.[1] || '',
                        title: summary ? '' : el.dataset.title || nameCopy?.textContent || '',
                        text, html: copy.innerHTML, url: link?.getAttribute('href') || '',
                        modtype: summary ? 'label' : el.dataset.modtype || '',
                        classes: el.className,
                        restricted: Boolean(el.querySelector('.availabilityinfo.isrestricted')) || el.getAttribute('aria-disabled') === 'true'
                    });
                }
                return rows;
            }''')
            result.extend(normalize_activities(rows, section, url))
        except Error as exc:
            check_session(page)
            raise PageLoadError(f"No se pudo leer el contenido de {section.name}; la sección no cargó o cambió su formato.") from exc
    return result
