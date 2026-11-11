"""Painel de Monitoramento da Cidade: gráficos interativos e filtros de ocorrências."""

from typing import List

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st

from frontend.state.session_manager import convert_history_to_dataframe
from frontend.ui.components import (
    render_empty_state_card,
    render_semantic_urgency_badge,
)

URGENCY_COLOR_PALETTE = {
    "CRITICA": "#DC2626",
    "ALTA": "#D97706",
    "MEDIA": "#2563EB",
    "BAIXA": "#16A34A",
}


def _apply_interactive_filters(
    dataframe: pd.DataFrame,
    selected_urgencies: List[str],
    selected_categories: List[str],
    minimum_risk_score: float,
    only_rain_events: bool,
) -> pd.DataFrame:
    """Filtra o DataFrame de ocorrências conforme os controles selecionados."""
    filtered = dataframe.copy()
    if selected_urgencies:
        filtered = filtered[filtered["urgency"].isin(selected_urgencies)]
    else:
        return filtered.iloc[0:0]

    if selected_categories:
        filtered = filtered[filtered["category_label"].isin(selected_categories)]
    else:
        return filtered.iloc[0:0]

    filtered = filtered[filtered["technical_risk_score"] >= minimum_risk_score]
    if only_rain_events:
        filtered = filtered[filtered["precipitation_mm"] > 0.0]

    return filtered


def _render_plotly_category_and_urgency_chart(filtered_df: pd.DataFrame) -> None:
    """Renderiza gráfico interativo de ocorrências por área de atendimento e prioridade."""
    grouped = (
        filtered_df.groupby(["category_label", "urgency"], as_index=False)
        .size()
        .rename(columns={"size": "quantidade"})
    )

    figure = px.bar(
        grouped,
        x="category_label",
        y="quantidade",
        color="urgency",
        barmode="group",
        color_discrete_map=URGENCY_COLOR_PALETTE,
        category_orders={"urgency": ["CRITICA", "ALTA", "MEDIA", "BAIXA"]},
        labels={
            "category_label": "Área de Atendimento Urbano",
            "quantidade": "Total de Solicitações",
            "urgency": "Prioridade",
        },
        title="Distribuição de Solicitações por Área e Prioridade",
        text_auto=True,
    )
    figure.update_layout(
        xaxis_title="Área de Atendimento",
        yaxis_title="Número de Protocolos",
        legend_title_text="Prioridade",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=55, b=20),
    )
    st.plotly_chart(figure, use_container_width=True)


def _render_plotly_climate_vs_risk_scatter(filtered_df: pd.DataFrame) -> None:
    """Renderiza gráfico interativo cruzando volume de chuva, gravidade e bairro."""
    figure = px.scatter(
        filtered_df,
        x="precipitation_mm",
        y="technical_risk_score",
        color="urgency",
        size="technical_risk_score",
        hover_name="neighborhood",
        hover_data={
            "protocol_number": True,
            "category_label": True,
            "precipitation_mm": ":.1f",
            "technical_risk_score": ":.1f",
            "department": True,
        },
        color_discrete_map=URGENCY_COLOR_PALETTE,
        labels={
            "precipitation_mm": "Volume de Chuva no Local (mm)",
            "technical_risk_score": "Índice de Gravidade no Local (0 a 100)",
            "urgency": "Prioridade",
        },
        title="Relação entre Volume de Chuva (mm) e Gravidade da Ocorrência por Bairro",
    )
    figure.update_layout(
        margin=dict(l=20, r=20, t=55, b=20),
        yaxis_range=[0, 105],
    )
    st.plotly_chart(figure, use_container_width=True)


def _render_complementary_matplotlib_neighborhood_chart(filtered_df: pd.DataFrame) -> None:
    """Renderiza gráfico complementar de média de gravidade por bairro."""
    with st.expander("Visualização Detalhada: Média de Gravidade por Bairro", expanded=False):
        neighborhood_avg = (
            filtered_df.groupby("neighborhood")["technical_risk_score"]
            .mean()
            .sort_values(ascending=True)
        )
        fig, ax = plt.subplots(figsize=(8, 3.2))
        bars = ax.barh(
            neighborhood_avg.index,
            neighborhood_avg.values,
            color="#2563EB",
            edgecolor="#1E3A8A",
        )
        ax.set_xlabel("Índice Médio de Gravidade (0 - 100)")
        ax.set_title("Média de Gravidade das Ocorrências por Bairro")
        ax.set_xlim(0, 105)
        ax.grid(axis="x", linestyle="--", alpha=0.5)
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + 1.5,
                bar.get_y() + bar.get_height() / 2,
                f"{width:.1f}",
                va="center",
                fontsize=9,
                fontweight="bold",
            )
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)


