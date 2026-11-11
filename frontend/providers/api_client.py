"""Cliente HTTP resiliente para consumo dos endpoints do back-end."""

import os
from typing import Any, Dict, Tuple

from dotenv import load_dotenv
import httpx
import streamlit as st

load_dotenv(override=False)


@st.cache_resource(show_spinner=False)
def get_backend_api_configuration() -> Dict[str, Any]:
    """Retorna a configuração de conexão HTTP cacheada como recurso compartilhado."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    timeout_seconds = float(os.getenv("EXTERNAL_API_TIMEOUT_SECONDS", "12.0"))
    return {
        "base_url": base_url,
        "timeout_seconds": timeout_seconds,
    }


@st.cache_data(ttl=15, show_spinner=False)
def _fetch_cached_backend_health(base_url: str) -> Tuple[bool, Dict[str, Any]]:
    """Executa consulta HTTP de saúde com cache de 15s para evitar chamadas repetidas a cada rerun."""
    try:
        with httpx.Client(timeout=3.5) as client:
            response = client.get(f"{base_url}/api/v1/health")
            response.raise_for_status()
            return True, response.json()
    except httpx.HTTPError:
        return False, {
            "error_code": "API_OFFLINE",
            "user_message": (
                "Não foi possível conectar à central de atendimento neste momento. "
                "Verifique se o serviço principal foi iniciado."
            ),
        }


def check_backend_health_status(simulate_offline: bool = False) -> Tuple[bool, Dict[str, Any]]:
    """Consulta o endpoint de saúde para verificar conectividade com o servidor."""
    if simulate_offline:
        return False, {
            "error_code": "SIMULATED_OFFLINE",
            "user_message": "Simulação de servidor fora do ar ativada no menu lateral.",
        }

    config = get_backend_api_configuration()
    return _fetch_cached_backend_health(config["base_url"])


def send_citizen_report_for_triage(
    report_payload: Dict[str, Any],
    simulate_offline: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    """Envia o relato validado para análise e trata falhas de comunicação."""
    if simulate_offline:
        return False, {
            "error_code": "SERVIDOR_INDISPONIVEL",
            "user_message": (
                "A conexão com a central de atendimento está indisponível no momento. "
                "As informações que você digitou foram mantidas na tela para uma nova tentativa."
            ),
        }

    config = get_backend_api_configuration()
    endpoint = f"{config['base_url']}/api/v1/occurrences/triage"

    try:
        with httpx.Client(timeout=config["timeout_seconds"]) as client:
            response = client.post(endpoint, json=report_payload)
            if response.status_code == 200:
                return True, response.json()

            error_body = response.json().get("detail", {})
            if isinstance(error_body, dict):
                return False, {
                    "error_code": error_body.get("error_code", f"STATUS_{response.status_code}"),
                    "user_message": error_body.get(
                        "user_message",
                        "O sistema não pôde concluir a análise da sua solicitação neste momento.",
                    ),
                    "fields": error_body.get("fields", []),
                }
            return False, {
                "error_code": f"STATUS_{response.status_code}",
                "user_message": "Recebemos uma resposta inesperada do servidor de atendimento.",
            }
    except httpx.TimeoutException:
        return False, {
            "error_code": "TEMPO_ESGOTADO",
            "user_message": (
                "O tempo de espera pela avaliação foi excedido. "
                "Por favor, tente enviar novamente em alguns instantes."
            ),
        }
    except httpx.RequestError:
        return False, {
            "error_code": "FALHA_CONEXAO",
            "user_message": (
                "O servidor de atendimento não respondeu. "
                "Em caso de emergência imediata, ligue 199 (Defesa Civil) ou 156."
            ),
        }
    except ValueError:
        return False, {
            "error_code": "FORMATO_INVALIDO",
            "user_message": "O servidor retornou dados em um formato inesperado.",
        }


def send_human_confirmation_to_backend(
    confirmation_payload: Dict[str, Any],
) -> Tuple[bool, Dict[str, Any]]:
    """Envia a confirmação ou revisão do cidadão/gestor para emissão do protocolo oficial."""
    config = get_backend_api_configuration()
    endpoint = f"{config['base_url']}/api/v1/occurrences/confirm"

    try:
        with httpx.Client(timeout=config["timeout_seconds"]) as client:
            response = client.post(endpoint, json=confirmation_payload)
            response.raise_for_status()
            return True, response.json()
    except httpx.HTTPError:
        return False, {
            "error_code": "FALHA_CONFIRMACAO",
            "user_message": (
                "Não foi possível sincronizar a confirmação com o servidor agora. "
                "Tente confirmar novamente."
            ),
        }
