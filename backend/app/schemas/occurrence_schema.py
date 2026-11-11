"""Esquemas Pydantic para validação de entrada, saída estruturada do LLM e auditoria."""

import html
import re
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class UrgencyLevel(str, Enum):
    """Níveis padronizados de criticidade e urgência de atendimento urbano."""

    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class OccurrenceCategory(str, Enum):
    """Categorias oficiais de zeladoria urbana, acessibilidade e defesa civil."""

    DRENAGEM_E_ALAGAMENTO = "DRENAGEM_E_ALAGAMENTO"
    ACESSIBILIDADE_E_CALCADAS = "ACESSIBILIDADE_E_CALCADAS"
    RISCO_ESTRUTURAL_E_ARVORES = "RISCO_ESTRUTURAL_E_ARVORES"
    ILUMINACAO_E_SEGURANCA_VIARIA = "ILUMINACAO_E_SEGURANCA_VIARIA"
    SANEAMENTO_E_RESIDUOS = "SANEAMENTO_E_RESIDUOS"


class VulnerabilityContext(str, Enum):
    """Contexto de vulnerabilidade social ou física no local da ocorrência."""

    NENHUMA_ESPECIFICA = "NENHUMA_ESPECIFICA"
    PESSOA_COM_DEFICIENCIA_OU_IDOSO = "PESSOA_COM_DEFICIENCIA_OU_IDOSO"
    ENTORNO_ESCOLAR_OU_SAUDE = "ENTORNO_ESCOLAR_OU_SAUDE"
    AREA_DE_ENCOSTA_OU_MARGEM_CORREGO = "AREA_DE_ENCOSTA_OU_MARGEM_CORREGO"


SUSPICIOUS_INJECTION_PATTERN = re.compile(
    r"(<\s*script|javascript\s*:|onerror\s*=|onload\s*=|union\s+select|drop\s+table|--\s*$)",
    re.IGNORECASE,
)
CPF_NUMBER_PATTERN = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
EMAIL_ADDRESS_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def sanitize_and_mask_personal_data(raw_text: str) -> str:
    """Remove vetores de XSS/SQLi e mascara dados sensíveis (CPF/E-mail) em conformidade com a LGPD."""
    cleaned_text = raw_text.strip()
    if SUSPICIOUS_INJECTION_PATTERN.search(cleaned_text):
        raise ValueError(
            "O texto informado contém sequências não permitidas por políticas de segurança."
        )
    escaped_text = html.escape(cleaned_text, quote=False)
    masked_cpf_text = CPF_NUMBER_PATTERN.sub("[CPF PROTEGIDO - LGPD]", escaped_text)
    masked_email_text = EMAIL_ADDRESS_PATTERN.sub("[EMAIL PROTEGIDO - LGPD]", masked_cpf_text)
    return masked_email_text


class CitizenReportRequest(BaseModel):
    """Dados de entrada enviados pelo cidadão para análise e triagem inteligente."""

    citizen_description: str = Field(
        ...,
        min_length=15,
        max_length=1500,
        description="Relato detalhado do problema vivenciado pelo cidadão.",
    )
    postal_code: str = Field(
        ...,
        min_length=8,
        max_length=10,
        description="CEP do local da ocorrência (com ou sem hífen).",
    )
    reference_location: Optional[str] = Field(
        default="",
        max_length=160,
        description="Ponto de referência opcional (ex.: em frente à UBS ou número aproximado).",
    )
    vulnerability_context: VulnerabilityContext = Field(
        default=VulnerabilityContext.NENHUMA_ESPECIFICA,
        description="Indica se há população vulnerável ou equipamento crítico no local.",
    )
    has_photo_evidence: bool = Field(
        default=False,
        description="Indica se o cidadão anexou evidência fotográfica da ocorrência.",
    )
    simulate_failure_mode: Literal["NONE", "TIMEOUT", "LLM_ERROR"] = Field(
        default="NONE",
        description="Modo auxiliar para demonstrar tratamento de falhas durante homologação.",
    )

    @field_validator("citizen_description")
    @classmethod
    def validate_citizen_description(cls, value: str) -> str:
        """Valida consistência semântica, sanitiza contra injeção e aplica máscara LGPD."""
        sanitized_text = sanitize_and_mask_personal_data(value)
        if len(sanitized_text.split()) < 3:
            raise ValueError(
                "Por favor, descreva o problema com pelo menos 3 palavras para uma análise precisa."
            )
        return sanitized_text

    @field_validator("postal_code")
    @classmethod
    def validate_and_normalize_postal_code(cls, value: str) -> str:
        """Extrai apenas dígitos e valida se o CEP possui exatamente 8 números."""
        digits_only = re.sub(r"\D", "", value or "")
        if len(digits_only) != 8:
            raise ValueError("O CEP deve conter exatamente 8 dígitos numéricos (ex.: 01310-100).")
        return f"{digits_only[:5]}-{digits_only[5:]}"

    @field_validator("reference_location")
    @classmethod
    def validate_reference_location(cls, value: Optional[str]) -> str:
        """Sanitiza o ponto de referência opcional informado pelo cidadão."""
        if not value:
            return ""
        return sanitize_and_mask_personal_data(value)


