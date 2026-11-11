"""Provedor de integração com APIs públicas abertas (ViaCEP e Open-Meteo)."""

import logging
import re
from typing import Dict, Tuple

import httpx

from backend.app.schemas.occurrence_schema import GeolocationAndWeatherContext

logger = logging.getLogger(__name__)

SAO_PAULO_CEP_PREFIX_FALLBACK: Dict[str, Tuple[str, str, float, float]] = {
    "01": ("Região Central / Bela Vista", "Av. Paulista / Centro Histórico", -23.5505, -46.6333),
    "02": ("Zona Norte / Santana", "Av. Cruzeiro do Sul", -23.5015, -46.6247),
    "03": ("Zona Leste / Tatuapé", "Av. Celso Garcia", -23.5401, -46.5766),
    "04": ("Zona Sul / Vila Mariana", "Av. Domingos de Morais", -23.5891, -46.6346),
    "05": ("Zona Oeste / Pinheiros", "Av. Rebouças", -23.5673, -46.6927),
    "08": ("Zona Leste / Itaquera", "Av. Jacu-Pêssego", -23.5419, -46.4711),
}


def _resolve_regional_fallback_by_cep(postal_code: str) -> Tuple[str, str, float, float]:
    """Retorna bairro, logradouro de referência e coordenadas aproximadas pelo prefixo do CEP."""
    digits_only = re.sub(r"\D", "", postal_code)
    prefix = digits_only[:2] if len(digits_only) >= 2 else "01"
    return SAO_PAULO_CEP_PREFIX_FALLBACK.get(
        prefix,
        ("Região Metropolitana", "Via Urbana Principal", -23.5505, -46.6333),
    )


def _fetch_address_from_viacep(
    postal_code: str, timeout_seconds: float
) -> Tuple[str, str, str, str, bool]:
    """Consulta a API pública ViaCEP para obter endereço e bairro a partir do CEP."""
    digits_only = re.sub(r"\D", "", postal_code)
    fallback_neighborhood, fallback_street, _, _ = _resolve_regional_fallback_by_cep(postal_code)

    try:
        with httpx.Client(timeout=timeout_seconds) as http_client:
            response = http_client.get(f"https://viacep.com.br/ws/{digits_only}/json/")
            response.raise_for_status()
            payload = response.json()

            if payload.get("erro"):
                logger.warning("CEP %s não localizado na base ViaCEP; aplicando fallback regional.", postal_code)
                return fallback_street, fallback_neighborhood, "São Paulo", "SP", False

            street_name = payload.get("logradouro") or fallback_street
            neighborhood = payload.get("bairro") or fallback_neighborhood
            city_name = payload.get("localidade") or "São Paulo"
            state_code = payload.get("uf") or "SP"
            return street_name, neighborhood, city_name, state_code, True
    except httpx.HTTPError as http_error:
        logger.warning(
            "Falha de rede ao consultar ViaCEP para o CEP %s (%s). Utilizando contingência local.",
            postal_code,
            http_error,
        )
        return fallback_street, fallback_neighborhood, "São Paulo", "SP", False


def _fetch_weather_from_open_meteo(
    latitude: float, longitude: float, timeout_seconds: float
) -> Tuple[float, float, str, bool]:
    """Consulta a API pública Open-Meteo para obter chuva (mm) e temperatura atuais."""
    weather_endpoint = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,precipitation,weather_code&timezone=America%2FSao_Paulo"
    )
    try:
        with httpx.Client(timeout=timeout_seconds) as http_client:
            response = http_client.get(weather_endpoint)
            response.raise_for_status()
            current_data = response.json().get("current", {})

            precipitation_mm = float(current_data.get("precipitation", 0.0))
            temperature_celsius = float(current_data.get("temperature_2m", 23.5))
            weather_code = int(current_data.get("weather_code", 0))

            weather_summary = _translate_wmo_weather_code(weather_code, precipitation_mm)
            return precipitation_mm, temperature_celsius, weather_summary, True
    except (httpx.HTTPError, ValueError, KeyError) as weather_error:
        logger.warning(
            "Falha ao consultar Open-Meteo (%s). Utilizando telemetria climática de contingência.",
            weather_error,
        )
        return 4.2, 22.8, "Instabilidade moderada com pancadas isoladas (Contingência)", False


def _translate_wmo_weather_code(weather_code: int, precipitation_mm: float) -> str:
    """Traduz o código meteorológico WMO da Open-Meteo para linguagem clara ao cidadão."""
    if precipitation_mm >= 10.0 or weather_code in {65, 82, 95, 96, 99}:
        return "Chuva forte / Tempestade com risco de alagamento"
    if precipitation_mm > 0.5 or weather_code in {51, 53, 55, 61, 63, 80, 81}:
        return "Chuva leve a moderada na região"
    if weather_code in {1, 2, 3, 45, 48}:
        return "Céu parcialmente nublado sem chuva severa"
    return "Tempo firme e estável no momento"


def fetch_geolocation_and_weather_context(
    postal_code: str, timeout_seconds: float = 4.5
) -> GeolocationAndWeatherContext:
    """Combina dados territoriais (ViaCEP) e climáticos (Open-Meteo) para enriquecer a triagem."""
    _, _, latitude, longitude = _resolve_regional_fallback_by_cep(postal_code)

    street_name, neighborhood, city_name, state_code, viacep_online = _fetch_address_from_viacep(
        postal_code=postal_code,
        timeout_seconds=timeout_seconds,
    )
    precipitation_mm, temperature_celsius, weather_summary, meteo_online = (
        _fetch_weather_from_open_meteo(
            latitude=latitude,
            longitude=longitude,
            timeout_seconds=timeout_seconds,
        )
    )

    is_rain_alert_active = precipitation_mm >= 2.0 or "Chuva" in weather_summary
    if viacep_online and meteo_online:
        source_label = "ViaCEP + Open-Meteo API (Tempo Real)"
    elif viacep_online or meteo_online:
        source_label = "Híbrido (API Pública + Contingência Regional)"
    else:
        source_label = "Base Territorial e Climática Local (Modo Offline Resiliente)"

    return GeolocationAndWeatherContext(
        postal_code=postal_code,
        street_name=street_name,
        neighborhood=neighborhood,
        city_name=city_name,
        state_code=state_code,
        current_precipitation_mm=round(precipitation_mm, 1),
        current_temperature_celsius=round(temperature_celsius, 1),
        weather_condition_summary=weather_summary,
        is_rain_alert_active=is_rain_alert_active,
        data_source_label=source_label,
    )
