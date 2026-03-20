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

            # Cards
            c1, c2, c3, _ = st.columns([1, 1, 1, 3])
            c1.markdown(
                f'<div style="display:inline-block;border:2px solid #EC6E21;border-radius:10px;padding:12px 20px;text-align:center;margin-bottom:16px;width:100%">'
                f'<div style="font-size:11px;color:rgba(255,255,255,0.5);letter-spacing:1px;text-transform:uppercase">Valor Total</div>'
                f'<div style="font-size:20px;font-weight:700;color:white;margin-top:4px">{moeda_br(total_estoque)}</div>'
                f'</div>', unsafe_allow_html=True
            )
            c2.markdown(
                f'<div style="display:inline-block;border:2px solid #EC6E21;border-radius:10px;padding:12px 20px;text-align:center;margin-bottom:16px;width:100%">'
                f'<div style="font-size:11px;color:rgba(255,255,255,0.5);letter-spacing:1px;text-transform:uppercase">Produtos</div>'
                f'<div style="font-size:20px;font-weight:700;color:white;margin-top:4px">{base["Produto"].nunique():,}</div>'
                f'</div>', unsafe_allow_html=True
            )
            c3.markdown(
                f'<div style="display:inline-block;border:2px solid #EC6E21;border-radius:10px;padding:12px 20px;text-align:center;margin-bottom:16px;width:100%">'
                f'<div style="font-size:11px;color:rgba(255,255,255,0.5);letter-spacing:1px;text-transform:uppercase">Registros</div>'
                f'<div style="font-size:20px;font-weight:700;color:white;margin-top:4px">{len(base):,}</div>'
                f'</div>', unsafe_allow_html=True
            )

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
            if "Vlr Unit" in base_display.columns:
                base_display["Vlr Unit"] = pd.to_numeric(
                    base_display["Vlr Unit"], errors="coerce"
                ).apply(lambda x: moeda_br(x) if pd.notna(x) else "—")

            # % Estoque
            base_display["% Estoque"] = base["Custo Total"].apply(
                lambda x: f"{(x / total_estoque * 100):.1f}%" if total_estoque > 0 else "—"
            )

            # Exportar + contagem
            col_info, col_export = st.columns([4, 1])
            with col_info:
                st.caption(f"{len(base):,} registros")
            with col_export:
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
