import streamlit as st
import pandas as pd
import io


def render(df_filtrado, moeda_br):

    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] > div,
    div[data-testid="stTextInput"] > div > div {
        background-color: #005562 !important;
    }
    div[data-testid="stTextInput"] input {
        border: 1px solid rgba(250,250,250,0.2) !important;
        border-radius: 6px !important;
        color: white !important;
        padding: 8px 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    base = df_filtrado.copy()
    base["Data Fechamento"] = pd.to_datetime(base["Data Fechamento"]).dt.date

    if "Custo Total" in base.columns:
        base = base.sort_values("Custo Total", ascending=False)

    # Formata para exibição
    base_display = base.copy()

    if "Vlr Unit" in base_display.columns:
        base_display["Vlr Unit"] = pd.to_numeric(base_display["Vlr Unit"], errors="coerce").apply(
            lambda x: moeda_br(x) if pd.notna(x) else ""
        )
    if "Custo Total" in base_display.columns:
        base_display["Custo Total"] = base_display["Custo Total"].apply(moeda_br)
    if "Ult_Movimentacao" in base_display.columns:
        base_display["Ult_Movimentacao"] = pd.to_datetime(
            base_display["Ult_Movimentacao"], errors="coerce"
        ).apply(lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "")
        base_display = base_display.rename(columns={"Ult_Movimentacao": "Ult Movimento"})

    col_busca, col_ord, col_dir, col_export = st.columns([3, 2, 1, 1])
    with col_busca:
        busca = st.text_input("🔍 PESQUISAR", placeholder="Produto, empresa, conta...", key="busca_base_obs")
    with col_ord:
        ord_col = st.selectbox("📊 Classificar por", list(base_display.columns), key="ord_col_base_obs")
    with col_dir:
        ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_base_obs")
    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        data_ref = base["Data Fechamento"].max() if not base.empty else "sem_data"
        buffer = io.BytesIO()
        base.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label="📥 Exportar",
            data=buffer.getvalue(),
            file_name=f"base_historica_obsoletos_{data_ref}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    if busca:
        mask = base_display.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
        base_display = base_display[mask]

    ascending = ord_dir == "⬆ Asc"
    try:
        base_display = base_display.sort_values(
            ord_col, ascending=ascending,
            key=lambda x: pd.to_numeric(
                x.astype(str).str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."),
                errors="coerce"
            ).fillna(x.astype(str))
        )
    except Exception:
        pass

    st.caption(f"{len(base_display)} produtos")
    st.dataframe(base_display, use_container_width=True, hide_index=True)
