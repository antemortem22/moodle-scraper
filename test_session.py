"""Comprobación visual y manual de la sesión guardada; ejecutar con Python."""

from playwright.sync_api import sync_playwright

from login import COURSES_URL, SESSION_FILE


def main():
    if not SESSION_FILE.is_file():
        print("No existe session.json. Ejecutá primero login.py e iniciá sesión.")
        return 1

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            context = browser.new_context(
                storage_state=str(SESSION_FILE), accept_downloads=False
            )
            page = context.new_page()
            page.goto(COURSES_URL, wait_until="domcontentloaded", timeout=60000)
            print("Comprobá que ves tu cuenta y tus cursos sin volver a iniciar sesión.")
            print("Si aparece el formulario de acceso, cerrá esta prueba y repetí login.py.")
            input("Presioná Enter en esta consola para cerrar el navegador: ")
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nComprobación cancelada.")
