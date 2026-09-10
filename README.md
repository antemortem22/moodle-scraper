# Moodle Scraper

## Interfaz de escritorio

```powershell
.\.venv\Scripts\python.exe gui.py
```

La ventana comprueba `session.json` y carga los cursos. Elegí un curso en el desplegable, marcá las semanas/secciones y pulsá **Descargar selección**. Las restringidas aparecen deshabilitadas. También podés marcar todas las disponibles o limpiar la selección.

La interfaz oscura tiene dos paneles redimensionables: **Descargar** y **Biblioteca local**. Podés arrastrar el separador central para repartir el espacio. La barra animada indica actividad; mientras descarga muestra la cantidad de archivos guardados, sin inventar un total que el exportador todavía no conoce. Al finalizar informa `Finalizado · N archivos · M errores`. Los mensajes técnicos quedan en **Ver detalles**, plegado por defecto.

El estado muestra **● Conectada / Renovar sesión** o **○ Sin sesión / Iniciar sesión**. Los botones de confirmar o cancelar el inicio sólo aparecen durante ese proceso.

La biblioteca refleja las carpetas y archivos reales de `downloads/`, incluidos ZIP y descargas anteriores. **Actualizar** vuelve a leer el disco. Al seleccionar un archivo se habilitan **Abrir archivo** y **Abrir ubicación**; al seleccionar una carpeta se habilitan **Abrir carpeta** y **Exportar ZIP**. Un doble clic en un archivo lo abre con su aplicación predeterminada de Windows. No se abren en lote los archivos de una carpeta.

El menú de clic derecho ofrece abrir, abrir ubicación, exportar una carpeta/sección a ZIP y **Eliminar descarga local**. La eliminación es permanente y siempre requiere confirmar la ruta; si es una carpeta incluye su contenido. Sólo se permiten rutas dentro de `downloads/` y no se siguen enlaces simbólicos ni uniones de carpetas. Moodle no se modifica.

El ZIP se guarda junto a la carpeta elegida: por ejemplo, `Curso/Semana 1.zip`, con la sección y su estructura interna. Conserva todos los archivos originales y no vuelve a descargar nada. Si el ZIP ya existe se usa `(2)`, `(3)`, etc., sin sobrescribirlo. La compresión y eliminación corren fuera del hilo de Tkinter; mientras trabajan se bloquean las acciones que podrían entrar en conflicto con una descarga.

La paleta está centralizada en **`ui/theme.py`, diccionario `PALETTE`**. Cambiá allí `bg`, `panel`, `accent`, `soft`, `deep`, `text`, `muted`, `border`, `success` y `error`, y reiniciá la app. `apply_theme()` aplica esos valores mediante `ttk.Style` y el tema `clam`; los widgets clásicos usan la misma paleta.

Si la sesión falta o expiró, pulsá **Iniciar / renovar sesión**. Se abre Chromium para iniciar sesión manualmente. Cuando veas tu cuenta, volvé a la interfaz y pulsá **Ya inicié sesión**. El programa verifica el acceso a tus cursos, guarda `session.json` y carga el desplegable automáticamente. Si todavía no completaste el login, permite reintentar. **Cancelar inicio** cierra el navegador sin reemplazar la sesión anterior. No hace falta usar Enter ni abrir una consola para este flujo; `login.py` sigue disponible como alternativa.

La interfaz no solicita ni guarda contraseñas. Ante un error de sesión se limpian las selecciones anteriores y se deshabilita la descarga. Si cerrás la ventana durante el login, se cancela; durante una exportación, espera a que termine para cerrar correctamente el navegador y los archivos.

