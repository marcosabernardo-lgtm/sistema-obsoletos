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
    Renderiza filtros como barra horizontal no topo da página.
    Usa multiselect estilizado — sem sidebar.

    Parâmetros:
        datas       : lista de strings de datas disponíveis
        empresas    : lista de empresas disponíveis
        extras      : dict com filtros adicionais {label: [opcoes]}
        key_prefix  : prefixo para as chaves

    Retorna dict com valores selecionados.
    """

    st.markdown("""
    <style>
    /* Estiliza multiselect no topo como pills */
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 10px !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {
        border-color: #EC6E21 !important;
    }
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background-color: rgba(236,110,33,0.2) !important;
        border: 1px solid #EC6E21 !important;
        border-radius: 20px !important;
        color: #EC6E21 !important;
        font-size: 11px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] span {
        color: #EC6E21 !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="select"] span,
    div[data-testid="stMultiSelect"] [data-baseweb="select"] div {
        color: rgba(255,255,255,0.5) !important;
    }

    /* Selectbox data */
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 10px !important;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] span {
        color: white !important;
        font-weight: 600 !important;
    }

    /* Labels dos filtros */
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stSelectbox"] label {
        font-size: 10px !important;
        font-weight: 600 !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
        color: rgba(255,255,255,0.35) !important;
    }

    /* Container fundo */
    .filtros-container {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 12px 20px 4px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="filtros-container">', unsafe_allow_html=True)

    # Monta colunas dinamicamente
    n_extras = len(extras) if extras else 0
    col_sizes = [1] + [2] + ([1.5] * n_extras)
    cols = st.columns(col_sizes)

    resultado = {}

    # Data
    with cols[0]:
        data_sel = st.selectbox(
            "Fechamento",
            options=datas,
            index=0,
            key=f"{key_prefix}_data"
        )
        resultado["data"] = data_sel

    # Empresa
    with cols[1]:
        empresas_sel = st.multiselect(
            "Empresa / Filial",
            options=empresas,
            default=[],
            key=f"{key_prefix}_empresas",
            placeholder="Todas as empresas"
        )
        resultado["empresas"] = empresas_sel

    # Extras (Conta, Faixa DIO, etc.)
    if extras:
        for idx, (label, opcoes) in enumerate(extras.items()):
            label_key = label.lower().replace(" ", "_").replace("/", "")
            with cols[2 + idx]:
                sel = st.multiselect(
                    label,
                    options=opcoes,
                    default=[],
                    key=f"{key_prefix}_{label_key}",
                    placeholder=f"Todas"
                )
                resultado[label_key] = sel

    st.markdown('</div>', unsafe_allow_html=True)
    return resultado
