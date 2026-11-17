"""Ponto de entrada do Front-end Streamlit — ZelaAI (Global Solution 2026/2)."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.features.analytics_dashboard import render_analytics_dashboard_feature
from frontend.features.citizen_portal import render_citizen_portal_feature
from frontend.features.manager_backoffice import render_manager_backoffice_feature
from frontend.providers.api_client import check_backend_health_status
from frontend.state.session_manager import initialize_application_session_state
from frontend.ui.accessibility import (
    apply_accessibility_and_theme_styles,
    render_accessibility_onboarding_screen,
    render_platform_accessibility_header_bar,
)

FAILURE_SIMULATION_LABELS = {
    "NONE": "Funcionamento Normal",
    "TIMEOUT": "Simular Lentidão no Atendimento",
    "LLM_ERROR": "Simular Indisponibilidade de Análise",
    "API_OFFLINE": "Simular Servidor Fora do Ar",
}


def _render_sidebar_controls() -> None:
    """Renderiza a barra lateral exclusiva de desenvolvimento (perfil e demonstração de resiliência)."""
    with st.sidebar:
        st.markdown("## ZelaAI")
        st.caption("Painel de Controle de Simulação e Homologação")
        st.markdown("---")

        st.markdown("### Perfil de Acesso")
        previous_role = st.session_state["active_user_role"]
        selected_role = st.radio(
            "Selecione como deseja acessar:",
            options=["CIDADAO", "GESTOR_PUBLICO"],
            index=0 if previous_role == "CIDADAO" else 1,
            format_func=lambda r: (
                "Cidadão / Morador"
                if r == "CIDADAO"
                else "Gestor Municipal / Defesa Civil"
            ),
        )
        if selected_role != previous_role:
            st.session_state["active_user_role"] = selected_role
            st.rerun()

        st.markdown("---")
        st.markdown("### Demonstração de Resiliência")
        st.session_state["simulate_failure_mode"] = st.radio(
            "Condição de operação do sistema:",
            options=list(FAILURE_SIMULATION_LABELS.keys()),
            index=list(FAILURE_SIMULATION_LABELS.keys()).index(
                st.session_state["simulate_failure_mode"]
            ),
            format_func=lambda k: FAILURE_SIMULATION_LABELS[k],
            help="Permite demonstrar como a plataforma orienta o cidadão caso ocorram falhas de comunicação.",
        )

        st.markdown("---")
        simulate_offline = st.session_state["simulate_failure_mode"] == "API_OFFLINE"
        is_online, health_payload = check_backend_health_status(
            simulate_offline=simulate_offline
        )
        if is_online:
            llm_model = health_payload.get("llm_model", "gemini-2.5-flash")
            st.caption(f"Status da API: **Online** (`{llm_model}`)")
        else:
            st.caption("Status da API: **Indisponível / Simulação Offline**")


def main() -> None:
    """Configura a página, tela inicial de acessibilidade e visão de Cidadão ou Gestor."""
    st.set_page_config(
        page_title="ZelaAI — Atendimento Urbano e Defesa Civil",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_application_session_state()
    _render_sidebar_controls()
    apply_accessibility_and_theme_styles(
        high_contrast_enabled=st.session_state["high_contrast_mode"],
        large_font_enabled=st.session_state["large_font_mode"],
    )

    active_role = st.session_state.get("active_user_role", "CIDADAO")

    onboarding_container = st.container()
    citizen_workspace = st.container()
    manager_workspace = st.container()

    if not st.session_state.get("accessibility_onboarding_completed", False):
        with onboarding_container:
            render_accessibility_onboarding_screen(active_role=active_role)
        return

    if active_role == "CIDADAO":
        with citizen_workspace:
            render_platform_accessibility_header_bar()
            tab_citizen, tab_citizen_analytics = st.tabs(
                [
                    "1. Portal do Cidadão (Registrar Solicitação)",
                    "2. Painel de Monitoramento e Gráficos",
                ]
            )
            with tab_citizen:
                render_citizen_portal_feature()
            with tab_citizen_analytics:
                render_analytics_dashboard_feature()
    else:
        with manager_workspace:
            render_platform_accessibility_header_bar()
            tab_manager, tab_analytics = st.tabs(
                [
                    "1. Central do Gestor (Fila e Despacho)",
                    "2. Painel de Monitoramento e Gráficos",
                ]
            )
            with tab_manager:
                render_manager_backoffice_feature()
            with tab_analytics:
                render_analytics_dashboard_feature()


if __name__ == "__main__":
    main()
