import streamlit as st
import pandas as pd
import io


def render(df_hist, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)

    top_n = st.slider("Quantidade de produtos", min_value=5, max_value=50, value=10, step=5)

    sub1, sub2 = st.tabs(["💰 Maior Valor em Estoque", "📈 Maior Variação MoM"])

    total_estoque = df_atual["Custo Total"].sum()

    # ── ABA 1: Maior Valor em Estoque ─────────────────────────────────────────
    with sub1:

        df_valor = (
            df_atual.groupby(["Empresa / Filial", "Conta", "Produto", "Descricao"])
            .agg(Qtd=("Saldo Atual", "sum"), Valor=("Custo Total", "sum"))
            .reset_index()
            .sort_values("Valor", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

        df_valor["% Estoque"] = df_valor["Valor"].apply(
            lambda x: f"{(x / total_estoque * 100):.1f}%" if total_estoque > 0 else "—"
        )

        # Tabela HTML
        linhas = ""
        for _, row in df_valor.iterrows():
            linhas += (
                "<tr>"
                f"<td>{row['Empresa / Filial']}</td>"
                f"<td>{row['Conta']}</td>"
                f"<td>{row['Produto']}</td>"
                f"<td>{row['Descricao']}</td>"
                f"<td style='text-align:right'>{int(row['Qtd']):,}</td>"
                f"<td style='text-align:right'>{moeda_br(row['Valor'])}</td>"
                f"<td style='text-align:right;color:#EC6E21;font-weight:600'>{row['% Estoque']}</td>"
                "</tr>"
            )

        css = (
            "<style>.tb-top{width:100%;border-collapse:collapse;font-size:13px;color:white}"
            ".tb-top th{background:#0f5a60;padding:10px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700}"
            ".tb-top td{padding:8px 12px;border-bottom:1px solid #1a6e75;background:#005562}"
            ".tb-top tr:hover td{background:#0a6570}</style>"
        )

        st.html(
            css +
            "<table class='tb-top'><thead><tr>"
            "<th>Empresa / Filial</th><th>Conta</th><th>Produto</th><th>Descrição</th>"
            "<th style='text-align:right'>Qtd</th><th style='text-align:right'>Valor</th>"
            "<th style='text-align:right'>% Estoque</th>"
            "</tr></thead><tbody>" + linhas + "</tbody></table>"
        )

        # Export
        buffer = io.BytesIO()
        df_valor.drop(columns=["% Estoque"]).to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button("📥 Exportar Excel", data=buffer, file_name="top_produtos_valor.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── ABA 2: Maior Variação MoM ─────────────────────────────────────────────
    with sub2:

        if df_mom.empty:
            st.info("Sem dados do mês anterior para calcular variação.")
            return

        grp_atual = df_atual.groupby(["Empresa / Filial", "Conta", "Produto", "Descricao"]).agg(
            Qtd_Atual=("Saldo Atual", "sum"), Valor_Atual=("Custo Total", "sum")
        ).reset_index()

        grp_mom = df_mom.groupby(["Produto"]).agg(
            Valor_MoM=("Custo Total", "sum")
        ).reset_index()

        df_var = grp_atual.merge(grp_mom, on="Produto", how="outer").fillna(0)
        df_var["Descricao"] = df_var["Descricao"].fillna("").astype(str)
        df_var["Variacao"] = df_var["Valor_Atual"] - df_var["Valor_MoM"]
        df_var["% Var"] = df_var.apply(
            lambda r: f"{(r['Variacao'] / r['Valor_MoM'] * 100):.1f}%" if r["Valor_MoM"] != 0 else "Novo",
            axis=1
        )
        df_var["% Estoque"] = df_var["Valor_Atual"].apply(
            lambda x: f"{(x / total_estoque * 100):.1f}%" if total_estoque > 0 else "—"
        )

        def icone(v):
            if v > 0:  return f'<span style="color:#ff6b6b">⬆ +{moeda_br(abs(v))}</span>'
            elif v < 0: return f'<span style="color:#51cf66">⬇ -{moeda_br(abs(v))}</span>'
            return f'<span style="color:#aaa">● {moeda_br(0)}</span>'

        col1, col2 = st.columns(2)

        css = (
            "<style>.tb-var{width:100%;border-collapse:collapse;font-size:13px;color:white}"
            ".tb-var th{background:#0f5a60;padding:10px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700}"
            ".tb-var td{padding:8px 12px;border-bottom:1px solid #1a6e75;background:#005562}"
            ".tb-var tr:hover td{background:#0a6570}</style>"
        )

        with col1:
            st.markdown("**⬆ Maiores Altas**")
            df_alta = df_var.sort_values("Variacao", ascending=False).head(top_n)
            linhas_alta = "".join(
                f"<tr><td>{r['Produto']}</td><td>{str(r['Descricao'])[:35]}</td>"
                f"<td style='text-align:right'>{moeda_br(r['Valor_Atual'])}</td>"
                f"<td style='text-align:right'>{icone(r['Variacao'])}</td>"
                f"<td style='text-align:right;color:#EC6E21'>{r['% Var']}</td></tr>"
                for _, r in df_alta.iterrows()
            )
            st.html(css + "<table class='tb-var'><thead><tr>"
                    "<th>Produto</th><th>Descrição</th><th style='text-align:right'>Valor</th>"
                    "<th style='text-align:right'>Variação</th><th style='text-align:right'>% Var</th>"
                    "</tr></thead><tbody>" + linhas_alta + "</tbody></table>")

        with col2:
            st.markdown("**⬇ Maiores Quedas**")
            df_queda = df_var.sort_values("Variacao", ascending=True).head(top_n)
            linhas_queda = "".join(
                f"<tr><td>{r['Produto']}</td><td>{str(r['Descricao'])[:35]}</td>"
                f"<td style='text-align:right'>{moeda_br(r['Valor_Atual'])}</td>"
                f"<td style='text-align:right'>{icone(r['Variacao'])}</td>"
                f"<td style='text-align:right;color:#EC6E21'>{r['% Var']}</td></tr>"
                for _, r in df_queda.iterrows()
            )
            st.html(css + "<table class='tb-var'><thead><tr>"
                    "<th>Produto</th><th>Descrição</th><th style='text-align:right'>Valor</th>"
                    "<th style='text-align:right'>Variação</th><th style='text-align:right'>% Var</th>"
                    "</tr></thead><tbody>" + linhas_queda + "</tbody></table>")
