"""Operaciones locales, limitadas a downloads y sin seguir enlaces de disco."""
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def checked_path(root, path):
    root, path = Path(root).resolve(), Path(path).absolute()
    resolved = path.resolve(strict=True)
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError('La operación debe apuntar a una descarga dentro de downloads.')
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError('No se permiten enlaces simbólicos ni uniones de carpetas.')
    return resolved


def checked_contents(root, folder):
    folder = checked_path(root, folder)
    items = []
    for path in folder.rglob('*'):
        checked_path(root, path)
        items.append(path)
    return items


def export_zip(root, folder):
    folder = checked_path(root, folder)
    if not folder.is_dir():
        raise ValueError('Seleccioná una carpeta para exportar ZIP.')
    contents = checked_contents(root, folder)
    count = 1
    while True:
        suffix = '' if count == 1 else f' ({count})'
        destination = folder.with_name(folder.name + suffix + '.zip')
        try:
            stream = destination.open('xb')
            break
        except FileExistsError:
            count += 1
    try:
        with stream, ZipFile(stream, 'w', compression=ZIP_DEFLATED) as archive:
            archive.write(folder, folder.name + '/')
            for path in contents:
                checked_path(root, path)
                archive.write(path, path.relative_to(folder.parent))
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def delete_local(root, path):
    path = checked_path(root, path)
    if path.is_dir():
        checked_contents(root, path)
        # Target absoluto verificado dentro de downloads antes de borrar.
        shutil.rmtree(path)
    else:
        path.unlink()
    return path
