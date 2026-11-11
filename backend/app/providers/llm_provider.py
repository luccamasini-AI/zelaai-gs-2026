"""Provedor de acesso ao LLM (Google Gemini API com Structured Outputs) e motor de contingência."""

import json
import logging
from typing import Tuple

import httpx
from pydantic import ValidationError

from backend.app.config import ApplicationSettings
from backend.app.schemas.occurrence_schema import (
    CitizenReportRequest,
    GeolocationAndWeatherContext,
    OccurrenceCategory,
    StructuredAiTriageOutput,
    UrgencyLevel,
    VulnerabilityContext,
)

logger = logging.getLogger(__name__)


class LlmTimeoutException(Exception):
    """Exceção lançada quando o provedor de IA excede o tempo limite de resposta."""


class LlmProviderUnavailableException(Exception):
    """Exceção lançada quando o provedor de IA retorna erro de serviço ou resposta inválida."""


GEMINI_RESPONSE_JSON_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "official_category": {
            "type": "STRING",
            "enum": [item.value for item in OccurrenceCategory],
        },
        "urgency_level": {
            "type": "STRING",
            "enum": [item.value for item in UrgencyLevel],
        },
        "responsible_department": {"type": "STRING"},
        "estimated_sla_hours": {"type": "INTEGER"},
        "citizen_immediate_guidance": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "manager_technical_summary": {"type": "STRING"},
        "classification_reasoning": {"type": "STRING"},
        "identified_risk_factors": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
    },
    "required": [
        "official_category",
        "urgency_level",
        "responsible_department",
        "estimated_sla_hours",
        "citizen_immediate_guidance",
        "manager_technical_summary",
        "classification_reasoning",
        "identified_risk_factors",
    ],
}


def _build_citizen_tech_prompt(
    report: CitizenReportRequest,
    location_weather: GeolocationAndWeatherContext,
    technical_risk_score: float,
) -> str:
    """Constrói o prompt estruturado combinando relato, geolocalização, clima e score ML."""
    return (
        "Você é o especialista de triagem da plataforma CitizenTech 'ZelaAI'.\n"
        "Sua missão é analisar o relato de um cidadão, cruzando-o com os dados climáticos "
        "e territoriais em tempo real e com o Score Técnico de Risco Urbano.\n\n"
        f"- Relato do cidadão: {report.citizen_description}\n"
        f"- Ponto de referência: {report.reference_location or 'Não informado'}\n"
        f"- Contexto de vulnerabilidade: {report.vulnerability_context.value}\n"
        f"- Endereço identificado (ViaCEP): {location_weather.street_name}, "
        f"{location_weather.neighborhood}, {location_weather.city_name}/{location_weather.state_code} "
        f"(CEP {location_weather.postal_code})\n"
        f"- Condição climática atual (Open-Meteo): {location_weather.weather_condition_summary}, "
        f"Precipitação={location_weather.current_precipitation_mm}mm, "
        f"Temperatura={location_weather.current_temperature_celsius}°C\n"
        f"- Score Técnico de Risco (Modelo RandomForest): {technical_risk_score}/100\n\n"
        "Retorne EXCLUSIVAMENTE um objeto JSON válido seguindo o schema definido, em português claro, "
        "empático, acessível ao cidadão e tecnicamente preciso para o gestor municipal."
    )


def _call_google_gemini_structured_api(
    prompt: str, settings: ApplicationSettings
) -> StructuredAiTriageOutput:
    """Realiza chamada HTTP para a API Google Gemini exigindo JSON Schema estruturado."""
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model_name}:generateContent?key={settings.gemini_api_key}"
    )
    request_payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseSchema": GEMINI_RESPONSE_JSON_SCHEMA,
        },
    }

    try:
        with httpx.Client(timeout=settings.external_api_timeout_seconds) as http_client:
            response = http_client.post(endpoint, json=request_payload)
            response.raise_for_status()
            data = response.json()
            raw_json_text = (
                data["candidates"][0]["content"]["parts"][0]["text"]
            )
            return StructuredAiTriageOutput.model_validate_json(raw_json_text)
    except httpx.TimeoutException as timeout_error:
        logger.error("Timeout ao aguardar resposta do Google Gemini: %s", timeout_error)
        raise LlmTimeoutException(
            "O serviço de Inteligência Artificial demorou mais que o esperado para responder."
        ) from timeout_error
    except (httpx.HTTPError, KeyError, IndexError, ValidationError, json.JSONDecodeError) as error:
        logger.error("Falha na comunicação ou validação estruturada com Google Gemini: %s", error)
        raise LlmProviderUnavailableException(
            "Não foi possível validar a resposta estruturada do provedor de IA."
        ) from error


