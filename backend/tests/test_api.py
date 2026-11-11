"""Testes dos endpoints e roteadores FastAPI (fluxo feliz, CORS e tratamento de falhas 502/504)."""

import pytest
from fastapi import HTTPException

from backend.app.config import ApplicationSettings
from backend.app.main import app
from backend.app.routers.health import get_service_health
from backend.app.routers.occurrences import (
    confirm_occurrence_triage,
    triage_citizen_occurrence,
)
from backend.app.schemas.occurrence_schema import (
    CitizenReportRequest,
    HumanInTheLoopConfirmationRequest,
    OccurrenceCategory,
    UrgencyLevel,
    VulnerabilityContext,
)


def test_fastapi_routes_are_registered() -> None:
    """Deve registrar todos os endpoints obrigatórios no schema OpenAPI do FastAPI."""
    openapi_paths = set(app.openapi().get("paths", {}).keys())
    assert "/api/v1/health" in openapi_paths
    assert "/api/v1/occurrences/triage" in openapi_paths
    assert "/api/v1/occurrences/confirm" in openapi_paths


def test_health_endpoint_returns_online_status() -> None:
    """Endpoint /api/v1/health deve retornar status online e metadados do serviço."""
    settings = ApplicationSettings()
    payload = get_service_health(settings=settings)
    assert payload["status"] == "online"
    assert "RandomForestRegressor" in payload["ml_risk_model"]


def test_triage_endpoint_returns_structured_pydantic_payload() -> None:
    """Endpoint /api/v1/occurrences/triage deve retornar modelo Pydantic estruturado."""
    settings = ApplicationSettings(gemini_api_key="")
    report = CitizenReportRequest(
        citizen_description="Bueiro entupido causando alagamento grave em frente à escola municipal.",
        postal_code="01310-100",
        reference_location="Próximo ao número 1000",
        vulnerability_context=VulnerabilityContext.ENTORNO_ESCOLAR_OU_SAUDE,
        has_photo_evidence=True,
        simulate_failure_mode="NONE",
    )

    response = triage_citizen_occurrence(report=report, settings=settings)

    assert response.ai_triage.official_category == OccurrenceCategory.DRENAGEM_E_ALAGAMENTO
    assert response.technical_risk_score > 0
    assert len(response.ai_triage.citizen_immediate_guidance) >= 2


def test_triage_endpoint_handles_simulated_timeout_gracefully() -> None:
    """Deve lançar HTTPException 504 com mensagem amigável sem expor stack trace técnico."""
    settings = ApplicationSettings(gemini_api_key="")
    report = CitizenReportRequest(
        citizen_description="Árvore com risco de queda sobre a fiação elétrica na rua toda.",
        postal_code="05409-000",
        simulate_failure_mode="TIMEOUT",
    )

    with pytest.raises(HTTPException) as exc_info:
        triage_citizen_occurrence(report=report, settings=settings)

    assert exc_info.value.status_code == 504
    assert exc_info.value.detail["error_code"] == "LLM_TIMEOUT"
    assert "demorou mais que o esperado" in exc_info.value.detail["user_message"]


def test_triage_endpoint_handles_simulated_llm_error_gracefully() -> None:
    """Deve lançar HTTPException 502 com mensagem amigável quando o LLM falha."""
    settings = ApplicationSettings(gemini_api_key="")
    report = CitizenReportRequest(
        citizen_description="Árvore com risco de queda sobre a fiação elétrica na rua toda.",
        postal_code="05409-000",
        simulate_failure_mode="LLM_ERROR",
    )

    with pytest.raises(HTTPException) as exc_info:
        triage_citizen_occurrence(report=report, settings=settings)

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["error_code"] == "LLM_UNAVAILABLE"


def test_confirm_endpoint_registers_human_in_the_loop_decision() -> None:
    """Endpoint /api/v1/occurrences/confirm deve retornar protocolo oficial validado."""
    confirmation = HumanInTheLoopConfirmationRequest(
        draft_protocol_number="TRIAGEM-2026-998877",
        confirmed_category=OccurrenceCategory.ACESSIBILIDADE_E_CALCADAS,
        confirmed_urgency=UrgencyLevel.ALTA,
        was_ai_helpful=True,
        human_review_notes="Confirmado pelo gestor regional.",
        reviewer_role="GESTOR_PUBLICO",
    )

    response = confirm_occurrence_triage(confirmation=confirmation)
    assert response.official_protocol_number == "ZC-OFICIAL-2026-998877"
    assert response.final_status == "AUDITADO_E_DESPACHADO_PELO_GESTOR"
