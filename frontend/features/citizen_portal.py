"""Tela do Cidadão: relato livre estruturado, análise de prioridade e confirmação de protocolo."""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.providers.api_client import (
    send_citizen_report_for_triage,
    send_human_confirmation_to_backend,
)
from frontend.state.session_manager import (
    add_confirmed_occurrence_to_history,
    get_category_metadata_catalog,
)
from frontend.ui.accessibility import render_text_to_speech_audio_player
from frontend.ui.components import (
    render_empty_state_card,
    render_friendly_error_banner,
    render_occurrence_summary_card,
)

VULNERABILITY_OPTIONS_MAP = {
    "NENHUMA_ESPECIFICA": "Circulação geral de moradores e pedestres",
    "PESSOA_COM_DEFICIENCIA_OU_IDOSO": "Pessoas com deficiência, cadeirantes ou idosos",
    "ENTORNO_ESCOLAR_OU_SAUDE": "Alunos de escola/creche ou pacientes de unidade de saúde próxima",
    "AREA_DE_ENCOSTA_OU_MARGEM_CORREGO": "Moradores próximos a encosta, barranco ou margem de córrego",
}

OBSERVED_PROBLEM_TYPES = [
    "Identificar automaticamente a partir da minha descrição",
    "Alagamento, água acumulada na via ou bueiro entupido",
    "Calçada danificada, falta de rampa ou bloqueio de passagem",
    "Árvore com risco de queda, galhos na fiação ou risco estrutural",
    "Falta de iluminação pública na rua ou semáforo apagado",
    "Descarte irregular de entulho, lixo acumulado ou vazamento",
]

DURATION_OPTIONS = [
    "Começou agora (Situação urgente)",
    "Começou hoje",
    "Ocorre há alguns dias",
    "Problema recorrente há mais de um mês",
]

PRESET_CITIZEN_SCENARIOS = {
    "Exemplo 1: Alagamento em frente a escola": {
        "cep": "01310-100",
        "reference": "Em frente à Escola Estadual, próximo ao número 950",
        "vulnerability": "ENTORNO_ESCOLAR_OU_SAUDE",
        "problem_type": "Alagamento, água acumulada na via ou bueiro entupido",
        "duration": "Começou agora (Situação urgente)",
        "description": (
            "Os dois bueiros da esquina estão totalmente entupidos de lixo e a água da chuva já "
            "invadiu a calçada da escola, impedindo a saída segura das crianças e alagando a via."
        ),
    },
    "Exemplo 2: Calçada destruída bloqueando cadeirante": {
        "cep": "04011-000",
        "reference": "Acesso ao Centro de Reabilitação na esquina",
        "vulnerability": "PESSOA_COM_DEFICIENCIA_OU_IDOSO",
        "problem_type": "Calçada danificada, falta de rampa ou bloqueio de passagem",
        "duration": "Ocorre há alguns dias",
        "description": (
            "A calçada cedeu formando um buraco fundo e a rampa de acesso está quebrada, "
            "obrigando cadeirantes e idosos a transitarem pela rua entre os veículos."
        ),
    },
    "Exemplo 3: Árvore inclinada sobre a fiação elétrica": {
        "cep": "05409-000",
        "reference": "Ao lado do ponto de ônibus principal",
        "vulnerability": "NENHUMA_ESPECIFICA",
        "problem_type": "Árvore com risco de queda, galhos na fiação ou risco estrutural",
        "duration": "Começou hoje",
        "description": (
            "Uma árvore de grande porte rachou após a ventania e os galhos pesados estão "
            "pressionando a fiação elétrica com faíscas ocasionais sobre a calçada."
        ),
    },
}


