"""Componentes visuais reutilizáveis com semântica de cores e rótulos textuais acessíveis."""

import re
from typing import Any, Dict

import streamlit as st

from frontend.state.session_manager import get_category_metadata_catalog
from frontend.ui.accessibility import render_text_to_speech_audio_player

URGENCY_SEMANTIC_SPEC = {
    "CRITICA": {
        "tag": "[PRIORIDADE CRÍTICA]",
        "title": "Risco Imediato à Segurança",
        "bg_color": "#FEF2F2",
        "border_color": "#DC2626",
        "text_color": "#991B1B",
        "sla_label": "Atendimento imediato (até 4 horas)",
    },
    "ALTA": {
        "tag": "[PRIORIDADE ALTA]",
        "title": "Intervenção Prioritária",
        "bg_color": "#FFFBEB",
        "border_color": "#D97706",
        "text_color": "#92400E",
        "sla_label": "Vistoria prioritária (até 12 horas)",
    },
    "MEDIA": {
        "tag": "[PRIORIDADE MÉDIA]",
        "title": "Manutenção Programada",
        "bg_color": "#EFF6FF",
        "border_color": "#2563EB",
        "text_color": "#1E40AF",
        "sla_label": "Programação técnica (até 48 horas)",
    },
    "BAIXA": {
        "tag": "[PRIORIDADE BAIXA]",
        "title": "Zeladoria Preventiva",
        "bg_color": "#F0FDF4",
        "border_color": "#16A34A",
        "text_color": "#166534",
        "sla_label": "Cronograma regular (até 120 horas)",
    },
}


