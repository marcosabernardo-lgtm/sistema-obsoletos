import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np
import io

from utils.navbar import render_navbar, render_filtros_topo

st.set_page_config(page_title="Dashboard DIO", layout="wide")
render_navbar("Dashboard DIO")

# -------------------------------------------------
# CSS
# -------------------------------------------------

st.markdown("""
<style>

/* Esconde sidebar */
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

/* HEADER TABLE */
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataFrame"] thead th {
    background-color:#0f5a60 !important;
    color:white !important;
    font-weight:600 !important;
    border-bottom: 1px solid #EC6E21 !important;
}

/* ROW COLOR */
div[data-testid="stDataFrame"] div[role="gridcell"]{
    background-color:#0f5a60 !important;
}

/* KPI */
.kpi-card{
    background-color:#005562;
    border:2px solid #EC6E21;
    padding:16px;
    border-radius:10px;
    text-align:center;
    min-height:100px;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    gap:4px;
}

.kpi-title{
    font-size:13px;
    color:white;
    line-height:1.2;
    white-space:nowrap;
}

.kpi-value{
    font-size:22px;
    font-weight:700;
    color:white;
    line-height:1.2;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    width:100%;
}

</style>
""", unsafe_allow_html=True)

st.title("📦 Dashboard DIO — Days Inventory Outstanding")
st.markdown("---")

# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_numero(valor):
    return f"{valor:,.0f}".replace(",", ".")

ORDEM_FAIXAS = [
    "Até 30 dias",
    "31–90 dias",
    "91–180 dias",
    "181–365 dias",
    "+ 1 ano",
    "Sem consumo"
]

CORES_FAIXAS = {
    "Até 30 dias":   "#2ecc71",
    "31–90 dias":    "#f1c40f",
    "91–180 dias":   "#e67e22",
    "181–365 dias":  "#e74c3c",
    "+ 1 ano":       "#8e44ad",
    "Sem consumo":   "#7f8c8d"
}

def categorizar_dio(dio):
    if dio == np.inf or pd.isna(dio):
        return "Sem consumo"
    if dio <= 30:   return "Até 30 dias"
    if dio <= 90:   return "31–90 dias"
    if dio <= 180:  return "91–180 dias"
    if dio <= 365:  return "181–365 dias"
    return "+ 1 ano"

def formatar_dio(dio):
    if dio == np.inf or pd.isna(dio):
        return "Sem consumo"
    dias  = int(round(dio))
    anos  = dias // 365
    meses = (dias % 365) // 30
    d     = (dias % 365) % 30
    partes = []
    if anos:  partes.append(f"{anos} ano{'s' if anos > 1 else ''}")
    if meses: partes.append(f"{meses} {'meses' if meses > 1 else 'mês'}")
    if d or not partes: partes.append(f"{d} dia{'s' if d != 1 else ''}")
    return " ".join(partes)

# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------

@st.cache_data
def carregar_base(pasta):
    arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith(".parquet")]
    df_all = pd.concat([pd.read_parquet(a) for a in arquivos], ignore_index=True)
    df_all["Data Fechamento"] = pd.to_datetime(df_all["Data Fechamento"])
    return df_all.sort_values("Data Fechamento")


PASTA_DIO = "data/dio"

if not os.path.exists(PASTA_DIO):
    st.warning("⚠️ Nenhuma base encontrada em **data/dio**. Processe o DIO primeiro no app principal.")
    st.stop()

arquivos = [f for f in os.listdir(PASTA_DIO) if f.endswith(".parquet")]

if not arquivos:
    st.warning("⚠️ Nenhum arquivo parquet encontrado em **data/dio**.")
    st.stop()

df_all = carregar_base(PASTA_DIO)

# -------------------------------------------------
# FILTROS SIDEBAR
# -------------------------------------------------

