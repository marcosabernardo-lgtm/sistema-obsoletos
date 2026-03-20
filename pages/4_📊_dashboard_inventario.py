import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

from utils.navbar import render_navbar

st.set_page_config(page_title="Dashboard Inventário", layout="wide")
render_navbar("Dashboard Inventário")

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

.kpi-card{
    background-color:#005562;
    border:2px solid #EC6E21;
    padding:16px;
    border-radius:10px;
    text-align:center;
}
.kpi-card-green{
    background-color:#005562;
    border:2px solid #51cf66;
    padding:16px;
    border-radius:10px;
    text-align:center;
}
.kpi-title{ font-size:14px; color:white; }
.kpi-value{ font-size:26px; font-weight:700; color:white; }
.kpi-value-green{ font-size:26px; font-weight:700; color:#51cf66; }

div[data-testid="stRadio"] > div {
    display: flex;
    gap: 10px;
    flex-direction: row !important;
}
div[data-testid="stRadio"] label {
    background-color: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    padding: 6px 20px;
    color: rgba(255,255,255,0.6) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    cursor: pointer;
    transition: all 0.2s;
}
div[data-testid="stRadio"] label:has(input:checked) {
    background-color: rgba(236,110,33,0.15);
    border-color: #EC6E21;
    color: #EC6E21 !important;
}
div[data-testid="stRadio"] input { display: none; }
div[data-testid="stRadio"] > label { display: none; }
</style>
""", unsafe_allow_html=True)

st.title("📋 Dashboard de Inventário")
st.markdown("---")

def moeda_br(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "—"

def fmt_qtd(valor):
    try:
        return f"{float(valor):,.0f}".replace(",", ".")
    except:
        return "—"

CAMINHO = "data/inventario/inventario_historico.parquet"

if not os.path.exists(CAMINHO):
    st.warning("⚠️ Nenhuma base encontrada. Acesse o **Configurador** para processar os dados.")
    st.stop()

try:
    df = pd.read_parquet(CAMINHO)
except Exception as e:
    st.error("Erro ao carregar a base de inventário.")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("⚠️ Base de dados vazia.")
    st.stop()

df["Data_Inventario"] = pd.to_datetime(df["Data_Inventario"])

datas_disponiveis = sorted(df["Data_Inventario"].dt.date.unique(), reverse=True)
datas_fmt_list    = [d.strftime("%d/%m/%Y") for d in datas_disponiveis]
datas_map         = {d.strftime("%d/%m/%Y"): d for d in datas_disponiveis}

st.markdown("""
<style>
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] span {
    color: white !important;
    font-weight: 600 !important;
}
div[data-testid="stSelectbox"] label {
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    color: rgba(255,255,255,0.35) !important;
}
.filtros-container {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 12px 20px 4px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="filtros-container">', unsafe_allow_html=True)
col_data, col_empresa = st.columns([1, 2])

with col_data:
    data_sel = st.selectbox("Fechamento", options=datas_fmt_list, index=0, key="inventario_data")

data_selecionada = pd.Timestamp(datas_map[data_sel])
df_data          = df[df["Data_Inventario"] == data_selecionada]
empresas_disp    = ["Todas"] + sorted(df_data["Nome_Empresa"].dropna().unique().tolist()) if "Nome_Empresa" in df_data.columns else ["Todas"]

with col_empresa:
    empresa_sel = st.selectbox("Empresa / Filial", options=empresas_disp, index=0, key="inventario_empresa")

st.markdown('</div>', unsafe_allow_html=True)

df_kpi = df[df["Data_Inventario"] == data_selecionada].copy()
if empresa_sel != "Todas":
    df_kpi = df_kpi[df_kpi["Nome_Empresa"] == empresa_sel]

df_hist_filtrado = df.copy()
if empresa_sel != "Todas":
    df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["Nome_Empresa"] == empresa_sel]

qtd_inventariada  = df_kpi["Qtd_Itens_Inventariados"].sum() if "Qtd_Itens_Inventariados" in df_kpi.columns else len(df_kpi)
qtd_divergentes   = int(df_kpi["Qtd_Itens_Divergentes"].sum()) if "Qtd_Itens_Divergentes" in df_kpi.columns else 0
acuracidade_itens = (qtd_inventariada - qtd_divergentes) / qtd_inventariada if qtd_inventariada > 0 else 0

