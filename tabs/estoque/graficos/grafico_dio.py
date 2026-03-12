cat > tabs/estoque/graficos/grafico_dio.py << 'EOF'
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# ATENÇÃO: A função agora recebe o df_obsoleto como segundo argumento!
def render(df_hist, df_obsoleto, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_hist = df_hist.copy()
    df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"]).dt.normalize()
    data_selecionada = pd.Timestamp(data_selecionada.date())

    # ── 1. Ajuste de Agrupamento (ID_UNICO) igual ao Power Query ──────────────
    df_hist["ID_UNICO"] = df_hist["Empresa / Filial"].astype(str) + "|" + df_hist["Produto"].astype(str)
    
    df_obsoleto = df_obsoleto.copy()
    if "ID_UNICO" not in df_obsoleto.columns:
        df_obsoleto["ID_UNICO"] = df_obsoleto["Empresa / Filial"].astype(str) + "|" + df_obsoleto["Produto"].astype(str)

    # ── DEDUPLICAR obsoleto: mantém só a última movimentação por ID_UNICO ──────
    if "Ult_Movimentacao" in df_obsoleto.columns:
        df_obsoleto["Ult_Movimentacao"] = pd.to_datetime(df_obsoleto["Ult_Movimentacao"], errors="coerce")
        df_obsoleto = (
            df_obsoleto
            .sort_values("Ult_Movimentacao", ascending=False)
            .drop_duplicates(subset="ID_UNICO", keep="first")
        )

    datas_sorted = sorted([d for d in df_hist["Data Fechamento"].unique() if d <= data_selecionada])

    if len(datas_sorted) < 2:
        st.info("Histórico insuficiente para calcular DIO.")
        return

    datas_janela = datas_sorted[-13:] if len(datas_sorted) >= 13 else datas_sorted

    # ── 2. Estoque atual ───────────────────────────────────────────────────────
    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()
    
    grp_atual = df_atual.groupby("ID_UNICO").agg({
        "Produto": "first",
        "Descricao": "first",
        "Conta": "first",
        "Empresa / Filial": "first",
        "Custo Total": "sum"
    }).rename(columns={"Custo Total": "Custo Total Atual"}).reset_index()

    # ── 3. Saldo Inicial ───────────────────────────────────────────────────────
    data_inicial = datas_janela[0]
    df_inicial = df_hist[df_hist["Data Fechamento"] == data_inicial].copy()
    grp_inicial = (
        df_inicial.groupby("ID_UNICO")["Custo Total"]
        .sum().reset_index().rename(columns={"Custo Total": "Saldo Inicial"})
    )

    # ── 4. Queda Mensal (CPV Básico) ───────────────────────────────────────────
    df_janela = df_hist[df_hist["Data Fechamento"].isin(datas_janela)].copy()

    pivot = (
        df_janela.groupby(["ID_UNICO", "Data Fechamento"])["Custo Total"]
        .sum()
        .unstack(fill_value=0)
        .sort_index(axis=1)
    )

    cpv_list = []
    for id_unico in pivot.index:
        valores = pivot.loc[id_unico].values
        reducoes = [max(0, valores[i] - valores[i+1]) for i in range(len(valores)-1)]
        cpv = sum(reducoes)
        cpv_list.append({"ID_UNICO": id_unico, "CPV_Calculado": cpv})

    df_cpv = pd.DataFrame(cpv_list)

    # ── 5. Unindo tudo (Merge Histórico + Obsoleto) ────────────────────────────
    df_dio = grp_atual.merge(grp_inicial, on="ID_UNICO", how="left")
    df_dio = df_dio.merge(df_cpv, on="ID_UNICO", how="left")
    
    df_obs_sub = df_obsoleto[["ID_UNICO", "Ult_Movimentacao"]].copy()
    df_dio = df_dio.merge(df_obs_sub, on="ID_UNICO", how="left")

    df_dio["Saldo Inicial"] = df_dio["Saldo Inicial"].fillna(0)
    df_dio["Estoque Medio"] = (df_dio["Saldo Inicial"] + df_dio["Custo Total Atual"]) / 2

    # ── 6. Trava do Sem Consumo ────────────────────────────────────────────────
    def definir_cpv(row):
        cpv = row["CPV_Calculado"] if pd.notna(row.get("CPV_Calculado")) else 0
        if pd.notna(row.get("Ult_Movimentacao")):
            dias_sem_mov = (data_selecionada - pd.to_datetime(row["Ult_Movimentacao"])).days
            if dias_sem_mov >= 365:
                cpv = 0
        else:
            cpv = 0
        return cpv

    df_dio["CPV 12m"] = df_dio.apply(definir_cpv, axis=1)

    # ── 7. Cálculo DIO e Classificação ─────────────────────────────────────────
    def calcular_dio(row):
        if row["CPV 12m"] > 0:
            return (row["Estoque Medio"] / row["CPV 12m"]) * 365
        return None

    df_dio["DIO"] = df_dio.apply(calcular_dio, axis=1)

    def classificar(dio):
        if dio is None:    return "Sem Consumo"
        elif dio <= 30:    return "Giro Alto (≤30d)"
        elif dio <= 90:    return "Giro Médio (31-90d)"
        elif dio <= 180:   return "Giro Baixo (91-180d)"
        else:              return "Crítico (>180d)"

    df_dio["Classificação"] = df_dio["DIO"].apply(classificar)

    # ── 8. Cards ───────────────────────────────────────────────────────────────
    total_estoque = df_dio["Custo Total Atual"].sum()
    dio_validos   = df_dio[df_dio["DIO"].notna() & (df_dio["DIO"] < 99999)]["DIO"]
    dio_mediano   = dio_validos.median() if not dio_validos.empty else None

    qtd_alto    = len(df_dio[df_dio["Classificação"] == "Giro Alto (≤30d)"])
    qtd_medio   = len(df_dio[df_dio["Classificação"] == "Giro Médio (31-90d)"])
    qtd_critico = len(df_dio[df_dio["Classificação"] == "Crítico (>180d)"])
    qtd_sem     = len(df_dio[df_dio["Classificação"] == "Sem Consumo"])

    val_critico  = df_dio[df_dio["Classificação"].isin(["Crítico (>180d)", "Sem Consumo"])]["Custo Total Atual"].sum()
    perc_critico = (val_critico / total_estoque * 100) if total_estoque > 0 else 0

    label_inicial = pd.Timestamp(data_inicial).strftime("%d/%m/%Y")
    label_atual   = data_selecionada.strftime("%d/%m/%Y")
    n_meses       = len(datas_janela) - 1

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
        <div class="sub" style="color:#ccc">{label_inicial} → {label_atual} ({n_meses}m)</div>
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

    # ── 9. Tabela resumo ───────────────────────────────────────────────────────
    ordem = ["Giro Alto (≤30d)", "Giro Médio (31-90d)", "Giro Baixo (91-180d)", "Crítico (>180d)", "Sem Consumo"]

    resumo = df_dio.groupby("Classificação").agg(
        Produtos=("Produto", "count"),
        Valor=("Custo Total Atual", "sum")
    ).reset_index()

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

    # ── 10. Filtro e tabela detalhada ──────────────────────────────────────────
    filtro = st.selectbox("Filtrar por classificação", ["Todos"] + ordem)

    df_tabela = df_dio.copy() if filtro == "Todos" else df_dio[df_dio["Classificação"] == filtro].copy()
    df_tabela = df_tabela.sort_values("DIO", ascending=False, na_position="first").reset_index(drop=True)

    # ── Exportação Excel ───────────────────────────────────────────────────────
    df_export = df_tabela.rename(columns={
        "Produto": "Código",
        "Descricao": "Descrição",
        "Custo Total Atual": "Estoque Final",
        "Estoque Medio": "Estoque Médio",
        "CPV 12m": "CPV (12m)",
        "DIO": "DIO (dias)"
    })

    colunas_excel = [
        "Código", "Descrição", "Conta", "Empresa / Filial", "Classificação",
        "Saldo Inicial", "Estoque Final", "Estoque Médio", "CPV (12m)",
        "DIO (dias)", "Ult_Movimentacao"
    ]
    colunas_excel = [c for c in colunas_excel if c in df_export.columns]
    df_export = df_export[colunas_excel]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Relatorio DIO')
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Exportar para Excel",
        data=excel_data,
        file_name="relatorio_dio.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # ── Tabela detalhada ───────────────────────────────────────────────────────
    linhas = ""
    for _, row in df_tabela.iterrows():
        dio_val = row["DIO"]
        dio_str = f"{dio_val:.0f}" if dio_val is not None and not (isinstance(dio_val, float) and np.isnan(dio_val)) else "—"
        ult_mov = pd.Timestamp(row["Ult_Movimentacao"]).strftime("%d/%m/%Y") if pd.notna(row.get("Ult_Movimentacao")) else "—"

        linhas += (
            "<tr>"
            "<td>" + str(row["Produto"]) + "</td>"
            "<td>" + str(row.get("Descricao", "")) + "</td>"
            "<td>" + str(row.get("Conta", "")) + "</td>"
            "<td>" + str(row.get("Empresa / Filial", "")) + "</td>"
            "<td style='" + cor_class(row["Classificação"]) + "'>" + str(row["Classificação"]) + "</td>"
            "<td>" + moeda_br(row["Saldo Inicial"]) + "</td>"
            "<td>" + moeda_br(row["Custo Total Atual"]) + "</td>"
            "<td>" + moeda_br(row["Estoque Medio"]) + "</td>"
            "<td>" + moeda_br(row["CPV 12m"]) + "</td>"
            "<td>" + dio_str + "</td>"
            "<td>" + ult_mov + "</td>"
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
        + "<th>Classificação</th><th>Saldo Inicial</th><th>Estoque Final</th>"
        + "<th>Estoque Médio</th><th>CPV (12m)</th><th>DIO (dias)</th><th>Ult Mov</th>"
        + "</tr></thead><tbody>"
        + linhas
        + "</tbody></table>"
    )

    st.html(tabela)
EOF