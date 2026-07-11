import uuid

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken

STATUS_TO_ERROR_CODE = {
    400: "VALIDATION_ERROR",
    401: "AUTHENTICATION_FAILED",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "CONFLICT"
    default_detail = "Conflict"

    def __init__(self, code=None, message=None):
        self.error_code = code or self.default_code
        super().__init__(detail=message or self.default_detail, code=self.error_code)


def custom_exception_handler(exc, context):
    """Translates DRF exceptions into the DOC 0 §5.3 error envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, InvalidToken):
        error_code = "TOKEN_EXPIRED"
    else:
        error_code = getattr(exc, "error_code", None) or STATUS_TO_ERROR_CODE.get(
            response.status_code, "INTERNAL_ERROR"
        )

    details = None
    message = response.data
    if isinstance(response.data, dict) and set(response.data.keys()) == {"detail"}:
        message = response.data["detail"]
    elif isinstance(response.data, (dict, list)):
        details = response.data
        message = "Validation failed" if response.status_code == 400 else "Request failed"

    response.data = {
        "error": {
            "code": error_code,
            "message": str(message),
            "details": details,
            "trace_id": str(uuid.uuid4()),
        }
    }
    return response
