class IdentityError(Exception):
    """Raised by XIA services for any caller-facing failure; routers translate
    `status_code` into the HTTP response. Keeps domain logic free of FastAPI
    imports.
    """

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
