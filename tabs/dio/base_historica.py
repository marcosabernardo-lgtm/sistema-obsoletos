import streamlit as st
import pandas as pd
import numpy as np
import io


def render(df, modo, data_selecionada, moeda_br):

    st.subheader("📚 Base Histórica DIO")

    visao = st.radio("Visualizar", ["Geral", "Sem Consumo"], horizontal=True, key="base_historica_dio_visao")
    busca_hist = st.text_input("🔍 Buscar por produto ou descrição", "", key="busca_base_hist_dio")

    df_base_hist = df[df["Faixa_calc"] == "Sem consumo"].copy() if visao == "Sem Consumo" else df.copy()

    if busca_hist:
        mask = (
            df_base_hist["Produto"].astype(str).str.contains(busca_hist, case=False, na=False) |
            df_base_hist["Descricao"].astype(str).str.contains(busca_hist, case=False, na=False)
        )
        df_base_hist = df_base_hist[mask]

    colunas_exib = [
        "Empresa / Filial", "Produto", "Descricao",
        "Saldo Atual", "Custo Total", "Vlr Unit",
        "Consumo_12m", "Consumo_Diario", "Ult_Mov_DIO",
        "DIO_calc", "DIO_fmt_calc", "Faixa_calc"
    ]
    colunas_presentes = [c for c in colunas_exib if c in df_base_hist.columns]
    df_base_exib = df_base_hist[colunas_presentes].copy().sort_values(
        "Custo Total", ascending=False
    ).reset_index(drop=True)

    df_base_display = df_base_exib.copy()
    df_base_display["Custo Total"]    = df_base_display["Custo Total"].apply(moeda_br)
    df_base_display["Vlr Unit"]       = df_base_display["Vlr Unit"].apply(moeda_br)
    df_base_display["Consumo_Diario"] = df_base_display["Consumo_Diario"].apply(lambda x: f"{x:.6f}")
    df_base_display["DIO_calc"]       = df_base_display["DIO_calc"].apply(lambda x: f"{x:.1f}" if x != np.inf else "∞")
    if "Ult_Mov_DIO" in df_base_display.columns:
        df_base_display["Ult_Mov_DIO"] = pd.to_datetime(
            df_base_display["Ult_Mov_DIO"], errors="coerce"
        ).apply(lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "Sem mov.")

    df_base_display = df_base_display.rename(columns={
        "Consumo_12m":    f"Consumo 12m ({'R$' if modo == 'Por Valor' else 'un'})",
        "Consumo_Diario": "Consumo/Dia",
        "Ult_Mov_DIO":    "Ult. Mov. (Saída/Mov)",
        "DIO_calc":       "DIO (dias)",
        "DIO_fmt_calc":   "DIO Formatado",
        "Faixa_calc":     "Faixa DIO"
    })

    st.caption(f"{len(df_base_hist)} produtos · Fechamento: {data_selecionada.strftime('%d/%m/%Y')} · Visão: {visao}")
    st.dataframe(df_base_display, use_container_width=True, hide_index=True)

    df_excel_hist = df_base_exib.copy()
    if "Ult_Mov_DIO" in df_excel_hist.columns:
        df_excel_hist["Ult_Mov_DIO"] = pd.to_datetime(
            df_excel_hist["Ult_Mov_DIO"], errors="coerce"
        ).apply(lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "Sem mov.")
    df_excel_hist = df_excel_hist.rename(columns={
        "Consumo_12m":    f"Consumo 12m ({'R$' if modo == 'Por Valor' else 'un'})",
        "Consumo_Diario": "Consumo Diario",
        "Ult_Mov_DIO":    "Ult. Mov. (Saida/Mov)",
        "DIO_calc":       "DIO (dias)",
        "DIO_fmt_calc":   "DIO Formatado",
        "Faixa_calc":     "Faixa DIO"
    })
    df_excel_hist["DIO (dias)"] = df_excel_hist["DIO (dias)"].replace(np.inf, 999999)

    buffer_hist = io.BytesIO()
    df_excel_hist.to_excel(buffer_hist, index=False)
    buffer_hist.seek(0)

    st.download_button(
        label="📥 Exportar Excel",
        data=buffer_hist.getvalue(),
        file_name=f"base_historica_dio_{'sem_consumo' if visao == 'Sem Consumo' else 'geral'}_{data_selecionada.strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
