import streamlit as st
import pandas as pd


def render(df_filtrado, moeda_br):

    ultima_data = df_filtrado["Data Fechamento"].max()
    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]

    css = (
        "<style>.tb-obs{width:100%;border-collapse:collapse;font-size:13px;color:white}"
        ".tb-obs th{background:#0f5a60;padding:10px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700}"
        ".tb-obs th:not(:first-child){text-align:right}"
        ".tb-obs td{padding:7px 12px;border-bottom:1px solid #1a6e75;background:#005562;color:white}"
        ".tb-obs td:not(:first-child){text-align:right}"
        ".tb-obs tr:last-child td{font-weight:700;border-top:2px solid #EC6E21}"
        ".tb-obs tr:hover td{background:#0a6570}</style>"
    )

    def montar_tabela(df_group, col_nome):
        total = df_group["Custo Total"].sum()
        linhas = ""
        for _, row in df_group.iterrows():
            perc = row["Custo Total"] / total * 100 if total > 0 else 0
            linhas += (
                f"<tr><td>{row[col_nome]}</td>"
                f"<td>{moeda_br(row['Custo Total'])}</td>"
                f"<td style='color:#EC6E21;font-weight:600'>{perc:.1f}%</td></tr>"
            )
        linhas += (
            f"<tr><td>Total</td>"
            f"<td>{moeda_br(total)}</td>"
            f"<td style='color:#EC6E21;font-weight:600'>100%</td></tr>"
        )
        st.markdown(
            css + f"<table class='tb-obs'><thead><tr>"
            f"<th>{col_nome}</th>"
            f"<th style='text-align:right'>Valor Obsoleto</th>"
            f"<th style='text-align:right'>%</th>"
            f"</tr></thead><tbody>{linhas}</tbody></table>",
            unsafe_allow_html=True
        )

    tab1, tab2, tab3 = st.tabs([
        "🏢 Por Empresa / Filial",
        "📋 Por Status do Movimento",
        "📦 Por Conta"
    ])

    with tab1:
        df_emp = (
            base.groupby("Empresa / Filial")
            .agg(**{"Custo Total": ("Custo Total", "sum")})
            .reset_index().sort_values("Custo Total", ascending=False)
        )
        montar_tabela(df_emp, "Empresa / Filial")

    with tab2:
        df_status = (
            base.groupby("Status do Movimento")
            .agg(**{"Custo Total": ("Custo Total", "sum")})
            .reset_index().sort_values("Custo Total", ascending=False)
        )
        montar_tabela(df_status, "Status do Movimento")

    with tab3:
        df_conta = (
            base.groupby("Conta")
            .agg(**{"Custo Total": ("Custo Total", "sum")})
            .reset_index().sort_values("Custo Total", ascending=False)
        )
        montar_tabela(df_conta, "Conta")
