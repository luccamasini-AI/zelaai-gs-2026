"""Ponto de entrada da aplicação FastAPI com CORS restritivo e tratamento amigável de erros."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import get_application_settings
from backend.app.routers import health, occurrences


def create_fastapi_application() -> FastAPI:
    """Instancia e configura a aplicação FastAPI seguindo boas práticas de segurança."""
    settings = get_application_settings()

    application = FastAPI(
        title=settings.application_title,
        version=settings.application_version,
        description=(
            "Back-end CitizenTech para triagem inteligente de zeladoria urbana, "
            "acessibilidade e resiliência climática com saída estruturada Pydantic."
        ),
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
    )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Retorna mensagens claras ao cidadão caso os dados enviados falhem na validação Pydantic."""
        friendly_errors = []
        for err in exc.errors():
            field_name = err.get("loc", ["campo"])[-1]
            message = err.get("msg", "Valor inválido")
            friendly_errors.append(f"{field_name}: {message}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": {
                    "error_code": "VALIDATION_ERROR",
                    "user_message": "Alguns campos do formulário precisam de revisão antes do envio.",
                    "fields": friendly_errors,
                }
            },
        )

    application.include_router(health.router)
    application.include_router(occurrences.router)
    return application


app = create_fastapi_application()
