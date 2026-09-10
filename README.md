# Moodle Scraper

Aplicación de escritorio en Python para descargar y organizar contenido de Moodle desde una sesión autenticada.

Permite elegir cursos y semanas/secciones, descargar todo el contenido disponible y guardarlo ordenado por materia.

Desarrollada para poder resolver una problematica organizacional que me surgió al comenzar mi trayecto como Técnica Superior en Desarrollo de Software a distancia.

## Features

- Login manual con sesión persistente
- Renovación de sesión cuando Moodle la vence
- Filtro de cursos destacados o todos
- Selección múltiple de semanas/secciones
- Detección de contenido restringido
- Descarga de archivos originales
- Conversión de contenido textual de Moodle a `.docx`
- Biblioteca local desde la GUI
- Apertura de archivos y carpetas
- Exportación a ZIP
- Eliminación de copias locales

## Stack

- Python
- Playwright
- Tkinter / ttk
- python-docx
- BeautifulSoup
- Pillow

## Instalación

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\playwright.exe install chromium
```

## Uso

```bash
.\.venv\Scripts\python.exe gui.py
```

Cuando no haya una sesión válida o la sesión haya vencido, iniciá sesión manualmente en Moodle desde Chromium para renovarla.

Después:

1. Elegí si querés ver cursos destacados o todos.
2. Seleccioná un curso.
3. Marcá las semanas/secciones.
4. Descargá la selección.

Los archivos quedan organizados en:

```text
downloads/
└── Curso/
    └── Semana/
        ├── contenido.docx
        ├── material.pdf
        └── ...
```

## Seguridad

El proyecto no guarda usuario ni contraseña.

`session.json` contiene el estado de autenticación y no debe subirse al repositorio. La sesión puede vencer y requerir un nuevo inicio de sesión.
