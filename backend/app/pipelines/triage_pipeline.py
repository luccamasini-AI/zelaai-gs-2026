"""Pipeline central de triagem CitizenTech e confirmação Human-in-the-loop."""

from datetime import datetime, timezone
import uuid

from backend.app.config import ApplicationSettings
from backend.app.providers.external_data_provider import fetch_geolocation_and_weather_context
from backend.app.providers.llm_provider import analyze_occurrence_with_llm
from backend.app.providers.risk_model_provider import compute_urban_technical_risk_score
from backend.app.schemas.occurrence_schema import (
    CitizenReportRequest,
    HumanInTheLoopConfirmationRequest,
    HumanInTheLoopConfirmationResponse,
    OccurrenceCategory,
    TriageCompleteResponse,
)

CATEGORY_TO_DEPARTMENT_MAP = {
    OccurrenceCategory.DRENAGEM_E_ALAGAMENTO: (
        "Secretaria Municipal de Infraestrutura Urbana e Defesa Civil (SIURB / COMDEC)"
    ),
    OccurrenceCategory.ACESSIBILIDADE_E_CALCADAS: (
        "Secretaria Municipal da Pessoa com Deficiência (SMPED) e Subprefeitura Local"
    ),
    OccurrenceCategory.RISCO_ESTRUTURAL_E_ARVORES: (
        "Defesa Civil Municipal (199) e Manejo Arbóreo"
    ),
    OccurrenceCategory.ILUMINACAO_E_SEGURANCA_VIARIA: (
        "Departamento de Iluminação Pública (ILUME) e Engenharia de Tráfego (CET)"
    ),
    OccurrenceCategory.SANEAMENTO_E_RESIDUOS: (
        "Autoridade Municipal de Limpeza Urbana (AMLURB) e Vigilância Ambiental"
    ),
}


def _generate_protocol_identifier(prefix: str) -> str:
    """Gera um identificador único legível para rastreamento pelo cidadão."""
    short_token = uuid.uuid4().hex[:6].upper()
    year_str = datetime.now(timezone.utc).strftime("%Y")
    return f"{prefix}-{year_str}-{short_token}"


def execute_citizen_triage_pipeline(
    report: CitizenReportRequest, settings: ApplicationSettings
) -> TriageCompleteResponse:
    """Orquestra consulta a APIs públicas, score ML e análise estruturada pelo LLM."""
    location_and_weather = fetch_geolocation_and_weather_context(
        postal_code=report.postal_code,
        timeout_seconds=min(4.5, settings.external_api_timeout_seconds),
    )

    technical_risk_score = compute_urban_technical_risk_score(
        description=report.citizen_description,
        precipitation_mm=location_and_weather.current_precipitation_mm,
        vulnerability_context=report.vulnerability_context,
        has_photo_evidence=report.has_photo_evidence,
    )

    ai_triage_output, engine_label = analyze_occurrence_with_llm(
        report=report,
        location_weather=location_and_weather,
        technical_risk_score=technical_risk_score,
        settings=settings,
    )

    privacy_applied = (
        "[CPF PROTEGIDO - LGPD]" in report.citizen_description
        or "[EMAIL PROTEGIDO - LGPD]" in report.citizen_description
    )

    return TriageCompleteResponse(
        draft_protocol_number=_generate_protocol_identifier("TRIAGEM"),
        created_at_iso=datetime.now(timezone.utc).isoformat(),
        sanitized_description=report.citizen_description,
        reference_location=report.reference_location or "",
        vulnerability_context=report.vulnerability_context,
        privacy_protection_applied=privacy_applied,
        location_and_weather=location_and_weather,
        technical_risk_score=technical_risk_score,
        ai_triage=ai_triage_output,
        processing_engine_used=engine_label,
    )


def confirm_human_in_the_loop_decision(
    confirmation: HumanInTheLoopConfirmationRequest,
) -> HumanInTheLoopConfirmationResponse:
    """Registra a validação, correção ou aprovação humana antes do despacho final."""
    official_protocol = confirmation.draft_protocol_number.replace("TRIAGEM-", "ZC-OFICIAL-")
    dispatch_destination = CATEGORY_TO_DEPARTMENT_MAP.get(
        confirmation.confirmed_category,
        "Central de Atendimento Municipal 156",
    )

    if confirmation.reviewer_role == "GESTOR_PUBLICO":
        status_label = "AUDITADO_E_DESPACHADO_PELO_GESTOR"
        message = (
            f"Ocorrência auditada pelo Gestor Público e despachada prioritariamente para "
            f"{dispatch_destination} sob protocolo {official_protocol}."
        )
    else:
        status_label = "CONFIRMADO_PELO_CIDADAO"
        message = (
            f"Sua solicitação foi validada com sucesso! O protocolo oficial {official_protocol} "
            f"foi encaminhado para {dispatch_destination}."
        )

    return HumanInTheLoopConfirmationResponse(
        official_protocol_number=official_protocol,
        confirmed_at_iso=datetime.now(timezone.utc).isoformat(),
        final_status=status_label,
        confirmed_category=confirmation.confirmed_category,
        confirmed_urgency=confirmation.confirmed_urgency,
        dispatch_destination=dispatch_destination,
        confirmation_message=message,
    )
