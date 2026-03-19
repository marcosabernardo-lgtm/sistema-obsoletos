import streamlit as st
import pandas as pd
import io


def render(df_filtrado, moeda_br):

    st.markdown("""
    <style>
    div[data-testid="stRadio"] > div {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 10px 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    col_filtro, col_export = st.columns([4, 1])

    with col_filtro:
        visao = st.radio(
            "Visualizar",
            ["Obsoleto", "Geral"],
            horizontal=True,
            key="base_historica_visao"
        )

    if visao == "Obsoleto":
        base = df_filtrado.copy()
    else:
        base = st.session_state.get("df_kpi_completo", df_filtrado).copy()

    base["Data Fechamento"] = pd.to_datetime(base["Data Fechamento"]).dt.date

    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        buffer = io.BytesIO()
        base.to_excel(buffer, index=False)
        buffer.seek(0)
        data_ref    = base["Data Fechamento"].max() if not base.empty else "sem_data"
        label_visao = "obsoletos" if visao == "Obsoleto" else "geral"
        st.download_button(
            label="📥 Exportar",
            data=buffer.getvalue(),
            file_name=f"base_historica_{label_visao}_{data_ref}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Formata para exibição
    base_display = base.copy()

    if "Vlr Unit" in base_display.columns:
        base_display["Vlr Unit"] = pd.to_numeric(base_display["Vlr Unit"], errors="coerce").apply(
            lambda x: moeda_br(x) if pd.notna(x) else ""
        )
    if "Custo Total" in base_display.columns:
        base_display["Custo Total"] = base_display["Custo Total"].apply(moeda_br)

    # Renomeia e formata Ult_Movimentacao
    if "Ult_Movimentacao" in base_display.columns:
        base_display["Ult_Movimentacao"] = pd.to_datetime(
            base_display["Ult_Movimentacao"], errors="coerce"
        ).apply(lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "")
        base_display = base_display.rename(columns={"Ult_Movimentacao": "Ult Movimento"})

    st.caption(f"{len(base)} produtos")
    st.dataframe(base_display, use_container_width=True, hide_index=True)
