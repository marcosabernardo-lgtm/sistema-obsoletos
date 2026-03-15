import streamlit as st
import pandas as pd
import io


def render(df_filtrado, moeda_br):

    base = df_filtrado.copy()

    base["Data Fechamento"] = pd.to_datetime(
        base["Data Fechamento"]
    ).dt.date

    # Versão display (formatada)
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

    # Exportar Excel (dados sem formatação de moeda para preservar números)
    buffer = io.BytesIO()
    base.to_excel(buffer, index=False)
    buffer.seek(0)

    data_ref = base["Data Fechamento"].max() if not base.empty else "sem_data"

    st.download_button(
        label="📥 Exportar Excel",
        data=buffer.getvalue(),
        file_name=f"obsoletos_{data_ref}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )