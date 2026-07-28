import enum


class ErrorCode(enum.Enum):
    def __init__(self, error_code: str, status_code: int):
        self.__error_code = error_code
        self.__status_code = status_code

    @property
    def error_code(self) -> str:
        return self.__error_code

    @property
    def status_code(self) -> int:
        return self.__status_code

    # System (500)
    UNKNOWN_ERROR = ("UNKNOWN_ERROR", 500)
    SYSTEM_ERROR = ("SYSTEM_ERROR", 500)

    # Auth (401)
    UNAUTHORIZED = ("UNAUTHORIZED_ERROR", 401)
    INVALID_CREDENTIALS = ("INVALID_CREDENTIALS", 401)
    JWT_TOKEN_REVOKED = ("JWT_TOKEN_REVOKED", 401)
    JWT_TOKEN_EXPIRED = ("JWT_TOKEN_EXPIRED", 401)
    JWT_TOKEN_NOT_FRESH = ("JWT_TOKEN_NOT_FRESH", 401)
    INVALID_JWT_TOKEN = ("INVALID_JWT_TOKEN", 401)
    LOGIN_FAILED = ("LOGIN_FAILED", 401)

    # Permission (403)
    FORBIDDEN = ("FORBIDDEN", 403)
    USER_INACTIVE = ("USER_NOT_ACTIVE", 403)

    # Client input (400)
    BAD_REQUEST = ("BAD_REQUEST", 400)
    VALIDATION_ERROR = ("VALIDATION_ERROR", 422)
    INVALID_CODE = ("INVALID_CODE", 400)
    CODE_EXPIRED = ("CODE_EXPIRED", 400)
    ACTION_ALREADY_PERFORMED = ("ACTION_ALREADY_PERFORMED", 409)
    ACTION_CONFLICT = ("ACTION_CONFLICT", 409)

    # Resource
    RESOURCE_NOT_FOUND = ("RESOURCE_NOT_FOUND", 404)
    RESOURCE_ALREADY_EXISTS = ("RESOURCE_ALREADY_EXISTS", 409)
    RESOURCE_CONFLICT = ("RESOURCE_CONFLICT", 409)
    RESOURCE_NOT_AVAILABLE = ("RESOURCE_NOT_AVAILABLE", 404)
    RESOURCE_IN_USE = ("RESOURCE_IN_USE", 409)

    # Rate limit
    RATE_LIMIT_EXCEEDED = ("RATE_LIMIT_EXCEEDED", 429)

    # Database
    DATA_INTEGRITY_ERROR = ("DATA_INTEGRITY_ERROR", 409)

    # File
    FILE_TOO_LARGE = ("FILE_TOO_LARGE", 413)
    UNSUPPORTED_FILE_TYPE = ("UNSUPPORTED_FILE_TYPE", 415)
    FILE_UPLOAD_FAILED = ("FILE_UPLOAD_FAILED", 400)