def _validate_citizen_inputs_before_submit(
    description: str,
    postal_code: str,
    uploaded_file: Optional[Any],
) -> List[str]:
    """Valida campos obrigatórios, tamanho, formato de CEP e arquivo antes de enviar a solicitação."""
    validation_errors: List[str] = []
    cleaned_description = (description or "").strip()
    digits_cep = re.sub(r"\D", "", postal_code or "")

    if len(cleaned_description) < 15:
        validation_errors.append(
            "O campo 'Descreva o ocorrido' deve conter pelo menos 15 caracteres para compreendermos a situação."
        )
    if len(cleaned_description) > 1500:
        validation_errors.append("O relato não pode ultrapassar 1.500 caracteres.")
    if len(cleaned_description.split()) < 3:
        validation_errors.append("Descreva o ocorrido utilizando pelo menos 3 palavras.")
    if len(digits_cep) != 8:
        validation_errors.append(
            "Informe um CEP válido com 8 números (exemplo: 01310-100)."
        )

    if uploaded_file is not None:
        max_size_bytes = 5 * 1024 * 1024
        if uploaded_file.size > max_size_bytes:
            validation_errors.append("O arquivo anexado excede o limite de 5 MB.")

    return validation_errors


def _render_triage_result_and_human_in_the_loop(triage_data: Dict[str, Any]) -> None:
    """Apresenta a orientação de atendimento e permite ao cidadão revisar e confirmar o protocolo."""
    catalog = get_category_metadata_catalog()
    ai_block = triage_data["ai_triage"]
    weather_block = triage_data["location_and_weather"]
    category_code = ai_block["official_category"]
    category_meta = catalog.get(category_code, {"label": category_code, "tag": "[OCORRÊNCIA]"})

    st.markdown("---")
    st.subheader("Orientação ao Cidadão e Confirmação do Relato")

    if triage_data.get("privacy_protection_applied"):
        st.info(
            "Proteção de Privacidade (LGPD): Identificamos dados pessoais (como CPF ou e-mail) no texto "
            "e realizamos a ocultação automática para proteger sua identidade."
        )

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric(
            label="Área de Atendimento",
            value=category_meta["label"],
        )
    with metric_col2:
        st.metric(
            label=f"Chuva Agora em {weather_block['neighborhood']}",
            value=f"{weather_block['current_precipitation_mm']} mm",
            delta="Alerta de Chuva Ativo" if weather_block["is_rain_alert_active"] else "Tempo estável",
            delta_color="inverse" if weather_block["is_rain_alert_active"] else "normal",
        )
    with metric_col3:
        st.metric(
            label="Temperatura Local",
            value=f"{weather_block['current_temperature_celsius']} °C",
            delta=weather_block["city_name"],
        )

    guidance_col, context_col = st.columns([1.45, 1.05])
    with guidance_col:
        with st.container(border=True):
            st.markdown("#### Orientações Imediatas de Segurança")
            guidance_items = ai_block.get("citizen_immediate_guidance", [])
            for step_idx, instruction in enumerate(guidance_items, start=1):
                st.markdown(f"**{step_idx}.** {instruction}")

            full_speech_text = (
                f"Atenção cidadão. Sua ocorrência foi direcionada para a área de {category_meta['label']}. "
                "Orientações de segurança: " + " ".join(guidance_items)
            )
            render_text_to_speech_audio_player(
                text_to_read=full_speech_text,
                element_id="citizen_guidance_tts",
            )

    with context_col:
        with st.container(border=True):
            st.markdown("#### Dados Identificados para o Encaminhamento")
            st.markdown(f"**Setor Responsável:** {ai_block['responsible_department']}")
            st.markdown(
                f"**Localização Identificada:** {weather_block['street_name']} — "
                f"**{weather_block['neighborhood']}** ({weather_block['postal_code']})"
            )
            st.markdown(f"**Condição Climática no Local:** {weather_block['weather_condition_summary']}")
            st.markdown(
                f"**Previsão de Atendimento Inicial:** Até {ai_block['estimated_sla_hours']} horas"
            )

    _render_citizen_human_in_the_loop_box(triage_data)


