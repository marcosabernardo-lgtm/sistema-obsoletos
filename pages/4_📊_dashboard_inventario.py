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
    min-height:100px;
    display:flex;
    flex-direction:column;
    justify-content:center;
}
.kpi-title{ font-size:13px; color:#ccc; }
.kpi-value{ font-size:20px; font-weight:700; color:white; }
.kpi-value-green{ font-size:20px; font-weight:700; color:#51cf66; }

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

from utils.navbar import render_filtros_topo as _render_filtros_topo

# Preview para montar opções
data_preview_str = st.session_state.get("inventario_data", datas_fmt_list[0])
data_preview     = pd.Timestamp(datas_map.get(data_preview_str, datas_disponiveis[0]))
df_preview       = df[df["Data_Inventario"] == data_preview]
empresas_ef_disp = sorted(df_preview["Nome_Empresa"].dropna().unique()) if "Nome_Empresa" in df_preview.columns else []

filtros = _render_filtros_topo(
    datas=datas_fmt_list,
    empresas=empresas_ef_disp,
    key_prefix="inventario"
)

data_selecionada = pd.Timestamp(datas_map[filtros["data"]])
ef_sel           = filtros["empresas"]  # lista de Nome_Empresa filtrada por Empresa+Filial

df_kpi = df[df["Data_Inventario"] == data_selecionada].copy()
if ef_sel:
    df_kpi = df_kpi[df_kpi["Nome_Empresa"].isin(ef_sel)]

df_hist_filtrado = df.copy()
if ef_sel:
    df_hist_filtrado = df_hist_filtrado[df_hist_filtrado["Nome_Empresa"].isin(ef_sel)]

qtd_inventariada  = df_kpi["Qtd_Itens_Inventariados"].sum() if "Qtd_Itens_Inventariados" in df_kpi.columns else len(df_kpi)
qtd_divergentes   = int(df_kpi["Qtd_Itens_Divergentes"].sum()) if "Qtd_Itens_Divergentes" in df_kpi.columns else 0
acuracidade_itens = (qtd_inventariada - qtd_divergentes) / qtd_inventariada if qtd_inventariada > 0 else 0

valor_inventariado = df_kpi["Valor_Inventariado"].sum() if "Valor_Inventariado" in df_kpi.columns else 0
valor_divergente   = df_kpi["Valor_Divergente"].sum()   if "Valor_Divergente"   in df_kpi.columns else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.markdown(f"""<div class="kpi-card"><div class="kpi-title">Qtd Inventariada</div><div class="kpi-value">{fmt_qtd(qtd_inventariada)}</div></div>""", unsafe_allow_html=True)
col2.markdown(f"""<div class="kpi-card"><div class="kpi-title">Qtd Divergentes</div><div class="kpi-value">{fmt_qtd(qtd_divergentes)}</div></div>""", unsafe_allow_html=True)
col3.markdown(f"""<div class="kpi-card"><div class="kpi-title">Acuracidade Qtd</div><div class="kpi-value kpi-value-green">{acuracidade_itens*100:.2f}%</div></div>""", unsafe_allow_html=True)
col4.markdown(f"""<div class="kpi-card"><div class="kpi-title">Valor Inventariado</div><div class="kpi-value">{moeda_br(valor_inventariado)}</div></div>""", unsafe_allow_html=True)
col5.markdown(f"""<div class="kpi-card"><div class="kpi-title">Valor Divergente</div><div class="kpi-value">{moeda_br(valor_divergente)}</div></div>""", unsafe_allow_html=True)
col6.markdown(f"""<div class="kpi-card"><div class="kpi-title">Acuracidade Valor</div><div class="kpi-value kpi-value-green">{acuracidade_itens*100:.2f}%</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# -------------------------------------------------
# ABAS
# -------------------------------------------------

tab1, tab2, tab3 = st.tabs(["📚 Base Histórica", "📊 Análise de Inventário", "📋 Resumo"])

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

    import io as _io

    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] > div,
    div[data-testid="stTextInput"] > div > div { background-color: #005562 !important; }
    div[data-testid="stTextInput"] input {
        border: 1px solid rgba(250,250,250,0.2) !important;
        border-radius: 6px !important; color: white !important; padding: 8px 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Formata para exibição
    df_display = df_tab.copy()
    for c in ["Valor Invent", "Valor Protheus", "Valor Divergente", "Valor Unit"]:
        if c in df_display.columns:
            df_display[c] = df_display[c].apply(moeda_br)
    for c in ["Qtd Invent", "Qtd Protheus", "Qtd Divergente"]:
        if c in df_display.columns:
            df_display[c] = df_display[c].apply(fmt_qtd)

    col_busca, col_ord, col_dir, col_export = st.columns([3, 2, 1, 1])
    with col_busca:
        busca = st.text_input("🔍 PESQUISAR", placeholder="Produto, empresa, descrição...", key="busca_inv_base")
    with col_ord:
        ord_col = st.selectbox("📊 Classificar por", list(df_display.columns), key="ord_col_inv_base")
    with col_dir:
        ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_inv_base")
    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        buf = _io.BytesIO()
        df_tab.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("📥 Exportar", data=buf, file_name="base_inventario.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

    if busca:
        mask = df_display.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
        df_display = df_display[mask]

    ascending = ord_dir == "⬆ Asc"
    try:
        df_display = df_display.sort_values(ord_col, ascending=ascending,
            key=lambda x: pd.to_numeric(
                x.astype(str).str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."),
                errors="coerce").fillna(x.astype(str)))
    except Exception:
        pass

    st.caption(f"{len(df_display):,} registros")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

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

# ── ABA 3: Resumo ─────────────────────────────────────────────────────────────
with tab3:

    import plotly.graph_objects as go

    df_res = df_kpi.copy()

    if df_res.empty:
        st.info("Sem dados para o fechamento selecionado.")
    else:

        # --------------------------------------------------
        # CALCULAR POR EMPRESA
        # --------------------------------------------------

        empresas_res = sorted(df_res["Nome_Empresa"].dropna().unique())
        rows_qtd = []
        rows_val = []

        for emp in empresas_res:
            df_e = df_res[df_res["Nome_Empresa"] == emp]

            # Quantidade — usa Qtd_Itens_Inventariados e Qtd_Itens_Divergentes (SKUs)
            qtd_inv = df_e["Qtd_Itens_Inventariados"].sum() if "Qtd_Itens_Inventariados" in df_e.columns else len(df_e)
            qtd_div = df_e["Qtd_Itens_Divergentes"].sum()   if "Qtd_Itens_Divergentes"   in df_e.columns else 0
            acu_qtd = (qtd_inv - qtd_div) / qtd_inv * 100   if qtd_inv > 0 else 0

            # Valor
            val_inv = df_e["Valor_Inventariado"].sum() if "Valor_Inventariado" in df_e.columns else 0
            val_div = df_e["Valor_Divergente"].sum()   if "Valor_Divergente"   in df_e.columns else 0
            acu_val = (val_inv - abs(val_div)) / val_inv * 100 if val_inv > 0 else 0

            rows_qtd.append({"Empresa / Filial": emp, "% Acuracidade": f"{acu_qtd:.2f}%", "SKUs Divergentes": int(qtd_div)})
            rows_val.append({"Empresa / Filial": emp, "% Acuracidade": f"{acu_val:.2f}%", "Valor Divergente": moeda_br(val_div)})

        # Totais
        qtd_inv_t = df_res["Qtd_Itens_Inventariados"].sum() if "Qtd_Itens_Inventariados" in df_res.columns else len(df_res)
        qtd_div_t = df_res["Qtd_Itens_Divergentes"].sum()   if "Qtd_Itens_Divergentes"   in df_res.columns else 0
        acu_qtd_t = (qtd_inv_t - qtd_div_t) / qtd_inv_t * 100 if qtd_inv_t > 0 else 0

        val_inv_t = df_res["Valor_Inventariado"].sum() if "Valor_Inventariado" in df_res.columns else 0
        val_div_t = df_res["Valor_Divergente"].sum()   if "Valor_Divergente"   in df_res.columns else 0
        acu_val_t = (val_inv_t - abs(val_div_t)) / val_inv_t * 100 if val_inv_t > 0 else 0

        rows_qtd.append({"Empresa / Filial": "Total", "% Acuracidade": f"{acu_qtd_t:.2f}%", "SKUs Divergentes": int(qtd_div_t)})
        rows_val.append({"Empresa / Filial": "Total", "% Acuracidade": f"{acu_val_t:.2f}%", "Valor Divergente": moeda_br(val_div_t)})

        # --------------------------------------------------
        # FILTRO — igual à aba Análise
        # --------------------------------------------------

        metrica_res = st.radio(
            "Resumo",
            options=["Acuracidade Quantidade", "Acuracidade Valor"],
            index=0,
            key="inv_resumo_metrica",
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        def gauge(valor, titulo, meta=95):
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=valor,
                number={"suffix": "%", "font": {"color": "white", "size": 28}},
                title={"text": titulo, "font": {"color": "white", "size": 14}},
                gauge={
                    "axis": {"range": [0, 100], "ticksuffix": "%", "tickfont": {"color": "white"}},
                    "bar":  {"color": "#EC6E21"},
                    "bgcolor": "rgba(255,255,255,0.05)",
                    "borderwidth": 0,
                    "threshold": {
                        "line": {"color": "#ff6b6b", "width": 3},
                        "thickness": 0.75,
                        "value": meta,
                    },
                    "steps": [
                        {"range": [0, meta],   "color": "rgba(255,107,107,0.15)"},
                        {"range": [meta, 100], "color": "rgba(81,207,102,0.15)"},
                    ],
                },
            ))
            fig.update_layout(
                paper_bgcolor="#005562",
                font=dict(color="white"),
                margin=dict(l=20, r=20, t=40, b=20),
                height=260,
            )
            return fig

        def html_tabela(rows, col_valor):
            header = f"<tr><th>Empresa / Filial</th><th>% Acuracidade</th><th>{col_valor}</th></tr>"
            linhas = ""
            for r in rows:
                peso = "font-weight:700;" if r["Empresa / Filial"] == "Total" else ""
                linhas += (
                    f'<tr style="{peso}">'
                    f'<td>{r["Empresa / Filial"]}</td>'
                    f'<td style="text-align:right">{r["% Acuracidade"]}</td>'
                    f'<td style="text-align:right">{r[col_valor]}</td>'
                    f'</tr>'
                )
            return f"""
            <style>
            .res-tb{{width:100%;border-collapse:collapse;font-size:13px;color:white}}
            .res-tb th{{background:#0f5a60;padding:8px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700}}
            .res-tb td{{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.06);background:#005562}}
            .res-tb tr:last-child td{{background:#0a4a50;font-weight:700}}
            </style>
            <table class="res-tb"><thead>{header}</thead><tbody>{linhas}</tbody></table>
            """

        # Extrair valor numérico do total para o gauge
        acu_qtd_gauge = float(rows_qtd[-1]["% Acuracidade"].replace("%", ""))
        acu_val_gauge = float(rows_val[-1]["% Acuracidade"].replace("%", ""))

        if metrica_res == "Acuracidade Quantidade":
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(html_tabela(rows_qtd, "SKUs Divergentes"), unsafe_allow_html=True)
            with c2:
                st.plotly_chart(gauge(acu_qtd_gauge, "% Acuracidade Itens"), use_container_width=True)
        else:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(html_tabela(rows_val, "Valor Divergente"), unsafe_allow_html=True)
            with c2:
                st.plotly_chart(gauge(acu_val_gauge, "% Acuracidade Valor"), use_container_width=True)
