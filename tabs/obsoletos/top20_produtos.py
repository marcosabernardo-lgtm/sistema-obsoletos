import streamlit as st
import pandas as pd
import io
from utils.utils import botao_download_excel


def card_mini(titulo, valor):
    st.markdown(
        f"""
        <div style="
            border:1px solid #EC6E21;
            border-radius:8px;
            padding:10px 14px;
            text-align:center;
            background-color:#005562;
        ">
            <div style="font-size:11px;color:#aaa">{titulo}</div>
            <div style="font-size:18px;font-weight:bold;color:white">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render(df_filtrado, moeda_br):

    ultima_data = df_filtrado["Data Fechamento"].max()

    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data].copy()

    # Proteção caso a coluna não exista em arquivos históricos antigos
    if "Tipo de Estoque" not in base.columns:
        base["Tipo de Estoque"] = "—"

    # Total geral do obsoleto (base para o %)
    total_geral = base["Custo Total"].sum()

    # Adicionado "Tipo de Estoque" no agrupamento para não perder a informação
    top20 = (
        base
        .groupby(
            ["Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao"],
            as_index=False
        )
        .agg(
            Quantidade=("Saldo Atual", "sum"),
            Custo_Total=("Custo Total", "sum")
        )
    )

    top20["%"] = (top20["Custo_Total"] / total_geral * 100) if total_geral > 0 else 0

    top20 = (
        top20
        .sort_values("Custo_Total", ascending=False)
        .head(20)
    )

    top20.insert(0, "Ranking", range(1, len(top20) + 1))
    top20 = top20.rename(columns={"Custo_Total": "Custo Total"})

    # ---------- CARDS MINI ----------
    total_top20 = top20["Custo Total"].sum()
    perc_top20  = (total_top20 / total_geral * 100) if total_geral > 0 else 0

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: card_mini("Valor Top 20", moeda_br(total_top20))
    with c2: card_mini("% do Obsoleto Total", f"{perc_top20:.2f}%")

    st.markdown("")

    # ---------- DATAFRAME PARA EXPORTAR ----------
    export_df = top20.copy()

    # ---------- FORMATAÇÃO PARA TELA ----------
    top20["Custo Total"] = top20["Custo Total"].apply(moeda_br)
    top20["%"] = top20["%"].apply(lambda x: f"{x:.2f}%")

    # Adicionado "Tipo de Estoque" na visualização
    top20 = top20[[
        "Ranking", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto",
        "Descricao", "Quantidade", "Custo Total", "%"
    ]]

    st.markdown("""
    <style>
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] > div,
    div[data-testid="stTextInput"] > div > div {
        background-color: #005562 !important;
    }
    div[data-testid="stTextInput"] input {
        border: 1px solid rgba(250,250,250,0.2) !important;
        border-radius: 6px !important;
        color: white !important;
        padding: 8px 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_busca, col_ord, col_dir, col_export = st.columns([3, 2, 1, 1])
    with col_busca:
        busca = st.text_input("🔍 PESQUISAR", placeholder="Produto, empresa, tipo...", key="busca_top20")
    with col_ord:
        ord_col = st.selectbox("📊 Classificar por", list(top20.columns), key="ord_col_top20")
    with col_dir:
        ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_top20")
    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        buffer = io.BytesIO()
        export_df.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label="📥 Exportar",
            data=buffer,
            file_name="top20_estoque_obsoleto.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    if busca:
        mask = top20.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
        top20 = top20[mask]

    ascending = ord_dir == "⬆ Asc"
    try:
        top20 = top20.sort_values(
            ord_col, ascending=ascending,
            key=lambda x: pd.to_numeric(
                x.astype(str).str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."),
                errors="coerce"
            ).fillna(x.astype(str))
        )
    except Exception:
        pass

    st.caption(f"{len(top20)} produtos")
    st.dataframe(top20, use_container_width=True, hide_index=True)