datas_disponiveis = sorted(df_all["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt_list = [d.strftime("%d/%m/%Y") for d in datas_disponiveis]
datas_map = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

data_preview = pd.Timestamp(datas_disponiveis[0])
df_preview = df_all[df_all["Data Fechamento"] == data_preview]
empresas_disponiveis = sorted(df_preview["Empresa / Filial"].dropna().unique())

filtros = render_filtros_topo(
    datas=datas_fmt_list,
    empresas=empresas_disponiveis,
    extras={"Faixa DIO": ORDEM_FAIXAS},
    key_prefix="dio"
)

data_selecionada = pd.Timestamp(datas_map[filtros["data"]])
empresas_sel     = filtros["empresas"]
faixas_sel       = filtros.get("faixa_dio", [])

# -------------------------------------------------
# BASE FILTRADA
# -------------------------------------------------

df = df_all[df_all["Data Fechamento"] == data_selecionada].copy()

if empresas_sel:
    df = df[df["Empresa / Filial"].isin(empresas_sel)]

# -------------------------------------------------
# MODO
# -------------------------------------------------

if "modo_dio" not in st.session_state:
    st.session_state["modo_dio"] = "Por Qtd"

modo = st.session_state["modo_dio"]

if modo == "Por Valor":
    df["Consumo_Diario_Valor"] = df["Consumo_Diario"] * df["Vlr Unit"]
    df["DIO_calc"] = np.where(
        df["Consumo_Diario_Valor"] > 0,
        df["Custo Total"] / df["Consumo_Diario_Valor"],
        np.inf
    )
    label_eixo    = "DIO Valor (dias)"
    label_consumo = "Consumo 12m (R$)"
    df["Consumo_exib"] = df["Consumo_12m"] * df["Vlr Unit"]
else:
    df["DIO_calc"]     = df["DIO"]
    label_eixo        = "DIO Qtd (dias)"
    label_consumo     = "Consumo 12m (un)"
    df["Consumo_exib"] = df["Consumo_12m"]

df["Faixa_calc"]   = df["DIO_calc"].apply(categorizar_dio)
df["DIO_fmt_calc"] = df["DIO_calc"].apply(formatar_dio)

if faixas_sel:
    df = df[df["Faixa_calc"].isin(faixas_sel)]

# -------------------------------------------------
# KPIs
# -------------------------------------------------

total_itens   = len(df)
sem_consumo   = (df["Faixa_calc"] == "Sem consumo").sum()
custo_total   = df["Custo Total"].sum()
custo_sem_consumo = df[df["Faixa_calc"] == "Sem consumo"]["Custo Total"].sum()
perc_sem_consumo  = (custo_sem_consumo / custo_total * 100) if custo_total > 0 else 0

df_com_dio    = df[df["DIO_calc"] != np.inf].copy()
dio_medio     = df_com_dio["DIO_calc"].mean() if not df_com_dio.empty else 0

dio_ponderado = (
    (df_com_dio["DIO_calc"] * df_com_dio["Custo Total"]).sum()
    / df_com_dio["Custo Total"].sum()
    if df_com_dio["Custo Total"].sum() > 0 else 0
)

col1, col2, col3 = st.columns(3)

col1.markdown(f"""<div class="kpi-card">
<div class="kpi-title">Total de Itens</div>
<div class="kpi-value">{fmt_numero(total_itens)}</div>
</div>""", unsafe_allow_html=True)

col2.markdown(f"""<div class="kpi-card">
<div class="kpi-title">Valor em Estoque</div>
<div class="kpi-value">{moeda_br(custo_total)}</div>
</div>""", unsafe_allow_html=True)

col3.markdown(f"""<div class="kpi-card">
<div class="kpi-title">Itens Sem Consumo</div>
<div class="kpi-value">{fmt_numero(sem_consumo)}</div>
</div>""", unsafe_allow_html=True)

st.markdown("")

col4, col5, col6 = st.columns(3)

col4.markdown(f"""<div class="kpi-card">
<div class="kpi-title">DIO Médio ({modo})</div>
<div class="kpi-value">{int(round(dio_medio))} dias</div>
</div>""", unsafe_allow_html=True)

col5.markdown(f"""<div class="kpi-card">
<div class="kpi-title">DIO Ponderado ({modo})</div>
<div class="kpi-value">{int(round(dio_ponderado))} dias</div>
</div>""", unsafe_allow_html=True)

col6.markdown(f"""<div class="kpi-card">
<div class="kpi-title">Capital Imobilizado Sem Consumo</div>
<div class="kpi-value">{moeda_br(custo_sem_consumo)}</div>
<div class="kpi-title" style="color:#EC6E21;font-weight:700">{perc_sem_consumo:.1f}% do estoque total</div>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# FILTRO POR QTD / POR VALOR
# -------------------------------------------------

novo_modo = st.radio(
    "Calcular DIO por",
    ["Por Qtd", "Por Valor"],
    index=0 if st.session_state["modo_dio"] == "Por Qtd" else 1,
    horizontal=True,
    key="radio_modo_dio"
)

if novo_modo != st.session_state["modo_dio"]:
    st.session_state["modo_dio"] = novo_modo
    st.rerun()

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Distribuição por Faixa DIO",
    "🏆 Top 20 Maior DIO",
    "📋 Todos os Produtos",
    "🔗 Cruzamento Obsoletos",
    "📚 Base Histórica DIO"
])

# ── TAB 1 ─────────────────────────────────────────────────

with tab1:

    st.subheader(f"Distribuição por Faixa DIO — {modo}")

    col_a, col_b = st.columns(2)

    df_dist = (
        df.groupby("Faixa_calc", as_index=False)
        .agg(Itens=("Produto", "count"), Custo=("Custo Total", "sum"))
        .rename(columns={"Faixa_calc": "Faixa DIO"})
    )
    df_dist["Faixa DIO"] = pd.Categorical(df_dist["Faixa DIO"], categories=ORDEM_FAIXAS, ordered=True)
    df_dist = df_dist.sort_values("Faixa DIO")

    with col_a:
        st.markdown("**Quantidade de Itens por Faixa**")
        st.altair_chart(
            alt.Chart(df_dist)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Faixa DIO:N", sort=ORDEM_FAIXAS, title="Faixa DIO",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                y=alt.Y("Itens:Q", title="Qtd Itens",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(domain=list(CORES_FAIXAS.keys()),
                                                range=list(CORES_FAIXAS.values())),
                                legend=None),
                tooltip=["Faixa DIO", "Itens"]
            )
            .properties(height=350, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72"),
            use_container_width=True
        )

    with col_b:
        st.markdown("**Valor (Custo Total) por Faixa**")
        st.altair_chart(
            alt.Chart(df_dist)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Faixa DIO:N", sort=ORDEM_FAIXAS, title="Faixa DIO",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                y=alt.Y("Custo:Q", title="Custo Total (R$)",
                        axis=alt.Axis(labelColor="white", titleColor="white", format=",.0f")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(domain=list(CORES_FAIXAS.keys()),
                                                range=list(CORES_FAIXAS.values())),
                                legend=None),
                tooltip=["Faixa DIO", alt.Tooltip("Custo:Q", format=",.2f", title="Custo R$")]
            )
            .properties(height=350, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72"),
            use_container_width=True
        )

    st.markdown("**Distribuição por Empresa / Filial**")
    df_emp = (
        df.groupby(["Empresa / Filial", "Faixa_calc"], as_index=False)
        .agg(Itens=("Produto", "count"))
        .rename(columns={"Faixa_calc": "Faixa DIO"})
    )
    df_emp["Faixa DIO"] = pd.Categorical(df_emp["Faixa DIO"], categories=ORDEM_FAIXAS, ordered=True)
    df_pivot = (
        df_emp.pivot_table(
            index="Empresa / Filial", columns="Faixa DIO",
            values="Itens", aggfunc="sum", fill_value=0
        ).reset_index()
    )
    cols_pres = ["Empresa / Filial"] + [f for f in ORDEM_FAIXAS if f in df_pivot.columns]
    st.dataframe(df_pivot[cols_pres], use_container_width=True, hide_index=True)


# ── TAB 2 ─────────────────────────────────────────────────

with tab2:

    st.subheader(f"Top 20 — Maior DIO {modo} (excluindo 'Sem consumo')")

    df_top = (
        df[df["DIO_calc"] != np.inf]
        .nlargest(20, "DIO_calc")
        [["Empresa / Filial", "Produto", "Descricao",
          "Saldo Atual", "Custo Total", "Consumo_exib",
          "DIO_calc", "DIO_fmt_calc", "Faixa_calc"]]
        .copy()
        .rename(columns={
            "DIO_calc":     "DIO",
            "DIO_fmt_calc": "Tempo DIO",
            "Faixa_calc":   "Faixa DIO",
            "Consumo_exib": label_consumo,
        })
    )

    if df_top.empty:
        st.info("Nenhum produto com DIO calculado para os filtros selecionados.")
    else:
        df_top_chart = df_top.copy()
        df_top_chart["Label"] = df_top_chart["Produto"] + " — " + df_top_chart["Descricao"].str[:30]

        st.altair_chart(
            alt.Chart(df_top_chart)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#EC6E21")
            .encode(
                y=alt.Y("Label:N", sort="-x", title=None,
                        axis=alt.Axis(labelColor="white", labelLimit=300)),
                x=alt.X("DIO:Q", title=label_eixo,
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                tooltip=["Empresa / Filial", "Produto", "Descricao",
                         alt.Tooltip("DIO:Q", format=".0f", title=label_eixo),
                         "Tempo DIO", "Faixa DIO"]
            )
            .properties(height=500, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72"),
            use_container_width=True
        )

        df_top_display = df_top.copy()
        df_top_display["Custo Total"] = df_top_display["Custo Total"].apply(moeda_br)
        df_top_display["DIO"] = df_top_display["DIO"].apply(lambda x: f"{x:.1f}")
        st.dataframe(df_top_display, use_container_width=True, hide_index=True)


# ── TAB 3 ─────────────────────────────────────────────────

with tab3:

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

# ── TAB 4: Cruzamento Obsoletos ───────────────────────────

with tab4:

    st.subheader("🔗 Cruzamento DIO × Obsolescência")

    PASTA_OBS = "data/obsoletos"

    if not os.path.exists(PASTA_OBS) or not [f for f in os.listdir(PASTA_OBS) if f.endswith(".parquet")]:
        st.warning("⚠️ Base de obsoletos não encontrada em **data/obsoletos**. Processe os obsoletos primeiro.")
    else:

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

        ORDEM_ZONAS = [
            "🔴 Obsoleto + Sem Consumo",
            "🟠 Obsoleto mas com DIO",
            "🟡 Sem Consumo (não obsoleto)",
            "🟢 Ativo"
        ]
        CORES_ZONAS = {
            "🔴 Obsoleto + Sem Consumo":     "#e74c3c",
            "🟠 Obsoleto mas com DIO":       "#e67e22",
            "🟡 Sem Consumo (não obsoleto)": "#f1c40f",
            "🟢 Ativo":                      "#2ecc71"
        }

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
        df_cross_display["Custo Total"]   = df_cross_display["Custo Total"].apply(moeda_br)
        df_cross_display["Meses Ult Mov"] = df_cross_display["Meses Ult Mov"].apply(
            lambda x: f"{int(x)} meses" if pd.notna(x) else "Sem mov."
        )
        df_cross_display["Status Estoque"] = df_cross_display["Status Estoque"].fillna("—")
        df_cross_display = df_cross_display.rename(columns={"DIO_fmt_calc": "DIO", "Faixa_calc": "Faixa DIO"})

        st.caption(f"{len(df_tabela_cross)} produtos · Total: {moeda_br(df_tabela_cross['Custo Total'].sum())}")
        st.dataframe(df_cross_display, use_container_width=True, hide_index=True)

        def gerar_excel_cruzamento(df_export):
            output = io.BytesIO()
            df_out = df_export.copy()
            df_out = df_out.rename(columns={"DIO_fmt_calc": "DIO Formatado", "Faixa_calc": "Faixa DIO"})
            df_out["Meses Ult Mov"] = df_out["Meses Ult Mov"].apply(
                lambda x: f"{int(x)} meses" if pd.notna(x) else "Sem mov."
            )
            df_out["Status Estoque"] = df_out["Status Estoque"].fillna("—")

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
            data=gerar_excel_cruzamento(df_tabela_cross),
            file_name=f"cruzamento_dio_obsoletos_{data_selecionada.strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ── TAB 5: Base Histórica DIO ─────────────────────────────

with tab5:

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
