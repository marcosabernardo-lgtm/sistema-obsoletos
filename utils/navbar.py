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


def split_empresa_filial(empresas_filiais: list):
    """
    Recebe lista de 'Empresa / Filial' e retorna
    (empresas_unicas, filiais_unicas) separadas.
    """
    empresas = sorted(set(ef.split(" / ")[0].strip() for ef in empresas_filiais if " / " in ef))
    filiais  = sorted(set(ef.split(" / ")[1].strip() for ef in empresas_filiais if " / " in ef))
    return empresas, filiais


def filtrar_por_empresa_filial(df_preview, empresa_sel, filial_sel):
    """
    Filtra df_preview pelo campo 'Empresa / Filial' com base nas
    seleções de empresa e filial separadas.
    Retorna (empresas_disponiveis, filiais_disponiveis, ef_selecionados)
    """
    col = "Empresa / Filial"
    todos = sorted(df_preview[col].dropna().unique())

    # Filial disponível filtrada pela empresa selecionada
    if empresa_sel:
        ef_por_empresa = [ef for ef in todos if ef.split(" / ")[0].strip() in empresa_sel]
    else:
        ef_por_empresa = todos
    _, filiais_disp = split_empresa_filial(ef_por_empresa)

    # Empresa disponível filtrada pela filial selecionada
    if filial_sel:
        ef_por_filial = [ef for ef in todos if ef.split(" / ")[1].strip() in filial_sel]
    else:
        ef_por_filial = todos
    empresas_disp, _ = split_empresa_filial(ef_por_filial)

    # EF selecionados para aplicar no df
    ef_sel = []
    for ef in todos:
        partes = ef.split(" / ")
        emp, fil = partes[0].strip(), partes[1].strip()
        ok_emp = (not empresa_sel) or (emp in empresa_sel)
        ok_fil = (not filial_sel)  or (fil in filial_sel)
        if ok_emp and ok_fil:
            ef_sel.append(ef)

    return empresas_disp, filiais_disp, ef_sel


def render_filtros_topo(datas: list, empresas: list, extras: dict = None, key_prefix: str = "filtro"):
    """
    Renderiza filtros como barra horizontal no topo da página.
    Usa multiselect estilizado — sem sidebar.

    Parâmetros:
        datas       : lista de strings de datas disponíveis
        empresas    : lista de 'Empresa / Filial' disponíveis (campo original)
        extras      : dict com filtros adicionais {label: [opcoes]}
        key_prefix  : prefixo para as chaves

    Retorna dict com valores selecionados, incluindo:
        - "empresas"     : lista de 'Empresa / Filial' que batem com os filtros
        - "empresa_sel"  : empresas selecionadas
        - "filial_sel"   : filiais selecionadas
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

    # Monta colunas dinamicamente: Data | Empresa | Filial | extras...
    n_extras = len(extras) if extras else 0
    col_sizes = [1, 1.5, 1.5] + ([1.2] * n_extras)
    cols = st.columns(col_sizes)

    resultado = {}

    # Recupera seleções atuais para bidirecionalidade
    empresa_ja_sel = st.session_state.get(f"{key_prefix}_empresa_sel", [])
    filial_ja_sel  = st.session_state.get(f"{key_prefix}_filial_sel",  [])

    # Calcula opções bidirecionais
    empresas_unicas, filiais_unicas = split_empresa_filial(empresas)
    empresas_disp, filiais_disp, ef_sel = filtrar_por_empresa_filial(
        __import__("pandas").DataFrame({
            "Empresa / Filial": empresas
        }),
        empresa_ja_sel,
        filial_ja_sel
    )

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
        empresa_sel = st.multiselect(
            "Empresa",
            options=empresas_disp,
            default=[v for v in empresa_ja_sel if v in empresas_disp],
            key=f"{key_prefix}_empresa_sel",
            placeholder="Todas as empresas"
        )

    # Filial
    with cols[2]:
        filial_sel = st.multiselect(
            "Filial",
            options=filiais_disp,
            default=[v for v in filial_ja_sel if v in filiais_disp],
            key=f"{key_prefix}_filial_sel",
            placeholder="Todas as filiais"
        )

    # Recalcula EF com seleções finais
    _, _, ef_final = filtrar_por_empresa_filial(
        __import__("pandas").DataFrame({"Empresa / Filial": empresas}),
        empresa_sel,
        filial_sel
    )
    resultado["empresas"]    = ef_final  # lista de "Empresa / Filial" para uso nos filtros
    resultado["empresa_sel"] = empresa_sel
    resultado["filial_sel"]  = filial_sel

    # Extras (Conta, Faixa DIO, etc.)
    if extras:
        for idx, (label, opcoes) in enumerate(extras.items()):
            label_key = label.lower().replace(" ", "_").replace("/", "")
            with cols[3 + idx]:
                sel = st.multiselect(
                    label,
                    options=opcoes,
                    default=[],
                    key=f"{key_prefix}_{label_key}",
                    placeholder="Todas"
                )
                resultado[label_key] = sel

    st.markdown('</div>', unsafe_allow_html=True)
    return resultado
