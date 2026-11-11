"""Configurações centralizadas e carregamento seguro de variáveis de ambiente."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

PROJECT_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=PROJECT_ROOT_DIRECTORY / ".env", override=False)


def _parse_allowed_cors_origins(raw_origins_value: str) -> List[str]:
    """Converte a string de origens permitidas em lista, bloqueando curingas inseguros."""
    default_safe_origins = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://frontend:8501",
    ]
    if not raw_origins_value or not raw_origins_value.strip():
        return default_safe_origins

    parsed_origins = [
        origin.strip()
        for origin in raw_origins_value.split(",")
        if origin.strip() and origin.strip() != "*"
    ]
    return parsed_origins if parsed_origins else default_safe_origins


@dataclass(frozen=True)
class ApplicationSettings:
    """Representa as configurações imutáveis de execução do servidor FastAPI."""

    application_title: str = "ZelaAI — API de Triagem Urbana e Resiliência Climática"
    application_version: str = "1.0.0"
    gemini_api_key: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip()
    )
    gemini_model_name: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip()
    )
    allowed_cors_origins: List[str] = field(
        default_factory=lambda: _parse_allowed_cors_origins(
            os.getenv("BACKEND_CORS_ORIGINS", "")
        )
    )
    external_api_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("EXTERNAL_API_TIMEOUT_SECONDS", "12.0"))
    )

    @property
    def has_configured_llm_api_key(self) -> bool:
        """Verifica se uma chave real do provedor de IA foi configurada no ambiente."""
        placeholder_values = {"", "coloque_sua_chave_gemini_aqui", "sua_chave_aqui"}
        return self.gemini_api_key not in placeholder_values and len(self.gemini_api_key) > 10


def get_application_settings() -> ApplicationSettings:
    """Retorna a instância de configurações carregada a partir do ambiente."""
    return ApplicationSettings()