def _render_citizen_human_in_the_loop_box(triage_data: Dict[str, Any]) -> None:
    """Renderiza a etapa de revisão e confirmação pelo cidadão antes de gerar o protocolo definitivo."""
    catalog = get_category_metadata_catalog()
    ai_block = triage_data["ai_triage"]
    weather_block = triage_data["location_and_weather"]

    with st.container(border=True):
        st.markdown("### Conferência e Confirmação da Solicitação")
        st.write(
            "Confira abaixo a área de atendimento identificada para o seu relato. Você pode manter "
            "a sugestão ou alterar a área antes de emitir o protocolo oficial:"
        )

        category_keys = list(catalog.keys())
        default_cat_idx = (
            category_keys.index(ai_block["official_category"])
            if ai_block["official_category"] in category_keys
            else 0
        )

        confirmed_category = st.selectbox(
            "Confirmar ou Alterar a Área de Atendimento:",
            options=category_keys,
            index=default_cat_idx,
            format_func=lambda k: f"{catalog[k]['tag']} {catalog[k]['label']}",
            key="hitl_citizen_category",
        )

        eval_col1, eval_col2 = st.columns([1.1, 1.4])
        with eval_col1:
            helpful_choice = st.radio(
                "As orientações apresentadas acima ajudaram você?",
                options=["Sim, as orientações foram claras e úteis", "Parcialmente, precisei ajustar a área acima"],
                horizontal=False,
                key="hitl_citizen_helpful",
            )
        with eval_col2:
            citizen_notes = st.text_input(
                "Informação complementar sobre o local (opcional):",
                placeholder="Ex.: O problema está próximo ao portão principal.",
                max_chars=300,
                key="hitl_citizen_notes",
            )

        action_col1, action_col2 = st.columns([1.6, 1.0])
        with action_col1:
            if st.button(
                "Confirmar Dados e Emitir Protocolo Oficial",
                type="primary",
                use_container_width=True,
            ):
                was_helpful_bool = helpful_choice.startswith("Sim")
                confirmed_urgency = ai_block.get("urgency_level", "MEDIA")
                confirm_payload = {
                    "draft_protocol_number": triage_data["draft_protocol_number"],
                    "confirmed_category": confirmed_category,
                    "confirmed_urgency": confirmed_urgency,
                    "was_ai_helpful": was_helpful_bool,
                    "human_review_notes": citizen_notes,
                    "reviewer_role": "CIDADAO",
                }
                with st.spinner("Emitindo protocolo oficial de atendimento..."):
                    ok, response_data = send_human_confirmation_to_backend(confirm_payload)

                official_protocol = (
                    response_data.get("official_protocol_number")
                    if ok
                    else triage_data["draft_protocol_number"].replace("TRIAGEM-", "ZC-OFICIAL-")
                )
                selected_meta = catalog[confirmed_category]

                history_entry = {
                    "protocol_number": official_protocol,
                    "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "neighborhood": weather_block["neighborhood"],
                    "postal_code": weather_block["postal_code"],
                    "reference_location": triage_data.get("reference_location", ""),
                    "category": confirmed_category,
                    "category_label": selected_meta["label"],
                    "urgency": confirmed_urgency,
                    "technical_risk_score": triage_data["technical_risk_score"],
                    "precipitation_mm": weather_block["current_precipitation_mm"],
                    "vulnerability": triage_data["vulnerability_context"],
                    "status": "CONFIRMADO_PELO_CIDADAO",
                    "was_ai_helpful": was_helpful_bool,
                    "description": triage_data["sanitized_description"],
                    "department": selected_meta["department"],
                }
                add_confirmed_occurrence_to_history(history_entry)
                st.session_state["last_confirmed_protocol"] = history_entry
                st.session_state["pending_triage_result"] = None
                st.rerun()

        with action_col2:
            if st.button("Cancelar e Preencher Novo Relato", use_container_width=True):
                st.session_state["pending_triage_result"] = None
                st.rerun()


