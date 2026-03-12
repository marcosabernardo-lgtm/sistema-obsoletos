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
        st.info("Sem dados do mês anterior para calcular redução.")
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

    # Merge outer para capturar produtos que sumiram
    df_var = grp_mom.merge(grp_atual, on="Produto", how="outer").fillna(0)
    df_var = df_var.merge(desc, on="Produto", how="left")
    df_var["Reducao"] = df_var["Valor MoM"] - df_var["Valor Atual"]
    df_var["Perc"]    = df_var.apply(
        lambda r: (r["Reducao"] / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1
    )

    # Só produtos que reduziram
    df_reduziu = df_var[df_var["Reducao"] > 0].copy()

    # Separar zerados e parciais
    df_zerados  = df_reduziu[df_reduziu["Valor Atual"] == 0].sort_values("Reducao", ascending=False).reset_index(drop=True)
    df_parciais = df_reduziu[df_reduziu["Valor Atual"] > 0].sort_values("Reducao", ascending=False).reset_index(drop=True)

    # Helper HTML
    def tabela_html(df, mostrar_valor_atual=True):
        if df.empty:
            return "<p style='color:#aaa;padding:16px'>Nenhum produto encontrado.</p>"

        linhas = ""
        for _, row in df.iterrows():
            perc = row["Perc"]
            perc_html = f'<span style="color:#51cf66;font-weight:700">⬇ {abs(perc):.0f}%</span>'

            linhas += (
                "<tr>"
                "<td>" + str(row["Produto"]) + "</td>"
                "<td>" + str(row["Descricao"]) + "</td>"
                "<td>" + str(row["Conta"]) + "</td>"
                "<td>" + str(row["Empresa / Filial"]) + "</td>"
                "<td>" + moeda_br(row["Valor MoM"]) + "</td>"
            )
            if mostrar_valor_atual:
                linhas += "<td>" + moeda_br(row["Valor Atual"]) + "</td>"
            linhas += (
                "<td style='color:#51cf66'>" + moeda_br(row["Reducao"]) + "</td>"
                "<td>" + perc_html + "</td>"
                "</tr>"
            )

        headers = (
            "<th>Código</th><th>Descrição</th><th>Conta</th><th>Empresa / Filial</th>"
            "<th>Valor MoM</th>"
        )
        if mostrar_valor_atual:
            headers += "<th>Valor Atual</th>"
        headers += "<th>Redução R$</th><th>% Redução</th>"

        css = (
            "<style>"
            ".tb-red{width:100%;border-collapse:collapse;font-size:13px;color:white;}"
            ".tb-red th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;"
            "border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap;}"
            ".tb-red th:not(:first-child):not(:nth-child(2)){text-align:right;}"
            ".tb-red td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}"
            ".tb-red td:not(:first-child):not(:nth-child(2)):not(:nth-child(3)):not(:nth-child(4)){text-align:right;}"
            ".tb-red tr:hover td{background-color:#0a6570;}"
            "</style>"
        )

        return (
            css
            + "<table class='tb-red'><thead><tr>"
            + headers
            + "</tr></thead><tbody>"
            + linhas
            + "</tbody></table>"
        )

    # Sub-abas
    sub1, sub2 = st.tabs([
        f"🚫 Zerados ({len(df_zerados)})",
        f"📉 Reduziram ({len(df_parciais)})"
    ])

    with sub1:
        st.markdown(
            f"<p style='color:#aaa;font-size:13px'>Produtos que estavam no estoque em "
            f"<b style='color:white'>{pd.Timestamp(data_mom).strftime('%d/%m/%Y')}</b> e "
            f"<b style='color:#51cf66'>zeraram</b> em "
            f"<b style='color:white'>{data_selecionada.strftime('%d/%m/%Y')}</b>.</p>",
            unsafe_allow_html=True
        )
        total_zerado = df_zerados["Reducao"].sum()
        st.markdown(
            f"<p style='color:white;font-size:14px'>💰 Total liberado: "
            f"<b style='color:#51cf66'>{moeda_br(total_zerado)}</b> | "
            f"<b style='color:white'>{len(df_zerados)}</b> produtos</p>",
            unsafe_allow_html=True
        )
        st.html(tabela_html(df_zerados, mostrar_valor_atual=False))

    with sub2:
        st.markdown(
            f"<p style='color:#aaa;font-size:13px'>Produtos que reduziram valor entre "
            f"<b style='color:white'>{pd.Timestamp(data_mom).strftime('%d/%m/%Y')}</b> e "
            f"<b style='color:white'>{data_selecionada.strftime('%d/%m/%Y')}</b>.</p>",
            unsafe_allow_html=True
        )
        total_parcial = df_parciais["Reducao"].sum()
        st.markdown(
            f"<p style='color:white;font-size:14px'>💰 Total reduzido: "
            f"<b style='color:#51cf66'>{moeda_br(total_parcial)}</b> | "
            f"<b style='color:white'>{len(df_parciais)}</b> produtos</p>",
            unsafe_allow_html=True
        )
        st.html(tabela_html(df_parciais, mostrar_valor_atual=True))