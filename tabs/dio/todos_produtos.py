import streamlit as st
import numpy as np
import io


def render(df, modo, label_consumo, data_selecionada, moeda_br):

    st.subheader("Todos os Produtos")

    busca = st.text_input("🔍 Buscar por produto ou descrição", "")

    df_tabela = (
        df[[
            "Empresa / Filial", "Produto", "Descricao",
            "Saldo Atual", "Custo Total", "Vlr Unit",
            "Consumo_exib", "Consumo_Diario",
            "DIO_calc", "DIO_fmt_calc", "Faixa_calc"
        ]]
        .copy()
        .rename(columns={
            "Consumo_exib":   label_consumo,
            "DIO_calc":       "DIO",
            "DIO_fmt_calc":   "Tempo DIO",
            "Faixa_calc":     "Faixa DIO",
            "Consumo_Diario": "Consumo/Dia",
        })
    )

    if busca:
        mask = (
            df_tabela["Produto"].astype(str).str.contains(busca, case=False, na=False) |
            df_tabela["Descricao"].astype(str).str.contains(busca, case=False, na=False)
        )
        df_tabela = df_tabela[mask]

    df_display = df_tabela.copy()
    df_display["Custo Total"]  = df_display["Custo Total"].apply(moeda_br)
    df_display["Vlr Unit"]     = df_display["Vlr Unit"].apply(moeda_br)
    df_display["Consumo/Dia"]  = df_display["Consumo/Dia"].apply(lambda x: f"{x:.4f}")
    df_display["DIO"]          = df_display["DIO"].apply(lambda x: f"{x:.1f}" if x != np.inf else "∞")

    st.caption(f"{len(df_tabela)} produtos encontrados")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    buffer_xlsx = io.BytesIO()
    df_tabela.to_excel(buffer_xlsx, index=False)
    buffer_xlsx.seek(0)
    st.download_button(
        label="📥 Exportar Excel",
        data=buffer_xlsx.getvalue(),
        file_name=f"dio_{modo.lower().replace(' ','_')}_{data_selecionada.strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
