import streamlit as st
import pandas as pd

from utils.navbar import render_navbar

st.set_page_config(page_title="Dashboard Inventário", layout="wide")
render_navbar("Dashboard Inventário")

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Dashboard de Inventário")
st.markdown("---")

# -------------------------------------------------
# CARREGAR E TRATAR
# -------------------------------------------------

df = pd.read_parquet("data/inventario/inventario_historico.parquet")

df["Data_Inventario"] = pd.to_datetime(df["Data_Inventario"]).dt.date

df = df.rename(columns={
    "Data_Inventario":    "Data Inventario",
    "Nome_Empresa":       "Empresa / Filial",
    "Codigo":             "Produto",
    "Qtd_Inventariada":   "Qtd Inventariada",
    "Qtd_Protheus":       "Qtd Protheus",
    "Qtd_Divergente":     "Qtd Divergente",
    "Valor_Unitario":     "Valor Unitario",
    "Valor_Protheus":     "Valor Protheus",
    "Valor_Inventariado": "Valor Inventariado",
    "Valor_Divergente":   "Valor Divergente",
})

df = df.drop(columns=[c for c in ["Empresa", "Qtd Itens Inventariados", "Qtd Itens Divergentes"] if c in df.columns], errors="ignore")

colunas_ordem = [
    "Data Inventario",
    "Empresa / Filial",
    "Produto",
    "Descricao",
    "Qtd Inventariada",
    "Valor Inventariado",
    "Qtd Protheus",
    "Valor Protheus",
    "Qtd Divergente",
    "Valor Divergente",
]
df = df[[c for c in colunas_ordem if c in df.columns]]

# -------------------------------------------------
# FORMATAR VALORES
# -------------------------------------------------

def moeda_br(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "—"

def fmt_qtd(valor):
    try:
        v = float(valor)
        return f"{v:,.0f}".replace(",", ".")
    except:
        return "—"

colunas_moeda = ["Valor Inventariado", "Valor Protheus", "Valor Divergente", "Valor Unitario"]
colunas_qtd   = ["Qtd Inventariada", "Qtd Protheus", "Qtd Divergente"]

df_fmt = df.copy()
for c in colunas_moeda:
    if c in df_fmt.columns:
        df_fmt[c] = df_fmt[c].apply(moeda_br)
for c in colunas_qtd:
    if c in df_fmt.columns:
        df_fmt[c] = df_fmt[c].apply(fmt_qtd)

# -------------------------------------------------
# RENDERIZAR TABELA HTML
# -------------------------------------------------

def render_tabela(df_render, df_raw):

    colunas = list(df_render.columns)
    header  = "".join(f"<th>{c}</th>" for c in colunas)

    rows = ""
    for i, (_, row) in enumerate(df_render.iterrows()):
        cells = ""
        for c in colunas:
            val   = row[c]
            style = ""
            if c in ["Qtd Divergente", "Valor Divergente"]:
                try:
                    raw = df_raw.iloc[i][c] if i < len(df_raw) else 0
                    if float(str(raw).replace("R$","").replace(".","").replace(",",".").strip()) > 0:
                        style = "color:#EC6E21;font-weight:600"
                    elif float(str(raw).replace("R$","").replace(".","").replace(",",".").strip()) < 0:
                        style = "color:#51cf66;font-weight:600"
                except:
                    pass
            cells += f'<td style="{style}">{val}</td>'
        rows += f"<tr>{cells}</tr>"

    return f"""
    <style>
    .inv-table-wrap {{
        overflow-x: auto;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.08);
    }}
    .inv-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        font-family: sans-serif;
    }}
    .inv-table thead th {{
        background-color: #0f5a60;
        color: white;
        font-weight: 600;
        padding: 10px 14px;
        text-align: left;
        border-bottom: 2px solid #EC6E21;
        white-space: nowrap;
    }}
    .inv-table tbody tr {{
        border-bottom: 1px solid rgba(255,255,255,0.06);
        transition: background 0.15s;
    }}
    .inv-table tbody tr:hover {{
        background-color: rgba(236,110,33,0.08);
    }}
    .inv-table tbody td {{
        padding: 9px 14px;
        color: white;
        background-color: #0f5a60;
        white-space: nowrap;
    }}
    .inv-table tbody tr:nth-child(even) td {{
        background-color: #0d4f55;
    }}
    </style>
    <div class="inv-table-wrap">
        <table class="inv-table">
            <thead><tr>{header}</tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """

st.write("Base de Inventário")
st.markdown(render_tabela(df_fmt, df), unsafe_allow_html=True)