def _run_deterministic_citizen_triage_fallback(
    report: CitizenReportRequest,
    location_weather: GeolocationAndWeatherContext,
    technical_risk_score: float,
) -> StructuredAiTriageOutput:
    """Executa análise semântica determinística estruturada quando sem chave de API externa."""
    text_lower = report.citizen_description.lower()
    has_rain_risk = location_weather.is_rain_alert_active or location_weather.current_precipitation_mm >= 2.0

    if any(k in text_lower for k in ("alagamento", "bueiro", "enchente", "inundação", "inundacao", "água", "agua", "córrego", "corrego", "drenagem")):
        category = OccurrenceCategory.DRENAGEM_E_ALAGAMENTO
        department = "Secretaria Municipal de Infraestrutura Urbana e Defesa Civil (SIURB / COMDEC)"
        guidance = [
            "Evite transitar a pé ou de veículo por áreas com lâmina d'água acumulada ou correnteza.",
            "Não tente desobstruir bueiros ou bocas de lobo manualmente devido ao risco de sucção.",
            "Em caso de elevação rápida do nível da água no imóvel, acione imediatamente a Defesa Civil (199).",
        ]
    elif any(k in text_lower for k in ("calçada", "calcada", "cadeirante", "rampa", "buraco", "piso tátil", "piso tatil", "acessibilidade", "idoso", "travessia")):
        category = OccurrenceCategory.ACESSIBILIDADE_E_CALCADAS
        department = "Secretaria Municipal da Pessoa com Deficiência (SMPED) e Subprefeitura Local"
        guidance = [
            "Utilize rota alternativa segura evitando descer para o leito carroçável sem sinalização.",
            "Se houver pedestre com mobilidade reduzida retido no trecho, solicite apoio da CET/GCM (156).",
            "Mantenha o número deste protocolo para acompanhamento prioritário pelo programa Calçada Segura.",
        ]
    elif any(k in text_lower for k in ("árvore", "arvore", "galho", "muro", "desabamento", "encosta", "deslizamento", "fiação", "fiacao", "poste")):
        category = OccurrenceCategory.RISCO_ESTRUTURAL_E_ARVORES
        department = "Defesa Civil Municipal (199) e Equipe de Manejo Arbóreo / Concessionária Elétrica"
        guidance = [
            "Mantenha distância mínima de 15 metros da estrutura, árvore inclinada ou fiação exposta.",
            "Jamais toque em cabos partidos ou galhos apoiados na rede elétrica.",
            "Em caso de estalos estruturais ou risco iminente de queda, acione o Corpo de Bombeiros (193).",
        ]
    elif any(k in text_lower for k in ("luz", "iluminação", "iluminacao", "escuro", "lâmpada", "lampada", "semáforo", "semaforo", "sinalização")):
        category = OccurrenceCategory.ILUMINACAO_E_SEGURANCA_VIARIA
        department = "Departamento de Iluminação Pública (ILUME) e Companhia de Engenharia de Tráfego (CET)"
        guidance = [
            "Redobre a atenção ao circular pelo trecho no período noturno e prefira vias adjacentes iluminadas.",
            "Caso haja semáforo apagado em cruzamento movimentado, aguarde a passagem segura na faixa.",
            "O ponto reportado foi georreferenciado pelo CEP para substituição de luminária LED.",
        ]
    else:
        category = OccurrenceCategory.SANEAMENTO_E_RESIDUOS
        department = "Autoridade Municipal de Limpeza Urbana (AMLURB) e Vigilância Ambiental"
        guidance = [
            "Evite contato direto com resíduos acumulados ou água servida para prevenir contaminações.",
            "Não realize queima de descartes ou entulhos no local.",
            "A equipe de zeladoria regional foi notificada com o endereço do CEP informado.",
        ]

    if technical_risk_score >= 80.0 or (
        category in {OccurrenceCategory.DRENAGEM_E_ALAGAMENTO, OccurrenceCategory.RISCO_ESTRUTURAL_E_ARVORES}
        and (has_rain_risk or report.vulnerability_context != VulnerabilityContext.NENHUMA_ESPECIFICA)
    ):
        urgency = UrgencyLevel.CRITICA
        sla_hours = 4
    elif technical_risk_score >= 60.0 or report.vulnerability_context != VulnerabilityContext.NENHUMA_ESPECIFICA:
        urgency = UrgencyLevel.ALTA
        sla_hours = 12
    elif technical_risk_score >= 35.0:
        urgency = UrgencyLevel.MEDIA
        sla_hours = 48
    else:
        urgency = UrgencyLevel.BAIXA
        sla_hours = 120

    risk_factors = [
        f"Índice de gravidade avaliado em {technical_risk_score}/100 com base nas condições do local",
        f"Localização: {location_weather.neighborhood} ({location_weather.city_name}/{location_weather.state_code})",
    ]
    if has_rain_risk:
        risk_factors.append(
            f"Condição climática no momento: {location_weather.weather_condition_summary} ({location_weather.current_precipitation_mm} mm)"
        )
    if report.vulnerability_context != VulnerabilityContext.NENHUMA_ESPECIFICA:
        risk_factors.append("Presença de público vulnerável ou equipamento público sensível no entorno")

    manager_summary = (
        f"Ocorrência registrada no bairro {location_weather.neighborhood} (CEP {location_weather.postal_code}) "
        f"com prioridade {urgency.value}. Índice de gravidade: {technical_risk_score}/100. "
        f"Encaminhamento indicado: {department}."
    )
    reasoning = (
        f"A prioridade {urgency.value} foi definida considerando os detalhes do relato informado pelo morador, "
        f"o impacto sobre a circulação de pessoas no entorno e a condição climática atual em "
        f"{location_weather.neighborhood} ({location_weather.weather_condition_summary})."
    )

    return StructuredAiTriageOutput(
        official_category=category,
        urgency_level=urgency,
        responsible_department=department,
        estimated_sla_hours=sla_hours,
        citizen_immediate_guidance=guidance,
        manager_technical_summary=manager_summary,
        classification_reasoning=reasoning,
        identified_risk_factors=risk_factors,
    )


