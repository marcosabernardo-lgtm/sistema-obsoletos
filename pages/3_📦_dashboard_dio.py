import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np

st.set_page_config(page_title="Dashboard DIO", layout="wide")

# -------------------------------------------------
# CSS — mesmo padrão visual das outras pages
# -------------------------------------------------

st.markdown("""
<style>

/* SIDEBAR */
section[data-testid="stSidebar"]{
    width:260px !important;
}

/* FILTROS */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] div[data-baseweb="select"] > div:focus-within {
    border: 2px solid #EC6E21 !important;
    border-radius: 8px !important;
    background-color: #005562 !important;
    color: white !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] div {
    color: white !important;
}

section[data-testid="stSidebar"] label {
    color: white !important;
    font-weight: 600 !important;
}

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
}

.kpi-title{
    font-size:14px;
    color:white;
}

.kpi-value{
    font-size:26px;
    font-weight:700;
    color:white;
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

# -------------------------------------------------
# CARREGAR BASE
# -------------------------------------------------

@st.cache_data
def carregar_base(pasta):
    arquivos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if f.endswith(".parquet")
    ]
    lista = []
    for arq in arquivos:
        df = pd.read_parquet(arq)
        lista.append(df)
    df_all = pd.concat(lista, ignore_index=True)
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

st.sidebar.header("Filtros")

datas_disponiveis = sorted(df_all["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

data_sel = st.sidebar.selectbox(
    "Data de Fechamento",
    options=list(datas_fmt.keys()),
    index=0
)
data_selecionada = pd.Timestamp(datas_fmt[data_sel])

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    sorted(df_all["Empresa / Filial"].dropna().unique())
)

faixas_sel = st.sidebar.multiselect(
    "Faixa DIO",
    options=ORDEM_FAIXAS,
    default=[]
)

# -------------------------------------------------
# BASE FILTRADA
# -------------------------------------------------

df = df_all[df_all["Data Fechamento"] == data_selecionada].copy()

if empresas_sel:
    df = df[df["Empresa / Filial"].isin(empresas_sel)]

if faixas_sel:
    df = df[df["Faixa DIO"].isin(faixas_sel)]

# -------------------------------------------------
# KPIs
# -------------------------------------------------

total_itens   = len(df)
sem_consumo   = (df["Faixa DIO"] == "Sem consumo").sum()
custo_total   = df["Custo Total"].sum()

# DIO médio simples (exclui sem consumo e infinito)
df_com_dio = df[df["DIO"] != np.inf].copy()
dio_medio = df_com_dio["DIO"].mean() if not df_com_dio.empty else 0

# DIO ponderado por custo
if df_com_dio["Custo Total"].sum() > 0:
    dio_ponderado = (
        (df_com_dio["DIO"] * df_com_dio["Custo Total"]).sum()
        / df_com_dio["Custo Total"].sum()
    )
else:
    dio_ponderado = 0

col1, col2, col3, col4, col5 = st.columns(5)

col1.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Total de Itens</div>
<div class="kpi-value">{fmt_numero(total_itens)}</div>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Valor em Estoque</div>
<div class="kpi-value">{moeda_br(custo_total)}</div>
</div>
""", unsafe_allow_html=True)

col3.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">DIO Médio</div>
<div class="kpi-value">{int(round(dio_medio))} dias</div>
</div>
""", unsafe_allow_html=True)

col4.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">DIO Ponderado (Custo)</div>
<div class="kpi-value">{int(round(dio_ponderado))} dias</div>
</div>
""", unsafe_allow_html=True)

