"""Ventana de selección y descarga. Sólo el hilo principal toca widgets."""
import os
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread
from tkinter import ttk, messagebox

from exporter.service import DOWNLOADS, EXPORT_LOG
from .worker import start_job, start_login
from .layout import build_layout
from .theme import apply_theme, PALETTE
from .library import checked_path, checked_contents, export_zip, delete_local


class MoodleApp:
    def __init__(self, root, *, auto_load=True, downloads=DOWNLOADS):
        self.root = root
        self.downloads = Path(downloads)
        self.events = Queue()
        self.busy = False
        self.closing = False
        self.login_active = False
        self.login_ready = False
        self.login_confirm = Event()
        self.login_cancel = Event()
        self.courses = []
        self.sections = []
        self.checks = []
        self.tree_paths = {}
        self.connected = False
        self.details_visible = False
        self.download_count = 0
        self.session = tk.StringVar(value='○ Sin sesión')
        self.status = tk.StringVar(value='Comprobá la sesión para cargar los cursos.')
        self.root.title('Moodle Scraper')
        self.root.geometry('1180x700')
        self.root.minsize(940, 600)
        self.style = apply_theme(root)
        self.build()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh_tree()
        self.poll_id = self.root.after(100, self.poll)
        if auto_load:
            self.load_courses()

    def build(self):
        build_layout(self)

    def selected_sections(self):
        return [section for section, variable, widget in self.checks if section.is_available and variable.get()]

    def update_controls(self):
        available = not self.busy and not self.closing
        self.session.set('● Conectada' if self.connected else '○ Sin sesión')
        self.session_label.configure(foreground=PALETTE['success'] if self.connected else PALETTE['muted'])
        self.login_button.configure(text='Renovar sesión' if self.connected else 'Iniciar sesión')
        self.login_button.configure(state='normal' if available else 'disabled')
        if self.login_active:
            self.login_actions.grid()
        else:
            self.login_actions.grid_remove()
        self.confirm_button.configure(state='normal' if self.login_active and self.login_ready and not self.closing else 'disabled')
        self.cancel_button.configure(state='normal' if self.login_active and not self.closing else 'disabled')
        self.course_combo.configure(state='readonly' if available and self.courses else 'disabled')
        for section, variable, widget in self.checks:
            widget.configure(state='normal' if available and section.is_available else 'disabled')
        state = 'normal' if available and any(s.is_available for s in self.sections) else 'disabled'
        self.all_button.configure(state=state)
        self.none_button.configure(state=state)
        self.download_button.configure(state='normal' if available and self.selected_sections() else 'disabled')
        self.update_library_actions()

    def begin(self, action, course=None, sections=None):
        if self.busy or self.closing:
            return
        self.busy = True
        self.update_controls()
        self.bar.configure(mode='indeterminate')
        self.bar.start(12)
        start_job(self.events, action, course, sections)

    def load_courses(self):
        if self.busy:
            return
        self.courses = []
        self.course_combo.set('')
        self.course_combo.configure(values=())
        self.show_sections([])
        self.connected = False
        self.status.set('Conectando con Moodle…')
        self.begin('courses')

    def clear_selection(self):
        self.courses = []
        self.course_combo.set('')
        self.course_combo.configure(values=())
        self.show_sections([])

    def login(self):
        if self.busy or self.closing:
            return
        self.busy = self.login_active = True
        self.login_ready = False
        self.login_confirm.clear()
        self.login_cancel.clear()
        self.clear_selection()
        self.connected = False
        self.status.set('Abriendo Chromium para iniciar sesión…')
        self.update_controls()
        self.bar.start(12)
        start_login(self.events, self.login_confirm, self.login_cancel)

    def confirm_login(self):
        if self.login_active and self.login_ready:
            self.login_ready = False
            self.status.set('Verificando acceso a tus cursos antes de guardar…')
            self.update_controls()
            self.login_confirm.set()

    def cancel_login(self):
        self.login_ready = False
        self.login_cancel.set()
        self.status.set('Cancelando el inicio de sesión…')
        self.update_controls()

    def course_changed(self, event=None):
        if self.busy:
            return
        index = self.course_combo.current()
        if index < 0:
            return
        self.show_sections([])
        self.status.set('Leyendo las secciones del curso…')
        self.begin('sections', self.courses[index])

    def show_sections(self, sections):
        for child in self.section_frame.winfo_children():
            child.destroy()
        self.sections, self.checks = sections, []
        for section in sections:
            variable = tk.BooleanVar(value=False)
            title = section.name + ('' if section.is_available else ' [RESTRINGIDA]')
            widget = ttk.Checkbutton(self.section_frame, text=title, variable=variable, command=self.selection_status, style='Section.TCheckbutton')
            widget.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-int(e.delta/120), 'units'))
            widget.pack(anchor='w', fill='x', pady=2)
            self.checks.append((section, variable, widget))
        self.canvas.yview_moveto(0)
        self.update_controls()

    def select_all(self, value):
        if self.busy:
            return
        for section, variable, widget in self.checks:
            variable.set(value and section.is_available)
        self.selection_status()

    def download(self):
        index = self.course_combo.current()
        selected = self.selected_sections()
        if self.busy or index < 0 or not selected:
            return
        self.status.set('Exportando las secciones seleccionadas…')
        self.download_count = 0
        self.begin('download', self.courses[index], selected)

    def selection_status(self):
        self.update_controls()
        if not self.busy:
            self.status.set('Lista para descargar' if self.selected_sections() else 'Elegí una o más secciones.')

    def append_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def log_local_action(self, message):
        self.append_log(message)
        try:
            EXPORT_LOG.parent.mkdir(parents=True, exist_ok=True)
            with EXPORT_LOG.open('a', encoding='utf-8') as stream:
                stream.write(message + '\n')
        except OSError as exc:
            self.append_log(f'[ERROR] No se pudo guardar el log técnico: {exc}')

    def handle(self, kind, payload):
        if kind == 'local_log':
            self.log_local_action(payload)
        elif kind in ('login_ready', 'login_retry'):
            self.login_ready = True
            self.status.set('Iniciá sesión en Chromium y luego pulsá “Ya inicié sesión” aquí.')
            if payload:
                self.append_log('[ERROR] ' + payload)
                self.status.set('No se pudo verificar el acceso. Completá el login y volvé a pulsar “Ya inicié sesión”.')
            self.update_controls()
        elif kind == 'login_cancelled':
            self.connected = False
            self.status.set('Inicio cancelado. La sesión guardada no se modificó.')
        elif kind == 'session':
            self.connected = True
            self.update_controls()
        elif kind == 'progress':
            if payload.startswith(('[DOWNLOAD]', '[DOCX]', '[ASSIGN]')):
                self.download_count += 1
            self.status.set(f'Descargando · {self.download_count} archivos guardados…')
            self.append_log(payload)
        elif kind == 'error':
            session_error, message = payload
            if session_error:
                self.connected = False
                self.clear_selection()
            self.status.set('La sesión venció. Iniciá sesión nuevamente.' if session_error else 'Error · No se pudo completar la operación. Ver detalles.')
            self.append_log('[ERROR] ' + message)
        elif kind == 'result':
            action, result = payload
            if action == 'courses':
                self.courses = result
                self.course_combo.configure(values=[course.name for course in result])
                self.status.set('Elegí un curso.' if result else 'No se encontraron cursos.')
            elif action == 'sections':
                self.show_sections(result)
                self.status.set('Marcá las secciones que querés descargar.' if result else 'El curso no muestra secciones.')
            elif action in ('zip', 'delete'):
                self.status.set('ZIP creado · ' + result.name if action == 'zip' else 'Descarga local eliminada')
                self.append_log(f'[{action.upper()}] {result}')
                if action == 'delete':
                    self.log_local_action(f'[DELETE LOCAL] Copia local eliminada: {result}')
                self.refresh_tree()
            else:
                self.status.set(f'Finalizado · {len(result.files)} archivos · {len(result.errors)} errores')
                self.append_log(f'[CARPETA] {result.directory}')
                self.refresh_tree()
        elif kind == 'done':
            self.busy = False
            self.login_active = self.login_ready = False
            self.bar.stop()
            self.bar.configure(value=0)
            self.refresh_tree()
            self.update_controls()
            if self.closing:
                self.root.destroy()

    def poll(self):
        try:
            for _ in range(100):
                kind, payload = self.events.get_nowait()
                self.handle(kind, payload)
                if self.closing and not self.busy:
                    return
        except Empty:
            pass
        self.poll_id = self.root.after(100, self.poll)

    def refresh_tree(self):
        known = {str(path) for path in self.tree_paths.values()}
        expanded = {str(path) for item,path in self.tree_paths.items() if self.tree.exists(item) and self.tree.item(item,'open')}
        selected = self.selected_path()
        self.tree.delete(*self.tree.get_children())
        self.tree_paths.clear()
        if not self.downloads.is_dir():
            self.update_library_actions()
            return
        try:
            def add(parent, folder):
                for path in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold())):
                    if path.is_symlink() or path.is_junction():
                        continue
                    if path.is_file() and path.suffix.lower() == '.log':
                        continue
                    node = self.tree.insert(parent, 'end', text=path.name, open=str(path) in expanded or (not parent and str(path) not in known))
                    self.tree_paths[node] = path
                    if path == selected:
                        self.tree.selection_set(node)
                        self.tree.focus(node)
                    if path.is_dir():
                        add(node, path)
            add('', self.downloads)
        except OSError as exc:
            self.append_log(f'[ERROR] No se pudo actualizar el árbol: {exc}')
        self.update_library_actions()

    def selected_path(self):
        selected = self.tree.selection()
        return self.tree_paths.get(selected[0]) if selected else None

    def update_library_actions(self):
        path = self.selected_path()
        enabled = path is not None and path.exists() and not self.busy and not self.closing
        folder = path is not None and path.is_dir()
        self.open_button.configure(text='Abrir carpeta' if folder else 'Abrir archivo', state='normal' if enabled else 'disabled')
        self.location_button.configure(state='normal' if enabled and path.is_file() else 'disabled')
        self.zip_button.configure(state='normal' if enabled and folder else 'disabled')
        self.update_library_hint()

    def update_library_hint(self):
        collapsed = any(not self.tree.item(item, 'open') and self.tree_paths[item].is_dir()
                        for item in self.tree.get_children())
        self.library_hint.configure(text='Expandí un curso para ver sus secciones y archivos.'
                                    if not self.selected_path() or collapsed else '')

    def open_selected(self):
        self.open_path(self.selected_path())

    def open_location(self):
        path = self.selected_path()
        if path:
            try:
                path = checked_path(self.downloads, path)
                os.startfile(path.parent)
            except (OSError, ValueError) as exc:
                self.append_log(f'[ERROR] {exc}')
                self.status.set('No se pudo abrir la ubicación. Ver detalles.')

    def open_path(self, path):
        if path and not self.busy:
            try:
                os.startfile(checked_path(self.downloads, path))
            except (OSError, ValueError) as exc:
                self.append_log(f'[ERROR] {exc}')
                self.status.set('No se pudo abrir la descarga. Ver detalles.')

    def local_job(self, action, path):
        if self.busy or self.closing:
            return
        self.busy = True
        self.status.set('Creando ZIP…' if action == 'zip' else 'Eliminando descarga local…')
        self.bar.start(12)
        self.update_controls()
        def work():
            try:
                operation = export_zip if action == 'zip' else delete_local
                self.events.put(('result', (action, operation(self.downloads, path))))
            except Exception as exc:
                if action == 'delete':
                    self.events.put(('local_log', f'[ERROR] Eliminación local de {path}: {exc}'))
                self.events.put(('error', (False, str(exc))))
            finally:
                self.events.put(('done', None))
        Thread(target=work, daemon=True).start()

    def zip_selected(self):
        path = self.selected_path()
        if path and path.is_dir():
            self.local_job('zip', path)

    def delete_selected(self):
        path = self.selected_path()
        if not path or self.busy or self.closing:
            return
        try:
            path = checked_path(self.downloads, path)
            title = self.delete_label(path)
            detail = ''
            if path.is_dir():
                count = sum(item.is_file() for item in checked_contents(self.downloads, path))
                detail = f'\n\nContiene {count} {"archivo" if count == 1 else "archivos"} en total (incluye subcarpetas).'
        except FileNotFoundError:
            self.status.set('La descarga local ya no existe. Biblioteca actualizada.')
            self.log_local_action(f'[DELETE LOCAL] La descarga ya no existe: {path}')
            self.refresh_tree()
            return
        except (OSError, ValueError) as exc:
            self.status.set('No se pudo preparar la eliminación local. Ver detalles.')
            self.log_local_action(f'[ERROR] Eliminación local: {exc}')
            return
        if messagebox.askyesno(title, f'¿Eliminar permanentemente esta copia local?\n\n{path}{detail}\n\nSolo se elimina contenido de downloads/. El contenido en Moodle no se modifica ni se elimina.', parent=self.root):
            self.log_local_action(f'[DELETE LOCAL] Eliminación confirmada: {path}')
            self.local_job('delete', path)

    def delete_label(self, path):
        if not path.is_dir():
            return 'Eliminar archivo local'
        if path.parent.resolve() == self.downloads.resolve():
            return 'Eliminar curso descargado'
        return 'Eliminar sección descargada'

    def context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item or self.busy:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        path = self.tree_paths[item]
        self.menu.delete(0,'end')
        self.menu.add_command(label='Abrir', command=self.open_selected)
        self.menu.add_command(label='Abrir ubicación', command=self.open_location)
        if path.is_dir():
            self.menu.add_command(label='Exportar sección a ZIP' if path.parent != self.downloads else 'Exportar carpeta a ZIP',command=self.zip_selected)
        self.menu.add_separator()
        self.menu.add_command(label=self.delete_label(path),command=self.delete_selected)
        try:
            self.menu.tk_popup(event.x_root,event.y_root)
        finally:
            self.menu.grab_release()

    def toggle_details(self):
        self.details_visible = not self.details_visible
        if self.details_visible:
            self.details_frame.grid()
        else:
            self.details_frame.grid_remove()
        self.details_button.configure(text='▾ Ocultar detalles' if self.details_visible else '▸ Ver detalles')

    def open_file(self, event=None):
        item = self.tree.identify_row(event.y) if event else self.tree.focus()
        path = self.tree_paths.get(item)
        if path and path.is_file():
            self.open_path(path)

    def close(self):
        if self.busy:
            self.closing = True
            if self.login_active:
                self.login_cancel.set()
            self.status.set('La ventana se cerrará cuando termine la operación en curso.')
            self.update_controls()
        else:
            self.root.after_cancel(self.poll_id)
            self.root.destroy()


def main():
    root = tk.Tk()
    MoodleApp(root)
    root.mainloop()
