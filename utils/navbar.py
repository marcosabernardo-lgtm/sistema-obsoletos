import streamlit as st


def render_navbar(titulo: str = ""):
    """
    Renderiza botão Home + título no topo da página.
    """
    st.markdown("""
    <style>
    /* Esconde nav links da sidebar */
    section[data-testid="stSidebarNav"] { display: none !important; }

    /* Botão Home */
    div[data-testid="stButton"].home-btn > button {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 8px !important;
        color: rgba(255,255,255,0.7) !important;
        font-size: 13px !important;
        padding: 6px 16px !important;
        height: auto !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stButton"].home-btn > button:hover {
        background: rgba(236,110,33,0.15) !important;
        border-color: #EC6E21 !important;
        color: #EC6E21 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_btn, col_title = st.columns([1, 9])
    with col_btn:
        st.markdown('<div class="home-btn">', unsafe_allow_html=True)
        if st.button("← Home", key="btn_home_navbar"):
            st.switch_page("app.py")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_title:
        if titulo:
            st.markdown(
                f"<p style='margin:0; padding:6px 0; color:rgba(255,255,255,0.4); font-size:13px'>{titulo}</p>",
                unsafe_allow_html=True
            )
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


def render_filtros_topo(datas: list, empresas: list, extras: dict = None, key_prefix: str = "filtro"):
    """
    Renderiza filtros como chips/pills no topo da página.

    Parâmetros:
        datas       : lista de strings formatadas de datas disponíveis
        empresas    : lista de empresas disponíveis
        extras      : dict com filtros adicionais {label: [opcoes]}
                      ex: {"Conta": ["Produto Acabado", "Matéria Prima"]}
        key_prefix  : prefixo para as chaves de session_state

    Retorna:
        dict com os valores selecionados:
        {
            "data": "28/02/2026",
            "empresas": ["Robotica / Matriz"],
            "conta": ["Produto Acabado"],   # se extras tiver "Conta"
            ...
        }
    """

    st.markdown("""
    <style>
    /* Container de filtros */
    .filtros-topo {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 24px;
        flex-wrap: wrap;
    }
    .filtro-label {
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: rgba(255,255,255,0.35);
        margin-bottom: 6px;
    }

    /* Chips — botões de seleção */
    div[data-testid="stButton"].chip-btn > button {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 20px !important;
        color: rgba(255,255,255,0.6) !important;
        font-size: 12px !important;
        padding: 4px 14px !important;
        height: auto !important;
        min-height: 0 !important;
        margin: 2px !important;
        transition: all 0.15s ease !important;
        white-space: nowrap !important;
    }
    div[data-testid="stButton"].chip-btn > button:hover {
        background: rgba(236,110,33,0.15) !important;
        border-color: rgba(236,110,33,0.5) !important;
        color: #EC6E21 !important;
    }
    div[data-testid="stButton"].chip-ativo > button {
        background: rgba(236,110,33,0.2) !important;
        border: 1px solid #EC6E21 !important;
        border-radius: 20px !important;
        color: #EC6E21 !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 4px 14px !important;
        height: auto !important;
        min-height: 0 !important;
        margin: 2px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    resultado = {}

    # ── DATA (selectbox compacto) ──────────────────────────
    col_data, col_emp, *col_extras = st.columns(
        [1.5, 2] + ([1.5] * len(extras)) if extras else [1.5, 2]
    )

    with col_data:
        st.markdown('<div class="filtro-label">Fechamento</div>', unsafe_allow_html=True)
        data_sel = st.selectbox(
            "Data",
            options=datas,
            index=0,
            key=f"{key_prefix}_data",
            label_visibility="collapsed"
        )
        resultado["data"] = data_sel

    # ── EMPRESA (chips) ────────────────────────────────────
    with col_emp:
        st.markdown('<div class="filtro-label">Empresa / Filial</div>', unsafe_allow_html=True)

        key_emp = f"{key_prefix}_empresas"
        if key_emp not in st.session_state:
            st.session_state[key_emp] = []

        cols_emp = st.columns(len(empresas)) if empresas else []
        for i, emp in enumerate(empresas):
            ativo = emp in st.session_state[key_emp]
            css_class = "chip-ativo" if ativo else "chip-btn"
            with cols_emp[i]:
                st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                if st.button(emp, key=f"{key_prefix}_emp_{i}"):
                    if ativo:
                        st.session_state[key_emp].remove(emp)
                    else:
                        st.session_state[key_emp].append(emp)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        resultado["empresas"] = st.session_state[key_emp]

    # ── EXTRAS (chips) ─────────────────────────────────────
    if extras:
        for idx, (label, opcoes) in enumerate(extras.items()):
            label_key = label.lower().replace(" ", "_").replace("/", "")
            key_extra = f"{key_prefix}_{label_key}"

            if key_extra not in st.session_state:
                st.session_state[key_extra] = []

            # Filtra opções conforme empresas selecionadas (passado de fora)
            with col_extras[idx]:
                st.markdown(f'<div class="filtro-label">{label}</div>', unsafe_allow_html=True)
                cols_ex = st.columns(len(opcoes)) if opcoes else []
                for i, opc in enumerate(opcoes):
                    ativo = opc in st.session_state[key_extra]
                    css_class = "chip-ativo" if ativo else "chip-btn"
                    with cols_ex[i]:
                        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
                        if st.button(opc, key=f"{key_prefix}_{label_key}_{i}"):
                            if ativo:
                                st.session_state[key_extra].remove(opc)
                            else:
                                st.session_state[key_extra].append(opc)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

            resultado[label_key] = st.session_state[key_extra]

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    return resultado
