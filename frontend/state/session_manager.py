"""Gerenciamento centralizado de st.session_state, @st.cache_data e @st.cache_resource."""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


@st.cache_data(ttl=3600, show_spinner=False)
def get_category_metadata_catalog() -> Dict[str, Dict[str, str]]:
    """Retorna o catálogo institucional de categorias e órgãos responsáveis (cacheado em memória)."""
    return {
        "DRENAGEM_E_ALAGAMENTO": {
            "label": "Drenagem e Alagamento",
            "tag": "[DRENAGEM]",
            "department": "Secretaria de Infraestrutura e Defesa Civil (199)",
            "ods": "Cidades Sustentáveis e Clima",
        },
        "ACESSIBILIDADE_E_CALCADAS": {
            "label": "Acessibilidade e Calçadas",
            "tag": "[ACESSIBILIDADE]",
            "department": "Secretaria da Pessoa com Deficiência e Subprefeitura",
            "ods": "Inclusão e Mobilidade Urbana",
        },
        "RISCO_ESTRUTURAL_E_ARVORES": {
            "label": "Risco Estrutural e Queda de Árvores",
            "tag": "[DEFESA CIVIL]",
            "department": "Defesa Civil Municipal e Manejo Arbóreo",
            "ods": "Prevenção de Desastres",
        },
        "ILUMINACAO_E_SEGURANCA_VIARIA": {
            "label": "Iluminação e Segurança da Via",
            "tag": "[ILUMINAÇÃO]",
            "department": "Departamento de Iluminação Pública e Trânsito",
            "ods": "Segurança Viária",
        },
        "SANEAMENTO_E_RESIDUOS": {
            "label": "Limpeza Urbana e Saneamento",
            "tag": "[ZELADORIA]",
            "department": "Autoridade Municipal de Limpeza Urbana e Vigilância",
            "ods": "Saúde e Saneamento",
        },
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_initial_seed_occurrences() -> List[Dict[str, Any]]:
    """Carrega base histórica inicial realista para alimentar gráficos e fila da gestão."""
    return [
        {
            "protocol_number": "ZC-2026-8F91A2",
            "created_at": "08/11/2026 09:15",
            "neighborhood": "Bela Vista",
            "postal_code": "01310-100",
            "category": "DRENAGEM_E_ALAGAMENTO",
            "category_label": "Drenagem e Alagamento",
            "urgency": "CRITICA",
            "technical_risk_score": 91.5,
            "precipitation_mm": 18.4,
            "vulnerability": "ENTORNO_ESCOLAR_OU_SAUDE",
            "status": "CONFIRMADO_PELO_CIDADAO",
            "was_ai_helpful": True,
            "description": "Bocas de lobo obstruídas gerando acúmulo rápido de água na saída da escola estadual.",
            "department": "Secretaria de Infraestrutura e Defesa Civil (199)",
        },
        {
            "protocol_number": "ZC-2026-3C44B1",
            "created_at": "08/11/2026 11:40",
            "neighborhood": "Vila Mariana",
            "postal_code": "04011-000",
            "category": "ACESSIBILIDADE_E_CALCADAS",
            "category_label": "Acessibilidade e Calçadas",
            "urgency": "ALTA",
            "technical_risk_score": 76.2,
            "precipitation_mm": 1.2,
            "vulnerability": "PESSOA_COM_DEFICIENCIA_OU_IDOSO",
            "status": "AUDITADO_E_DESPACHADO_PELO_GESTOR",
            "was_ai_helpful": True,
            "description": "Rampa de acessibilidade danificada e piso tátil solto em frente ao centro de reabilitação.",
            "department": "Secretaria da Pessoa com Deficiência e Subprefeitura",
        },
        {
            "protocol_number": "ZC-2026-7D20E9",
            "created_at": "08/11/2026 14:20",
            "neighborhood": "Tatuapé",
            "postal_code": "03064-000",
            "category": "RISCO_ESTRUTURAL_E_ARVORES",
            "category_label": "Risco Estrutural e Queda de Árvores",
            "urgency": "CRITICA",
            "technical_risk_score": 88.9,
            "precipitation_mm": 14.0,
            "vulnerability": "ENTORNO_ESCOLAR_OU_SAUDE",
            "status": "CONFIRMADO_PELO_CIDADAO",
            "was_ai_helpful": True,
            "description": "Árvore de grande porte inclinada sobre a rede elétrica após fortes ventos.",
            "department": "Defesa Civil Municipal e Manejo Arbóreo",
        },
        {
            "protocol_number": "ZC-2026-1A55F0",
            "created_at": "08/11/2026 16:05",
            "neighborhood": "Pinheiros",
            "postal_code": "05409-000",
            "category": "ILUMINACAO_E_SEGURANCA_VIARIA",
            "category_label": "Iluminação e Segurança da Via",
            "urgency": "MEDIA",
            "technical_risk_score": 52.0,
            "precipitation_mm": 0.0,
            "vulnerability": "NENHUMA_ESPECIFICA",
            "status": "CONFIRMADO_PELO_CIDADAO",
            "was_ai_helpful": True,
            "description": "Quatro postes consecutivos apagados próximo à parada de ônibus no período noturno.",
            "department": "Departamento de Iluminação Pública e Trânsito",
        },
        {
            "protocol_number": "ZC-2026-9E12C4",
            "created_at": "08/11/2026 18:30",
            "neighborhood": "Itaquera",
            "postal_code": "08210-000",
            "category": "DRENAGEM_E_ALAGAMENTO",
            "category_label": "Drenagem e Alagamento",
            "urgency": "CRITICA",
            "technical_risk_score": 94.8,
            "precipitation_mm": 24.5,
            "vulnerability": "AREA_DE_ENCOSTA_OU_MARGEM_CORREGO",
            "status": "AUDITADO_E_DESPACHADO_PELO_GESTOR",
            "was_ai_helpful": True,
            "description": "Elevação do nível do córrego com risco de erosão na margem próxima às residências.",
            "department": "Secretaria de Infraestrutura e Defesa Civil (199)",
        },
        {
            "protocol_number": "ZC-2026-5B78D3",
            "created_at": "09/11/2026 08:10",
            "neighborhood": "Santana",
            "postal_code": "02011-000",
            "category": "SANEAMENTO_E_RESIDUOS",
            "category_label": "Limpeza Urbana e Saneamento",
            "urgency": "BAIXA",
            "technical_risk_score": 29.4,
            "precipitation_mm": 0.0,
            "vulnerability": "NENHUMA_ESPECIFICA",
            "status": "CONFIRMADO_PELO_CIDADAO",
            "was_ai_helpful": True,
            "description": "Acúmulo de entulho descartado irregularmente na calçada lateral da praça.",
            "department": "Autoridade Municipal de Limpeza Urbana e Vigilância",
        },
        {
            "protocol_number": "ZC-2026-6F33A8",
            "created_at": "09/11/2026 09:45",
            "neighborhood": "Vila Mariana",
            "postal_code": "04012-010",
            "category": "ACESSIBILIDADE_E_CALCADAS",
            "category_label": "Acessibilidade e Calçadas",
            "urgency": "ALTA",
            "technical_risk_score": 73.5,
            "precipitation_mm": 3.2,
            "vulnerability": "PESSOA_COM_DEFICIENCIA_OU_IDOSO",
            "status": "CONFIRMADO_PELO_CIDADAO",
            "was_ai_helpful": True,
            "description": "Degrau irregular de 18cm sem rampa na faixa de travessia em frente à clínica.",
            "department": "Secretaria da Pessoa com Deficiência e Subprefeitura",
        },
    ]


def initialize_application_session_state() -> None:
    """Inicializa todas as chaves necessárias no st.session_state caso ainda não existam."""
    if "occurrence_history" not in st.session_state:
        st.session_state["occurrence_history"] = list(get_initial_seed_occurrences())

    if "pending_triage_result" not in st.session_state:
        st.session_state["pending_triage_result"] = None

    if "last_confirmed_protocol" not in st.session_state:
        st.session_state["last_confirmed_protocol"] = None

    if "high_contrast_mode" not in st.session_state:
        st.session_state["high_contrast_mode"] = False

    if "large_font_mode" not in st.session_state:
        st.session_state["large_font_mode"] = False

    if "accessibility_onboarding_completed" not in st.session_state:
        st.session_state["accessibility_onboarding_completed"] = False

    if "active_user_role" not in st.session_state:
        st.session_state["active_user_role"] = "CIDADAO"

    if "simulate_failure_mode" not in st.session_state:
        st.session_state["simulate_failure_mode"] = "NONE"


def add_confirmed_occurrence_to_history(record: Dict[str, Any]) -> None:
    """Insere uma nova ocorrência validada no topo do histórico persistido na sessão."""
    initialize_application_session_state()
    st.session_state["occurrence_history"].insert(0, record)


def update_occurrence_status_in_history(
    protocol_number: str,
    new_status: str,
    new_urgency: Optional[str] = None,
    manager_note: Optional[str] = None,
) -> None:
    """Atualiza o status ou urgência de um protocolo após revisão da gestão municipal."""
    initialize_application_session_state()
    for item in st.session_state["occurrence_history"]:
        if item["protocol_number"] == protocol_number:
            item["status"] = new_status
            if new_urgency:
                item["urgency"] = new_urgency
            if manager_note:
                item["manager_note"] = manager_note
            break


@st.cache_data(show_spinner=False)
def convert_history_to_dataframe(history_records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Converte a lista de registros do histórico em DataFrame pandas (cacheado por conteúdo)."""
    if not history_records:
        return pd.DataFrame()
    return pd.DataFrame(history_records)
