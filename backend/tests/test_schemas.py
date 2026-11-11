"""Testes unitários dos modelos Pydantic, sanitização de segurança e proteção LGPD."""

import pytest
from pydantic import ValidationError

from backend.app.schemas.occurrence_schema import (
    CitizenReportRequest,
    VulnerabilityContext,
)


def test_valid_citizen_report_normalizes_postal_code() -> None:
    """Deve normalizar CEP sem hífen para o formato padrão 00000-000."""
    request = CitizenReportRequest(
        citizen_description="Bueiro completamente entupido causando alagamento na esquina.",
        postal_code="01310100",
        vulnerability_context=VulnerabilityContext.ENTORNO_ESCOLAR_OU_SAUDE,
    )
    assert request.postal_code == "01310-100"


def test_lgpd_masking_of_cpf_and_email_in_description() -> None:
    """Deve mascarar automaticamente CPF e e-mail inseridos acidentalmente pelo cidadão."""
    request = CitizenReportRequest(
        citizen_description=(
            "Calçada quebrada na frente de casa, meu CPF é 123.456.789-00 e email cidadao@teste.com.br."
        ),
        postal_code="04011-000",
    )
    assert "123.456.789-00" not in request.citizen_description
    assert "cidadao@teste.com.br" not in request.citizen_description
    assert "[CPF PROTEGIDO - LGPD]" in request.citizen_description
    assert "[EMAIL PROTEGIDO - LGPD]" in request.citizen_description


def test_rejects_xss_and_sql_injection_payloads() -> None:
    """Deve bloquear tentativas de injeção de script ou SQL na validação de entrada."""
    with pytest.raises(ValidationError):
        CitizenReportRequest(
            citizen_description="<script>alert('xss')</script> buraco na rua principal",
            postal_code="01310-100",
        )


def test_rejects_invalid_postal_code_length() -> None:
    """Deve rejeitar CEPs que não contenham 8 dígitos numéricos."""
    with pytest.raises(ValidationError):
        CitizenReportRequest(
            citizen_description="Iluminação pública apagada em toda a quadra há três dias.",
            postal_code="12345",
        )