def render_analytics_dashboard_feature() -> None:
    """Renderiza a tela de monitoramento urbano com filtros e gráficos interativos."""
    st.markdown("### Painel de Monitoramento Urbano e Condições Climáticas")
    st.write(
        "Acompanhe em tempo real os indicadores das solicitações registradas pelos moradores. "
        "Utilize os filtros abaixo para consultar ocorrências por prioridade, área de atendimento, "
        "gravidade e presença de chuva."
    )

    history_records = st.session_state.get("occurrence_history", [])
    dataframe = convert_history_to_dataframe(history_records)
    if dataframe.empty:
        render_empty_state_card(
            title="Sem registros para exibir no momento",
            subtitle="Registre uma solicitação na aba '1. Portal do Cidadão' para alimentar o painel.",
        )
        return

    all_category_labels = sorted(dataframe["category_label"].unique().tolist())
    all_urgencies = ["CRITICA", "ALTA", "MEDIA", "BAIXA"]

    with st.container(border=True):
        st.markdown("#### Filtros de Consulta")
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.3, 1.5, 1.1, 0.9])
        with filter_col1:
            selected_urgencies = st.multiselect(
                "1. Filtrar por Prioridade:",
                options=all_urgencies,
                default=all_urgencies,
                key="dash_filter_urgency",
            )
        with filter_col2:
            selected_categories = st.multiselect(
                "2. Filtrar por Área de Atendimento:",
                options=all_category_labels,
                default=all_category_labels,
                key="dash_filter_category",
            )
        with filter_col3:
            min_risk_score = st.slider(
                "3. Índice Mínimo de Gravidade:",
                min_value=0.0,
                max_value=95.0,
                value=0.0,
                step=5.0,
                key="dash_filter_score",
            )
        with filter_col4:
            st.markdown("<br>", unsafe_allow_html=True)
            only_rain_flag = st.checkbox(
                "Apenas locais com chuva",
                value=False,
                key="dash_filter_rain",
            )

    filtered_df = _apply_interactive_filters(
        dataframe=dataframe,
        selected_urgencies=selected_urgencies,
        selected_categories=selected_categories,
        minimum_risk_score=min_risk_score,
        only_rain_events=only_rain_flag,
    )

    if filtered_df.empty:
        render_empty_state_card(
            title="Nenhuma ocorrência corresponde aos filtros selecionados",
            subtitle="Reduza o Índice Mínimo de Gravidade ou selecione mais áreas e prioridades acima.",
        )
        return

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    critical_count = int((filtered_df["urgency"] == "CRITICA").sum())
    avg_risk = float(filtered_df["technical_risk_score"].mean())
    avg_rain = float(filtered_df["precipitation_mm"].mean())
    approval_rate = float(filtered_df["was_ai_helpful"].mean() * 100.0)

    with kpi_col1:
        st.metric("Total de Protocolos Exibidos", f"{len(filtered_df)}")
    with kpi_col2:
        st.metric("Ocorrências de Prioridade Crítica", f"{critical_count}")
    with kpi_col3:
        st.metric("Gravidade Média no Recorte", f"{avg_risk:.1f}/100")
    with kpi_col4:
        st.metric(
            "Satisfação com as Orientações",
            f"{approval_rate:.0f}%",
            delta=f"Chuva média: {avg_rain:.1f} mm",
        )

    highest_urgency_present = (
        "CRITICA"
        if critical_count > 0
        else ("ALTA" if (filtered_df["urgency"] == "ALTA").any() else "MEDIA")
    )
    render_semantic_urgency_badge(
        urgency_level=highest_urgency_present,
        custom_subtitle=(
            f"Maior nível de prioridade presente no grupo filtrado ({len(filtered_df)} ocorrências)"
        ),
        compact=True,
    )

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        _render_plotly_category_and_urgency_chart(filtered_df)
    with chart_col2:
        _render_plotly_climate_vs_risk_scatter(filtered_df)

    _render_complementary_matplotlib_neighborhood_chart(filtered_df)
