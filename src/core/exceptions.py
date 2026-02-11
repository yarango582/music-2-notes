"""Excepciones personalizadas del sistema."""


class Music2NotesError(Exception):
    """Excepción base del sistema."""
    pass


class AudioProcessingError(Music2NotesError):
    """Error durante el procesamiento de audio."""
    pass


class JobNotFoundError(Music2NotesError):
    """Job no encontrado en la base de datos."""
    pass


class JobNotCompletedError(Music2NotesError):
    """Se intentó acceder al resultado de un job no completado."""
    pass


class StorageError(Music2NotesError):
    """Error de almacenamiento de archivos."""
    pass


class WebhookDeliveryError(Music2NotesError):
    """Error al enviar webhook."""
    pass
