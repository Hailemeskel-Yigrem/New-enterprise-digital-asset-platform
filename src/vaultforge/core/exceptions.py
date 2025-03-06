"""Domain and application exception hierarchy."""


class VaultForgeError(Exception):
    """Base error for all application failures."""

    def __init__(self, message: str, *, code: str = "vaultforge_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(VaultForgeError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found")


class ConflictError(VaultForgeError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, code="conflict")


class AuthorizationError(VaultForgeError):
    def __init__(self, message: str = "Not authorized") -> None:
        super().__init__(message, code="forbidden")


class AuthenticationError(VaultForgeError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="unauthorized")


class ValidationError(VaultForgeError):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, code="validation_error")
