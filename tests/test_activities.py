import unittest
from unittest.mock import Mock

from playwright.sync_api import sync_playwright

from models import Course, Section
from scraper.activities import classify_activity, get_activities
from scraper.browser import BASE_URL
from scraper.errors import MoodleError


class ActivityModelTests(unittest.TestCase):
    def test_types_and_metadata(self):
        for kind in ('resource', 'page', 'assign', 'url', 'folder', 'forum', 'quiz', 'book', 'h5pactivity'):
            with self.subTest(kind=kind):
                self.assertEqual(classify_activity('', '', f'{BASE_URL}/mod/{kind}/view.php?id=1'), kind)
        self.assertEqual(classify_activity('resource_pdf', '', None), 'resource')
        self.assertEqual(classify_activity('', 'activity modtype_label', None), 'label')
        self.assertEqual(classify_activity('assign', '', f'{BASE_URL}/mod/page/view.php?id=1'), 'assign')
        self.assertEqual(classify_activity('', '', None), 'other')

    def test_restricted_section_rejected_before_any_navigation(self):
        page = Mock()
        course = Course(12, 'Curso', f'{BASE_URL}/course/view.php?id=12')
        sections = [Section('OK', 1, course.url + '&section=1'), Section('Futura', 2, course.url + '&section=2', False)]
        with self.assertRaises(MoodleError):
            get_activities(page, course, sections)
        page.goto.assert_not_called()

    def test_resource_url_not_used_as_section(self):
        page = Mock()
        course = Course(12, 'Curso', f'{BASE_URL}/course/view.php?id=12')
        with self.assertRaises(MoodleError):
            get_activities(page, course, [Section('Recurso', 1, f'{BASE_URL}/mod/resource/view.php?id=1')])
        page.goto.assert_not_called()


class ActivityBrowserTests(unittest.TestCase):
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
        self.page.set_default_timeout(1000)
        self.course = Course(12, 'Curso', f'{BASE_URL}/course/view.php?id=12')

    def tearDown(self):
        self.context.close()

    def test_selected_sections_only_order_labels_and_restrictions(self):
        requests = []
        html = '''<meta charset="utf-8"><div role="main"><div class="course-content">
          <div class="course-section" id="section-0"><div class="content"><div class="summary"><p>Orientaciones generales</p></div></div></div>
          <div class="course-section" id="section-1"><ul>
            <li class="activity spacer" aria-hidden="true">Decoración</li>
            <li class="activity modtype_resource resourcetype_pdf" data-cmid="10" data-title="Arquitectura" data-modtype="resource_pdf"><a class="cm-link" href="/mod/resource/view.php?id=10">Arquitectura</a></li>
            <li class="activity modtype_label" data-cmid="11"><p>Leé estas instrucciones</p></li>
            <li class="activity modtype_assign" data-cmid="12" data-title="Entrega futura"><div class="availabilityinfo isrestricted">Disponible desde mañana</div></li>
            <li class="activity" data-cmid="13" data-title="Otra cosa"><a class="cm-link" href="/mod/custom/view.php?id=13">Otra cosa</a></li>
          </ul></div>
          <div class="course-section" id="section-2"><li class="activity" data-title="No seleccionada" data-modtype="quiz"></li></div>
          </div></div>'''
        def serve(route):
            requests.append(route.request.url)
            route.fulfill(content_type='text/html; charset=utf-8', body=html)
        self.page.route('**/*', serve)
        general = Section('General', 1, self.course.url + '#section-0')
        week = Section('Semana 1', 2, self.course.url + '&section=1')
        result = get_activities(self.page, self.course, [week, general, week])
        self.assertEqual([a.type for a in result], ['label', 'resource', 'label', 'assign', 'other'])
        self.assertEqual([a.position for a in result], [1, 1, 2, 3, 4])
        self.assertEqual(result[0].title, 'Orientaciones generales')
        self.assertEqual(result[2].title, 'Leé estas instrucciones')
        self.assertIs(result[1].section, week)
        self.assertEqual(result[1].file_format, 'pdf')
        self.assertFalse(result[3].is_available)
        self.assertIsNone(result[3].url)
        self.assertEqual(len(requests), 2)
        self.assertTrue(all('/course/view.php' in url for url in requests))

    def test_general_anchor_reuses_loaded_course(self):
        html = '<div role="main"><div class="course-content"><div class="course-section" id="section-0"><div class="content"><div class="summary">Introducción</div></div></div></div></div>'
        self.page.route('**/*', lambda route: route.fulfill(content_type='text/html; charset=utf-8', body=html))
        self.page.goto(self.course.url)
        requests = []
        self.page.on('request', lambda request: requests.append(request.url))
        result = get_activities(self.page, self.course, [Section('General', 1, self.course.url + '#section-0')])
        self.assertEqual(result[0].type, 'label')
        self.assertEqual(requests, [])

    def test_empty_section_and_new_restriction(self):
        section = Section('Semana', 1, self.course.url + '&section=1')
        self.page.route('**/*', lambda route: route.fulfill(content_type='text/html', body='''
            <div role="main"><div class="course-content"><div class="course-section" id="section-1" style="min-height:1px"></div></div></div>'''))
        self.assertEqual(get_activities(self.page, self.course, [section]), [])
        self.page.unroute('**/*')
        self.page.route('**/*', lambda route: route.fulfill(content_type='text/html', body='''
            <div role="main"><div class="course-content"><div class="course-section" id="section-1"><div class="availabilityinfo isrestricted">Restringido</div></div></div></div>'''))
        with self.assertRaisesRegex(MoodleError, 'ahora muestra'):
            get_activities(self.page, self.course, [section])


if __name__ == '__main__':
    unittest.main()
