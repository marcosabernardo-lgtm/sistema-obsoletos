import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_hist = df_hist.copy()
    df_hist["Data Fechamento"] = pd.to_datetime(df_hist["Data Fechamento"]).dt.normalize()
    data_selecionada = pd.Timestamp(data_selecionada.date())

    # Período sem movimentação
    meses = st.slider("Meses sem movimentação", min_value=1, max_value=24, value=6, step=1)

    # Datas disponíveis até a data selecionada
    datas_sorted = sorted([d for d in df_hist["Data Fechamento"].unique() if d <= data_selecionada])

    if len(datas_sorted) < 2:
        st.info("Histórico insuficiente para calcular giro.")
        return

    # Produtos no estoque na data selecionada
    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()
    produtos_atual = set(df_atual["Produto"].unique())

    # Datas anteriores dentro da janela de meses
    datas_janela = [d for d in datas_sorted if d < data_selecionada]
    datas_janela = datas_janela[-meses:] if len(datas_janela) >= meses else datas_janela

    if not datas_janela:
        st.info("Sem histórico suficiente para o período selecionado.")
        return

    # Para cada produto no estoque atual, verificar se houve variação nos últimos X meses
    df_janela = df_hist[df_hist["Data Fechamento"].isin(datas_janela)].copy()

    # Calcular variação mês a mês por produto
    pivot = (
        df_hist[df_hist["Data Fechamento"].isin(datas_janela + [data_selecionada])]
        .groupby(["Produto", "Data Fechamento"])["Custo Total"]
        .sum()
        .unstack(fill_value=0)
    )

    # Verificar se houve qualquer mudança no valor entre os meses da janela
    def teve_movimentacao(row):
        valores = row.values
        return not all(v == valores[0] for v in valores)

    pivot["Movimentou"] = pivot.apply(teve_movimentacao, axis=1)

    # Juntar com dados atuais
    desc = df_atual.groupby("Produto")[["Descricao", "Conta", "Empresa / Filial"]].first().reset_index()

    df_giro = df_atual.groupby("Produto")["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor Atual"})
    df_giro = df_giro.merge(desc, on="Produto", how="left")
    df_giro = df_giro.merge(pivot[["Movimentou"]].reset_index(), on="Produto", how="left")
    df_giro["Movimentou"] = df_giro["Movimentou"].fillna(False)

    # Calcular meses em estoque sem movimentação
    def meses_parado(produto):
        datas_prod = sorted([
            d for d in datas_janela
            if produto in df_hist[df_hist["Data Fechamento"] == d]["Produto"].values
        ], reverse=True)
        count = 0
        val_ref = None
        for d in datas_prod:
            val = df_hist[(df_hist["Data Fechamento"] == d) & (df_hist["Produto"] == produto)]["Custo Total"].sum()
            if val_ref is None:
                val_ref = val
                count = 1
            elif val == val_ref:
                count += 1
            else:
                break
        return count

    df_sem_mov = df_giro[~df_giro["Movimentou"]].copy()
    df_com_mov = df_giro[df_giro["Movimentou"]].copy()

    # Cards
    total_estoque   = df_giro["Valor Atual"].sum()
    total_sem_mov   = df_sem_mov["Valor Atual"].sum()
    total_com_mov   = df_com_mov["Valor Atual"].sum()
    perc_sem_mov    = (total_sem_mov / total_estoque * 100) if total_estoque > 0 else 0
    qtd_sem_mov     = len(df_sem_mov)
    qtd_com_mov     = len(df_com_mov)
    qtd_total       = len(df_giro)

    label_data = data_selecionada.strftime("%d/%m/%Y")
    label_janela = datas_janela[0].strftime("%d/%m/%Y") if datas_janela else ""

    st.markdown("""
    <style>
    .card-giro {
        background-color:#005562;
        border:2px solid #EC6E21;
        border-radius:10px;
        padding:14px 16px;
        text-align:center;
    }
    .card-giro .titulo { font-size:12px; color:#ccc; margin-bottom:4px; }
    .card-giro .valor  { font-size:20px; font-weight:700; color:white; }
    .card-giro .sub    { font-size:12px; margin-top:4px; }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(f"""
    <div class="card-giro">
        <div class="titulo">Total em Estoque</div>
        <div class="valor">{moeda_br(total_estoque)}</div>
        <div class="sub" style="color:#ccc">{qtd_total} produtos</div>
    </div>""", unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="card-giro">
        <div class="titulo">🚨 Sem Movimentação ({meses}m)</div>
        <div class="valor" style="color:#ff6b6b">{moeda_br(total_sem_mov)}</div>
        <div class="sub" style="color:#ff6b6b">{qtd_sem_mov} produtos — {perc_sem_mov:.1f}% do estoque</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="card-giro">
        <div class="titulo">✅ Com Movimentação ({meses}m)</div>
        <div class="valor" style="color:#51cf66">{moeda_br(total_com_mov)}</div>
        <div class="sub" style="color:#51cf66">{qtd_com_mov} produtos</div>
    </div>""", unsafe_allow_html=True)

    c4.markdown(f"""
    <div class="card-giro">
        <div class="titulo">📅 Janela Analisada</div>
        <div class="valor" style="font-size:15px">{label_janela}</div>
        <div class="sub" style="color:#ccc">até {label_data}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filtro
    opcoes = ["Sem Movimentação", "Com Movimentação", "Todos"]
    filtro = st.selectbox("Filtrar por", opcoes)

    if filtro == "Sem Movimentação":
        df_tabela = df_sem_mov.sort_values("Valor Atual", ascending=False).reset_index(drop=True)
    elif filtro == "Com Movimentação":
        df_tabela = df_com_mov.sort_values("Valor Atual", ascending=False).reset_index(drop=True)
    else:
        df_tabela = df_giro.sort_values("Valor Atual", ascending=False).reset_index(drop=True)

    # Tabela HTML
    def status_html(mov):
        if mov:
            return '<span style="color:#51cf66;font-weight:700">✅ Movimentou</span>'
        return '<span style="color:#ff6b6b;font-weight:700">🚨 Parado</span>'

    linhas = ""
    for _, row in df_tabela.iterrows():
        linhas += (
            "<tr>"
            "<td>" + str(row["Produto"]) + "</td>"
            "<td>" + str(row.get("Descricao", "")) + "</td>"
            "<td>" + str(row.get("Conta", "")) + "</td>"
            "<td>" + str(row.get("Empresa / Filial", "")) + "</td>"
            "<td>" + status_html(row["Movimentou"]) + "</td>"
            "<td>" + moeda_br(row["Valor Atual"]) + "</td>"
            "</tr>"
        )

    css = (
        "<style>"
        ".tb-giro{width:100%;border-collapse:collapse;font-size:13px;color:white;}"
        ".tb-giro th{background-color:#0f5a60;color:white;padding:9px 12px;text-align:left;"
        "border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap;}"
        ".tb-giro th:last-child{text-align:right;}"
        ".tb-giro td{padding:7px 12px;border-bottom:1px solid #1a6e75;background-color:#005562;color:white;}"
        ".tb-giro td:last-child{text-align:right;}"
        ".tb-giro tr:hover td{background-color:#0a6570;}"
        "</style>"
    )

    tabela = (
        css
        + f"<p style='color:#aaa;font-size:12px'>{len(df_tabela)} produtos</p>"
        + "<table class='tb-giro'><thead><tr>"
        + "<th>Código</th><th>Descrição</th><th>Conta</th><th>Empresa / Filial</th>"
        + "<th>Status</th><th>Valor Atual</th>"
        + "</tr></thead><tbody>"
        + linhas
        + "</tbody></table>"
    )

    st.html(tabela)