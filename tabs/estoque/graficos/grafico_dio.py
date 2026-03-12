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

    datas_sorted = sorted([d for d in df_hist["Data Fechamento"].unique() if d <= data_selecionada])

    if len(datas_sorted) < 2:
        st.info("Histórico insuficiente para calcular DIO.")
        return

    datas_janela = datas_sorted[-12:] if len(datas_sorted) >= 12 else datas_sorted

    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()
    desc = df_atual.groupby("Produto")[["Descricao", "Conta", "Empresa / Filial"]].first().reset_index()

    grp_atual = (
        df_atual.groupby("Produto")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Custo Total Atual"})
    )

    data_inicial = datas_janela[0]
    df_inicial = df_hist[df_hist["Data Fechamento"] == data_inicial].copy()
    grp_inicial = (
        df_inicial.groupby("Produto")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Saldo Inicial"})
    )

    df_janela = df_hist[df_hist["Data Fechamento"].isin(datas_janela)].copy()

    pivot = (
        df_janela.groupby(["Produto", "Data Fechamento"])["Custo Total"]
        .sum()
        .unstack(fill_value=0)
        .sort_index(axis=1)
    )

    cpv_list = []
    ult_mov_list = []

    for produto in pivot.index:
        valores = pivot.loc[produto].values
        datas   = list(pivot.columns)
        reducoes = [max(0, valores[i] - valores[i+1]) for i in range(len(valores)-1)]
        cpv = sum(reducoes)
        ult_mov = None
        for i in range(len(valores)-2, -1, -1):
            if valores[i] > valores[i+1]:
                ult_mov = datas[i+1]
                break
        cpv_list.append({"Produto": produto, "CPV 12m": cpv})
        ult_mov_list.append({"Produto": produto, "Ult Mov": ult_mov})

    df_cpv    = pd.DataFrame(cpv_list)
    df_ultmov = pd.DataFrame(ult_mov_list)

    df_dio = grp_atual.merge(grp_inicial, on="Produto", how="left")
    df_dio = df_dio.merge(df_cpv, on="Produto", how="left")
    df_dio = df_dio.merge(df_ultmov, on="Produto", how="left")
    df_dio = df_dio.merge(desc, on="Produto", how="left")

    df_dio["Saldo Inicial"] = df_dio["Saldo Inicial"].fillna(0)
    df_dio["CPV 12m"]       = df_dio["CPV 12m"].fillna(0)
    df_dio["Estoque Medio"] = (df_dio["Saldo Inicial"] + df_dio["Custo Total Atual"]) / 2

    def calcular_dio(row):
        if row["CPV 12m"] > 0:
            return (row["Estoque Medio"] / row["CPV 12m"]) * 365
        return None

    df_dio["DIO"] = df_dio.apply(calcular_dio, axis=1)

    def classificar(dio):
        if dio is None:  return "Sem Consumo"
        elif dio <= 30:  return "Giro Alto (<=30d)"
        elif dio <= 90:  return "Giro Medio (31-90d)"
        elif dio <= 180: return "Giro Baixo (91-180d)"
        else:            return "Critico (>180d)"

    df_dio["Classificacao"] = df_dio["DIO"].apply(classificar)

    total_estoque = df_dio["Custo Total Atual"].sum()
    dio_validos   = df_dio[df_dio["DIO"].notna() & (df_dio["DIO"] < 99999)]["DIO"]
    dio_mediano   = dio_validos.median() if not dio_validos.empty else None

    qtd_alto    = len(df_dio[df_dio["Classificacao"] == "Giro Alto (<=30d)"])
    qtd_medio   = len(df_dio[df_dio["Classificacao"] == "Giro Medio (31-90d)"])
    qtd_critico = len(df_dio[df_dio["Classificacao"] == "Critico (>180d)"])
    qtd_sem     = len(df_dio[df_dio["Classificacao"] == "Sem Consumo"])

    val_critico  = df_dio[df_dio["Classificacao"].isin(["Critico (>180d)", "Sem Consumo"])]["Custo Total Atual"].sum()
    perc_critico = (val_critico / total_estoque * 100) if total_estoque > 0 else 0

    label_inicial = pd.Timestamp(data_inicial).strftime("%d/%m/%Y")
    label_atual   = data_selecionada.strftime("%d/%m/%Y")
    n_meses       = len(datas_janela)

    st.markdown("""
    <style>
    .card-dio{background-color:#005562;border:2px solid #EC6E21;border-radius:10px;padding:14px 16px;text-align:center;}
    .card-dio .titulo{font-size:12px;color:#ccc;margin-bottom:4px;}
    .card-dio .valor{font-size:20px;font-weight:700;color:white;}
    .card-dio .sub{font-size:12px;margin-top:4px;}
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="card-dio"><div class="titulo">Total em Estoque</div><div class="valor">{moeda_br(total_estoque)}</div><div class="sub" style="color:#ccc">{len(df_dio)} produtos</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="card-dio"><div class="titulo">DIO Mediano</div><div class="valor">{f"{dio_mediano:.0f} dias" if dio_mediano is not None else "--"}</div><div class="sub" style="color:#ccc">{label_inicial} a {label_atual} ({n_meses}m)</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="card-dio"><div class="titulo">Critico + Sem Consumo</div><div class="valor" style="color:#ff6b6b">{moeda_br(val_critico)}</div><div class="sub" style="color:#ff6b6b">{qtd_critico + qtd_sem} produtos -- {perc_critico:.1f}%</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="card-dio"><div class="titulo">Giro Alto + Medio</div><div class="valor" style="color:#51cf66">{qtd_alto + qtd_medio} produtos</div><div class="sub" style="color:#51cf66">ate 90 dias</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    ordem = ["Giro Alto (<=30d)", "Giro Medio (31-90d)", "Giro Baixo (91-180d)", "Critico (>180d)", "Sem Consumo"]

    resumo = df_dio.groupby("Classificacao").agg(Produtos=("Produto", "count"), Valor=("Custo Total Atual", "sum")).reset_index()
    resumo["_ordem"] = resumo["Classificacao"].apply(lambda x: ordem.index(x) if x in ordem else 99)
    resumo = resumo.sort_values("_ordem").drop(columns="_ordem")

    def cor_class(c):
        if "Alto"    in c: return "color:#51cf66;font-weight:700"
        if "Medio"   in c: return "color:#74c0fc;font-weight:700"
        if "Baixo"   in c: return "color:#f0a500;font-weight:700"
        if "Critico" in c: return "color:#ff6b6b;font-weight:700"
        return "color:#aaa;font-weight:700"

    linhas_resumo = ""
    for _, row in resumo.iterrows():
        perc = (row["Valor"] / total_estoque * 100) if total_estoque > 0 else 0
        linhas_resumo += "<tr><td style='" + cor_class(row["Classificacao"]) + "'>" + str(row["Classificacao"]) + "</td><td>" + str(int(row["Produtos"])) + "</td><td>" + moeda_br(row["Valor"]) + "</td><td>" + f"{perc:.1f}%" + "</td></tr>"

    st.html("<style>.tb-resumo{width:100%;border-collapse:collapse;font-size:13px;color:white;margin-bottom:24px;}.tb-resumo th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700;}.tb-resumo th:not(:first-child){text-align:right;}.tb-resumo td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;}.tb-resumo td:not(:first-child){text-align:right;}</style><table class='tb-resumo'><thead><tr><th>Classificacao</th><th>Produtos</th><th>Valor</th><th>% Estoque</th></tr></thead><tbody>" + linhas_resumo + "</tbody></table>")

    filtro = st.selectbox("Filtrar por classificacao", ["Todos"] + ordem)
    df_tabela = df_dio.copy() if filtro == "Todos" else df_dio[df_dio["Classificacao"] == filtro].copy()
    df_tabela = df_tabela.sort_values("DIO", ascending=False, na_position="first").reset_index(drop=True)

    linhas = ""
    for _, row in df_tabela.iterrows():
        dio_val = row["DIO"]
        dio_str = f"{dio_val:.0f}" if dio_val is not None and not (isinstance(dio_val, float) and np.isnan(dio_val)) else "--"
        ult_mov = pd.Timestamp(row["Ult Mov"]).strftime("%d/%m/%Y") if pd.notna(row.get("Ult Mov")) else "--"
        linhas += "<tr><td>" + str(row["Produto"]) + "</td><td>" + str(row.get("Descricao","")) + "</td><td>" + str(row.get("Conta","")) + "</td><td>" + str(row.get("Empresa / Filial","")) + "</td><td style='" + cor_class(row["Classificacao"]) + "'>" + str(row["Classificacao"]) + "</td><td>" + moeda_br(row["Saldo Inicial"]) + "</td><td>" + moeda_br(row["Custo Total Atual"]) + "</td><td>" + moeda_br(row["Estoque Medio"]) + "</td><td>" + moeda_br(row["CPV 12m"]) + "</td><td>" + dio_str + "</td><td>" + ult_mov + "</td></tr>"

    st.html("<style>.tb-dio{width:100%;border-collapse:collapse;font-size:13px;color:white;}.tb-dio th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap;}.tb-dio th:nth-child(n+6){text-align:right;}.tb-dio td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}.tb-dio td:nth-child(n+6){text-align:right;}.tb-dio tr:hover td{background-color:#0a6570;}</style>" + f"<p style='color:#aaa;font-size:12px'>{len(df_tabela)} produtos</p><table class='tb-dio'><thead><tr><th>Codigo</th><th>Descricao</th><th>Conta</th><th>Empresa / Filial</th><th>Classificacao</th><th>Saldo Inicial</th><th>Estoque Final</th><th>Estoque Medio</th><th>CPV (12m)</th><th>DIO (dias)</th><th>Ult Mov</th></tr></thead><tbody>" + linhas + "</tbody></table>")
