"""Recursos de acessibilidade, alto contraste, escala tipográfica e leitura em voz alta."""

import json
import streamlit as st
import streamlit.components.v1 as components


def apply_accessibility_and_theme_styles(
    high_contrast_enabled: bool,
    large_font_enabled: bool,
) -> None:
    """Injeta folhas de estilo acessíveis (foco visível, abas responsivas, cursores e alto contraste)."""
    base_font_size = "18px" if large_font_enabled else "16px"

    shared_ux_css = f"""
        html, body, [class*="css"] {{
            font-size: {base_font_size} !important;
        }}
        .block-container {{
            padding-top: 3.6rem !important;
            padding-left: 2.2rem !important;
            padding-right: 2.2rem !important;
            max-width: 100% !important;
        }}
        div[data-baseweb="select"],
        div[data-baseweb="select"] *,
        div[data-baseweb="select"] input {{
            cursor: pointer !important;
            caret-color: transparent !important;
            user-select: none !important;
        }}
        div[data-baseweb="select"] input:focus,
        div[data-baseweb="select"] input:focus-visible {{
            outline: none !important;
            box-shadow: none !important;
        }}
        div[data-baseweb="tab-list"] {{
            display: flex !important;
            width: 100% !important;
            gap: 0.75rem !important;
            border-bottom: 2px solid rgba(148, 163, 184, 0.25) !important;
            padding-bottom: 0.25rem !important;
        }}
        div[data-baseweb="tab-list"] button[data-baseweb="tab"] {{
            flex: 1 1 0% !important;
            justify-content: center !important;
            padding: 0.65rem 1rem !important;
            border-radius: 8px 8px 0 0 !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            white-space: nowrap !important;
            cursor: pointer !important;
        }}
    """

    if high_contrast_enabled:
        theme_css = f"""
        <style>
            {shared_ux_css}
            .stApp {{
                background-color: #000000 !important;
                color: #FFFFFF !important;
            }}
            [data-testid="stSidebar"] {{
                background-color: #0A0A0A !important;
                border-right: 2px solid #FFD600 !important;
            }}
            h1, h2, h3, h4, label, p, span, li {{
                color: #FFFFFF !important;
            }}
            div[data-testid="stVerticalBlockBorderWrapper"] {{
                border: 2px solid #FFD600 !important;
                background-color: #080808 !important;
            }}
            .zela-card {{
                background-color: #0D0D0D !important;
                border: 2px solid #FFD600 !important;
                color: #FFFFFF !important;
            }}
            button:focus-visible, textarea:focus-visible {{
                outline: 3px solid #00E5FF !important;
                outline-offset: 2px !important;
            }}
        </style>
        """
    else:
        theme_css = f"""
        <style>
            {shared_ux_css}
            .zela-card {{
                background-color: #FFFFFF;
                border: 1px solid #DCE3EC;
                border-radius: 12px;
                padding: 1.15rem;
                margin-bottom: 0.9rem;
                box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05);
            }}
            @media (prefers-color-scheme: dark) {{
                .zela-card {{
                    background-color: #1E293B;
                    border: 1px solid #334155;
                }}
            }}
            button:focus-visible, textarea:focus-visible {{
                outline: 2px solid #2563EB !important;
                outline-offset: 2px !important;
            }}
        </style>
        """
    st.markdown(theme_css, unsafe_allow_html=True)


def render_text_to_speech_audio_player(
    text_to_read: str,
    element_id: str = "tts_main",
    button_label: str = "🔊 Ouvir em Áudio",
) -> None:
    """Renderiza botão acessível que lê em voz alta (em português) textos e instruções da tela."""
    safe_json_text = json.dumps(text_to_read, ensure_ascii=False)
    html_snippet = f"""
    <div style="display:flex; align-items:center; gap:10px; margin: 4px 0; font-family: sans-serif;">
        <button
            id="play_{element_id}"
            type="button"
            aria-label="{button_label}"
            style="
                background-color:#1D4ED8;
                color:#FFFFFF;
                border:2px solid #93C5FD;
                border-radius:8px;
                padding:8px 14px;
                font-weight:600;
                font-size:14px;
                cursor:pointer;
            "
        >
            {button_label}
        </button>
        <button
            id="stop_{element_id}"
            type="button"
            aria-label="Parar leitura em voz alta"
            style="
                background-color:#334155;
                color:#FFFFFF;
                border:1px solid #64748B;
                border-radius:8px;
                padding:8px 12px;
                font-weight:600;
                font-size:14px;
                cursor:pointer;
            "
        >
            ⏹ Parar Áudio
        </button>
        <span id="status_{element_id}" style="font-size:13px; color:#93C5FD; font-weight:600;"></span>
    </div>
    <script>
        (function() {{
            const textToSpeak = {safe_json_text};
            const playBtn = document.getElementById("play_{element_id}");
            const stopBtn = document.getElementById("stop_{element_id}");
            const statusEl = document.getElementById("status_{element_id}");
            const synth = (window.parent && window.parent.speechSynthesis)
                ? window.parent.speechSynthesis
                : window.speechSynthesis;
            const UtteranceClass = (window.parent && window.parent.SpeechSynthesisUtterance)
                ? window.parent.SpeechSynthesisUtterance
                : window.SpeechSynthesisUtterance;

            function selectPortugueseVoice() {{
                if (!synth) return null;
                const voices = synth.getVoices() || [];
                return (
                    voices.find(v => v.lang && v.lang.toLowerCase() === "pt-br") ||
                    voices.find(v => v.lang && v.lang.toLowerCase().startsWith("pt")) ||
                    null
                );
            }}

            if (synth && synth.onvoiceschanged !== undefined) {{
                synth.onvoiceschanged = selectPortugueseVoice;
            }}

            playBtn.addEventListener("click", function() {{
                if (!synth || !UtteranceClass) {{
                    statusEl.textContent = "Navegador sem suporte a voz.";
                    return;
                }}
                synth.cancel();
                setTimeout(function() {{
                    const utterance = new UtteranceClass(textToSpeak);
                    utterance.lang = "pt-BR";
                    utterance.rate = 1.0;
                    const ptVoice = selectPortugueseVoice();
                    if (ptVoice) {{
                        utterance.voice = ptVoice;
                    }}
                    utterance.onstart = function() {{
                        statusEl.textContent = "Reproduzindo áudio...";
                    }};
                    utterance.onend = function() {{
                        statusEl.textContent = "";
                    }};
                    utterance.onerror = function() {{
                        statusEl.textContent = "";
                    }};
                    synth.speak(utterance);
                }}, 60);
            }});

            stopBtn.addEventListener("click", function() {{
                if (synth) {{
                    synth.cancel();
                }}
                statusEl.textContent = "";
            }});
        }})();
    </script>
    """
    components.html(html_snippet, height=54)