- `gui.py`: inicia Tkinter.
- `ui/app.py`: controles, casillas, barra de actividad, mensajes y árbol de archivos.
- `ui/layout.py`: distribución de los dos paneles y widgets.
- `ui/theme.py`: paleta oscura y estilos violetas.
- `ui/library.py`: creación de ZIP y eliminación local con validación de rutas.
- `tests/test_library.py`: pruebas de ZIP, colisiones y límites de eliminación.
- `ui/worker.py`: conexión y exportación en un hilo separado; crea, usa y cierra Playwright dentro de ese mismo hilo. Se comunica con Tkinter mediante una cola.
- `tests/test_ui.py`: pruebas del hilo de trabajo y de los controles, con ventanas ocultas y sin acceder a Moodle.

Tkinter ya está disponible en la instalación de Python de este equipo. `main.py` sigue siendo la alternativa por consola. La interfaz reutiliza el exportador actual y no genera índices por sección.

Herramienta en Python para acceder a una cuenta de Moodle, reutilizar una sesión autenticada y, progresivamente, exportar cursos y contenido disponible para el usuario.

Actualmente están implementadas la autenticación manual, la selección de secciones disponibles y la exportación de sus actividades: archivos originales y documentos Word editables. El resto del alcance previsto es trabajo futuro.

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
│   ├── activity.py
│   └── section.py
├── scraper/
│   ├── __init__.py
│   ├── browser.py
│   ├── courses.py
│   ├── activities.py
│   ├── sections.py
│   └── errors.py
├── tests/
│   └── test_scraper.py
├── requirements.txt
├── .gitignore
└── .venv/
```

## Etapa 2: probar desde PowerShell

No hace falta activar `.venv`. Para la exportación actual, instalá las dependencias de `requirements.txt` como se indica en la etapa 4.

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
7. El programa lee únicamente las secciones elegidas y exporta todas sus actividades compatibles y disponibles, sin pedir selección recurso por recurso.
8. Presioná Enter para cerrar el navegador. También podés cancelar con Ctrl+C.

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

La capa de detección sigue devolviendo modelos independientes. La exportación actual se describe en la etapa 4. `session.json` se usa para abrir el navegador y no se reescribe.

## Etapa 3: detectar y clasificar actividades

La detección forma parte del flujo integrado actual:

```powershell
.\.venv\Scripts\python.exe main.py
```

Elegí un curso y luego las secciones, por ejemplo `1,3,8` si esos números están disponibles. Tras mostrar “Seleccionadas”, la etapa 4 exporta sus recursos. `all` recorre sólo las secciones disponibles. La salida de ejemplo de esta etapa documenta la clasificación previa a la exportación.

Archivos de esta etapa:

- `models/activity.py`: modelo inmutable `Activity(id, title, url, type, section, position, is_available, file_format)`. `section` es el objeto `Section` original; `position` comienza en 1 dentro de esa sección. `id`, `url` y `file_format` pueden ser `None`. El ID corresponde al módulo del curso, no a su instancia interna.
- `models/__init__.py`: exporta `Activity` junto con los modelos existentes.
- `scraper/activities.py`: `get_activities(page, course, sections)` devuelve una lista de objetos `Activity`. Valida las secciones antes de navegar, conserva su orden y lee sólo sus contenedores. No imprime ni solicita entradas de consola.
- `main.py`: integra ahora la exportación y presenta su progreso por consola.
- `tests/test_activities.py`: pruebas locales de tipos, restricciones, etiquetas, secciones vacías, orden y navegación limitada a las secciones elegidas.

### Detección basada en el HTML inspeccionado

En el formato Tiles de esta instalación, cada sección tiene un contenedor `.course-section#section-N`. Sus actividades están en `.activity`, con atributos como `data-cmid`, `data-title`, `data-modtype`, clases `modtype_*` y enlaces `a.cm-link`. La vista de General también usa `.activityname a`. Se ignoran separadores `.spacer`, controles de finalización y elementos ocultos.

