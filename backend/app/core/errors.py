from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorDetail, ErrorResponse


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        del request
        payload = ErrorResponse(
            error="http_error",
            details=[ErrorDetail(message=str(exc.detail))],
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        details = [
            ErrorDetail(
                field=".".join(str(part) for part in error["loc"]),
                message=error["msg"],
            )
            for error in exc.errors()
        ]
        payload = ErrorResponse(error="validation_error", details=details)
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        del request
        del exc
        payload = ErrorResponse(
            error="internal_server_error",
            details=[ErrorDetail(message="An unexpected error occurred.")],
        )
        return JSONResponse(status_code=500, content=payload.model_dump())
