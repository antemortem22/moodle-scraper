"""Trabajo de red y Playwright fuera del hilo de Tkinter."""
from queue import Queue
from threading import Thread
from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright

from exporter.service import export_sections
from scraper.browser import open_moodle, COURSES_URL, SESSION_FILE, navigate, check_session
from scraper.courses import get_courses
from scraper.errors import SessionError
from scraper.sections import get_sections


def verify_session(page):
    """Confirma acceso actual al área privada, no sólo ausencia del formulario de login."""
    navigate(page, COURSES_URL)
    check_session(page)
    # Verificado en el HTML real de esta instalación de Moodle.
    if not page.locator('a[href*="/login/logout.php"]').count():
        raise SessionError('No se pudo confirmar una sesión autenticada. Iniciá sesión nuevamente.')


def run_job(events: Queue, action: str, course=None, sections=None):
    try:
        # Crear, usar y cerrar Playwright siempre en este mismo hilo.
        with open_moodle(headless=True) as page:
            if action == 'courses':
                result = get_courses(page)
            elif action == 'sections':
                result = get_sections(page, course)
            elif action == 'download':
                result = export_sections(page, course, sections,
                                         progress=lambda text: events.put(('progress', text)))
            else:
                raise ValueError('Operación desconocida.')
            verify_session(page)
        events.put(('session', 'Sesión verificada'))
        events.put(('result', (action, result)))
    except Exception as exc:
        events.put(('error', (isinstance(exc, SessionError), str(exc))))
    finally:
        events.put(('done', None))


def start_job(events: Queue, action: str, course=None, sections=None):
    thread = Thread(target=run_job, args=(events, action, course, sections), daemon=True)
    thread.start()
    return thread


def save_session(context, destination=SESSION_FILE):
    """Reemplaza la sesión sólo después de escribir íntegramente el nuevo estado."""
    destination = Path(destination)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.tmp', delete=False) as file:
        temporary = Path(file.name)
    try:
        context.storage_state(path=str(temporary), indexed_db=True)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def run_login(events, confirm, cancel):
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False)
            try:
                context = browser.new_context(accept_downloads=False)
                page = context.new_page()
                page.goto(COURSES_URL, wait_until='domcontentloaded', timeout=60000)
                events.put(('login_ready', None))
                while not cancel.is_set():
                    if page.is_closed() or not browser.is_connected():
                        events.put(('login_cancelled', None))
                        return
                    if confirm.is_set():
                        confirm.clear()
                        try:
                            navigate(page, COURSES_URL)
                            courses = get_courses(page)
                            verify_session(page)
                        except Exception as exc:
                            events.put(('login_retry', str(exc)))
                            continue
                        if cancel.is_set():
                            break
                        save_session(context)
                        events.put(('session', 'Sesión verificada y guardada'))
                        events.put(('result', ('courses', courses)))
                        return
                    page.wait_for_timeout(100)
                events.put(('login_cancelled', None))
            finally:
                browser.close()
    except Exception as exc:
        events.put(('error', (False, f'No se pudo completar el inicio de sesión: {exc}')))
    finally:
        events.put(('done', None))


def start_login(events, confirm, cancel):
    thread = Thread(target=run_login, args=(events, confirm, cancel), daemon=True)
    thread.start()
    return thread