def render_semantic_urgency_badge(
    urgency_level: str,
    custom_subtitle: str = "",
    compact: bool = False,
) -> None:
    """Componente reutilizável que exibe criticidade unindo cor de alto contraste e rótulo explícito."""
    spec = URGENCY_SEMANTIC_SPEC.get(urgency_level.upper(), URGENCY_SEMANTIC_SPEC["MEDIA"])
    subtitle_text = custom_subtitle or spec["sla_label"]
    padding_style = "0.55rem 0.85rem" if compact else "0.9rem 1.15rem"

    badge_html = f"""
    <div role="status" aria-label="{spec['tag']} {spec['title']}" style="
        background-color: {spec['bg_color']};
        border-left: 6px solid {spec['border_color']};
        border-top: 1px solid {spec['border_color']};
        border-right: 1px solid {spec['border_color']};
        border-bottom: 1px solid {spec['border_color']};
        border-radius: 8px;
        padding: {padding_style};
        margin-bottom: 0.75rem;
        color: {spec['text_color']};
    ">
        <div style="font-weight: 800; font-size: 0.98rem; letter-spacing: 0.3px;">
            {spec['tag']} — {spec['title']}
        </div>
        <div style="font-size: 0.88rem; margin-top: 0.2rem; font-weight: 600;">
            Prazo de referência: {subtitle_text}
        </div>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)


VULNERABILITY_LABELS = {
    "NENHUMA_ESPECIFICA": "Circulação geral de moradores e pedestres",
    "PESSOA_COM_DEFICIENCIA_OU_IDOSO": "Pessoas com deficiência, cadeirantes ou idosos",
    "ENTORNO_ESCOLAR_OU_SAUDE": "Alunos de escola/creche ou pacientes de unidade de saúde próxima",
    "AREA_DE_ENCOSTA_OU_MARGEM_CORREGO": "Moradores próximos a encosta, barranco ou margem de córrego",
}


def render_occurrence_summary_card(
    occurrence: Dict[str, Any],
    context_origin: str = "Portal do Cidadão",
    show_technical_metrics: bool = False,
) -> None:
    """Componente reutilizável para exibir um cartão resumido de protocolo em diferentes telas."""
    catalog = get_category_metadata_catalog()
    category_key = occurrence.get("category", "SANEAMENTO_E_RESIDUOS")
    cat_meta = catalog.get(
        category_key,
        {"label": category_key, "tag": "[OCORRÊNCIA]", "department": "Central 156", "ods": "Zeladoria"},
    )

    status_raw = occurrence.get("status", "CONFIRMADO_PELO_CIDADAO")
    if status_raw == "AUDITADO_E_DESPACHADO_PELO_GESTOR":
        status_badge = "Situação: Equipe Acionada pela Gestão Municipal"
    else:
        status_badge = "Situação: Registrado pelo Cidadão"

    reference_text = (occurrence.get("reference_location") or "").strip()
    reference_suffix = f" · Referência: {reference_text}" if reference_text else ""
    vulnerability_key = occurrence.get("vulnerability", "NENHUMA_ESPECIFICA")
    vulnerability_label = VULNERABILITY_LABELS.get(vulnerability_key, vulnerability_key)

    with st.container(border=True):
        if show_technical_metrics:
            top_col1, top_col2 = st.columns([2.2, 1.3])
            with top_col1:
                st.markdown(
                    f"**{cat_meta['tag']} {cat_meta['label']}** · "
                    f"Protocolo: `{occurrence.get('protocol_number', 'N/A')}`"
                )
                st.caption(
                    f"Bairro: **{occurrence.get('neighborhood', 'SP')}** "
                    f"(CEP {occurrence.get('postal_code', '00000-000')}){reference_suffix} · "
                    f"Data: {occurrence.get('created_at', 'Recente')} · {status_badge}"
                )
            with top_col2:
                render_semantic_urgency_badge(
                    urgency_level=occurrence.get("urgency", "MEDIA"),
                    custom_subtitle=(
                        f"Índice de Gravidade: {occurrence.get('technical_risk_score', 50.0)}/100 | "
                        f"Chuva: {occurrence.get('precipitation_mm', 0.0)} mm"
                    ),
                    compact=True,
                )
        else:
            st.markdown(
                f"**Protocolo `{occurrence.get('protocol_number', 'N/A')}`** — {cat_meta['label']}"
            )
            st.caption(
                f"Local: **{occurrence.get('neighborhood', 'SP')}** "
                f"(CEP {occurrence.get('postal_code', '00000-000')}){reference_suffix} · "
                f"Registrado em: {occurrence.get('created_at', 'Recente')} · {status_badge}"
            )

        st.write(f"**Relato descrito:** {occurrence.get('description', '')}")
        st.caption(
            f"**Pessoas afetadas no entorno:** {vulnerability_label} | "
            f"**Setor encaminhado:** {occurrence.get('department', cat_meta['department'])}"
        )
        if st.session_state.get("large_font_mode", False):
            proto_id = re.sub(r"[^a-zA-Z0-9_]", "_", str(occurrence.get("protocol_number", "item")))
            card_speech = (
                f"Protocolo {occurrence.get('protocol_number', '')}, área de {cat_meta['label']}. "
                f"Local: bairro {occurrence.get('neighborhood', '')}, CEP {occurrence.get('postal_code', '')}. "
                f"Relato descrito: {occurrence.get('description', '')}. "
                f"Pessoas afetadas no entorno: {vulnerability_label}."
            )
            render_text_to_speech_audio_player(
                text_to_read=card_speech,
                element_id=f"card_tts_{proto_id}_{ 'mgr' if show_technical_metrics else 'cit' }",
                button_label="🔊 Ouvir Relato em Áudio",
            )


def render_friendly_error_banner(
    error_code: str,
    user_message: str,
    recovery_instructions: str,
) -> None:
    """Exibe estado de erro amigável e acessível sem expor termos técnicos ao cidadão."""
    error_html = f"""
    <div role="alert" style="
        background-color: #FEF2F2;
        border: 2px solid #DC2626;
        border-radius: 10px;
        padding: 1.1rem 1.25rem;
        margin: 0.85rem 0;
        color: #7F1D1D;
    ">
        <div style="font-weight: 800; font-size: 1.02rem;">
            [ATENÇÃO] Não foi possível concluir o envio da sua solicitação
        </div>
        <p style="margin: 0.45rem 0; font-weight: 500;">
            {user_message}
        </p>
        <div style="font-size: 0.9rem; background: #FEE2E2; padding: 0.55rem 0.75rem; border-radius: 6px;">
            <strong>Como proceder:</strong> {recovery_instructions}
        </div>
    </div>
    """
    st.markdown(error_html, unsafe_allow_html=True)


def render_empty_state_card(title: str, subtitle: str) -> None:
    """Exibe estado vazio claro e orientativo quando filtros ou listas não possuem itens."""
    empty_html = f"""
    <div style="
        text-align: center;
        padding: 2rem 1.5rem;
        border: 2px dashed #94A3B8;
        border-radius: 10px;
        margin: 1rem 0;
    ">
        <div style="font-weight: 700; font-size: 1.08rem;">{title}</div>
        <p style="font-size: 0.95rem; opacity: 0.85; margin-top: 0.3rem;">{subtitle}</p>
    </div>
    """
    st.markdown(empty_html, unsafe_allow_html=True)
