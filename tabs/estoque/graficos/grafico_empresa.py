import streamlit as st
import pandas as pd
import altair as alt


def render(df, moeda_br, data_selecionada=None):
    df = df.copy()
    df["Data Fechamento"] = pd.to_datetime(df["Data Fechamento"])

    ultima_data = df["Data Fechamento"].max()
    data_ref = data_selecionada if data_selecionada is not None else ultima_data

    base = df[df["Data Fechamento"] == data_ref]

    empresa = (
        base.groupby("Empresa / Filial")["Custo Total"]
        .sum()
        .reset_index()
        .sort_values("Custo Total", ascending=False)
    )

    empresa["Label"] = empresa["Custo Total"].apply(
        lambda x: f"R$ {x/1_000_000:.1f} Mi" if x >= 1_000_000 else f"R$ {x/1_000:.0f} Mil"
    )

    bars = alt.Chart(empresa).mark_bar(
        color="#FF9A4D",
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4
    ).encode(
        x=alt.X(
            "Empresa / Filial:N",
            sort=alt.SortField(field="Custo Total", order="descending"),
            axis=alt.Axis(
                title=None,
                labelAngle=0,
                labelColor="white",
                labelFontSize=11,
                tickColor="white",
                domainColor="white"
            )
        ),
        y=alt.Y(
            "Custo Total:Q",
            axis=alt.Axis(
                title=None,
                labels=False,
                ticks=False,
                grid=False,
                domain=False
            )
        ),
        tooltip=[
            alt.Tooltip("Empresa / Filial:N", title="Empresa"),
            alt.Tooltip("Custo Total:Q", title="Valor", format=",.2f")
        ]
    )

    labels = alt.Chart(empresa).mark_text(
        dy=-10,
        color="white",
        fontSize=11
    ).encode(
        x=alt.X(
            "Empresa / Filial:N",
            sort=alt.SortField(field="Custo Total", order="descending")
        ),
        y=alt.Y("Custo Total:Q"),
        text="Label"
    )

    chart = (bars + labels).properties(
        height=420
    ).configure_view(
        strokeWidth=0
    ).configure_axisX(
        grid=False,
        labelColor="white",
        labelAngle=0,
        tickColor="white",
        domainColor="white"
    ).configure_axisY(
        grid=False,
        labels=False,
        ticks=False,
        domain=False,
        title=None
    )

    st.altair_chart(chart, use_container_width=True)

    # ── Tabela Por Empresa ─────────────────────────────────────────────────────
    st.markdown("---")

    # Período atual
    df_atual = df[df["Data Fechamento"] == data_ref].copy()

    # Período anterior (MoM)
    datas_sorted = sorted(df["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_ref) if data_ref in datas_sorted else -1

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df[df["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df.columns)

    grp_atual = (
        df_atual.groupby("Empresa / Filial")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor Estoque"})
    )
    grp_mom = (
        df_mom.groupby("Empresa / Filial")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor MoM"})
    ) if not df_mom.empty else pd.DataFrame(columns=["Empresa / Filial", "Valor MoM"])

    df_tabela = grp_atual.merge(grp_mom, on="Empresa / Filial", how="left")
    df_tabela["Valor MoM"] = df_tabela["Valor MoM"].fillna(0)
    df_tabela["Perc MoM"]  = df_tabela.apply(
        lambda r: ((r["Valor Estoque"] - r["Valor MoM"]) / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1
    )
    df_tabela = df_tabela.sort_values("Valor Estoque", ascending=False).reset_index(drop=True)

    # Totais
    total_atual = df_tabela["Valor Estoque"].sum()
    total_mom   = df_tabela["Valor MoM"].sum()
    total_perc  = ((total_atual - total_mom) / total_mom * 100) if total_mom != 0 else 0

    def icone_perc(perc):
        if perc > 1:    return '<span style="color:#ff6b6b;font-weight:700">&#11014; ' + f'{abs(perc):.0f}%</span>'
        elif perc < -1: return '<span style="color:#51cf66;font-weight:700">&#11015; ' + f'{abs(perc):.0f}%</span>'
        else:           return '<span style="color:#f0a500;font-weight:700">&#9679; ' + f'{abs(perc):.0f}%</span>'

    linhas = ""
    for _, row in df_tabela.iterrows():
        linhas += (
            "<tr>"
            "<td>" + str(row["Empresa / Filial"]) + "</td>"
            "<td>" + moeda_br(row["Valor Estoque"]) + "</td>"
            "<td>" + moeda_br(row["Valor MoM"]) + "</td>"
            "<td>" + icone_perc(row["Perc MoM"]) + "</td>"
            "</tr>"
        )

    total_html = (
        "<tr style='font-weight:700;border-top:2px solid #EC6E21'>"
        "<td>Total</td>"
        "<td>" + moeda_br(total_atual) + "</td>"
        "<td>" + moeda_br(total_mom) + "</td>"
        "<td>" + icone_perc(total_perc) + "</td>"
        "</tr>"
    )

    css = (
        "<style>"
        ".tb-emp{width:100%;border-collapse:collapse;font-size:14px;color:white;}"
        ".tb-emp th{background-color:#0f5a60;color:white;padding:10px 14px;text-align:left;"
        "border-bottom:2px solid #EC6E21;font-weight:700;}"
        ".tb-emp th:not(:first-child){text-align:right;}"
        ".tb-emp td{padding:8px 14px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}"
        ".tb-emp td:not(:first-child){text-align:right;}"
        ".tb-emp tr:hover td{background-color:#0a6570;}"
        "</style>"
    )

    tabela = (
        css
        + "<table class='tb-emp'><thead><tr>"
        + "<th>Empresa / Filial</th><th>Valor Estoque (Total)</th><th>Vir Est MoM</th><th>% MoM</th>"
        + "</tr></thead><tbody>"
        + linhas
        + total_html
        + "</tbody></table>"
    )

    st.html(tabela)