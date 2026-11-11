"""Endpoint de verificação de saúde e diagnóstico do back-end."""

from fastapi import APIRouter, Depends

from backend.app.config import ApplicationSettings, get_application_settings

router = APIRouter(prefix="/api/v1/health", tags=["Health & Diagnostics"])


@router.get("")
def get_service_health(
    settings: ApplicationSettings = Depends(get_application_settings),
) -> dict:
    """Retorna o status operacional da API, motor de IA e modelo preditivo embarcado."""
    return {
        "status": "online",
        "service": settings.application_title,
        "version": settings.application_version,
        "llm_provider_configured": settings.has_configured_llm_api_key,
        "llm_model": settings.gemini_model_name,
        "ml_risk_model": "RandomForestRegressor (scikit-learn ativo)",
        "public_apis": ["ViaCEP", "Open-Meteo"],
    }
