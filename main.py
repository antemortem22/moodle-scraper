"""Prueba de integración por consola: cursos y secciones únicamente."""
from models import Course
from scraper.browser import open_moodle
from scraper.courses import get_courses
from scraper.errors import MoodleError
from scraper.sections import get_sections


def select_course(courses: list[Course]) -> Course | None:
    while True:
        value = input("\nElegí el número de un curso (0 para salir): ").strip()
        try:
            number = int(value)
        except ValueError:
            print("Ingresá un número de la lista.")
            continue
        if number == 0:
            return None
        if 1 <= number <= len(courses):
            return courses[number - 1]
        print(f"Elegí un número entre 1 y {len(courses)}, o 0 para salir.")


def main() -> int:
    try:
        with open_moodle() as page:
            print("Leyendo cursos de Moodle...")
            courses = get_courses(page)
            if not courses:
                print("No se encontraron cursos en la vista Todos de Moodle.")
                return 0
            print("\nCursos encontrados:\n")
            for index, course in enumerate(courses, start=1):
                print(f"[{index}] {course.name}")
            course = select_course(courses)
            if course is None:
                return 0
            sections = get_sections(page, course)
            print(f"\nCurso: {course.name}\n")
            if not sections:
                print("El curso no muestra secciones reconocibles en su página principal.")
            for section in sections:
                print(f"[{section.position}] {section.name}")
            input("\nPresioná Enter para cerrar el navegador: ")
        return 0
    except MoodleError as exc:
        print(f"\nError: {exc}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nOperación cancelada.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
