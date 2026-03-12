import streamlit as st
import pandas as pd
import numpy as np


def render(df_hist, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_hist = df_hist.copy()
    df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"]).dt.normalize()
    data_selecionada = pd.Timestamp(data_selecionada.date())

    meses = st.slider("Meses para calcular consumo médio", min_value=2, max_value=24, value=6, step=1)

    datas_sorted = sorted([d for d in df_hist["Data Fechamento"].unique() if d <= data_selecionada])

    if len(datas_sorted) < 2:
        st.info("Histórico insuficiente para calcular DIO.")
        return

    datas_janela = datas_sorted[-meses:] if len(datas_sorted) >= meses else datas_sorted

    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()
    desc = df_atual.groupby("Produto")[["Descricao", "Conta", "Empresa / Filial"]].first().reset_index()

    grp_atual = (
        df_atual.groupby("Produto")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Valor Atual"})
    )

    df_janela = df_hist[df_hist["Data Fechamento"].isin(datas_janela)].copy()

    pivot = (
        df_janela.groupby(["Produto", "Data Fechamento"])["Custo Total"]
        .sum()
        .unstack(fill_value=0)
        .sort_index(axis=1)
    )

    consumo_list = []
    for produto in pivot.index:
        valores = pivot.loc[produto].values
        reducoes = [max(0, valores[i] - valores[i+1]) for i in range(len(valores)-1)]
        consumo_medio = np.mean(reducoes) if reducoes else 0
        consumo_list.append({"Produto": produto, "Consumo Medio Mensal": consumo_medio})

    df_consumo = pd.DataFrame(consumo_list)

    df_dio = grp_atual.merge(df_consumo, on="Produto", how="left")
    df_dio = df_dio.merge(desc, on="Produto", how="left")
    df_dio["Consumo Medio Mensal"] = df_dio["Consumo Medio Mensal"].fillna(0)

    def calcular_dio(row):
        if row["Consumo Medio Mensal"] > 0:
            return (row["Valor Atual"] / row["Consumo Medio Mensal"]) * 30
        return None

    df_dio["DIO"] = df_dio.apply(calcular_dio, axis=1)

    def classificar(dio):
        if dio is None:         return "Sem Consumo"
        elif dio <= 30:         return "Giro Alto (≤30d)"
        elif dio <= 90:         return "Giro Médio (31-90d)"
        elif dio <= 180:        return "Giro Baixo (91-180d)"
        else:                   return "Crítico (>180d)"

    df_dio["Classificação"] = df_dio["DIO"].apply(classificar)

    # Cards
    total_estoque = df_dio["Valor Atual"].sum()

    # DIO mediano — ignorar valores absurdos acima de 9999 dias
    dio_validos  = df_dio[df_dio["DIO"].notna() & (df_dio["DIO"] < 9999)]["DIO"]
    dio_mediano  = dio_validos.median() if not dio_validos.empty else None

    qtd_alto    = len(df_dio[df_dio["Classificação"] == "Giro Alto (≤30d)"])
    qtd_medio   = len(df_dio[df_dio["Classificação"] == "Giro Médio (31-90d)"])
    qtd_baixo   = len(df_dio[df_dio["Classificação"] == "Giro Baixo (91-180d)"])
    qtd_critico = len(df_dio[df_dio["Classificação"] == "Crítico (>180d)"])
    qtd_sem     = len(df_dio[df_dio["Classificação"] == "Sem Consumo"])

    val_critico  = df_dio[df_dio["Classificação"].isin(["Crítico (>180d)", "Sem Consumo"])]["Valor Atual"].sum()
    perc_critico = (val_critico / total_estoque * 100) if total_estoque > 0 else 0

    st.markdown("""
    <style>
    .card-dio{background-color:#005562;border:2px solid #EC6E21;border-radius:10px;padding:14px 16px;text-align:center;}
    .card-dio .titulo{font-size:12px;color:#ccc;margin-bottom:4px;}
    .card-dio .valor{font-size:20px;font-weight:700;color:white;}
    .card-dio .sub{font-size:12px;margin-top:4px;}
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(f"""
    <div class="card-dio">
        <div class="titulo">Total em Estoque</div>
        <div class="valor">{moeda_br(total_estoque)}</div>
        <div class="sub" style="color:#ccc">{len(df_dio)} produtos</div>
    </div>""", unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="card-dio">
        <div class="titulo">DIO Mediano</div>
        <div class="valor">{f"{dio_mediano:.0f} dias" if dio_mediano is not None else "—"}</div>
        <div class="sub" style="color:#ccc">últimos {meses} meses</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="card-dio">
        <div class="titulo">🚨 Crítico + Sem Consumo</div>
        <div class="valor" style="color:#ff6b6b">{moeda_br(val_critico)}</div>
        <div class="sub" style="color:#ff6b6b">{qtd_critico + qtd_sem} produtos — {perc_critico:.1f}%</div>
    </div>""", unsafe_allow_html=True)

    c4.markdown(f"""
    <div class="card-dio">
        <div class="titulo">✅ Giro Alto + Médio</div>
        <div class="valor" style="color:#51cf66">{qtd_alto + qtd_medio} produtos</div>
        <div class="sub" style="color:#51cf66">≤ 90 dias</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabela resumo por classificação
    resumo = df_dio.groupby("Classificação").agg(
        Produtos=("Produto", "count"),
        Valor=("Valor Atual", "sum")
    ).reset_index()

    ordem = ["Giro Alto (≤30d)", "Giro Médio (31-90d)", "Giro Baixo (91-180d)", "Crítico (>180d)", "Sem Consumo"]
    resumo["_ordem"] = resumo["Classificação"].apply(lambda x: ordem.index(x) if x in ordem else 99)
    resumo = resumo.sort_values("_ordem").drop(columns="_ordem")

    def cor_class(c):
        if c == "Giro Alto (≤30d)":     return "color:#51cf66;font-weight:700"
        if c == "Giro Médio (31-90d)":  return "color:#74c0fc;font-weight:700"
        if c == "Giro Baixo (91-180d)": return "color:#f0a500;font-weight:700"
        if c == "Crítico (>180d)":      return "color:#ff6b6b;font-weight:700"
        return "color:#aaa;font-weight:700"

    linhas_resumo = ""
    for _, row in resumo.iterrows():
        perc = (row["Valor"] / total_estoque * 100) if total_estoque > 0 else 0
        linhas_resumo += (
            "<tr>"
            "<td style='" + cor_class(row["Classificação"]) + "'>" + str(row["Classificação"]) + "</td>"
            "<td>" + str(int(row["Produtos"])) + "</td>"
            "<td>" + moeda_br(row["Valor"]) + "</td>"
            "<td>" + f"{perc:.1f}%" + "</td>"
            "</tr>"
        )

    css_resumo = (
        "<style>"
        ".tb-resumo{width:100%;border-collapse:collapse;font-size:13px;color:white;margin-bottom:24px;}"
        ".tb-resumo th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700;}"
        ".tb-resumo th:not(:first-child){text-align:right;}"
        ".tb-resumo td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;}"
        ".tb-resumo td:not(:first-child){text-align:right;}"
        "</style>"
    )

    st.html(css_resumo + "<table class='tb-resumo'><thead><tr>"
        + "<th>Classificação</th><th>Produtos</th><th>Valor</th><th>% Estoque</th>"
        + "</tr></thead><tbody>" + linhas_resumo + "</tbody></table>")

    # Filtro e tabela detalhada
    filtro = st.selectbox("Filtrar por classificação", ["Todos"] + ordem)

    df_tabela = df_dio.copy() if filtro == "Todos" else df_dio[df_dio["Classificação"] == filtro].copy()
    df_tabela = df_tabela.sort_values("DIO", ascending=False, na_position="first").reset_index(drop=True)

    linhas = ""
    for _, row in df_tabela.iterrows():
        dio_val = row["DIO"]
        dio_str = f"{dio_val:.0f} dias" if dio_val is not None and not (isinstance(dio_val, float) and np.isnan(dio_val)) else "—"
        consumo_str = moeda_br(row["Consumo Medio Mensal"]) if row["Consumo Medio Mensal"] > 0 else "—"
        linhas += (
            "<tr>"
            "<td>" + str(row["Produto"]) + "</td>"
            "<td>" + str(row.get("Descricao", "")) + "</td>"
            "<td>" + str(row.get("Conta", "")) + "</td>"
            "<td>" + str(row.get("Empresa / Filial", "")) + "</td>"
            "<td style='" + cor_class(row["Classificação"]) + "'>" + str(row["Classificação"]) + "</td>"
            "<td>" + consumo_str + "</td>"
            "<td>" + moeda_br(row["Valor Atual"]) + "</td>"
            "<td>" + dio_str + "</td>"
            "</tr>"
        )

    css = (
        "<style>"
        ".tb-dio{width:100%;border-collapse:collapse;font-size:13px;color:white;}"
        ".tb-dio th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;"
        "border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap;}"
        ".tb-dio th:nth-child(n+6){text-align:right;}"
        ".tb-dio td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}"
        ".tb-dio td:nth-child(n+6){text-align:right;}"
        ".tb-dio tr:hover td{background-color:#0a6570;}"
        "</style>"
    )

    tabela = (
        css
        + f"<p style='color:#aaa;font-size:12px'>{len(df_tabela)} produtos</p>"
        + "<table class='tb-dio'><thead><tr>"
        + "<th>Código</th><th>Descrição</th><th>Conta</th><th>Empresa / Filial</th>"
        + "<th>Classificação</th><th>Consumo Médio/Mês</th><th>Valor Atual</th><th>DIO</th>"
        + "</tr></thead><tbody>"
        + linhas
        + "</tbody></table>"
    )

    st.html(tabela)