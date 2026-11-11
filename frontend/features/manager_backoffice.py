"""Visão da Gestão Municipal: revisão de protocolos e despacho de equipes de atendimento."""

import streamlit as st

from frontend.providers.api_client import send_human_confirmation_to_backend
from frontend.state.session_manager import update_occurrence_status_in_history
from frontend.ui.components import (
    render_empty_state_card,
    render_occurrence_summary_card,
    render_semantic_urgency_badge,
)


def render_manager_backoffice_feature() -> None:
    """Renderiza a central de despacho da Gestão Municipal."""
    st.markdown("### Central da Gestão Municipal e Defesa Civil")
    st.write(
        "Área destinada aos gestores municipais para conferência das solicitações registradas, "
        "revisão de prioridade e acionamento das equipes de vistoria em campo."
    )

    active_role = st.session_state.get("active_user_role", "CIDADAO")
    if active_role != "GESTOR_PUBLICO":
        st.warning(
            "Modo de Acesso do Cidadão Ativo: Para revisar protocolos e acionar equipes "
            "como Gestor Municipal, altere o 'Perfil de Acesso' na barra lateral esquerda "
            "ou utilize o botão abaixo."
        )
        if st.button("Alternar para Perfil de Gestor Municipal", type="primary"):
            st.session_state["active_user_role"] = "GESTOR_PUBLICO"
            st.rerun()
        return

    history_records = st.session_state.get("occurrence_history", [])
    if not history_records:
        render_empty_state_card(
            title="Fila de atendimento vazia",
            subtitle="Não há protocolos registrados na sessão atual.",
        )
        return

    pending_dispatch_count = sum(
        1 for item in history_records if item.get("status") != "AUDITADO_E_DESPACHADO_PELO_GESTOR"
    )
    dispatched_count = sum(
        1 for item in history_records if item.get("status") == "AUDITADO_E_DESPACHADO_PELO_GESTOR"
    )
    critical_queue_count = sum(
        1 for item in history_records if item.get("urgency") == "CRITICA"
    )

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        st.metric("Total na Fila Municipal", f"{len(history_records)}")
    with kpi_col2:
        st.metric("Aguardando Despacho", f"{pending_dispatch_count}")
    with kpi_col3:
        st.metric("Equipes Já Acionadas", f"{dispatched_count}")
    with kpi_col4:
        st.metric("Prioridade Crítica", f"{critical_queue_count}")

    protocol_options = [item["protocol_number"] for item in history_records]

    with st.container(border=True):
        st.markdown("#### Revisar Solicitação e Acionar Equipe de Campo")
        selected_protocol = st.selectbox(
            "Selecione o Protocolo para Revisão:",
            options=protocol_options,
            format_func=lambda proto: next(
                (
                    f"{p['protocol_number']} — [{p['urgency']}] {p['category_label']} ({p['neighborhood']})"
                    for p in history_records
                    if p["protocol_number"] == proto
                ),
                proto,
            ),
            key="manager_selected_proto",
        )

        selected_record = next(
            (p for p in history_records if p["protocol_number"] == selected_protocol),
            history_records[0],
        )

        render_semantic_urgency_badge(
            urgency_level=selected_record["urgency"],
            custom_subtitle=(
                f"Bairro: {selected_record['neighborhood']} | "
                f"Índice de Gravidade: {selected_record['technical_risk_score']}/100"
            ),
            compact=True,
        )

        m_col1, m_col2 = st.columns(2)
        urgency_list = ["BAIXA", "MEDIA", "ALTA", "CRITICA"]
        current_urg_idx = (
            urgency_list.index(selected_record["urgency"])
            if selected_record["urgency"] in urgency_list
            else 2
        )
        with m_col1:
            new_urgency = st.selectbox(
                "Confirmar ou Alterar Prioridade de Atendimento:",
                options=urgency_list,
                index=current_urg_idx,
                key="manager_new_urgency",
            )
        with m_col2:
            dispatch_note = st.text_input(
                "Instrução para a Equipe de Campo:",
                value="Equipe regional acionada para vistoria prioritária no endereço.",
                key="manager_dispatch_note",
            )

        if st.button(
            "Aprovar Encaminhamento e Acionar Equipe",
            type="primary",
            use_container_width=True,
        ):
            payload = {
                "draft_protocol_number": selected_record["protocol_number"],
                "confirmed_category": selected_record["category"],
                "confirmed_urgency": new_urgency,
                "was_ai_helpful": True,
                "human_review_notes": dispatch_note,
                "reviewer_role": "GESTOR_PUBLICO",
            }
            send_human_confirmation_to_backend(payload)
            update_occurrence_status_in_history(
                protocol_number=selected_record["protocol_number"],
                new_status="AUDITADO_E_DESPACHADO_PELO_GESTOR",
                new_urgency=new_urgency,
                manager_note=dispatch_note,
            )
            st.success(
                f"Protocolo `{selected_record['protocol_number']}` aprovado e equipe acionada "
                f"com prioridade **{new_urgency}**."
            )
            st.rerun()

    st.markdown("---")
    st.markdown("#### Fila Geral de Solicitações Registradas")
    for record in history_records:
        render_occurrence_summary_card(
            record,
            context_origin="Central da Gestão Municipal",
            show_technical_metrics=True,
        )
