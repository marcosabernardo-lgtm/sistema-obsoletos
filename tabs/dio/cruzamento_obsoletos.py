import streamlit as st
import pandas as pd
import os
import io
import numpy as np


ORDEM_ZONAS = [
    "🔴 Obsoleto + Sem Consumo",
    "🟠 Obsoleto mas com DIO",
    "🟡 Sem Consumo (não obsoleto)",
    "🟢 Ativo"
]


def render(df, data_selecionada, empresas_sel, moeda_br):

    st.subheader("🔗 Cruzamento DIO × Obsolescência")

    PASTA_OBS = "data/obsoletos"

    if not os.path.exists(PASTA_OBS) or not [f for f in os.listdir(PASTA_OBS) if f.endswith(".parquet")]:
        st.warning("⚠️ Base de obsoletos não encontrada. Processe os obsoletos primeiro.")
        return

    @st.cache_data
    def carregar_obsoletos(pasta):
        arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith(".parquet")]
        df_obs = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
        df_obs["Data Fechamento"] = pd.to_datetime(df_obs["Data Fechamento"])
        return df_obs

    df_obs_full = carregar_obsoletos(PASTA_OBS)
    df_obs = df_obs_full[df_obs_full["Data Fechamento"] == data_selecionada].copy()

    if empresas_sel:
        df_obs = df_obs[df_obs["Empresa / Filial"].isin(empresas_sel)]

    df_dio_base = df[["Empresa / Filial", "Produto", "Custo Total",
                       "DIO_calc", "DIO_fmt_calc", "Faixa_calc"]].copy()
    df_obs_base = df_obs[["Empresa / Filial", "Produto",
                           "Status Estoque", "Meses Ult Mov"]].copy()

    df_cross = df_dio_base.merge(df_obs_base, on=["Empresa / Filial", "Produto"], how="left")

    def zona_risco(row):
        obsoleto    = row.get("Status Estoque") == "Obsoleto"
        sem_consumo = row["Faixa_calc"] == "Sem consumo"
        if obsoleto and sem_consumo:     return "🔴 Obsoleto + Sem Consumo"
        if obsoleto and not sem_consumo: return "🟠 Obsoleto mas com DIO"
        if not obsoleto and sem_consumo: return "🟡 Sem Consumo (não obsoleto)"
        return "🟢 Ativo"

    df_cross["Zona de Risco"] = df_cross.apply(zona_risco, axis=1)

    resumo = df_cross.groupby("Zona de Risco").agg(
        Itens=("Produto", "count"), Custo=("Custo Total", "sum")
    ).reindex(ORDEM_ZONAS).fillna(0).reset_index()

    custo_total_cross = df_cross["Custo Total"].sum()

    st.markdown("##### Distribuição por Zona de Risco")
    cols = st.columns(4)
    for i, row in resumo.iterrows():
        perc = (row["Custo"] / custo_total_cross * 100) if custo_total_cross > 0 else 0
        cols[i].markdown(f"""<div class="kpi-card">
<div class="kpi-title">{row['Zona de Risco']}</div>
<div class="kpi-value">{moeda_br(row['Custo'])}</div>
<div class="kpi-title" style="color:#EC6E21;font-weight:700">{int(row['Itens'])} itens · {perc:.1f}%</div>
</div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("##### Detalhamento completo por Zona de Risco")

    zonas_filtro = st.multiselect(
        "Filtrar por Zona de Risco",
        options=ORDEM_ZONAS,
        default=ORDEM_ZONAS,
        key="filtro_zona"
    )

    df_tabela_cross = df_cross[
        df_cross["Zona de Risco"].isin(zonas_filtro)
    ][[
        "Empresa / Filial", "Produto", "Custo Total",
        "Meses Ult Mov", "Status Estoque",
        "DIO_fmt_calc", "Faixa_calc", "Zona de Risco"
    ]].copy().sort_values(["Zona de Risco", "Custo Total"], ascending=[True, False])

    df_cross_display = df_tabela_cross.copy()
    df_cross_display["Custo Total"]    = df_cross_display["Custo Total"].apply(moeda_br)
    df_cross_display["Meses Ult Mov"]  = df_cross_display["Meses Ult Mov"].apply(
        lambda x: f"{int(x)} meses" if pd.notna(x) else "Sem mov."
    )
    df_cross_display["Status Estoque"] = df_cross_display["Status Estoque"].fillna("—")
    df_cross_display = df_cross_display.rename(columns={"DIO_fmt_calc": "DIO", "Faixa_calc": "Faixa DIO"})

    st.caption(f"{len(df_tabela_cross)} produtos · Total: {moeda_br(df_tabela_cross['Custo Total'].sum())}")
    st.dataframe(df_cross_display, use_container_width=True, hide_index=True)

    def gerar_excel(df_export):
        output = io.BytesIO()
        df_out = df_export.copy()
        df_out = df_out.rename(columns={"DIO_fmt_calc": "DIO Formatado", "Faixa_calc": "Faixa DIO"})
        df_out["Meses Ult Mov"]    = df_out["Meses Ult Mov"].apply(lambda x: f"{int(x)} meses" if pd.notna(x) else "Sem mov.")
        df_out["Status Estoque"]   = df_out["Status Estoque"].fillna("—")

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            resumo_excel = df_out.groupby("Zona de Risco").agg(
                Itens=("Produto", "count"), Custo_Total=("Custo Total", "sum")
            ).reindex(ORDEM_ZONAS).fillna(0).reset_index()
            resumo_excel.columns = ["Zona de Risco", "Qtd Itens", "Custo Total (R$)"]
            resumo_excel.to_excel(writer, sheet_name="Resumo", index=False)
            for zona in ORDEM_ZONAS:
                df_zona = df_out[df_out["Zona de Risco"] == zona].drop(columns=["Zona de Risco"])
                nome_aba = zona.split(" ", 1)[1][:28]
                if not df_zona.empty:
                    df_zona.to_excel(writer, sheet_name=nome_aba, index=False)
            df_out.to_excel(writer, sheet_name="Todos", index=False)

        output.seek(0)
        return output.getvalue()

    st.download_button(
        label="📥 Exportar Excel (todas as zonas)",
        data=gerar_excel(df_tabela_cross),
        file_name=f"cruzamento_dio_obsoletos_{data_selecionada.strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