def analyze_occurrence_with_llm(
    report: CitizenReportRequest,
    location_weather: GeolocationAndWeatherContext,
    technical_risk_score: float,
    settings: ApplicationSettings,
) -> Tuple[StructuredAiTriageOutput, str]:
    """Executa a análise inteligente via Google Gemini API ou contingência estruturada."""
    if report.simulate_failure_mode == "TIMEOUT":
        raise LlmTimeoutException(
            "Simulação de Timeout ativada: o provedor de IA excedeu o limite de tempo de resposta."
        )
    if report.simulate_failure_mode == "LLM_ERROR":
        raise LlmProviderUnavailableException(
            "Simulação de Falha do LLM ativada: o provedor de IA retornou resposta indisponível."
        )

    prompt = _build_citizen_tech_prompt(
        report=report,
        location_weather=location_weather,
        technical_risk_score=technical_risk_score,
    )

    if settings.has_configured_llm_api_key:
        try:
            structured_output = _call_google_gemini_structured_api(prompt=prompt, settings=settings)
            return structured_output, f"Google Gemini API ({settings.gemini_model_name})"
        except (LlmTimeoutException, LlmProviderUnavailableException) as llm_error:
            logger.warning(
                "Provedor Gemini indisponível (%s). Acionando motor determinístico de contingência.",
                llm_error,
            )

    fallback_output = _run_deterministic_citizen_triage_fallback(
        report=report,
        location_weather=location_weather,
        technical_risk_score=technical_risk_score,
    )
    return fallback_output, "Motor Semântico Estruturado + RandomForest (Contingência Resiliente)"
