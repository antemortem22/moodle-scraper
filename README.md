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
├── selection.py
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
5. Ante `Elegí una o más secciones:`, ingresá `3`, `2,3,5`, `2-5`, `1,3-5,7` o `all` para todas las disponibles. Se ignoran espacios alrededor de números y separadores. Las entradas inválidas o que incluyen secciones restringidas muestran un mensaje y vuelven a solicitarse.
6. Se muestran las seleccionadas sin duplicados y en el orden del curso: `5,2,3-5` selecciona `2,3,4,5`.
7. Presioná Enter para cerrar el navegador. También podés cancelar con Ctrl+C.

Ejemplo basado en la inspección real (los cursos pueden cambiar):

```text
Cursos encontrados:

[1] Administración de Base de Datos 2026 2C - 1° E
[2] Aula de tutoría (1E) 2C2026
[3] Construí tu futuro Orientación
...

Elegí el número de un curso (0 para salir): 1

Curso: Administración de Base de Datos 2026 2C - 1° E

[1] General
[2] Semana 0 - ¡Comenzá por acá!
[3] Semana 1 - Introducción a las Bases de Datos
[4] Semana 2 - Modelo Relacional
...
```

La primera sección se llama `General` únicamente si no tiene título visible; si lo tiene, se conserva. El número entre corchetes es la posición en el listado, no el número de semana. Se conservan títulos como `Entrega PFO 1` y `Encuesta`.

## Responsabilidad de cada archivo

- `models/course.py`: modelo inmutable `Course(id, name, url)`, sin dependencia del navegador.
- `models/section.py`: modelo inmutable `Section(name, position, url, is_available)`. `position` empieza en 1; `url` puede ser `None`; `is_available` indica si la sección está habilitada.
- `models/__init__.py`: exporta ambos modelos.
- `scraper/__init__.py`: define el paquete de lectura.
- `scraper/browser.py`: `open_moodle()` administra Chromium y carga la sesión; `navigate()` controla navegación, fallos HTTP y redirecciones al login.
- `scraper/courses.py`: `get_courses(page)` devuelve una lista de `Course`, espera la carga dinámica, recorre la paginación y elimina duplicados por ID.
- `scraper/sections.py`: `get_sections(page, course)` devuelve una lista de `Section`, conserva el orden y maneja títulos vacíos. Lee los títulos del resumen del curso, sin abrir las secciones ni las actividades.
- `scraper/errors.py`: errores `MoodleError`, `SessionError` y `PageLoadError`, que cualquier interfaz puede capturar.
- `main.py`: prueba de integración por consola; contiene la selección y los mensajes al usuario.
- `selection.py`: `parse_section_selection(value, sections)` valida números y rangos y devuelve los objetos `Section` originales, sin duplicados y en orden del curso. No depende de consola ni navegador; los errores se comunican con `ValueError`. `select_sections()` en `main.py` sólo solicita la entrada y reintenta cuando es inválida.
- `tests/test_selection.py`: verifica formatos, errores, reintentos y nombres de respaldo.
- `tests/test_scraper.py`: pruebas locales con páginas simuladas, sin leer tu sesión ni acceder al sitio real.

`scraper/` no contiene `input()`, `print()` ni código de interfaz gráfica. Una futura UI podrá reutilizar sus funciones y recibir los mismos modelos y excepciones. Las operaciones son sincrónicas y deben ejecutarse en el mismo hilo que crea Playwright; una futura UI deberá usar un hilo de trabajo para no bloquearse.

## Criterios y límites de lectura

Los selectores se basan en el HTML inspeccionado con la sesión real: `data-region="myoverview"`, enlaces `a.coursename` a `/course/view.php?id=`, `.multiline[title]`, paginación por `data-page`, y el formato Tiles con `li.tile`, `a.tile-link` y títulos `h3`.

La lista selecciona el filtro **Todos** de Moodle: incluye los cursos visibles de esa vista, no los que quitaste mediante “Eliminar de la vista”. El filtro puede quedar guardado como preferencia de Moodle. En la inspección aparecieron 9 cursos en Todos y 4 en Destacados. No se recorren automáticamente los cursos: sólo se abre el seleccionado.

Moodle duplica algunos textos para lectores de pantalla y crea contenedores ocultos de sección. Se eliminan esas duplicaciones, respetando los títulos reales. La primera sección sin título visible se conserva como `General`; las demás sin título usan `Sección sin título (N)`, incluso si están vacías. Las URL apuntan al enlace de sección disponible o a su ancla en el curso.

La lectura se verificó con el formato Tiles de esta instalación. Otros formatos o futuros cambios del sitio pueden requerir adaptar `sections.py`; si no hay secciones reconocibles se informa en consola. No se usa el contenido de actividades como título de sección.

Esta etapa no descarga archivos, no extrae actividades ni páginas HTML, no genera un manifest y no implementa Tkinter. `session.json` se usa para abrir el navegador y no se reescribe.

## Errores y comprobación

### Secciones restringidas

Las secciones no habilitadas siguen en el listado con `[RESTRINGIDA]`. La selección manual de una de ellas (también dentro de un rango) rechaza toda la entrada y vuelve a preguntar. `all` devuelve sólo objetos `Section` disponibles, manteniendo el orden original. Si todas están restringidas, se informa y no se solicita una selección imposible.

La detección en el formato Tiles usa señales verificadas en el HTML real: `tile-restricted` y `.availabilityinfo.isrestricted`. Los mosaicos habilitados tienen `tile-clickable` y un enlace `a.tile-link` con `href`; si faltan esas señales, no se permite seleccionarlos. Se observó el mensaje “Restringido” y un tooltip “Disponible desde…” en semanas futuras. No se calculan fechas de habilitación ni se intenta acceder al contenido para comprobarlas.

Las restricciones de actividades dentro de una sección no restringen automáticamente la sección completa. La disponibilidad se vuelve a leer al ejecutar el programa; representa lo que Moodle muestra en ese momento. La detección está verificada para el formato de esta instalación, no para todos los formatos posibles de Moodle.

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
