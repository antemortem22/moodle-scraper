# Moodle Scraper

Herramienta en Python para acceder a una cuenta de Moodle, reutilizar una sesión autenticada y, progresivamente, exportar cursos y contenido disponible para el usuario.

Actualmente están implementadas la autenticación manual y la lectura de cursos y secciones mediante Playwright. El resto del alcance previsto es trabajo futuro.

## Objetivo

La idea del proyecto es construir un exportador de contenido de Moodle que permita guardar localmente información de los cursos accesibles desde una cuenta autenticada, 
con el fin de facilitar la recolección de información a lo largo de mi camino en la Tecnicatura Superior en Desarrollo de Software.

El alcance previsto incluye:

- cursos
- secciones y unidades
- archivos descargables
- páginas HTML
- imágenes incrustadas
- consignas de actividades
- links externos
- metadata de los recursos
- estructura local por curso

El proyecto no busca acceder a contenido fuera de los permisos de la cuenta utilizada.

## Tecnologías

- Python
- Playwright
- Chromium

## Estructura

```text
moodle-scraper/
├── login.py
├── test_session.py
├── main.py
├── models/
│   ├── __init__.py
│   ├── course.py
│   └── section.py
├── scraper/
│   ├── __init__.py
│   ├── browser.py
│   ├── courses.py
│   ├── sections.py
│   └── errors.py
├── tests/
│   └── test_scraper.py
├── requirements.txt
├── .gitignore
└── .venv/
```

## Etapa 2: probar desde PowerShell

La instalación existente sirve; no hay dependencias nuevas. No hace falta activar `.venv`.

```powershell
cd C:\Users\Antemortem\Desktop\moodle-scraper
.\.venv\Scripts\python.exe main.py
```

1. Se abre Chromium visible usando `session.json`.
2. Se lee `/my/courses.php` y se muestra la lista de cursos.
3. Escribí el número de un curso y presioná Enter. `0` sale; los valores inválidos vuelven a solicitarse.
4. Se abre únicamente ese curso y se muestran sus secciones en el orden original.
5. Presioná Enter para cerrar el navegador. También podés cancelar con Ctrl+C.

Ejemplo basado en la inspección real (los cursos pueden cambiar):

```text
Cursos encontrados:

[1] Administración de Base de Datos 2026 2C - 1° E
[2] Aula de tutoría (1E) 2C2026
[3] Construí tu futuro Orientación
...

Elegí el número de un curso (0 para salir): 1

Curso: Administración de Base de Datos 2026 2C - 1° E

[1] Sección sin título (1)
[2] Semana 0 - ¡Comenzá por acá!
[3] Semana 1 - Introducción a las Bases de Datos
[4] Semana 2 - Modelo Relacional
...
```

La sección inicial del curso inspeccionado contiene una presentación sin encabezado. Se conserva con un nombre de respaldo. El número entre corchetes es la posición en el listado, no el número de semana. Se conservan títulos como `Entrega PFO 1` y `Encuesta`.

## Responsabilidad de cada archivo

- `models/course.py`: modelo inmutable `Course(id, name, url)`, sin dependencia del navegador.
- `models/section.py`: modelo inmutable `Section(name, position, url)`. `position` empieza en 1; `url` puede ser `None`.
- `models/__init__.py`: exporta ambos modelos.
- `scraper/__init__.py`: define el paquete de lectura.
- `scraper/browser.py`: `open_moodle()` administra Chromium y carga la sesión; `navigate()` controla navegación, fallos HTTP y redirecciones al login.
- `scraper/courses.py`: `get_courses(page)` devuelve una lista de `Course`, espera la carga dinámica, recorre la paginación y elimina duplicados por ID.
- `scraper/sections.py`: `get_sections(page, course)` devuelve una lista de `Section`, conserva el orden y maneja títulos vacíos. Lee los títulos del resumen del curso, sin abrir las secciones ni las actividades.
- `scraper/errors.py`: errores `MoodleError`, `SessionError` y `PageLoadError`, que cualquier interfaz puede capturar.
- `main.py`: prueba de integración por consola; contiene la selección y los mensajes al usuario.
- `tests/test_scraper.py`: pruebas locales con páginas simuladas, sin leer tu sesión ni acceder al sitio real.

`scraper/` no contiene `input()`, `print()` ni código de interfaz gráfica. Una futura UI podrá reutilizar sus funciones y recibir los mismos modelos y excepciones. Las operaciones son sincrónicas y deben ejecutarse en el mismo hilo que crea Playwright; una futura UI deberá usar un hilo de trabajo para no bloquearse.

## Criterios y límites de lectura

Los selectores se basan en el HTML inspeccionado con la sesión real: `data-region="myoverview"`, enlaces `a.coursename` a `/course/view.php?id=`, `.multiline[title]`, paginación por `data-page`, y el formato Tiles con `li.tile`, `a.tile-link` y títulos `h3`.

La lista selecciona el filtro **Todos** de Moodle: incluye los cursos visibles de esa vista, no los que quitaste mediante “Eliminar de la vista”. El filtro puede quedar guardado como preferencia de Moodle. En la inspección aparecieron 9 cursos en Todos y 4 en Destacados. No se recorren automáticamente los cursos: sólo se abre el seleccionado.

Moodle duplica algunos textos para lectores de pantalla y crea contenedores ocultos de sección. Se eliminan esas duplicaciones, respetando los títulos reales. Las secciones visibles sin título se conservan como `Sección sin título (N)`, incluso si están vacías. Las URL apuntan al enlace de sección disponible o a su ancla en el curso.

La lectura se verificó con el formato Tiles de esta instalación. Otros formatos o futuros cambios del sitio pueden requerir adaptar `sections.py`; si no hay secciones reconocibles se informa en consola. No se usa el contenido de actividades como título de sección.

Esta etapa no descarga archivos, no extrae actividades ni páginas HTML, no genera un manifest y no implementa Tkinter. `session.json` se usa para abrir el navegador y no se reescribe.

## Errores y comprobación

Si falta la sesión o expiró, ejecutá:

```powershell
.\.venv\Scripts\python.exe login.py
.\.venv\Scripts\python.exe test_session.py
.\.venv\Scripts\python.exe main.py
```

En `login.py`, completá el acceso en Chromium y luego presioná Enter en la consola para guardar la sesión. Si la página falla o tarda demasiado, el programa muestra un error: revisá la conexión y probá otra vez. Si no hay cursos o secciones, muestra un mensaje y no falla por intentar seleccionar una lista vacía.

Para repetir las pruebas locales:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las esperas de contenido usan la API de [Playwright](https://playwright.dev/python/docs/api/class-page#page-wait-for-function), sin pausas fijas para asumir que Moodle ya terminó de cargar.
