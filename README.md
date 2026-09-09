# Aulas Virtuales: inicio de sesión manual

Primera etapa: abrir Moodle, iniciar sesión manualmente y reutilizar esa sesión.
No se recorren cursos ni se descargan archivos.

## Archivos

- `login.py`: abre Chromium visible en `https://aulasvirtuales.bue.edu.ar/my/courses.php`, espera tu inicio de sesión manual y guarda `session.json` cuando presionás Enter en la consola. Luego cierra el navegador.
- `test_session.py`: carga esa sesión y abre la misma página para comprobar visualmente el acceso. Espera Enter para cerrar. Es un script manual, no una prueba de pytest.
- `requirements.txt`: fija la versión de Playwright.
- `.gitignore`: excluye `.venv/`, `session.json`, `downloads/` y archivos temporales de Python.
- `.venv/`: entorno local de Python y sus dependencias.
- `session.json`: se genera al ejecutar el login; se guarda junto a los scripts, aunque los ejecutes desde otra carpeta.

## Preparación en Windows (PowerShell)

Abrí una terminal PowerShell y entrá a la carpeta:

```powershell
cd C:\Users\Antemortem\Desktop\moodle-scraper
```

Si preparás el proyecto desde cero, creá el entorno (si `.venv` ya existe y funciona, omití este comando):

```powershell
py -m venv .venv
```

Instalá la dependencia y Chromium:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Los comandos usan directamente Python de `.venv`: no hace falta activar el entorno ni cambiar la política de ejecución de PowerShell.

## Guardar la sesión

```powershell
.\.venv\Scripts\python.exe login.py
```

1. Se abre Chromium. Ingresá tus datos únicamente en el sitio y completá cualquier paso de autenticación.
2. Esperá a ver tu cuenta y la página de tus cursos.
3. Dejá abierto el navegador, volvé a PowerShell y presioná Enter.
4. Verás el mensaje de sesión guardada y se cerrará Chromium.

Enter es tu confirmación de que terminaste el login; el script no verifica automáticamente la autenticación. No presiones Enter mientras todavía estés en el formulario de acceso.

## Comprobar que funciona

```powershell
.\.venv\Scripts\python.exe test_session.py
```

Se abre una nueva ventana con `session.json`. Si ves tu cuenta y tus cursos sin ingresar credenciales, funcionó. Presioná Enter en PowerShell para cerrar.

Si Moodle vuelve a pedir acceso, la sesión puede haber vencido o haberse guardado antes de completar el login. Cerrá la prueba, ejecutá `login.py` otra vez y repetí la comprobación. La prueba no modifica el archivo de sesión.

## Problemas frecuentes

- **No existe session.json:** ejecutá primero `login.py`.
- **Falta el ejecutable del navegador:** repetí el comando `-m playwright install chromium` indicado arriba.
- **La página no carga o aparece un timeout:** comprobá tu conexión y el acceso al sitio en tu navegador habitual; después repetí el comando.
- **session.json está dañado:** ejecutá `login.py` para reemplazarlo con una sesión nueva.
- **Cancelar:** presioná Ctrl+C en la consola. Para el flujo normal, usá Enter antes de cerrar la ventana del navegador.

No hay usuario ni contraseña en el código. `session.json` contiene datos de autenticación: no lo compartas ni lo subas a Git. Playwright documenta cómo guardar y reutilizar el estado en https://playwright.dev/python/docs/auth.