La clasificación prioriza los metadatos del elemento; después usa la ruta `/mod/<tipo>/` si es necesario. Admite `resource`, `page`, `assign`, `url`, `folder`, `forum`, `quiz`, `book`, `h5pactivity`, `label` y `other`. `resource_pdf` se normaliza a `resource`; el indicador PDF se obtiene de ese atributo o de `resourcetype_pdf`, sin consultar ni descargar el archivo.

Las etiquetas declaradas como `label` se conservan aunque no tengan enlace. Un resumen textual de la sección se representa también como `label`, con un extracto de hasta 200 caracteres si no tiene título. No se convierte cada párrafo de la interfaz en una actividad ni se extraen imágenes. Los bloques desconocidos permanecen como `other`.

Las actividades con `.availabilityinfo.isrestricted`, `aria-disabled="true"` o sin enlace habilitado (salvo etiquetas) se muestran como `[RESTRINGIDA/NO HABILITADA]`. No se inventan URL para ellas. Si una sección presenta una nueva restricción al cargarla, se detiene la lectura con un mensaje. La comprobación no abre ninguna actividad, archivo, carpeta, foro ni quiz: sólo lee su presencia en la sección.

### Resultado verificado en Moodle

En General, Semana 1 y Entrega PFO 1 de Administración de Base de Datos se encontraron **13 elementos**: `forum`, `page`, `resource` con marca PDF, `folder` y `assign`. Los demás tipos están contemplados, pero no se observaron en esas tres secciones. Las etiquetas y restricciones individuales se probaron con HTML local; no se encontró ninguna en esa muestra real.

Ejemplo de salida real, abreviado:

```text
Curso: Administración de Base de Datos 2026 2C - 1° E

General

[FORUM] Avisos

Semana 1 - Introducción a las Bases de Datos

[PAGE] Apertura
[PAGE] Orientaciones de la semana
[PDF/RESOURCE] ⭐ Arquitectura Cliente-Servidor
[PDF/RESOURCE] ⭐ Bases de Datos
[FORUM] Foro de orientaciones y consultas
...

Entrega PFO 1

[ASSIGN] Buzón de Entrega - PFO 1
[FORUM] Consultas
```

## Errores y comprobación

## Etapa 4: exportar las secciones seleccionadas

### Ejecutar en Windows

```powershell
cd C:\Users\Antemortem\Desktop\moodle-scraper
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Elegí el curso y las secciones, por ejemplo `3,8` o `all`. La exportación comienza automáticamente: no hay selección de actividades individuales. `all` incluye únicamente secciones disponibles. Al terminar se informa la carpeta de salida, el número de archivos y los errores registrados.

### Tipos soportados

| Tipo | Resultado |
|---|---|
| `resource` | Archivo original, siguiendo redirecciones y enlaces de archivo de Moodle. |
| `page` | `.docx` con el contenido académico de `.generalbox .no-overflow`. |
| `assign` | `.docx` con la consigna de `#intro` y descargas separadas de los adjuntos visibles. No incluye entregas, calificaciones ni comentarios del alumno. |
| `url` | `.docx` con título y URL destino. No solicita el sitio externo. |
| `folder` | Todos los archivos accesibles del árbol de la carpeta; conserva formatos y nombres originales. |
| `label` | `.docx` con el HTML académico que se capturó en la sección. |
| Otros | Mensaje `[SKIP] Tipo no soportado: ...`, continuando con el resto. |

Los archivos PDF, DOCX, PPTX, XLSX, ZIP, imágenes, SQL y otros formatos se conservan como bytes originales; no se convierten a Word. Las actividades restringidas no se solicitan. Los fallos individuales, incluidos adjuntos e imágenes, se registran y no interrumpen los siguientes recursos.

### Estructura del Word

Se usa `python-docx` con un título `Heading 1`, subtítulos jerárquicos, párrafos Normal, negrita, cursiva, listas de Word, tablas con celdas combinadas, citas y bloques de código en Consolas. Se mantiene el orden de los elementos. Los enlaces se conservan como texto seguido de la URL completa, editable en Word.

