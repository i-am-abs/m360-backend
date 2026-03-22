from http import HTTPStatus


class ApiException(RuntimeError):
    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_GATEWAY.value):
        super().__init__(message)
        self.status_code = status_code
