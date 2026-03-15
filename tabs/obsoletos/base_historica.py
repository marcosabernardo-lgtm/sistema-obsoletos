import streamlit as st
import pandas as pd
import io


def render(df_filtrado, moeda_br):

    # df_filtrado já vem com apenas obsoletos — precisamos do df completo
    # O dashboard passa df_kpi completo como segundo argumento opcional
    # Para manter compatibilidade, usamos session_state para o toggle

    col_toggle, _ = st.columns([2, 8])

    with col_toggle:
        visao = st.radio(
            "Visualizar",
            ["Obsoleto", "Geral"],
            horizontal=True,
            key="base_historica_visao"
        )

    if visao == "Obsoleto":
        base = df_filtrado.copy()
    else:
        # df_filtrado pode ter vindo filtrado; pedimos o df completo via session_state
        base = st.session_state.get("df_kpi_completo", df_filtrado).copy()

    base["Data Fechamento"] = pd.to_datetime(base["Data Fechamento"]).dt.date

    # Versão display formatada
    base_display = base.copy()

    if "Vlr Unit" in base_display.columns:
        base_display["Vlr Unit"] = pd.to_numeric(base_display["Vlr Unit"], errors="coerce").apply(
            lambda x: moeda_br(x) if pd.notna(x) else ""
        )

    base_display["Custo Total"] = base_display["Custo Total"].apply(moeda_br)

    st.caption(f"{len(base)} produtos")

    st.dataframe(
        base_display,
        use_container_width=True,
        hide_index=True
    )

    # Exportar Excel
    buffer = io.BytesIO()
    base.to_excel(buffer, index=False)
    buffer.seek(0)

    data_ref = base["Data Fechamento"].max() if not base.empty else "sem_data"
    label_visao = "obsoletos" if visao == "Obsoleto" else "geral"

    st.download_button(
        label="📥 Exportar Excel",
        data=buffer.getvalue(),
        file_name=f"base_historica_{label_visao}_{data_ref}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )