import streamlit as st
import pandas as pd
import io

def card_mini(titulo, valor):
    st.markdown(
        f"""
        <div style="border:1px solid #EC6E21; border-radius:8px; padding:10px 14px; text-align:center; background-color:#005562;">
            <div style="font-size:11px;color:#aaa">{titulo}</div>
            <div style="font-size:18px;font-weight:bold;color:white">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render(df_filtrado, moeda_br):
    ultima_data = df_filtrado["Data Fechamento"].max()
    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data].copy()

    if "Tipo de Estoque" not in base.columns: base["Tipo de Estoque"] = "—"
    if "Conta" not in base.columns: base["Conta"] = "—"

    total_geral = base["Custo Total"].sum()

    # AJUSTE: Agrupamento consolidado por Produto para não diluir o ranking
    top20 = (
        base
        .groupby(["Empresa / Filial", "Produto"], as_index=False)
        .agg({
            "Saldo Atual": "sum",
            "Custo Total": "sum",
            "Descricao": "first",
            "Conta": "first",
            "Tipo de Estoque": "first"
        })
    )

    top20["%"] = (top20["Custo Total"] / total_geral * 100) if total_geral > 0 else 0
    top20 = top20.sort_values("Custo Total", ascending=False).head(20)
    top20.insert(0, "Ranking", range(1, len(top20) + 1))

    # ---------- CARDS MINI ----------
    total_top20 = top20["Custo Total"].sum()
    perc_top20  = (total_top20 / total_geral * 100) if total_geral > 0 else 0

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1: card_mini("Valor Top 20", moeda_br(total_top20))
    with c2: card_mini("% do Obsoleto Total", f"{perc_top20:.2f}%")

    st.markdown("")
    export_df = top20.copy()

    # ---------- FORMATAÇÃO ----------
    top20_display = top20.copy()
    top20_display["Custo Total"] = top20_display["Custo Total"].apply(moeda_br)
    top20_display["%"] = top20_display["%"].apply(lambda x: f"{x:.2f}%")

    top20_display = top20_display[[
        "Ranking", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto",
        "Descricao", "Saldo Atual", "Custo Total", "%"
    ]]

    # (Mantive seu CSS e lógica de busca/ordenação original abaixo)
    st.markdown("<style>div[data-testid='stTextInput'] input { background-color: #005562 !important; color: white !important; }</style>", unsafe_allow_html=True)

    col_busca, col_ord, col_dir, col_export = st.columns([3, 2, 1, 1])
    with col_busca:
        busca = st.text_input("🔍 PESQUISAR", placeholder="Produto...", key="busca_top20")
    with col_ord:
        ord_col = st.selectbox("📊 Classificar por", list(top20_display.columns), index=7, key="ord_col_top20")
    with col_dir:
        ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_top20")
    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        buffer = io.BytesIO()
        export_df.to_excel(buffer, index=False)
        st.download_button("📥 Exportar", buffer.getvalue(), "top20_obsoletos.xlsx", use_container_width=True)

    if busca:
        mask = top20_display.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
        top20_display = top20_display[mask]

    ascending = ord_dir == "⬆ Asc"
    try:
        top20_display = top20_display.sort_values(ord_col, ascending=ascending)
    except: pass

    st.dataframe(top20_display, use_container_width=True, hide_index=True)