class GeolocationAndWeatherContext(BaseModel):
    """Contexto territorial e microclimático obtido via APIs públicas (ViaCEP + Open-Meteo)."""

    postal_code: str
    street_name: str
    neighborhood: str
    city_name: str
    state_code: str
    current_precipitation_mm: float = Field(..., ge=0.0)
    current_temperature_celsius: float
    weather_condition_summary: str
    is_rain_alert_active: bool
    data_source_label: str


class StructuredAiTriageOutput(BaseModel):
    """Modelo Pydantic estrito exigido como saída estruturada do LLM."""

    official_category: OccurrenceCategory = Field(
        ...,
        description="Categoria oficial atribuída pela IA após análise do relato e contexto.",
    )
    urgency_level: UrgencyLevel = Field(
        ...,
        description="Nível de criticidade calculado para priorização do atendimento público.",
    )
    responsible_department: str = Field(
        ...,
        min_length=5,
        max_length=140,
        description="Órgão ou secretaria municipal responsável pelo encaminhamento.",
    )
    estimated_sla_hours: int = Field(
        ...,
        ge=1,
        le=720,
        description="Prazo estimado em horas para vistoria ou atendimento inicial.",
    )
    citizen_immediate_guidance: List[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Lista de orientações práticas e seguras para o cidadão seguir imediatamente.",
    )
    manager_technical_summary: str = Field(
        ...,
        min_length=15,
        max_length=400,
        description="Resumo técnico objetivo para a fila de despacho do gestor público.",
    )
    classification_reasoning: str = Field(
        ...,
        min_length=15,
        max_length=450,
        description="Explicação transparente dos fatores que motivaram a classificação da IA.",
    )
    identified_risk_factors: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Fatores de risco concretos identificados no relato e no clima.",
    )


class TriageCompleteResponse(BaseModel):
    """Resposta completa retornada pelo back-end após o pipeline de triagem."""

    draft_protocol_number: str
    created_at_iso: str
    sanitized_description: str
    reference_location: str
    vulnerability_context: VulnerabilityContext
    privacy_protection_applied: bool
    location_and_weather: GeolocationAndWeatherContext
    technical_risk_score: float = Field(..., ge=0.0, le=100.0)
    ai_triage: StructuredAiTriageOutput
    processing_engine_used: str


class HumanInTheLoopConfirmationRequest(BaseModel):
    """Dados de confirmação, revisão ou avaliação enviados pelo cidadão ou gestor (Human-in-the-loop)."""

    draft_protocol_number: str = Field(..., min_length=5, max_length=40)
    confirmed_category: OccurrenceCategory
    confirmed_urgency: UrgencyLevel
    was_ai_helpful: bool = Field(
        ...,
        description="Avaliação do cidadão sobre a utilidade da triagem e orientação da IA.",
    )
    human_review_notes: Optional[str] = Field(
        default="",
        max_length=400,
        description="Observação ou correção humana adicionada antes do encaminhamento final.",
    )
    reviewer_role: Literal["CIDADAO", "GESTOR_PUBLICO"] = Field(default="CIDADAO")

    @field_validator("human_review_notes")
    @classmethod
    def sanitize_review_notes(cls, value: Optional[str]) -> str:
        """Sanitiza comentários de revisão humana."""
        if not value:
            return ""
        return sanitize_and_mask_personal_data(value)


class HumanInTheLoopConfirmationResponse(BaseModel):
    """Protocolo definitivo gerado após a etapa de validação humana (Human-in-the-loop)."""

    official_protocol_number: str
    confirmed_at_iso: str
    final_status: str
    confirmed_category: OccurrenceCategory
    confirmed_urgency: UrgencyLevel
    dispatch_destination: str
    confirmation_message: str