def _render_optional_example_loader() -> None:
    """Exibe opções de exemplos e abre uma caixa demonstrando como preencher os campos."""
    audio_assist_enabled = bool(st.session_state.get("large_font_mode", False))
    is_expanded = bool(st.session_state.get("selected_example_scenario"))
    with st.expander(
        "Exemplos de ocorrências para consulta de preenchimento",
        expanded=is_expanded,
    ):
        st.caption("Clique em uma das opções abaixo para visualizar um exemplo de como preencher os campos:")
        preset_cols = st.columns(3)
        for idx, (scenario_title, _scenario_data) in enumerate(PRESET_CITIZEN_SCENARIOS.items()):
            with preset_cols[idx]:
                if st.button(scenario_title, key=f"preset_btn_{idx}", use_container_width=True):
                    st.session_state["selected_example_scenario"] = scenario_title

        selected_title = st.session_state.get("selected_example_scenario")
        if selected_title and selected_title in PRESET_CITIZEN_SCENARIOS:
            example_data = PRESET_CITIZEN_SCENARIOS[selected_title]
            vuln_label = VULNERABILITY_OPTIONS_MAP.get(
                example_data["vulnerability"],
                example_data["vulnerability"],
            )
            with st.container(border=True):
                st.markdown(f"#### {selected_title}")
                if audio_assist_enabled:
                    example_speech = (
                        f"{selected_title}. "
                        f"Relato sugerido: {example_data['description']} "
                        f"Tipo de situação: {example_data['problem_type']}. "
                        f"Tempo de ocorrência: {example_data['duration']}. "
                        f"CEP do local: {example_data['cep']}. "
                        f"Ponto de referência: {example_data['reference']}. "
                        f"Pessoas afetadas no entorno: {vuln_label}."
                    )
                    render_text_to_speech_audio_player(
                        text_to_read=example_speech,
                        element_id="example_scenario_tts",
                        button_label="🔊 Ouvir este Exemplo em Áudio",
                    )
                st.markdown(
                    f"**Relate com suas palavras o problema observado:**\n> {example_data['description']}"
                )
                ex_col1, ex_col2 = st.columns(2)
                with ex_col1:
                    st.markdown(f"**Tipo de situação observada:** {example_data['problem_type']}")
                    st.markdown(f"**CEP do Local:** `{example_data['cep']}`")
                    st.markdown(f"**Endereço ou Ponto de Referência:** {example_data['reference']}")
                with ex_col2:
                    st.markdown(f"**Há quanto tempo ocorre:** {example_data['duration']}")
                    st.markdown(f"**Quem é mais afetado no entorno:** {vuln_label}")


