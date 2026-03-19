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

    # MoM
    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)

    # YoY
    data_yoy_alvo = pd.Timestamp(data_selecionada) - pd.DateOffset(years=1)
    datas_yoy = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
    if datas_yoy:
        data_yoy = min(datas_yoy, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
        df_yoy = df_hist[df_hist["Data Fechamento"] == data_yoy].copy()
    else:
        df_yoy = pd.DataFrame(columns=df_hist.columns)

    top_n = st.slider("Quantidade de produtos", min_value=5, max_value=50, value=10, step=5)

    sub1, sub2, sub3 = st.tabs(["💰 Maior Valor em Estoque", "📈 Maior Variação MoM", "📅 Maior Variação YoY"])

    total_estoque = df_atual["Custo Total"].sum()

    # Helper — descrição limpa
    def desc_limpa(df):
        # Busca descrição real do produto em todo o histórico
        desc_map = (
            df_hist[df_hist["Descricao"].notna() & (df_hist["Descricao"].astype(str).str.strip() != "") & (df_hist["Descricao"].astype(str) != "0")]
            .groupby("Produto")["Descricao"]
            .first()
            .to_dict()
        )
        df = df.copy()
        df["Descricao"] = df["Produto"].map(desc_map).fillna(df.get("Descricao", "")).astype(str)
        df["Descricao"] = df["Descricao"].replace("0", "—").replace("", "—")
        return df

    css = (
        "<style>.tb-top{width:100%;border-collapse:collapse;font-size:13px;color:white}"
        ".tb-top th{background:#0f5a60;padding:10px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700}"
        ".tb-top td{padding:8px 12px;border-bottom:1px solid #1a6e75;background:#005562}"
        ".tb-top tr:hover td{background:#0a6570}</style>"
    )

    def icone(v):
        if v > 0:   return f'<span style="color:#ff6b6b">⬆ +{moeda_br(abs(v))}</span>'
        elif v < 0: return f'<span style="color:#51cf66">⬇ -{moeda_br(abs(v))}</span>'
        return f'<span style="color:#aaa">● {moeda_br(0)}</span>'

    def tabela_variacao(df_base, df_comp, label_comp):
        if df_comp.empty:
            st.info(f"Sem dados de {label_comp} para calcular variação.")
            return

        grp_atual = df_base.groupby(["Empresa / Filial", "Conta", "Produto"]).agg(
            Valor_Atual=("Custo Total", "sum")
        ).reset_index()

        grp_comp = df_comp.groupby(["Produto"]).agg(
            Valor_Comp=("Custo Total", "sum")
        ).reset_index()

        df_var = grp_atual.merge(grp_comp, on="Produto", how="outer").fillna(0)
        df_var = desc_limpa(df_var)
        df_var["Variacao"] = df_var["Valor_Atual"] - df_var["Valor_Comp"]
        df_var["% Var"] = df_var.apply(
            lambda r: f"{(r['Variacao'] / r['Valor_Comp'] * 100):.1f}%" if r["Valor_Comp"] != 0 else "Novo",
            axis=1
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**⬆ Maiores Altas**")
            df_alta = df_var.sort_values("Variacao", ascending=False).head(top_n)
            linhas = "".join(
                f"<tr><td>{r['Produto']}</td><td>{r['Descricao'][:40]}</td>"
                f"<td style='text-align:right'>{moeda_br(r['Valor_Atual'])}</td>"
                f"<td style='text-align:right'>{icone(r['Variacao'])}</td>"
                f"<td style='text-align:right;color:#EC6E21'>{r['% Var']}</td></tr>"
                for _, r in df_alta.iterrows()
            )
            st.markdown(css + "<table class='tb-top'><thead><tr>"
                    "<th>Produto</th><th>Descrição</th><th style='text-align:right'>Valor Atual</th>"
                    f"<th style='text-align:right'>Variação vs {label_comp}</th><th style='text-align:right'>% Var</th>"
                    "</tr></thead><tbody>" + linhas + "</tbody></table>",
            unsafe_allow_html=True
        )

        with col2:
            st.markdown("**⬇ Maiores Quedas**")
            df_queda = df_var.sort_values("Variacao", ascending=True).head(top_n)
            linhas = "".join(
                f"<tr><td>{r['Produto']}</td><td>{r['Descricao'][:40]}</td>"
                f"<td style='text-align:right'>{moeda_br(r['Valor_Atual'])}</td>"
                f"<td style='text-align:right'>{icone(r['Variacao'])}</td>"
                f"<td style='text-align:right;color:#EC6E21'>{r['% Var']}</td></tr>"
                for _, r in df_queda.iterrows()
            )
            st.markdown(css + "<table class='tb-top'><thead><tr>"
                    "<th>Produto</th><th>Descrição</th><th style='text-align:right'>Valor Atual</th>"
                    f"<th style='text-align:right'>Variação vs {label_comp}</th><th style='text-align:right'>% Var</th>"
                    "</tr></thead><tbody>" + linhas + "</tbody></table>",
            unsafe_allow_html=True
        )

    # ── ABA 1: Maior Valor em Estoque ─────────────────────────────────────────
    with sub1:
        df_valor = (
            df_atual.groupby(["Empresa / Filial", "Conta", "Produto"])
            .agg(Qtd=("Saldo Atual", "sum"), Valor=("Custo Total", "sum"))
            .reset_index()
            .sort_values("Valor", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )
        df_valor = desc_limpa(df_valor)
        df_valor["% Estoque"] = df_valor["Valor"].apply(
            lambda x: f"{(x / total_estoque * 100):.1f}%" if total_estoque > 0 else "—"
        )

        linhas = ""
        for _, row in df_valor.iterrows():
            linhas += (
                "<tr>"
                f"<td>{row['Empresa / Filial']}</td>"
                f"<td>{row['Conta']}</td>"
                f"<td>{row['Produto']}</td>"
                f"<td>{row['Descricao'][:40]}</td>"
                f"<td style='text-align:right'>{int(row['Qtd']):,}</td>"
                f"<td style='text-align:right'>{moeda_br(row['Valor'])}</td>"
                f"<td style='text-align:right;color:#EC6E21;font-weight:600'>{row['% Estoque']}</td>"
                "</tr>"
            )

        st.markdown(
            css +
            "<table class='tb-top'><thead><tr>"
            "<th>Empresa / Filial</th><th>Conta</th><th>Produto</th><th>Descrição</th>"
            "<th style='text-align:right'>Qtd Estoque</th><th style='text-align:right'>Valor Estoque</th>"
            "<th style='text-align:right'>% Estoque</th>"
            "</tr></thead><tbody>" + linhas + "</tbody></table>",
        unsafe_allow_html=True
        )

        buffer = io.BytesIO()
        df_valor.drop(columns=["% Estoque"]).to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button("📥 Exportar Excel", data=buffer, file_name="top_produtos_valor.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ── ABA 2: Maior Variação MoM ─────────────────────────────────────────────
    with sub2:
        label_mom = pd.Timestamp(data_mom).strftime('%d/%m/%Y') if not df_mom.empty else "mês anterior"
        tabela_variacao(df_atual, df_mom, label_mom)

    # ── ABA 3: Maior Variação YoY ─────────────────────────────────────────────
    with sub3:
        label_yoy = pd.Timestamp(data_yoy).strftime('%d/%m/%Y') if not df_yoy.empty else "ano anterior"
        tabela_variacao(df_atual, df_yoy, label_yoy)
