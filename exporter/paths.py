import re
from pathlib import Path


def safe_name(name: str, limit: int = 90) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip().rstrip('. ')
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', name, re.I):
        name = '_' + name
    return (name[:limit].rstrip('. ') or 'Sin nombre')


def unique_path(parent: Path, name: str, *, directory: bool = False) -> Path:
    name = safe_name(name, 500)
    parent.mkdir(parents=True, exist_ok=True)
    # Mantener margen respecto del límite tradicional de rutas de Windows.
    limit = min(100, 235 - len(str(parent.resolve())))
    if limit < 20:
        raise ValueError('Ruta demasiado larga. Elegí una carpeta de salida más corta.')
    suffix = '' if directory else Path(name).suffix[:15]
    stem = name if directory or not suffix else name[:-len(suffix)]
    stem = safe_name(stem, limit - len(suffix) - 10)
    for count in range(1, 10000):
        tail = '' if count == 1 else f' ({count})'
        path = parent / f'{stem}{tail}{suffix}'
        try:
            if directory:
                path.mkdir()
            else:
                with path.open('xb'):
                    pass
            return path
        except FileExistsError:
            continue
    raise ValueError('Demasiados nombres repetidos.')
