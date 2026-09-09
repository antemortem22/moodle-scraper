"""GET autenticados con las cookies de Playwright; sin modificar Moodle."""
from dataclasses import dataclass
from email.message import Message
from email.utils import collapse_rfc2231_value
import mimetypes
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from .paths import unique_path


@dataclass
class Payload:
    url: str
    headers: dict
    data: bytes

    @property
    def is_html(self):
        content_type = self.headers.get('content-type', '').lower()
        return 'text/html' in content_type or 'application/xhtml' in content_type or self.data.lstrip().lower().startswith((b'<!doctype html', b'<html'))

    def soup(self):
        return BeautifulSoup(self.data, 'html.parser')


class Downloader:
    def __init__(self, request):
        self.request = request

    def fetch(self, url: str) -> Payload:
        for _ in range(12):
            if urlsplit(url).scheme not in ('http', 'https'):
                raise ValueError('URL de descarga no admitida.')
            response = self.request.get(url, max_redirects=0, timeout=60000)
            try:
                if 300 <= response.status < 400:
                    location = response.headers.get('location')
                    if not location:
                        raise ValueError('Redirección sin destino.')
                    url = urljoin(url, location)
                    if '/login/' in urlsplit(url).path:
                        raise ValueError('Sesión expirada. Ejecutá login.py.')
                    continue
                if not response.ok:
                    raise ValueError(f'HTTP {response.status} al obtener el contenido.')
                payload = Payload(response.url, response.headers, response.body())
            finally:
                response.dispose()
            if payload.is_html:
                soup = payload.soup()
                if soup.select_one('input[type="password"]') or '/login/' in urlsplit(payload.url).path:
                    raise ValueError('Moodle solicita iniciar sesión nuevamente.')
                if soup.select_one('[role="main"] .errorbox, [data-rel="fatalerror"]'):
                    raise ValueError('Moodle devolvió una página de error.')
            return payload
        raise ValueError('Demasiadas redirecciones.')

    def filename(self, payload: Payload, fallback: str) -> str:
        header = payload.headers.get('content-disposition', '')
        message = Message()
        message['Content-Disposition'] = header
        name = message.get_filename()
        if isinstance(name, tuple):
            name = collapse_rfc2231_value(name)
        # Algunos Content-Disposition de Moodle llegan con bytes UTF-8
        # interpretados como Latin-1 (por ejemplo, GuÃ­a.pdf).
        if name and any(marker in name for marker in ('Ã', 'Â')):
            try:
                name = name.encode('latin-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        name = name or unquote(urlsplit(payload.url).path.rsplit('/', 1)[-1])
        if not name or name.endswith('.php'):
            name = fallback
            if not Path(name).suffix:
                media_type = payload.headers.get('content-type', '').split(';', 1)[0].strip()
                name += mimetypes.guess_extension(media_type) or ''
        return name.replace('\\', '/').rsplit('/', 1)[-1]

    def download(self, url: str, directory: Path, prefix: str, fallback: str) -> Path:
        visited = set()
        for _ in range(6):
            if url in visited:
                raise ValueError('El recurso devuelve un enlace circular.')
            visited.add(url)
            payload = self.fetch(url)
            if not payload.is_html or 'attachment' in payload.headers.get('content-disposition', '').lower():
                path = unique_path(directory, prefix + self.filename(payload, fallback))
                try:
                    path.write_bytes(payload.data)
                except Exception:
                    path.unlink(missing_ok=True)
                    raise
                return path
            soup = payload.soup()
            main = soup.select_one('[role="main"]')
            if not main or main.select_one('.availabilityinfo.isrestricted'):
                raise ValueError('Recurso restringido o sin archivo descargable.')
            candidates = [el.get('href') or el.get('data') or el.get('src') for el in main.select('a[href], object[data], iframe[src], embed[src]')]
            target = next((urljoin(payload.url, value) for value in candidates if value and '/pluginfile.php/' in value), None)
            if not target:
                raise ValueError('No se encontró un archivo en el contenedor del recurso.')
            url = target
        raise ValueError('No se pudo resolver el archivo del recurso.')

    def external_url(self, url: str) -> str:
        """Resuelve /mod/url sin solicitar el sitio de destino."""
        origin = urlsplit(url).netloc
        for _ in range(8):
            response = self.request.get(url, max_redirects=0, timeout=60000)
            try:
                if 300 <= response.status < 400:
                    target = urljoin(url, response.headers.get('location', ''))
                    if '/login/' in urlsplit(target).path:
                        raise ValueError('Sesión expirada.')
                    if urlsplit(target).netloc != origin or not urlsplit(target).path.startswith('/mod/url/'):
                        return target
                    url = target
                    continue
                if not response.ok:
                    raise ValueError(f'HTTP {response.status} al leer el enlace.')
                soup = BeautifulSoup(response.body(), 'html.parser')
            finally:
                response.dispose()
            if soup.select_one('input[type="password"]'):
                raise ValueError('Sesión expirada.')
            main = soup.select_one('[role="main"]')
            if not main or main.select_one('.availabilityinfo.isrestricted'):
                raise ValueError('Enlace restringido o contenido no reconocido.')
            for el in main.select('.urlworkaround a[href], .urlworkaround iframe[src], iframe[src], object[data]'):
                target = el.get('href') or el.get('src') or el.get('data')
                if target:
                    return urljoin(url, target)
            # Moodle puede mostrar un enlace simple dentro de su área principal.
            for el in main.select('a[href]'):
                target = urljoin(url, el['href'])
                if urlsplit(target).netloc != origin:
                    return target
            raise ValueError('No se encontró la URL destino; no se visitó el sitio externo.')
        raise ValueError('Demasiadas redirecciones del enlace.')
