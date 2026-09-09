"""Pruebas locales: no usan session.json ni se conectan a Moodle."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright

from main import select_course
from models import Course
from scraper.browser import BASE_URL, COURSES_URL, navigate, open_moodle
from scraper.courses import get_courses, normalize_courses
from scraper.errors import PageLoadError, SessionError
from scraper.sections import get_sections


class ModelTests(unittest.TestCase):
    def test_course_identity_and_external_links(self):
        result = normalize_courses([
            {"url": "/course/view.php?id=12&section=2", "name": "  Inglés\n Técnico "},
            {"url": "/course/view.php?id=12", "name": "Duplicado"},
            {"url": "https://otro.test/course/view.php?id=3", "name": "Ajeno"},
            {"url": "/course/view.php?id=abc", "name": "Inválido"},
        ])
        self.assertEqual(result, [Course(12, "Inglés Técnico", f"{BASE_URL}/course/view.php?id=12")])

    def test_missing_and_invalid_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.json"
            for contents in (None, "no es JSON", "[]"):
                if contents is not None:
                    path.write_text(contents, encoding="utf-8")
                with self.assertRaises(SessionError):
                    with open_moodle(path):
                        self.fail("No debe abrir el navegador")

    def test_console_selection_retries(self):
        course = Course(1, "Curso", "url")
        with patch("builtins.input", side_effect=["abc", "-1", "5", "1"]), patch("builtins.print"):
            self.assertEqual(select_course([course]), course)


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.set_default_timeout(2000)

    def tearDown(self):
        self.context.close()

    def serve(self, html, status=200):
        self.page.route("**/*", lambda route: route.fulfill(status=status, content_type="text/html", body=html))

    def test_delayed_courses_and_pagination(self):
        self.serve('''<div role="main"><div data-region="myoverview">
            <a data-filter="grouping" data-value="all" aria-current="true">Todos</a>
            <div id="pages"></div>
            <nav data-region="paging-bar" data-active-page-number="1" data-last-page-number="2">
                <li data-control="next" aria-disabled="false"><a href="#" data-region="page-link" onclick="render(2);return false">Next</a></li>
            </nav></div></div>
            <script>
            function render(n) {
                document.querySelector('nav').dataset.activePageNumber = n;
                setTimeout(() => {
                    document.querySelector('#pages').innerHTML = `<div data-region="paged-content-page" data-page="${n}">
                    <a class="coursename" href="/course/view.php?id=${n}"><span class="sr-only">Nombre del curso</span><span class="multiline" title="Curso ${n}">Curso ${n}</span></a>
                    <a class="coursename" href="/course/view.php?id=${n}&section=3">Duplicado</a></div>`;
                    document.querySelector('li').setAttribute('aria-disabled', n === 2 ? 'true' : 'false');
                }, 150);
            }
            render(1);
            </script>''')
        navigate(self.page, COURSES_URL)
        self.assertEqual([c.name for c in get_courses(self.page)], ["Curso 1", "Curso 2"])

    def test_empty_courses(self):
        self.serve('''<div role="main"><div data-region="myoverview">
            <a data-filter="grouping" data-value="all" aria-current="true">Todos</a>
            <div data-region="paged-content-page" data-page="1"><div data-region="empty-message">Sin cursos</div></div>
            <nav data-region="paging-bar" data-active-page-number="1" data-last-page-number="1">
            <li data-control="next" aria-disabled="true"></li></nav></div></div>''')
        navigate(self.page, COURSES_URL)
        self.assertEqual(get_courses(self.page), [])

    def test_sections_order_blanks_and_hidden_placeholders(self):
        self.serve('''<div role="main"><div class="course-content">
            <div class="course-section" data-section="0" id="section-0"><div class="content"><div class="summary"><h3>Texto que no es título de sección</h3></div></div></div>
            <ul><li class="tile" data-section="2" id="tile-2"><a class="tile-link" href="?id=12&section=2"><h3>Unidad 4</h3></a></li>
            <li class="course-section" data-section="2" style="display:none"></li>
            <li class="tile" data-section="1"><a class="tile-link" href="?id=12&section=1"><h3>Entrega PFO</h3></a></li></ul>
            </div></div>''')
        course = Course(12, "Ejemplo", f"{BASE_URL}/course/view.php?id=12")
        result = get_sections(self.page, course)
        self.assertEqual([s.name for s in result], ["General", "Unidad 4", "Entrega PFO"])
        self.assertEqual([s.position for s in result], [1, 2, 3])
        self.assertTrue(result[1].url.endswith("?id=12&section=2"))

    def test_course_without_sections(self):
        self.serve('<div role="main"><div class="course-content"></div></div>')
        self.assertEqual(get_sections(self.page, Course(1, "Vacío", f"{BASE_URL}/course/view.php?id=1")), [])

    def test_real_tiles_restriction_signals(self):
        self.serve('''<meta charset="utf-8"><div role="main"><div class="course-content">
            <div class="course-section" data-section="0"><div class="content">
                <li class="activity"><div class="availabilityinfo isrestricted">Actividad restringida</div></li>
            </div></div>
            <ul>
                <li class="tile tile-clickable" data-section="1"><a class="tile-link" href="?id=12&section=1"><h3>Disponible</h3></a></li>
                <li class="tile tile-restricted" data-section="2"><a class="tile-link"><h3>Futura</h3></a></li>
                <li class="tile tile-clickable" data-section="3"><a class="tile-link" href="?id=12&section=3"><div class="availabilityinfo isrestricted"><span title="Disponible desde una fecha futura">Restringido</span></div><h3>Con restricción explícita</h3></a></li>
                <li class="tile" data-section="4"><a class="tile-link"><h3>Sin enlace habilitado</h3></a></li>
            </ul></div></div>''')
        course = Course(12, "Ejemplo", f"{BASE_URL}/course/view.php?id=12")
        sections = get_sections(self.page, course)
        self.assertEqual([s.is_available for s in sections], [True, True, False, False, False])
        self.assertEqual([s.name for s in sections], ["General", "Disponible", "Futura", "Con restricción explícita", "Sin enlace habilitado"])

    def test_expired_session(self):
        self.serve('<div role="main"><input type="password"></div>')
        with self.assertRaises(SessionError):
            navigate(self.page, COURSES_URL)

    def test_http_error(self):
        self.serve('<div role="main">No disponible</div>', status=503)
        with self.assertRaises(PageLoadError):
            navigate(self.page, COURSES_URL)


if __name__ == "__main__":
    unittest.main()
