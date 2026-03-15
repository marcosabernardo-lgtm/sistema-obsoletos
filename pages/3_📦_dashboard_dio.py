import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np

st.set_page_config(page_title="Dashboard DIO", layout="wide")

# -------------------------------------------------
# CSS
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

st.sidebar.header("Filtros")

datas_disponiveis = sorted(df_all["Data Fechamento"].dt.date.unique(), reverse=True)
datas_fmt = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

data_sel = st.sidebar.selectbox("Data de Fechamento", options=list(datas_fmt.keys()), index=0)
data_selecionada = pd.Timestamp(datas_fmt[data_sel])

empresas_sel = st.sidebar.multiselect(
    "Empresa / Filial",
    sorted(df_all["Empresa / Filial"].dropna().unique())
)

faixas_sel = st.sidebar.multiselect("Faixa DIO", options=ORDEM_FAIXAS, default=[])

# -------------------------------------------------
# BASE FILTRADA (sem faixa ainda — faixa depende do modo)
# -------------------------------------------------

df = df_all[df_all["Data Fechamento"] == data_selecionada].copy()

if empresas_sel:
    df = df[df["Empresa / Filial"].isin(empresas_sel)]

# -------------------------------------------------
# MODO — session_state permite renderizar radio abaixo dos KPIs
# -------------------------------------------------

if "modo_dio" not in st.session_state:
    st.session_state["modo_dio"] = "Por Qtd"

modo = st.session_state["modo_dio"]

if modo == "Por Valor":
    # Consumo em R$/dia = consumo_diario (un/dia) × vlr_unit (R$/un)
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

# Aplica filtro de faixa (agora calculado com o modo correto)
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

# Linha 1 — visão geral
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

# Linha 2 — DIO e capital parado
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
# FILTRO POR QTD / POR VALOR — abaixo dos KPIs
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

tab1, tab2, tab3 = st.tabs([
    "📊 Distribuição por Faixa DIO",
    "🏆 Top 20 Maior DIO",
    "📋 Todos os Produtos"
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
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                y=alt.Y("Label:N", sort="-x", title=None,
                        axis=alt.Axis(labelColor="white", labelLimit=300)),
                x=alt.X("DIO:Q", title=label_eixo,
                        axis=alt.Axis(labelColor="white", titleColor="white")),
                color=alt.Color("Faixa DIO:N",
                                scale=alt.Scale(domain=list(CORES_FAIXAS.keys()),
                                                range=list(CORES_FAIXAS.values())),
                                legend=alt.Legend(labelColor="white", titleColor="white",
                                                  title="Faixa DIO")),
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

    csv = df_tabela.to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="⬇️ Exportar CSV",
        data=csv.encode("utf-8-sig"),
        file_name=f"dio_{modo.lower().replace(' ','_')}_{data_selecionada.strftime('%Y-%m-%d')}.csv",
        mime="text/csv"
    )