col5.markdown(f"""
<div class="kpi-card">
<div class="kpi-title">Itens Sem Consumo</div>
<div class="kpi-value">{fmt_numero(sem_consumo)}</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2, tab3 = st.tabs([
    "📊 Distribuição por Faixa DIO",
    "🏆 Top 20 Maior DIO",
    "📋 Todos os Produtos"
])

# ── TAB 1: Distribuição por Faixa DIO ─────────────────────

with tab1:

    st.subheader("Distribuição por Faixa DIO")

    col_a, col_b = st.columns(2)

    # Contagem de itens por faixa
    df_dist = (
        df.groupby("Faixa DIO", as_index=False)
        .agg(Itens=("Produto", "count"), Custo=("Custo Total", "sum"))
    )
    df_dist["Faixa DIO"] = pd.Categorical(
        df_dist["Faixa DIO"], categories=ORDEM_FAIXAS, ordered=True
    )
    df_dist = df_dist.sort_values("Faixa DIO")
    df_dist["Cor"] = df_dist["Faixa DIO"].map(CORES_FAIXAS)

    with col_a:
        st.markdown("**Quantidade de Itens por Faixa**")
        chart_itens = (
            alt.Chart(df_dist)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Faixa DIO:N", sort=ORDEM_FAIXAS, title="Faixa DIO",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                y=alt.Y("Itens:Q", title="Qtd Itens",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(
                                    domain=list(CORES_FAIXAS.keys()),
                                    range=list(CORES_FAIXAS.values())
                                ),
                                legend=None),
                tooltip=["Faixa DIO", "Itens"]
            )
            .properties(height=350, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72")
        )
        st.altair_chart(chart_itens, use_container_width=True)

    with col_b:
        st.markdown("**Valor (Custo Total) por Faixa**")
        chart_custo = (
            alt.Chart(df_dist)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("Faixa DIO:N", sort=ORDEM_FAIXAS, title="Faixa DIO",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                y=alt.Y("Custo:Q", title="Custo Total (R$)",
                        axis=alt.Axis(labelColor="white", titleColor="white",
                                      format=",.0f")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(
                                    domain=list(CORES_FAIXAS.keys()),
                                    range=list(CORES_FAIXAS.values())
                                ),
                                legend=None),
                tooltip=["Faixa DIO",
                         alt.Tooltip("Custo:Q", format=",.2f", title="Custo R$")]
            )
            .properties(height=350, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72")
        )
        st.altair_chart(chart_custo, use_container_width=True)

    # Tabela resumo por empresa x faixa
    st.markdown("**Distribuição por Empresa / Filial**")
    df_emp = (
        df.groupby(["Empresa / Filial", "Faixa DIO"], as_index=False)
        .agg(Itens=("Produto", "count"), Custo=("Custo Total", "sum"))
    )
    df_emp["Faixa DIO"] = pd.Categorical(
        df_emp["Faixa DIO"], categories=ORDEM_FAIXAS, ordered=True
    )
    df_pivot = (
        df_emp
        .pivot_table(
            index="Empresa / Filial",
            columns="Faixa DIO",
            values="Itens",
            aggfunc="sum",
            fill_value=0
        )
        .reset_index()
    )
    # Garante ordem das colunas
    cols_presentes = ["Empresa / Filial"] + [f for f in ORDEM_FAIXAS if f in df_pivot.columns]
    st.dataframe(df_pivot[cols_presentes], use_container_width=True, hide_index=True)


# ── TAB 2: Top 20 Maior DIO ───────────────────────────────

with tab2:

    st.subheader("Top 20 — Maior DIO (excluindo 'Sem consumo')")

    df_top = (
        df[df["DIO"] != np.inf]
        .nlargest(20, "DIO")
        [[
            "Empresa / Filial", "Produto", "Descricao",
            "Saldo Atual", "Custo Total", "Consumo_12m",
            "DIO", "DIO_Formatado", "Faixa DIO"
        ]]
        .copy()
    )

    if df_top.empty:
        st.info("Nenhum produto com DIO calculado para os filtros selecionados.")
    else:
        # Gráfico horizontal
        df_top_chart = df_top.head(20).copy()
        df_top_chart["Label"] = df_top_chart["Produto"] + " — " + df_top_chart["Descricao"].str[:30]

        chart_top = (
            alt.Chart(df_top_chart)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                y=alt.Y("Label:N", sort="-x", title=None,
                        axis=alt.Axis(labelColor="white", labelLimit=300)),
                x=alt.X("DIO:Q", title="DIO (dias)",
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(
                                    domain=list(CORES_FAIXAS.keys()),
                                    range=list(CORES_FAIXAS.values())
                                ),
                                legend=alt.Legend(
                                    labelColor="white", titleColor="white",
                                    title="Faixa DIO"
                                )),
                tooltip=[
                    "Empresa / Filial", "Produto", "Descricao",
                    alt.Tooltip("DIO:Q", format=".0f", title="DIO (dias)"),
                    "DIO_Formatado", "Faixa DIO"
                ]
            )
            .properties(height=500, background="transparent")
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#1a6b72")
        )
        st.altair_chart(chart_top, use_container_width=True)

        # Tabela detalhada
        df_top_display = df_top.copy()
        df_top_display["Custo Total"] = df_top_display["Custo Total"].apply(moeda_br)
        df_top_display["DIO"] = df_top_display["DIO"].apply(lambda x: f"{x:.1f}")
        df_top_display = df_top_display.rename(columns={
            "DIO_Formatado": "Tempo",
            "Consumo_12m": "Consumo 12m (un)"
        })
        st.dataframe(df_top_display, use_container_width=True, hide_index=True)


# ── TAB 3: Todos os Produtos ──────────────────────────────

with tab3:

    st.subheader("Todos os Produtos")

    # Busca textual
    busca = st.text_input("🔍 Buscar por produto ou descrição", "")

    df_tabela = df[[
        "Empresa / Filial", "Produto", "Descricao",
        "Saldo Atual", "Custo Total", "Vlr Unit",
        "Consumo_12m", "Consumo_Diario",
        "DIO", "DIO_Formatado", "Faixa DIO"
    ]].copy()

    if busca:
        mask = (
            df_tabela["Produto"].astype(str).str.contains(busca, case=False, na=False) |
            df_tabela["Descricao"].astype(str).str.contains(busca, case=False, na=False)
        )
        df_tabela = df_tabela[mask]

    # Formata colunas de exibição
    df_display = df_tabela.copy()
    df_display["Custo Total"] = df_display["Custo Total"].apply(moeda_br)
    df_display["Vlr Unit"]    = df_display["Vlr Unit"].apply(moeda_br)
    df_display["Consumo_Diario"] = df_display["Consumo_Diario"].apply(lambda x: f"{x:.4f}")
    df_display["DIO"] = df_display["DIO"].apply(
        lambda x: f"{x:.1f}" if x != np.inf else "∞"
    )
    df_display = df_display.rename(columns={
        "DIO_Formatado":  "Tempo DIO",
        "Consumo_12m":    "Consumo 12m (un)",
        "Consumo_Diario": "Consumo/Dia"
    })

    st.caption(f"{len(df_tabela)} produtos encontrados")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Download
    csv = df_tabela.to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="⬇️ Exportar CSV",
        data=csv.encode("utf-8-sig"),
        file_name=f"dio_{data_selecionada.strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )