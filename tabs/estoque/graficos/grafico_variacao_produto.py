import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()

    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    if idx <= 0:
        st.info("Sem dados do mês anterior para calcular variação.")
        return

    data_mom = datas_sorted[idx - 1]
    df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()

    # Agrupar por Produto
    grp_atual = df_atual.groupby("Produto")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor Atual"})
    grp_mom   = df_mom.groupby("Produto")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor MoM"})

    # Descrição com fallback
    desc_atual = df_atual.groupby("Produto")[["Descricao", "Conta", "Empresa / Filial"]].first().reset_index()
    desc_mom   = df_mom.groupby("Produto")[["Descricao", "Conta", "Empresa / Filial"]].first().reset_index()
    desc = pd.concat([desc_mom, desc_atual]).drop_duplicates(subset="Produto", keep="last")

    df_var = grp_mom.merge(grp_atual, on="Produto", how="outer").fillna(0)
    df_var = df_var.merge(desc, on="Produto", how="left")
    df_var["Variacao"] = df_var["Valor Atual"] - df_var["Valor MoM"]
    df_var["Perc"] = df_var.apply(
        lambda r: (r["Variacao"] / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1
    )

    # Status Mov
    def status(row):
        if row["Valor MoM"] > 0 and row["Valor Atual"] == 0:
            return "Zerado"
        elif row["Variacao"] < 0:
            return "Reduziu"
        elif row["Variacao"] > 0:
            return "Aumentou"
        else:
            return "Manteve"

    df_var["Status Mov"] = df_var.apply(status, axis=1)

    # Totais para cards
    total_mom    = df_var["Valor MoM"].sum()
    total_atual  = df_var["Valor Atual"].sum()
    total_aument = df_var[df_var["Status Mov"] == "Aumentou"]["Variacao"].sum()
    total_reduz  = df_var[df_var["Status Mov"] == "Reduziu"]["Variacao"].abs().sum()
    total_zerado = df_var[df_var["Status Mov"] == "Zerado"]["Valor MoM"].sum()

    qtd_zerado   = len(df_var[df_var["Status Mov"] == "Zerado"])
    qtd_reduz    = len(df_var[df_var["Status Mov"] == "Reduziu"])
    qtd_aument   = len(df_var[df_var["Status Mov"] == "Aumentou"])
    qtd_manteve  = len(df_var[df_var["Status Mov"] == "Manteve"])

    label_mom   = pd.Timestamp(data_mom).strftime("%d/%m/%Y")
    label_atual = data_selecionada.strftime("%d/%m/%Y")

    # ── Cards de resumo ────────────────────────────────────────────────────────
    st.markdown(f"""
    <style>
    .card-mov {{
        background-color:#005562;
        border:2px solid #EC6E21;
        border-radius:10px;
        padding:14px 16px;
        text-align:center;
    }}
    .card-mov .titulo {{ font-size:12px; color:#ccc; margin-bottom:4px; }}
    .card-mov .valor  {{ font-size:20px; font-weight:700; color:white; }}
    .card-mov .sub    {{ font-size:12px; margin-top:4px; }}
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(f"""
    <div class="card-mov">
        <div class="titulo">Estoque {label_mom}</div>
        <div class="valor">{moeda_br(total_mom)}</div>
        <div class="sub" style="color:#ccc">Mês anterior</div>
    </div>""", unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="card-mov">
        <div class="titulo">⬆ Aumentos ({qtd_aument})</div>
        <div class="valor" style="color:#ff6b6b">+{moeda_br(total_aument)}</div>
        <div class="sub" style="color:#ff6b6b">Entradas</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="card-mov">
        <div class="titulo">⬇ Reduções ({qtd_reduz})</div>
        <div class="valor" style="color:#51cf66">-{moeda_br(total_reduz)}</div>
        <div class="sub" style="color:#51cf66">Saídas parciais</div>
    </div>""", unsafe_allow_html=True)

    c4.markdown(f"""
    <div class="card-mov">
        <div class="titulo">🚫 Zerados ({qtd_zerado})</div>
        <div class="valor" style="color:#51cf66">-{moeda_br(total_zerado)}</div>
        <div class="sub" style="color:#51cf66">Saídas totais</div>
    </div>""", unsafe_allow_html=True)

    c5.markdown(f"""
    <div class="card-mov">
        <div class="titulo">Estoque {label_atual}</div>
        <div class="valor">{moeda_br(total_atual)}</div>
        <div class="sub" style="color:#ccc">Mês atual</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filtro por status ──────────────────────────────────────────────────────
    # DEPOIS
    opcoes = ["Todos", "Aumentou", "Reduziu", "Zerado", "Manteve"]
    status_sel = st.selectbox("Filtrar por Status Mov", opcoes)

    df_filtrado = df_var.copy()
    if status_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Status Mov"] == status_sel]

    df_filtrado = df_filtrado.sort_values("Variacao", key=abs, ascending=False).reset_index(drop=True)

    # ── Tabela HTML ────────────────────────────────────────────────────────────
    def cor_status(s):
        if s == "Aumentou": return "color:#ff6b6b;font-weight:700"
        if s == "Reduziu":  return "color:#51cf66;font-weight:700"
        if s == "Zerado":   return "color:#51cf66;font-weight:700"
        return "color:#f0a500;font-weight:700"

    def icone_perc(perc, status):
        if status == "Aumentou": return f'<span style="color:#ff6b6b;font-weight:700">⬆ {abs(perc):.0f}%</span>'
        if status in ("Reduziu","Zerado"): return f'<span style="color:#51cf66;font-weight:700">⬇ {abs(perc):.0f}%</span>'
        return f'<span style="color:#f0a500;font-weight:700">● 0%</span>'

    linhas = ""
    for _, row in df_filtrado.iterrows():
        cs = cor_status(row["Status Mov"])
        linhas += (
            "<tr>"
            "<td>" + str(row["Produto"]) + "</td>"
            "<td>" + str(row.get("Descricao","")) + "</td>"
            "<td>" + str(row.get("Conta","")) + "</td>"
            "<td>" + str(row.get("Empresa / Filial","")) + "</td>"
            "<td style='" + cs + "'>" + str(row["Status Mov"]) + "</td>"
            "<td>" + moeda_br(row["Valor MoM"]) + "</td>"
            "<td>" + moeda_br(row["Valor Atual"]) + "</td>"
            "<td>" + moeda_br(abs(row["Variacao"])) + "</td>"
            "<td>" + icone_perc(row["Perc"], row["Status Mov"]) + "</td>"
            "</tr>"
        )

    css = (
        "<style>"
        ".tb-mov{width:100%;border-collapse:collapse;font-size:13px;color:white;}"
        ".tb-mov th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;"
        "border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap;}"
        ".tb-mov th:nth-child(n+6){text-align:right;}"
        ".tb-mov td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}"
        ".tb-mov td:nth-child(n+6){text-align:right;}"
        ".tb-mov tr:hover td{background-color:#0a6570;}"
        "</style>"
    )

    tabela = (
        css
        + f"<p style='color:#aaa;font-size:12px'>{len(df_filtrado)} produtos</p>"
        + "<table class='tb-mov'><thead><tr>"
        + "<th>Código</th><th>Descrição</th><th>Conta</th><th>Empresa / Filial</th>"
        + "<th>Status Mov</th><th>Valor MoM</th><th>Valor Atual</th><th>Variação R$</th><th>%</th>"
        + "</tr></thead><tbody>"
        + linhas
        + "</tbody></table>"
    )

    st.html(tabela)