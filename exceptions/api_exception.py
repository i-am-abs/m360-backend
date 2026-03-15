from starlette.status import HTTP_502_BAD_GATEWAY


class ApiException(RuntimeError):
    def __init__(self, message: str, status_code: int = HTTP_502_BAD_GATEWAY):
        super().__init__(message)
        self.status_code = status_code
