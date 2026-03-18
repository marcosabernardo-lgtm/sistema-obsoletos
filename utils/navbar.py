import streamlit as st


def render_navbar(titulo: str = ""):
    """
    Renderiza botão de voltar para home no topo da página.
    Chame logo após st.set_page_config().
    """

    st.markdown("""
    <style>
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

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
