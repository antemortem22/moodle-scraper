"""Orquesta una exportación completa y aislada por sección y actividad."""
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from urllib.parse import urljoin

from models import Course, Section
from scraper.activities import get_activities
from .docx_exporter import DocxExporter
from .downloader import Downloader
from .paths import unique_path

DOWNLOADS = Path(__file__).resolve().parents[1] / 'downloads'
SUPPORTED = {'resource','page','assign','url','folder','label'}


@dataclass
class ExportReport:
    directory: Path
    files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def academic_content(payload, kind):
    if not payload.is_html:
        raise ValueError('Se esperaba una página HTML de Moodle.')
    soup = payload.soup()
    main = soup.select_one('[role="main"]')
    if not main:
        raise ValueError('No se encontró el área principal de Moodle.')
    if main.select_one('.availabilityinfo.isrestricted'):
        raise ValueError('La actividad está restringida.')
    if kind == 'page':
        content = main.select_one('.generalbox .no-overflow')
        if content is None:
            raise ValueError('No se encontró el contenido académico de la página.')
        return str(content), []
    if kind == 'assign':
        intro = soup.select_one('#intro')
        if intro is None:
            return '<p>Esta actividad no muestra una consigna o descripción.</p>', []
        if intro.select_one('.availabilityinfo.isrestricted'):
            raise ValueError('La consigna está restringida.')
        files = list(dict.fromkeys(urljoin(payload.url, a['href']) for a in intro.select('a[href]')
                                  if '/pluginfile.php/' in a['href']))
        for technical in intro.select('[id^="assign_files_tree"], .fileuploadsubmissiontime, img.icon'):
            technical.decompose()
        return str(intro), files
    if kind == 'folder':
        tree = main.select_one('.foldertree')
        if tree is None:
            raise ValueError('No se encontró el árbol de archivos de la carpeta.')
        files = list(dict.fromkeys(urljoin(payload.url, a['href']) for a in tree.select('a[href]')
                                  if '/pluginfile.php/' in a['href'] and not a.find_parent(class_='isrestricted')))
        return '', files
    raise ValueError('Tipo de contenido no reconocido.')


def export_sections(page, course: Course, sections: list[Section], *, output_root=DOWNLOADS,
                    create_index=True, progress=lambda message: None) -> ExportReport:
    directory = unique_path(Path(output_root), course.name, directory=True)
    report = ExportReport(directory)
    downloader = Downloader(page.context.request)

    def emit(message):
        progress(message)
        with (directory / 'export.log').open('a', encoding='utf-8') as log:
            log.write(message + '\n')

    def error(message):
        report.errors.append(message)
        emit('[ERROR] ' + message)

    emit('[CURSO] ' + course.name)
    seen = set()
    for section in sorted(sections, key=lambda s: s.position):
        if section.position in seen:
            continue
        seen.add(section.position)
        if not section.is_available:
            emit('[SKIP] Sección restringida: ' + section.name)
            continue
        emit('[SECCION] ' + section.name)
        exported = []
        try:
            section_dir = unique_path(directory, section.name, directory=True)
            activities = get_activities(page, course, [section])
        except Exception as exc:
            error(f'{section.name}: {exc}')
            continue

        def record(path, tag):
            exported.append(path)
            report.files.append(path)
            emit(f'[{tag}] {path.name}')

        for activity in activities:
            if not activity.is_available:
                emit('[SKIP] Actividad restringida/no disponible: ' + activity.title)
                continue
            if activity.type not in SUPPORTED:
                emit('[SKIP] Tipo no soportado: ' + activity.type)
                continue
            prefix = f'{activity.position:02d} - '
            docx = DocxExporter(downloader, lambda message: error(f'{activity.title}: {message}'))
            try:
                if activity.type == 'resource':
                    record(downloader.download(activity.url, section_dir, prefix, activity.title), 'DOWNLOAD')
                    continue
                if activity.type == 'url':
                    target = downloader.external_url(activity.url)
                    html = f'<p>URL destino: <a href="{escape(target, quote=True)}">{escape(target)}</a></p>'
                    record(docx.export(activity.title, html, activity.url, section_dir, prefix + activity.title + '.docx'), 'DOCX')
                    continue
                if activity.type == 'label':
                    if not activity.content_html:
                        emit('[SKIP] Etiqueta sin contenido académico: ' + activity.title)
                        continue
                    record(docx.export(activity.title, activity.content_html, section.url, section_dir, prefix + activity.title + '.docx'), 'DOCX')
                    continue
                payload = downloader.fetch(activity.url)
                html, files = academic_content(payload, activity.type)
                if activity.type != 'folder':
                    # Los adjuntos se intentan incluso si falla la conversión de la consigna.
                    try:
                        record(docx.export(activity.title, html, payload.url, section_dir, prefix + activity.title + '.docx'),
                               'ASSIGN' if activity.type == 'assign' else 'DOCX')
                    except Exception as exc:
                        error(f'{activity.title} (DOCX): {exc}')
                if activity.type == 'folder' and not files:
                    emit('[SKIP] Carpeta sin archivos accesibles: ' + activity.title)
                for number, url in enumerate(files, 1):
                    try:
                        record(downloader.download(url, section_dir, f'{activity.position:02d}.{number:02d} - ', activity.title), 'DOWNLOAD')
                    except Exception as exc:
                        error(f'{activity.title}, archivo {number}: {exc}')
            except Exception as exc:
                error(f'{activity.title}: {exc}')
        if not activities:
            emit('[INFO] Sin actividades')
        if create_index:
            try:
                html = '<ol>' + ''.join(f'<li>{escape(p.name)}</li>' for p in exported) + '</ol>'
                if not exported:
                    html = '<p>No se exportaron recursos. Consultá export.log.</p>'
                index = DocxExporter(downloader).export(section.name, html, '', section_dir, '00 - Índice.docx')
                report.files.append(index)
                emit('[DOCX] ' + index.name)
            except Exception as exc:
                error(f'Índice de {section.name}: {exc}')
    return report
