"""Testes unitários dos pipelines de IA, modelo preditivo scikit-learn e Human-in-the-loop."""

from backend.app.config import ApplicationSettings
from backend.app.pipelines.triage_pipeline import (
    confirm_human_in_the_loop_decision,
    execute_citizen_triage_pipeline,
)
from backend.app.providers.risk_model_provider import compute_urban_technical_risk_score
from backend.app.schemas.occurrence_schema import (
    CitizenReportRequest,
    HumanInTheLoopConfirmationRequest,
    OccurrenceCategory,
    UrgencyLevel,
    VulnerabilityContext,
)


def test_scikit_learn_risk_model_scores_high_hazard_higher_than_low_hazard() -> None:
    """O modelo RandomForest deve atribuir score maior para alagamento com chuva do que limpeza simples."""
    critical_score = compute_urban_technical_risk_score(
        description="Enchente severa e desabamento de muro com fios caídos na rua.",
        precipitation_mm=22.0,
        vulnerability_context=VulnerabilityContext.AREA_DE_ENCOSTA_OU_MARGEM_CORREGO,
        has_photo_evidence=True,
    )
    low_score = compute_urban_technical_risk_score(
        description="Solicito pintura de guia e capina preventiva na praça do bairro.",
        precipitation_mm=0.0,
        vulnerability_context=VulnerabilityContext.NENHUMA_ESPECIFICA,
        has_photo_evidence=False,
    )
    assert critical_score > 75.0
    assert low_score < 45.0
    assert critical_score > low_score


def test_triage_pipeline_classifies_accessibility_occurrence_correctly() -> None:
    """Deve classificar relato de rampa e calçada bloqueada para cadeirante em Acessibilidade."""
    settings = ApplicationSettings(gemini_api_key="")
    report = CitizenReportRequest(
        citizen_description=(
            "Calçada totalmente destruída e rampa de cadeirante bloqueada impedindo passagem de idosos."
        ),
        postal_code="04011-000",
        vulnerability_context=VulnerabilityContext.PESSOA_COM_DEFICIENCIA_OU_IDOSO,
        has_photo_evidence=True,
    )

    result = execute_citizen_triage_pipeline(report=report, settings=settings)

    assert result.ai_triage.official_category == OccurrenceCategory.ACESSIBILIDADE_E_CALCADAS
    assert result.ai_triage.urgency_level in {UrgencyLevel.ALTA, UrgencyLevel.CRITICA}
    assert len(result.ai_triage.citizen_immediate_guidance) >= 2
    assert result.draft_protocol_number.startswith("TRIAGEM-")


def test_human_in_the_loop_confirmation_generates_official_protocol() -> None:
    """Deve gerar protocolo oficial definitivo após validação humana do cidadão."""
    confirmation_request = HumanInTheLoopConfirmationRequest(
        draft_protocol_number="TRIAGEM-2026-AB12CD",
        confirmed_category=OccurrenceCategory.DRENAGEM_E_ALAGAMENTO,
        confirmed_urgency=UrgencyLevel.CRITICA,
        was_ai_helpful=True,
        human_review_notes="Confirmo a classificação, água já subiu 20cm na calçada.",
        reviewer_role="CIDADAO",
    )

    confirmation_response = confirm_human_in_the_loop_decision(confirmation_request)

    assert confirmation_response.official_protocol_number == "ZC-OFICIAL-2026-AB12CD"
    assert confirmation_response.final_status == "CONFIRMADO_PELO_CIDADAO"
    assert confirmation_response.confirmed_urgency == UrgencyLevel.CRITICA
