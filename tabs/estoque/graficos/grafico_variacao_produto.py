import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    # Período atual
    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

    # Período anterior (MoM)
    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    if idx <= 0:
        st.info("Sem dados do mês anterior para calcular variação.")
        return

    data_mom = datas_sorted[idx - 1]
    df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()

    # Agrupar por Produto
    grp_atual = (
        df_atual.groupby("Produto")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor Atual"})
    )
    grp_mom = (
        df_mom.groupby("Produto")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor MoM"})
    )

    # Descrição com fallback para mês anterior
    desc_atual = df_atual.groupby("Produto")[["Descricao", "Conta", "Empresa / Filial"]].first().reset_index()
    desc_mom   = df_mom.groupby("Produto")[["Descricao", "Conta", "Empresa / Filial"]].first().reset_index()
    desc = pd.concat([desc_mom, desc_atual]).drop_duplicates(subset="Produto", keep="last")

    # Merge outer para capturar produtos que sumiram ou apareceram
    df_var = grp_mom.merge(grp_atual, on="Produto", how="outer").fillna(0)
    df_var = df_var.merge(desc, on="Produto", how="left")
    df_var["Variacao"] = df_var["Valor Atual"] - df_var["Valor MoM"]
    df_var["Perc"] = df_var.apply(
        lambda r: (r["Variacao"] / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1
    )

    # Separar grupos
    df_zerados   = df_var[(df_var["Valor Atual"] == 0) & (df_var["Valor MoM"] > 0)].sort_values("Variacao").reset_index(drop=True)
    df_reduziram = df_var[(df_var["Valor Atual"] > 0) & (df_var["Variacao"] < 0)].sort_values("Variacao").reset_index(drop=True)
    df_aumentaram = df_var[df_var["Variacao"] > 0].sort_values("Variacao", ascending=False).reset_index(drop=True)

    # Helper tabela HTML
    def tabela_html(df, tipo="reducao"):
        if df.empty:
            return "<p style='color:#aaa;padding:16px'>Nenhum produto encontrado.</p>"

        linhas = ""
        for _, row in df.iterrows():
            perc = row["Perc"]

            if tipo == "aumento":
                perc_html = f'<span style="color:#ff6b6b;font-weight:700">⬆ {abs(perc):.0f}%</span>'
                cor_var   = "color:#ff6b6b"
            else:
                perc_html = f'<span style="color:#51cf66;font-weight:700">⬇ {abs(perc):.0f}%</span>'
                cor_var   = "color:#51cf66"

            linhas += (
                "<tr>"
                "<td>" + str(row["Produto"]) + "</td>"
                "<td>" + str(row.get("Descricao", "")) + "</td>"
                "<td>" + str(row.get("Conta", "")) + "</td>"
                "<td>" + str(row.get("Empresa / Filial", "")) + "</td>"
                "<td>" + moeda_br(row["Valor MoM"]) + "</td>"
                "<td>" + moeda_br(row["Valor Atual"]) + "</td>"
                "<td style='" + cor_var + "'>" + moeda_br(abs(row["Variacao"])) + "</td>"
                "<td>" + perc_html + "</td>"
                "</tr>"
            )

        css = (
            "<style>"
            ".tb-var{width:100%;border-collapse:collapse;font-size:13px;color:white;}"
            ".tb-var th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;"
            "border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap;}"
            ".tb-var th:nth-child(n+5){text-align:right;}"
            ".tb-var td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}"
            ".tb-var td:nth-child(n+5){text-align:right;}"
            ".tb-var tr:hover td{background-color:#0a6570;}"
            "</style>"
        )

        return (
            css
            + "<table class='tb-var'><thead><tr>"
            + "<th>Código</th><th>Descrição</th><th>Conta</th><th>Empresa / Filial</th>"
            + "<th>Valor MoM</th><th>Valor Atual</th><th>Variação R$</th><th>%</th>"
            + "</tr></thead><tbody>"
            + linhas
            + "</tbody></table>"
        )

    def resumo_html(total, qtd, cor, label):
        return (
            f"<p style='color:white;font-size:14px'>💰 Total: "
            f"<b style='color:{cor}'>{moeda_br(total)}</b> | "
            f"<b style='color:white'>{qtd}</b> {label}</p>"
        )

    # Sub-abas
    sub1, sub2, sub3 = st.tabs([
        f"🚫 Zerados ({len(df_zerados)})",
        f"📉 Reduziram ({len(df_reduziram)})",
        f"📈 Aumentaram ({len(df_aumentaram)})"
    ])

    with sub1:
        st.markdown(
            f"<p style='color:#aaa;font-size:13px'>Produtos que estavam no estoque em "
            f"<b style='color:white'>{pd.Timestamp(data_mom).strftime('%d/%m/%Y')}</b> e "
            f"<b style='color:#51cf66'>zeraram</b> em "
            f"<b style='color:white'>{data_selecionada.strftime('%d/%m/%Y')}</b>.</p>",
            unsafe_allow_html=True
        )
        st.markdown(resumo_html(df_zerados["Valor MoM"].sum(), len(df_zerados), "#51cf66", "produtos zerados"), unsafe_allow_html=True)
        st.html(tabela_html(df_zerados[["Produto","Descricao","Conta","Empresa / Filial","Valor MoM","Valor Atual","Variacao","Perc"]], tipo="reducao"))

    with sub2:
        st.markdown(
            f"<p style='color:#aaa;font-size:13px'>Produtos que reduziram parcialmente entre "
            f"<b style='color:white'>{pd.Timestamp(data_mom).strftime('%d/%m/%Y')}</b> e "
            f"<b style='color:white'>{data_selecionada.strftime('%d/%m/%Y')}</b>.</p>",
            unsafe_allow_html=True
        )
        st.markdown(resumo_html(df_reduziram["Variacao"].abs().sum(), len(df_reduziram), "#51cf66", "produtos reduziram"), unsafe_allow_html=True)
        st.html(tabela_html(df_reduziram[["Produto","Descricao","Conta","Empresa / Filial","Valor MoM","Valor Atual","Variacao","Perc"]], tipo="reducao"))

    with sub3:
        st.markdown(
            f"<p style='color:#aaa;font-size:13px'>Produtos que aumentaram de valor entre "
            f"<b style='color:white'>{pd.Timestamp(data_mom).strftime('%d/%m/%Y')}</b> e "
            f"<b style='color:white'>{data_selecionada.strftime('%d/%m/%Y')}</b>.</p>",
            unsafe_allow_html=True
        )
        st.markdown(resumo_html(df_aumentaram["Variacao"].sum(), len(df_aumentaram), "#ff6b6b", "produtos aumentaram"), unsafe_allow_html=True)
        st.html(tabela_html(df_aumentaram[["Produto","Descricao","Conta","Empresa / Filial","Valor MoM","Valor Atual","Variacao","Perc"]], tipo="aumento"))