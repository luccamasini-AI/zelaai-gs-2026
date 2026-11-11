"""Endpoints FastAPI para triagem inteligente de ocorrências e confirmação Human-in-the-loop."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.config import ApplicationSettings, get_application_settings
from backend.app.pipelines.triage_pipeline import (
    confirm_human_in_the_loop_decision,
    execute_citizen_triage_pipeline,
)
from backend.app.providers.llm_provider import (
    LlmProviderUnavailableException,
    LlmTimeoutException,
)
from backend.app.schemas.occurrence_schema import (
    CitizenReportRequest,
    HumanInTheLoopConfirmationRequest,
    HumanInTheLoopConfirmationResponse,
    TriageCompleteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/occurrences", tags=["CitizenTech Occurrences"])


@router.post(
    "/triage",
    response_model=TriageCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Analisa o relato do cidadão com IA estruturada, clima em tempo real e modelo de risco",
)
def triage_citizen_occurrence(
    report: CitizenReportRequest,
    settings: ApplicationSettings = Depends(get_application_settings),
) -> TriageCompleteResponse:
    """Processa o relato do cidadão e retorna classificação estruturada validada pelo Pydantic."""
    try:
        return execute_citizen_triage_pipeline(report=report, settings=settings)
    except LlmTimeoutException as timeout_error:
        logger.warning("Timeout controlado durante triagem: %s", timeout_error)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error_code": "LLM_TIMEOUT",
                "user_message": (
                    "O serviço de análise inteligente demorou mais que o esperado para responder. "
                    "Por favor, tente novamente em alguns instantes ou utilize o telefone 156/199 em emergências."
                ),
            },
        ) from timeout_error
    except LlmProviderUnavailableException as provider_error:
        logger.warning("Indisponibilidade controlada do provedor de IA: %s", provider_error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error_code": "LLM_UNAVAILABLE",
                "user_message": (
                    "O motor de Inteligência Artificial está temporariamente indisponível para classificar seu relato. "
                    "Nenhum dado foi perdido. Tente reenviar em instantes."
                ),
            },
        ) from provider_error
    except Exception as unexpected_error:
        logger.exception("Erro inesperado no processamento da ocorrência: %s", unexpected_error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_PROCESSING_ERROR",
                "user_message": (
                    "Ocorreu uma instabilidade temporária ao processar sua solicitação. "
                    "Nossa equipe técnica foi notificada."
                ),
            },
        ) from unexpected_error


@router.post(
    "/confirm",
    response_model=HumanInTheLoopConfirmationResponse,
    status_code=status.HTTP_200_OK,
    summary="Registra a validação humana (cidadão ou gestor) antes do encaminhamento final",
)
def confirm_occurrence_triage(
    confirmation: HumanInTheLoopConfirmationRequest,
) -> HumanInTheLoopConfirmationResponse:
    """Efetiva o protocolo após confirmação, correção ou avaliação humana (Human-in-the-loop)."""
    return confirm_human_in_the_loop_decision(confirmation=confirmation)
