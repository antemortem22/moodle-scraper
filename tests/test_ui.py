import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from queue import Queue
from threading import Event
from unittest.mock import MagicMock, patch

from models import Section
from scraper.errors import SessionError
from ui.app import MoodleApp
from ui.worker import run_job, run_login, save_session


class WorkerTests(unittest.TestCase):
    def test_session_failure_always_finishes(self):
        events = Queue()
        with patch('ui.worker.open_moodle', side_effect=SessionError('Sesión expirada')):
            run_job(events, 'courses')
        self.assertEqual(events.get(), ('error', (True, 'Sesión expirada')))
        self.assertEqual(events.get(), ('done', None))

    def test_download_passes_models_and_reports_progress(self):
        events = Queue()
        context = MagicMock()
        page = context.__enter__.return_value
        sections = [Section('General', 1)]
        def export(page, course, selected, progress):
            self.assertIs(selected, sections)
            progress('[DOCX] Archivo.docx')
            return 'report'
        with patch('ui.worker.open_moodle', return_value=context), patch('ui.worker.export_sections', side_effect=export):
            run_job(events, 'download', 'course', sections)
        self.assertEqual([events.get()[0] for _ in range(4)], ['progress', 'session', 'result', 'done'])
        context.__exit__.assert_called_once()

    def test_login_validates_before_saving(self):
        events, confirm, cancel = Queue(), Event(), Event()
        confirm.set()
        manager = MagicMock()
        browser = manager.__enter__.return_value.chromium.launch.return_value
        page = browser.new_context.return_value.new_page.return_value
        page.is_closed.return_value = False
        with patch('ui.worker.sync_playwright', return_value=manager), patch('ui.worker.navigate'), patch('ui.worker.get_courses', return_value=['course']), patch('ui.worker.save_session') as save:
            run_login(events, confirm, cancel)
        save.assert_called_once_with(browser.new_context.return_value)
        self.assertEqual([events.get()[0] for _ in range(4)], ['login_ready','session','result','done'])
        browser.close.assert_called_once()

    def test_invalid_login_does_not_overwrite_session(self):
        events, confirm, cancel = Queue(), Event(), Event()
        confirm.set()
        manager = MagicMock()
        browser = manager.__enter__.return_value.chromium.launch.return_value
        page = browser.new_context.return_value.new_page.return_value
        page.is_closed.return_value = False
        page.wait_for_timeout.side_effect = lambda ms: cancel.set()
        with patch('ui.worker.sync_playwright', return_value=manager), patch('ui.worker.navigate', side_effect=SessionError('Falta login')), patch('ui.worker.save_session') as save:
            run_login(events, confirm, cancel)
        save.assert_not_called()
        self.assertEqual([events.get()[0] for _ in range(4)], ['login_ready','login_retry','login_cancelled','done'])

    def test_failed_storage_write_preserves_previous_session(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'session.json'
            path.write_text('previous')
            context = MagicMock()
            context.storage_state.side_effect = OSError('No se pudo guardar')
            with self.assertRaises(OSError):
                save_session(context, path)
            self.assertEqual(path.read_text(), 'previous')
            self.assertEqual(list(Path(directory).iterdir()), [path])


class WindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        log_patch = patch('ui.app.EXPORT_LOG', Path(self.temp.name)/'logs'/'export.log')
        log_patch.start()
        self.addCleanup(log_patch.stop)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = MoodleApp(self.root, auto_load=False, downloads=self.temp.name)

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def test_restricted_sections_and_busy_controls(self):
        sections = [Section('General', 1), Section('Futura', 2, is_available=False)]
        self.app.show_sections(sections)
        self.app.select_all(True)
        self.assertEqual(self.app.selected_sections(), [sections[0]])
        self.assertIn('disabled', self.app.checks[1][2].state())
        self.app.busy = True
        self.app.update_controls()
        self.assertIn('disabled', self.app.download_button.state())
        self.app.handle('done', None)
        self.assertNotIn('disabled', self.app.download_button.state())

    def test_tree_courses_sections_files(self):
        folder = Path(self.temp.name) / 'Curso' / 'Semana'
        folder.mkdir(parents=True)
        file = folder / '01 - Texto.docx'
        file.write_bytes(b'test')
        (folder/'debug.LOG').write_text('technical')
        (folder.parent/'export.log').write_text('technical')
        self.app.refresh_tree()
        courses = self.app.tree.get_children()
        self.assertEqual(len(courses), 1)
        sections = self.app.tree.get_children(courses[0])
        files = self.app.tree.get_children(sections[0])
        self.assertEqual(self.app.tree_paths[files[0]], file)
        self.assertEqual(len(files), 1)
        self.assertFalse(any(path.suffix.lower() == '.log' for path in self.app.tree_paths.values()))

    def test_error_state_and_status(self):
        self.app.show_sections([Section('General',1)])
        self.app.select_all(True)
        self.app.handle('error', (True, 'Ejecutá login.py'))
        self.assertEqual(self.app.session.get(), '○ Sin sesión')
        self.assertIn('Iniciá sesión', self.app.status.get())
        self.assertEqual(self.app.selected_sections(), [])
        self.assertIn('disabled', self.app.download_button.state())

    def test_login_buttons_and_retry(self):
        with patch('ui.app.start_login') as start:
            self.app.login()
            start.assert_called_once()
        self.app.handle('login_ready', None)
        self.assertNotIn('disabled', self.app.confirm_button.state())
        self.app.confirm_login()
        self.assertTrue(self.app.login_confirm.is_set())
        self.assertIn('disabled', self.app.confirm_button.state())
        self.app.handle('login_retry', 'No inició sesión')
        self.assertNotIn('disabled', self.app.confirm_button.state())
        self.app.cancel_login()
        self.assertTrue(self.app.login_cancel.is_set())
        self.app.handle('done', None)

    def test_library_actions_and_delete_confirmation(self):
        folder = Path(self.temp.name)/'Curso'/'Semana'
        folder.mkdir(parents=True)
        file = folder/'Texto.docx'
        file.write_bytes(b'doc')
        self.app.refresh_tree()
        node = next(node for node,path in self.app.tree_paths.items() if path == folder)
        self.app.tree.selection_set(node)
        self.app.update_library_actions()
        self.assertEqual(self.app.open_button.cget('text'), 'Abrir carpeta')
        self.assertNotIn('disabled',self.app.zip_button.state())
        with patch('ui.app.messagebox.askyesno',return_value=False), patch.object(self.app,'local_job') as job:
            self.app.delete_selected()
            job.assert_not_called()
        with patch('ui.app.messagebox.askyesno',return_value=True), patch.object(self.app,'local_job') as job:
            self.app.delete_selected()
            job.assert_called_once_with('delete',folder.resolve())
        node = next(node for node,path in self.app.tree_paths.items() if path == file)
        self.app.tree.selection_set(node)
        self.app.update_library_actions()
        self.assertEqual(self.app.open_button.cget('text'),'Abrir archivo')
        self.assertIn('disabled',self.app.zip_button.state())
        with patch('ui.app.os.startfile') as open_file:
            self.app.open_selected()
            open_file.assert_called_once_with(file.resolve())

    def test_details_and_connected_state(self):
        self.assertFalse(self.app.details_visible)
        self.app.toggle_details()
        self.assertTrue(self.app.details_visible)
        self.app.toggle_details()
        self.assertFalse(self.app.details_visible)
        self.app.handle('session','verificada')
        self.assertEqual(self.app.session.get(),'● Conectada')
        self.assertEqual(self.app.login_button.cget('text'),'Renovar sesión')

    def test_local_delete_labels_confirmation_and_missing_file(self):
        course = Path(self.temp.name)/'Curso'
        section = course/'Semana'
        section.mkdir(parents=True)
        file = section/'Texto.docx'
        file.write_bytes(b'doc')
        self.assertEqual(self.app.delete_label(course), 'Eliminar curso descargado')
        self.assertEqual(self.app.delete_label(section), 'Eliminar sección descargada')
        self.assertEqual(self.app.delete_label(file), 'Eliminar archivo local')
        self.app.refresh_tree()
        nodes = {path: node for node, path in self.app.tree_paths.items()}
        self.app.tree.selection_set(nodes[section])
        with patch('ui.app.messagebox.askyesno', return_value=False) as confirm, patch.object(self.app, 'local_job') as job:
            self.app.delete_selected()
            self.assertIn('Contiene 1 archivo', confirm.call_args.args[1])
            self.assertIn('Moodle no se modifica', confirm.call_args.args[1])
            job.assert_not_called()
        self.app.tree.selection_set(nodes[file])
        file.unlink()
        with patch('ui.app.messagebox.askyesno') as confirm:
            self.app.delete_selected()
            confirm.assert_not_called()
        self.assertNotIn(file, self.app.tree_paths.values())
        self.assertIn('ya no existe', self.app.status.get())
        self.app.handle('result', ('delete', file))
        log = (Path(self.temp.name)/'logs'/'export.log').read_text(encoding='utf-8')
        self.assertIn('Copia local eliminada', log)

    def test_library_button_states_and_collapsed_hint(self):
        folder = Path(self.temp.name)/'Curso'/'Semana'
        folder.mkdir(parents=True)
        file = folder/'Texto.docx'
        file.write_bytes(b'doc')
        self.app.refresh_tree()
        for button in (self.app.open_button, self.app.location_button, self.app.zip_button):
            self.assertIn('disabled', button.state())
        self.assertIn('Expandí un curso', self.app.library_hint.cget('text'))
        for node, path in self.app.tree_paths.items():
            self.app.tree.selection_set(node)
            self.app.update_library_actions()
            self.assertNotIn('disabled', self.app.open_button.state())
            self.assertEqual('disabled' in self.app.location_button.state(), path.is_dir())
            self.assertEqual('disabled' in self.app.zip_button.state(), path.is_file())
        course = self.app.tree.get_children()[0]
        self.app.tree.item(course, open=False)
        self.app.refresh_tree()
        self.assertFalse(self.app.tree.item(self.app.tree.get_children()[0], 'open'))
        self.assertIn('Expandí un curso', self.app.library_hint.cget('text'))

    def test_selection_readiness_and_final_status(self):
        self.app.show_sections([Section('General', 1), Section('Futura', 2, is_available=False)])
        self.app.checks[0][2].invoke()
        self.assertEqual(self.app.status.get(), 'Lista para descargar')
        self.app.select_all(False)
        self.assertIn('Elegí', self.app.status.get())
        report = MagicMock(files=['a', 'b'], errors=['falló'], directory=Path(self.temp.name))
        self.app.handle('result', ('download', report))
        self.app.handle('done', None)
        self.assertEqual(self.app.status.get(), 'Finalizado · 2 archivos · 1 errores')


if __name__ == '__main__':
    unittest.main()
