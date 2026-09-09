"""Errores que cualquier interfaz puede presentar al usuario."""


class MoodleError(Exception):
    pass


class SessionError(MoodleError):
    pass


class PageLoadError(MoodleError):
    pass