valor_inventariado = df_kpi["Valor_Inventariado"].sum() if "Valor_Inventariado" in df_kpi.columns else 0
valor_divergente   = df_kpi["Valor_Divergente"].sum()   if "Valor_Divergente"   in df_kpi.columns else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.markdown(f"""<div class="kpi-card"><div class="kpi-title">Qtd Inventariada</div><div class="kpi-value">{fmt_qtd(qtd_inventariada)}</div></div>""", unsafe_allow_html=True)
col2.markdown(f"""<div class="kpi-card"><div class="kpi-title">Qtd Divergentes</div><div class="kpi-value">{fmt_qtd(qtd_divergentes)}</div></div>""", unsafe_allow_html=True)
col3.markdown(f"""<div class="kpi-card-green"><div class="kpi-title">Acuracidade %</div><div class="kpi-value-green">{acuracidade_itens*100:.2f}%</div></div>""", unsafe_allow_html=True)
col4.markdown(f"""<div class="kpi-card"><div class="kpi-title">Valor Inventariado</div><div class="kpi-value">{moeda_br(valor_inventariado)}</div></div>""", unsafe_allow_html=True)
col5.markdown(f"""<div class="kpi-card"><div class="kpi-title">Valor Divergente</div><div class="kpi-value">{moeda_br(valor_divergente)}</div></div>""", unsafe_allow_html=True)
col6.markdown(f"""<div class="kpi-card-green"><div class="kpi-title">Acuracidade %</div><div class="kpi-value-green">{acuracidade_itens*100:.2f}%</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2 = st.tabs(["📚 Base Histórica", "📊 Análise de Inventário"])

# ── ABA 1: Base Histórica ────────────────────────────────────────────────────
with tab1:

    visao = st.radio(
        "Visualização",
        options=["Geral", "Divergente"],
        index=0,
        key="inv_visao",
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    df_tab = df_kpi.copy()

    if visao == "Divergente":
        df_tab = df_tab[df_tab["Qtd_Divergente"] != 0] if "Qtd_Divergente" in df_tab.columns else df_tab

    df_tab["Data_Inventario"] = df_tab["Data_Inventario"].dt.date

    df_tab = df_tab.rename(columns={
        "Data_Inventario":    "Data Inventario",
        "Nome_Empresa":       "Empresa / Filial",
        "Codigo":             "Produto",
        "Qtd_Inventariada":   "Qtd Invent",
        "Qtd_Protheus":       "Qtd Protheus",
        "Qtd_Divergente":     "Qtd Divergente",
        "Valor_Unitario":     "Valor Unit",
        "Valor_Protheus":     "Valor Protheus",
        "Valor_Inventariado": "Valor Invent",
        "Valor_Divergente":   "Valor Divergente",
    })

    df_tab = df_tab.drop(
        columns=[c for c in ["Empresa", "Qtd Itens Inventariados", "Qtd Itens Divergentes"] if c in df_tab.columns],
        errors="ignore"
    )

    colunas_ordem = [
        "Data Inventario", "Empresa / Filial", "Produto", "Descricao", "Valor Unit",
        "Qtd Invent", "Valor Invent", "Qtd Protheus", "Valor Protheus",
        "Qtd Divergente", "Valor Divergente",
    ]
    df_tab = df_tab[[c for c in colunas_ordem if c in df_tab.columns]]

    LINHAS_POR_PAGINA = 50
    total_linhas  = len(df_tab)
    total_paginas = max(1, -(-total_linhas // LINHAS_POR_PAGINA))

    col_info, col_nav = st.columns([3, 1])
    with col_info:
        st.write(f"**{total_linhas:,}** registros".replace(",", "."))
    with col_nav:
        pagina = st.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1, label_visibility="collapsed")
        st.caption(f"Página {pagina} de {total_paginas}")

    inicio  = (pagina - 1) * LINHAS_POR_PAGINA
    fim     = inicio + LINHAS_POR_PAGINA
    df_page = df_tab.iloc[inicio:fim].copy()
    df_raw  = df_page.copy()

    colunas_moeda = ["Valor Invent", "Valor Protheus", "Valor Divergente", "Valor Unit"]
    colunas_qtd   = ["Qtd Invent", "Qtd Protheus", "Qtd Divergente"]

    for c in colunas_moeda:
        if c in df_page.columns:
            df_page[c] = df_page[c].apply(moeda_br)
    for c in colunas_qtd:
        if c in df_page.columns:
            df_page[c] = df_page[c].apply(fmt_qtd)

    colunas = list(df_page.columns)
    header  = "".join(f"<th>{c}</th>" for c in colunas)
    rows    = ""
    for i, (_, row) in enumerate(df_page.iterrows()):
        cells = ""
        for c in colunas:
            style = ""
            if c in ["Qtd Divergente", "Valor Divergente"]:
                try:
                    v = float(df_raw.iloc[i][c])
                    if v > 0:
                        style = "color:#EC6E21;font-weight:600"
                    elif v < 0:
                        style = "color:#51cf66;font-weight:600"
                except:
                    pass
            cells += f'<td style="{style}">{row[c]}</td>'
        rows += f"<tr>{cells}</tr>"

    st.markdown(f"""
    <style>
    .inv-table-wrap {{ overflow-x:auto; border-radius:10px; border:1px solid rgba(255,255,255,0.08); }}
    .inv-table {{ width:100%; border-collapse:collapse; font-size:13px; font-family:sans-serif; }}
    .inv-table thead th {{ background-color:#0f5a60; color:white; font-weight:600; padding:10px 14px; text-align:left; border-bottom:2px solid #EC6E21; white-space:nowrap; }}
    .inv-table tbody tr {{ border-bottom:1px solid rgba(255,255,255,0.06); }}
    .inv-table tbody tr:hover {{ background-color:rgba(236,110,33,0.08); }}
    .inv-table tbody td {{ padding:9px 14px; color:white; background-color:#0f5a60; white-space:nowrap; }}
    .inv-table tbody tr:nth-child(even) td {{ background-color:#0d4f55; }}
    </style>
    <div class="inv-table-wrap">
        <table class="inv-table">
            <thead><tr>{header}</tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)

# ── ABA 2: Análise de Inventário ─────────────────────────────────────────────
with tab2:

    # Filtro Por Qtd / Por Valor
    metrica = st.radio(
        "Análise",
        options=["Acuracidade Quantidade", "Acuracidade Valor"],
        index=0,
        key="inv_metrica",
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Calcular acuracidade por data
    datas_hist = sorted(df_hist_filtrado["Data_Inventario"].unique())

    registros = []
    for data in datas_hist:
        df_d = df_hist_filtrado[df_hist_filtrado["Data_Inventario"] == data]

        qtd_inv  = df_d["Qtd_Itens_Inventariados"].sum() if "Qtd_Itens_Inventariados" in df_d.columns else len(df_d)
        qtd_div  = df_d["Qtd_Itens_Divergentes"].sum()   if "Qtd_Itens_Divergentes"   in df_d.columns else 0
        acu_qtd  = (qtd_inv - qtd_div) / qtd_inv * 100   if qtd_inv > 0 else 0

        val_inv  = df_d["Valor_Inventariado"].sum() if "Valor_Inventariado" in df_d.columns else 0
        val_div  = df_d["Valor_Divergente"].sum()   if "Valor_Divergente"   in df_d.columns else 0
        acu_val  = (val_inv - abs(val_div)) / val_inv * 100 if val_inv > 0 else 0

        registros.append({
            "Data":             pd.Timestamp(data),
            "Acuracidade Qtd":  round(acu_qtd, 2),
            "Acuracidade Valor": round(acu_val, 2),
        })

    df_evolucao = pd.DataFrame(registros).sort_values("Data")

    if df_evolucao.empty:
        st.info("Dados insuficientes para gerar o gráfico de evolução.")
    else:
        col_y      = "Acuracidade Qtd" if metrica == "Acuracidade Quantidade" else "Acuracidade Valor"
        titulo_graf = "Acuracidade Quantidade" if metrica == "Acuracidade Quantidade" else "Acuracidade Valor"

        x_labels = df_evolucao["Data"].dt.strftime("%Y-%m").tolist()
        y_vals   = df_evolucao[col_y].tolist()

        fig = go.Figure()

        # Área preenchida — sem rótulos, só hover
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=y_vals,
            mode="lines+markers",
            name=titulo_graf,
            line=dict(color="#EC6E21", width=3),
            marker=dict(size=8, color="#EC6E21"),
            fill="tozeroy",
            fillcolor="rgba(101,116,43,0.5)",
            hovertemplate="%{x}<br><b>%{y:.2f}%</b><extra></extra>",
        ))

        # Linha de meta 95%
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=[95] * len(x_labels),
            mode="lines",
            name="Meta 95%",
            line=dict(color="#ff6b6b", width=2, dash="dash"),
            hovertemplate="Meta: 95%<extra></extra>",
        ))

        y_min = max(0, min(y_vals + [95]) - 2)
        y_max = min(101, max(y_vals) + 1)

        fig.update_layout(
            title=dict(text=titulo_graf, font=dict(color="white", size=16)),
            plot_bgcolor="#005562",
            paper_bgcolor="#005562",
            font=dict(color="white"),
            xaxis=dict(
                showgrid=False,
                tickfont=dict(color="white"),
                title="",
                type="category",
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(255,255,255,0.08)",
                tickfont=dict(color="white"),
                ticksuffix="%",
                range=[y_min, y_max],
                title="",
            ),
            legend=dict(
                font=dict(color="white"),
                bgcolor="rgba(0,0,0,0)",
            ),
            margin=dict(l=60, r=60, t=60, b=40),
            height=450,
        )

        st.plotly_chart(fig, use_container_width=True)