Las imágenes incrustadas se obtienen con la sesión autenticada cuando corresponde y se insertan en el DOCX ajustadas al ancho. Pillow adapta formatos como WebP/GIF para insertarlos en Word. Si una imagen falla o su formato no puede insertarse, se registra el error y se conserva su descripción y URL en el documento.

Los iframes, vídeos y aplicaciones externas como Genially se conservan como título/enlace: su contenido interactivo no se convierte ni se descarga. No se reproduce el CSS de Moodle. Los contenedores académicos están verificados en esta instalación; un cambio de tema o formato puede necesitar ajustes.

### Archivos y organización

```text
downloads/
└── Nombre del Curso/
    └── Nombre de la Sección/
        ├── 01 - Apertura.docx
        ├── 03 - Archivo original.pdf
        ├── 08.01 - Archivo de carpeta.sql
        └── ...
```

El prefijo corresponde a la posición original de la actividad; se conservan los huecos de actividades omitidas. Los adjuntos y archivos de carpetas usan subnúmeros (`08.01`, `08.02`). No se generan índices por sección.

Los mensajes técnicos se acumulan en `logs/export.log`, fuera de `downloads/`. La carpeta `logs/` se crea automáticamente y está ignorada por Git. La Biblioteca Local oculta los archivos `.log`, incluidos los de exportaciones anteriores.

Los nombres se sanitizan para Windows. Si ya existe una carpeta de curso se crea otra con sufijo `(2)`, `(3)`, etc.; nunca se reutiliza para una sincronización. Los nombres de archivo repetidos también reciben sufijos. Esto evita sobrescrituras, incluso si dos nombres distintos se vuelven iguales al quitar caracteres no válidos. Las carpetas Moodle anidadas se reúnen dentro de la carpeta de la sección, con nombres únicos.

### Módulos de exportación

- `exporter/service.py`: `export_sections(page, course, sections, output_root=..., progress=...)`; coordina las secciones, devuelve `ExportReport` con archivos y errores y emite mensajes mediante un callback. Agrega los mensajes a `logs/export.log`.
- `exporter/downloader.py`: solicitudes GET autenticadas, redirecciones, detección de archivos y nombres originales mediante `Content-Disposition` o URL. Resuelve actividades URL sin visitar el sitio externo.
- `exporter/docx_exporter.py`: mapeo de HTML a Word e inserción de imágenes.
- `exporter/paths.py`: nombres seguros, rutas cortas y reserva de archivos sin sobrescribir.
- `models/activity.py` y `scraper/activities.py`: conservan el HTML de etiquetas en `content_html` para exportarlo sin perder su estructura.
- `main.py`: conserva la selección existente y llama a la exportación.
- `requirements.txt`: agrega `python-docx`, `beautifulsoup4` y `Pillow`.
- `tests/test_exporter.py`: valida documentos Word, nombres, redirecciones, aislamiento de contenido, continuidad ante errores y ausencia de índices.

### Comprobación realizada

Se exportaron Semana 1 y Entrega PFO 1 del curso de Administración de Base de Datos: 15 archivos, incluidos 8 DOCX, PDFs originales, dos SQL y los adjuntos de la consigna. Se reabrieron los Word con `python-docx`, verificando también imágenes y una tabla, y se comprobaron las cabeceras de los PDF. No se realizó una revisión visual en Microsoft Word. Los nombres con acentos de los adjuntos y sus índices se corrigieron.

Para revisar manualmente, abrí `downloads`, entrá en el curso y la sección y abrí sus `.docx` con Word. Probá editar los títulos, párrafos y tablas. Si aparece `[ERROR]`, consultá `logs/export.log`; el resto de la exportación continúa.

El proyecto todavía no implementa manifest, sincronización, conversión a Markdown/PDF ni exportación interna de foros, quizzes, H5P, SCORM o libros Moodle.

## Comprobación de sesión y pruebas

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
