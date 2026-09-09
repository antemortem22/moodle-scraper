# Moodle Scraper

Herramienta en Python para acceder a una cuenta de Moodle, reutilizar una sesión autenticada y, progresivamente, exportar cursos y contenido disponible para el usuario.

Actualmente el proyecto se encuentra en una etapa inicial enfocada en autenticación y persistencia de sesión mediante Playwright.

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
├── requirements.txt
├── .gitignore
└── .venv/
