import streamlit as st
import pandas as pd
import io
from tabs.estoque.graficos.grafico_evolucao import render as grafico_evolucao
from tabs.estoque.graficos.grafico_empresa import render as grafico_empresa
from tabs.estoque.graficos.grafico_conta import render as grafico_conta
from tabs.estoque.graficos.grafico_top_produtos import render as grafico_top_produtos
from tabs.estoque.graficos.grafico_variacao_produto import render as grafico_variacao_produto


def render(df_hist, df_obsoleto, moeda_br, df_kpi=None, data_selecionada=None, valor_mom=None, valor_yoy=None):

    st.subheader("📦 Evolução de Estoque")

    df = df_hist.copy()

    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📚 Base Histórica",
        "📈 Evolução Estoque",
        "🏢 Por Empresa",
        "📊 Por Conta",
        "⬆ Top Produtos",
        "📦 Variação por Produto"
    ])

    # ── ABA 0: Base Histórica — todos os itens do fechamento selecionado ──────
    with tab0:

        base = df_kpi.copy() if df_kpi is not None and not df_kpi.empty else pd.DataFrame()

        if base.empty:
            st.info("Selecione um fechamento para visualizar a base histórica.")
        else:
            total_estoque = base["Custo Total"].sum()

            # Ordenar por Custo Total
            base = base.sort_values("Custo Total", ascending=False)

            # Formatar para exibição
            base_display = base.copy()
            if "Data Fechamento" in base_display.columns:
                base_display["Data Fechamento"] = pd.to_datetime(
                    base_display["Data Fechamento"], errors="coerce"
                ).dt.strftime("%d/%m/%Y")
            if "Custo Total" in base_display.columns:
                base_display["Custo Total"] = base_display["Custo Total"].apply(moeda_br)
            if "Tipo de Estoque" not in base_display.columns and "Tipo de Estoque" in base.columns:
                base_display["Tipo de Estoque"] = base["Tipo de Estoque"]
            if "Vlr Unit" in base_display.columns:
                base_display["Vlr Unit"] = pd.to_numeric(
                    base_display["Vlr Unit"], errors="coerce"
                ).apply(lambda x: moeda_br(x) if pd.notna(x) else "—")

            # % Estoque
            base_display["% Estoque"] = base["Custo Total"].apply(
                lambda x: f"{(x / total_estoque * 100):.1f}%" if total_estoque > 0 else "—"
            )

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
                busca = st.text_input("🔍 PESQUISAR", placeholder="Produto, empresa, conta...", key="busca_base_hist")
            with col_ord:
                ord_col = st.selectbox("📊 Classificar por", list(base_display.columns), key="ord_col_base_hist")
            with col_dir:
                ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_base_hist")
            with col_export:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                buffer = io.BytesIO()
                base.to_excel(buffer, index=False)
                buffer.seek(0)
                st.download_button(
                    label="📥 Exportar",
                    data=buffer.getvalue(),
                    file_name="base_historica_estoque.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            if busca:
                mask = base_display.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
                base_display = base_display[mask]

            ascending = ord_dir == "⬆ Asc"
            try:
                base_display = base_display.sort_values(
                    ord_col, ascending=ascending,
                    key=lambda x: pd.to_numeric(
                        x.astype(str).str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."),
                        errors="coerce"
                    ).fillna(x.astype(str))
                )
            except Exception:
                pass

            st.caption(f"{len(base_display):,} registros")
            st.dataframe(base_display, use_container_width=True, hide_index=True)

    with tab1:
        grafico_evolucao(df)

    with tab2:
        grafico_empresa(df, moeda_br, data_selecionada)

    with tab3:
        grafico_conta(df, moeda_br, data_selecionada)

    with tab4:
        grafico_top_produtos(df, moeda_br, data_selecionada)

    with tab5:
        grafico_variacao_produto(df, moeda_br, data_selecionada)
