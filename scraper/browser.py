"""Ciclo de vida del navegador y navegación autenticada."""
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import urlsplit

from playwright.sync_api import Error, Page, TimeoutError, sync_playwright

from .errors import PageLoadError, SessionError

BASE_URL = "https://aulasvirtuales.bue.edu.ar"
COURSES_URL = f"{BASE_URL}/my/courses.php"
SESSION_FILE = Path(__file__).resolve().parents[1] / "session.json"


def check_session(page: Page) -> None:
    location = urlsplit(page.url)
    if (
        location.netloc != urlsplit(BASE_URL).netloc
        or "/login/" in location.path
        or page.locator('input[type="password"]:visible').count()
    ):
        raise SessionError("La sesión expiró o Moodle pide iniciar sesión. Ejecutá login.py.")


def navigate(page: Page, url: str) -> None:
    """Abre una página de Moodle y distingue errores de carga y autenticación."""
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
        check_session(page)
        if response is None or response.status >= 400:
            status = response.status if response else "sin respuesta"
            raise PageLoadError(f"Moodle no pudo cargar la página (HTTP {status}).")
        if urlsplit(page.url).path != urlsplit(url).path:
            raise PageLoadError("Moodle redirigió a otra página. Comprobá el acceso con test_session.py.")
        page.locator('[role="main"]').wait_for(state="attached")
    except TimeoutError as exc:
        check_session(page)
        raise PageLoadError("La página tardó demasiado en cargar. Revisá la conexión e intentá otra vez.") from exc
    except Error as exc:
        raise PageLoadError("No se pudo abrir la página de Moodle. Revisá la conexión y el navegador.") from exc


@contextmanager
def open_moodle(
    session_file: Path = SESSION_FILE, *, headless: bool = False
) -> Iterator[Page]:
    """Abre Mis cursos con la sesión existente y cierra Chromium al salir del with."""
    session_file = Path(session_file)
    if not session_file.is_file():
        raise SessionError("No existe session.json. Ejecutá login.py antes de continuar.")
    try:
        state = json.loads(session_file.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or not isinstance(state.get("cookies"), list) or not isinstance(state.get("origins"), list):
            raise ValueError("Estado de sesión inválido")
    except (OSError, ValueError) as exc:
        raise SessionError("No se pudo leer session.json. Ejecutá login.py para regenerarlo.") from exc

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=headless)
        except Error as exc:
            raise PageLoadError("No se pudo iniciar Chromium. Ejecutá: .\\.venv\\Scripts\\python.exe -m playwright install chromium") from exc
        try:
            try:
                context = browser.new_context(storage_state=state, accept_downloads=False)
            except Error as exc:
                raise SessionError("Playwright no pudo cargar session.json. Regeneralo con login.py.") from exc
            page = context.new_page()
            page.set_default_timeout(30000)
            navigate(page, COURSES_URL)
            yield page
        finally:
            browser.close()