def render_accessibility_onboarding_screen(active_role: str = "CIDADAO") -> None:
    """Exibe a tela inicial de acessibilidade antes do acesso ao portal (Cidadão ou Gestor)."""
    role_context_label = (
        "Portal do Cidadão"
        if active_role == "CIDADAO"
        else "Central da Gestão Municipal e Defesa Civil"
    )

    st.markdown(f"## Bem-vindo ao ZelaAI — {role_context_label}")
    st.markdown(
        "### Você possui alguma dificuldade para ler letras pequenas ou enxergar cores na tela?"
    )
    st.write(
        "Escolha abaixo como prefere visualizar a plataforma hoje. "
        "Você também pode ouvir a explicação desta tela em voz alta antes de escolher:"
    )

    onboarding_speech_text = (
        f"Bem-vindo ao ZelaAI, {role_context_label}. "
        "Escolha uma das três opções na tela para ajustar a leitura: "
        "Opção 1: Visualização Padrão, para quem não possui dificuldades de leitura. "
        "Opção 2: Letras Ampliadas, ideal para idosos ou dificuldade com letras pequenas. "
        "Opção 3: Alto Contraste e Letras Ampliadas, ideal para baixa visão ou dificuldade para diferenciar cores."
    )
    render_text_to_speech_audio_player(
        text_to_read=onboarding_speech_text,
        element_id="onboarding_welcome_tts",
    )

    st.markdown("---")

    col_std, col_large, col_contrast = st.columns(3)

    with col_std:
        with st.container(border=True):
            st.markdown("#### 1. Visualização Padrão")
            st.write(
                "Não possuo dificuldades de leitura. Prefiro utilizar a plataforma com "
                "cores e tamanho de texto no formato tradicional."
            )
            if st.button(
                "Entrar no Modo Padrão",
                key="btn_onboard_standard",
                use_container_width=True,
            ):
                st.session_state["high_contrast_mode"] = False
                st.session_state["large_font_mode"] = False
                st.session_state["accessibility_onboarding_completed"] = True
                st.rerun()

    with col_large:
        with st.container(border=True):
            st.markdown("#### 2. Letras Ampliadas")
            st.write(
                "Tenho dificuldade para ler letras pequenas. Desejo aumentar o tamanho "
                "de todos os textos e contar com leitura em áudio ao registrar ocorrências."
            )
            if st.button(
                "Entrar com Letras Ampliadas",
                key="btn_onboard_large_font",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["high_contrast_mode"] = False
                st.session_state["large_font_mode"] = True
                st.session_state["accessibility_onboarding_completed"] = True
                st.rerun()

    with col_contrast:
        with st.container(border=True):
            st.markdown("#### 3. Alto Contraste + Letras Ampliadas")
            st.write(
                "Tenho baixa visão, sensibilidade à claridade ou dificuldade com cores. "
                "Desejo fundo escuro com bordas amarelas, letras grandes e apoio em áudio."
            )
            if st.button(
                "Entrar com Alto Contraste",
                key="btn_onboard_high_contrast",
                type="primary",
                use_container_width=True,
            ):
                st.session_state["high_contrast_mode"] = True
                st.session_state["large_font_mode"] = True
                st.session_state["accessibility_onboarding_completed"] = True
                st.rerun()


def render_platform_accessibility_header_bar() -> None:
    """Renderiza cabeçalho da plataforma com botão visível para reabrir as opções de acessibilidade."""
    high_contrast = st.session_state.get("high_contrast_mode", False)
    large_font = st.session_state.get("large_font_mode", False)

    if high_contrast and large_font:
        active_mode_label = "Alto Contraste + Letras Ampliadas"
    elif high_contrast:
        active_mode_label = "Alto Contraste"
    elif large_font:
        active_mode_label = "Letras Ampliadas"
    else:
        active_mode_label = "Padrão"

    header_col1, header_col2 = st.columns([2.6, 1.1], vertical_alignment="center")
    with header_col1:
        st.title("ZelaAI — Zeladoria Urbana, Acessibilidade e Prevenção Climática")
    with header_col2:
        st.markdown(
            f"<div style='padding-top: 0.5rem; margin-bottom: 0.35rem; font-size: 0.92rem;'>"
            f"Modo de visualização atual: <strong>{active_mode_label}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Alterar Modo de Leitura / Acessibilidade",
            key="btn_reopen_accessibility_screen",
            use_container_width=True,
        ):
            st.session_state["accessibility_onboarding_completed"] = False
            st.rerun()
