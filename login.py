"""Inicio de sesión manual en Aulas Virtuales."""

from pathlib import Path

from playwright.sync_api import sync_playwright


COURSES_URL = "https://aulasvirtuales.bue.edu.ar/my/courses.php"
SESSION_FILE = Path(__file__).resolve().parent / "session.json"


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            context = browser.new_context(accept_downloads=False)
            page = context.new_page()
            page.goto(COURSES_URL, wait_until="domcontentloaded", timeout=60000)
            print("Iniciá sesión manualmente en el navegador.")
            print("Esperá a ver tu cuenta y la página de tus cursos.")
            input("Después volvé a esta consola y presioná Enter para guardar la sesión: ")
            context.storage_state(path=str(SESSION_FILE), indexed_db=True)
            print(f"Sesión guardada en {SESSION_FILE}")
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nInicio de sesión cancelado.")