def render_citizen_portal_feature() -> None:
    """Renderiza a jornada completa do cidadão centrada no relato livre do ocorrido."""
    audio_assist_enabled = bool(st.session_state.get("large_font_mode", False))

    st.markdown("### Registrar Nova Solicitação")
    st.write(
        "Informe abaixo o que está acontecendo na sua rua ou bairro. O sistema identifica o endereço "
        "pelo CEP, verifica se há chuva forte na região neste momento e indica as medidas de segurança "
        "e o setor responsável pelo atendimento."
    )

    if audio_assist_enabled:
        form_intro_speech = (
            "Registrar Nova Solicitação. "
            "Para registrar sua ocorrência, preencha duas etapas: "
            "Na Etapa 1, descreva com suas palavras o problema observado, o tipo de situação e há quanto tempo ela ocorre. "
            "Na Etapa 2, informe os 8 números do CEP do local, um endereço ou ponto de referência opcional e quem é mais afetado no entorno. "
            "Ao finalizar, clique no botão Enviar Relato e Receber Orientação."
        )
        render_text_to_speech_audio_player(
            text_to_read=form_intro_speech,
            element_id="citizen_form_intro_tts",
            button_label="🔊 Ouvir Instruções de Preenchimento",
        )

    if st.session_state.get("last_confirmed_protocol"):
        confirmed = st.session_state["last_confirmed_protocol"]
        st.success(
            f"Protocolo Oficial `{confirmed['protocol_number']}` registrado com sucesso! "
            f"Sua solicitação foi encaminhada para **{confirmed['department']}** (Bairro: {confirmed['neighborhood']})."
        )

    with st.form("citizen_occurrence_form", clear_on_submit=False):
        st.markdown("#### 1. Descreva o Ocorrido")
        if audio_assist_enabled:
            render_text_to_speech_audio_player(
                text_to_read=(
                    "Etapa 1: Descreva o ocorrido. "
                    "Digite no campo abaixo o que aconteceu na sua rua ou bairro com pelo menos 15 caracteres. "
                    "Em seguida, escolha o tipo de situação observada e há quanto tempo ela ocorre."
                ),
                element_id="citizen_step1_tts",
                button_label="🔊 Ouvir Etapa 1 (Descrição)",
            )
        description_value = st.text_area(
            "Relate com suas palavras o problema observado * (mínimo de 15 caracteres)",
            value=st.session_state.get("form_desc_input", ""),
            height=130,
            placeholder=(
                "Explique o que aconteceu, como isso está afetando os moradores ou pedestres e se "
                "há perigo imediato no local (ex.: calçada quebrada, bueiro transbordando, árvore inclinada)..."
            ),
            help="Não é necessário informar documentos pessoais como CPF. Sua privacidade é protegida.",
        )

        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            default_type = st.session_state.get("form_type_input", OBSERVED_PROBLEM_TYPES[0])
            type_idx = (
                OBSERVED_PROBLEM_TYPES.index(default_type)
                if default_type in OBSERVED_PROBLEM_TYPES
                else 0
            )
            problem_type_value = st.selectbox(
                "Tipo de situação observada (Opcional — auxilia no direcionamento):",
                options=OBSERVED_PROBLEM_TYPES,
                index=type_idx,
            )
        with detail_col2:
            default_duration = st.session_state.get("form_duration_input", DURATION_OPTIONS[0])
            duration_idx = (
                DURATION_OPTIONS.index(default_duration)
                if default_duration in DURATION_OPTIONS
                else 0
            )
            duration_value = st.selectbox(
                "Há quanto tempo essa situação ocorre?",
                options=DURATION_OPTIONS,
                index=duration_idx,
            )

        st.markdown("#### 2. Localização e Pessoas Afetadas")
        if audio_assist_enabled:
            render_text_to_speech_audio_player(
                text_to_read=(
                    "Etapa 2: Localização e Pessoas Afetadas. "
                    "Informe o CEP do local com 8 números, um ponto de referência opcional e selecione quem é mais afetado no entorno. "
                    "Se desejar, anexe uma fotografia do local e clique no botão Enviar Relato e Receber Orientação."
                ),
                element_id="citizen_step2_tts",
                button_label="🔊 Ouvir Etapa 2 (Localização)",
            )
        loc_col1, loc_col2, loc_col3 = st.columns([1.0, 1.3, 1.5])
        with loc_col1:
            postal_code_value = st.text_input(
                "CEP do Local *",
                value=st.session_state.get("form_cep_input", "01310-100"),
                placeholder="Ex.: 01310-100",
                help="Digite os 8 números do CEP para localizarmos a rua e o bairro automaticamente.",
            )
        with loc_col2:
            reference_value = st.text_input(
                "Endereço ou Ponto de Referência (Opcional)",
                value=st.session_state.get("form_ref_input", ""),
                placeholder="Ex.: Próximo ao número 450 / Em frente ao posto de saúde",
                max_chars=160,
            )
        with loc_col3:
            vulnerability_value = st.selectbox(
                "Quem é mais afetado no entorno?",
                options=list(VULNERABILITY_OPTIONS_MAP.keys()),
                index=list(VULNERABILITY_OPTIONS_MAP.keys()).index(
                    st.session_state.get("form_vuln_input", "ENTORNO_ESCOLAR_OU_SAUDE")
                ),
                format_func=lambda k: VULNERABILITY_OPTIONS_MAP[k],
                help="Informe quem circula ou reside próximo ao local da ocorrência.",
            )

        uploaded_evidence = st.file_uploader(
            "Anexar Fotografia do Local (Opcional — Formatos JPG, PNG ou PDF até 5 MB)",
            type=["jpg", "jpeg", "png", "pdf"],
            help="Caso possua uma foto do problema, anexe aqui para auxiliar a equipe de vistoria.",
        )

        submit_triggered = st.form_submit_button(
            "Enviar Relato e Receber Orientação",
            type="primary",
            use_container_width=True,
        )

    _render_optional_example_loader()

    if submit_triggered:
        st.session_state["last_confirmed_protocol"] = None
        validation_errors = _validate_citizen_inputs_before_submit(
            description=description_value,
            postal_code=postal_code_value,
            uploaded_file=uploaded_evidence,
        )

        if validation_errors:
            render_friendly_error_banner(
                error_code="REVISAO_CAMPOS",
                user_message="Algumas informações precisam ser preenchidas corretamente antes do envio:",
                recovery_instructions=" • ".join(validation_errors),
            )
        else:
            sim_mode = st.session_state.get("simulate_failure_mode", "NONE")
            simulate_offline_flag = sim_mode == "API_OFFLINE"
            backend_sim_mode = sim_mode if sim_mode in {"NONE", "TIMEOUT", "LLM_ERROR"} else "NONE"

            composed_description = description_value.strip()
            if problem_type_value != OBSERVED_PROBLEM_TYPES[0]:
                composed_description = f"[{problem_type_value} — {duration_value}] {composed_description}"

            request_payload = {
                "citizen_description": composed_description,
                "postal_code": postal_code_value,
                "reference_location": reference_value,
                "vulnerability_context": vulnerability_value,
                "has_photo_evidence": uploaded_evidence is not None,
                "simulate_failure_mode": backend_sim_mode,
            }

            with st.status(
                "Analisando sua solicitação e verificando condições do local...", expanded=True
            ) as status_box:
                st.write("1. Localizando endereço pelo CEP e consultando volume de chuva no bairro...")
                st.write("2. Avaliando nível de risco para pedestres e moradores no entorno...")
                st.write("3. Preparando orientações de segurança e encaminhamento para o setor responsável...")
                success, api_response = send_citizen_report_for_triage(
                    report_payload=request_payload,
                    simulate_offline=simulate_offline_flag,
                )
                if success:
                    status_box.update(
                        label="Avaliação concluída! Confira abaixo a orientação e confirme seu protocolo.",
                        state="complete",
                        expanded=False,
                    )
                    st.session_state["pending_triage_result"] = api_response
                else:
                    status_box.update(
                        label="Não foi possível concluir a análise neste momento.",
                        state="error",
                        expanded=True,
                    )
                    st.session_state["pending_triage_result"] = None
                    render_friendly_error_banner(
                        error_code=api_response.get("error_code", "INDISPONIBILIDADE"),
                        user_message=api_response.get(
                            "user_message",
                            "O sistema de atendimento está temporariamente indisponível.",
                        ),
                        recovery_instructions=(
                            "Caso o modo de demonstração de falhas esteja ativo na barra lateral esquerda, "
                            "selecione 'Funcionamento Normal' e envie novamente."
                        ),
                    )

    if st.session_state.get("pending_triage_result"):
        _render_triage_result_and_human_in_the_loop(st.session_state["pending_triage_result"])

    st.markdown("---")
    st.subheader("Relatos das Ocorrências Registradas")
    history_records = st.session_state.get("occurrence_history", [])
    if not history_records:
        render_empty_state_card(
            title="Nenhuma solicitação registrada ainda",
            subtitle="Utilize o formulário acima para registrar sua primeira ocorrência.",
        )
    else:
        for record in history_records[:4]:
            render_occurrence_summary_card(
                record,
                context_origin="Portal do Cidadão",
                show_technical_metrics=False,
            )
