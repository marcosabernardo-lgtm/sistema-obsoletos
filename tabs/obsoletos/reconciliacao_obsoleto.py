import streamlit as st
import pandas as pd

# -------------------------------------------------------
# CARD
# -------------------------------------------------------
def card(titulo, valor, cor_borda="#EC6E21", cor_valor=None, subtitulo=None):
    cor_val = cor_valor if cor_valor else "white"
    sub_html = f'<div style="font-size:12px;color:#aaa;margin-top:4px">{subtitulo}</div>' if subtitulo else ""
    st.markdown(
        f"""
        <div style="
            border:2px solid {cor_borda};
            border-radius:12px;
            padding:16px;
            min-height:90px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            text-align:center;
        ">
            <div style="font-size:13px;color:white">{titulo}</div>
            <div style="font-size:22px;font-weight:bold;color:{cor_val}">{valor}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------------------------------------
# FUNÇÃO PRINCIPAL
# -------------------------------------------------------
def render(df_hist, moeda_br, data_selecionada=None):

    df = df_hist.copy()

    if "Tipo de Estoque" not in df.columns:
        df["Tipo de Estoque"] = "Não Informado"
    if "Conta" not in df.columns:
        df["Conta"] = "Não Informado"

    df = (
        df.groupby(
            ["Data Fechamento", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao", "Status Estoque"],
            as_index=False
        ).agg({"Saldo Atual": "sum", "Custo Total": "sum"})
    )

    df["obsoleto"] = df["Status Estoque"] == "Obsoleto"
    datas = sorted(df["Data Fechamento"].unique())

    # Datas
    if data_selecionada is not None:
        data_sel_ts = pd.Timestamp(data_selecionada)
        datas_anteriores = [d for d in datas if pd.Timestamp(d) < data_sel_ts]

        if data_sel_ts not in [pd.Timestamp(d) for d in datas]:
            st.warning("Data não encontrada.")
            return

        if len(datas_anteriores) == 0:
            st.info("Primeiro fechamento disponível.")
            return

        data_atual = data_sel_ts
        data_anterior = pd.Timestamp(max(datas_anteriores))
    else:
        if len(datas) < 2:
            st.warning("Histórico insuficiente.")
            return

        data_atual = pd.Timestamp(datas[-1])
        data_anterior = pd.Timestamp(datas[-2])

    st.caption(f"Comparando **{data_atual.strftime('%d/%m/%Y')}** vs **{data_anterior.strftime('%d/%m/%Y')}**")

    # Base deduplicada
    df_at = df[df["Data Fechamento"] == data_atual].copy()
    df_an = df[df["Data Fechamento"] == data_anterior].copy()

    df_at_dedup = df_at.sort_values("obsoleto", ascending=False).drop_duplicates(
        subset=["Empresa / Filial", "Produto"], keep="first"
    )

    df_an_dedup = df_an.sort_values("obsoleto", ascending=False).drop_duplicates(
        subset=["Empresa / Filial", "Produto"], keep="first"
    )

    chave = ["Empresa / Filial", "Produto"]

    df_ant = df_an_dedup[chave + ["Custo Total", "Saldo Atual", "obsoleto"]].rename(columns={
        "Custo Total": "Vlr Ant",
        "Saldo Atual": "Qtd Ant",
        "obsoleto": "Obs Ant"
    })

    df_atual = df_at_dedup[chave + ["Custo Total", "Saldo Atual", "obsoleto"]].rename(columns={
        "Custo Total": "Vlr Atual",
        "Saldo Atual": "Qtd Atual",
        "obsoleto": "Obs Atual"
    })

    base = df_atual.merge(df_ant, on=chave, how="outer")

    for c in ["Vlr Ant", "Qtd Ant", "Vlr Atual", "Qtd Atual"]:
        base[c] = base[c].fillna(0)

    # Movimentos
    entrou = base[(base["Vlr Ant"] == 0) & (base["Vlr Atual"] > 0)]
    saiu = base[(base["Vlr Ant"] > 0) & (base["Vlr Atual"] == 0)]

    saiu_obs = base[
        (base["Obs Ant"] == True) &
        (base["Obs Atual"] == False) &
        (base["Qtd Atual"] > 0)
    ]

    variacao = base[
        (base["Vlr Ant"] > 0) &
        (base["Vlr Atual"] > 0) &
        (base["Qtd Ant"] == base["Qtd Atual"]) &
        (base["Vlr Ant"] != base["Vlr Atual"])
    ]

    # Valores
    obs_ant = base[base["Obs Ant"] == True]["Vlr Ant"].sum()
    obs_atual = base[base["Obs Atual"] == True]["Vlr Atual"].sum()

    entrou_val = entrou["Vlr Atual"].sum()
    saiu_val = saiu["Vlr Ant"].sum()
    saiu_obs_val = (saiu_obs["Vlr Ant"] - saiu_obs["Vlr Atual"]).sum()
    variacao_val = variacao["Vlr Atual"].sum() - variacao["Vlr Ant"].sum()

    reconstruido = (
        obs_ant
        + entrou_val
        - saiu_val
        - saiu_obs_val
        + variacao_val
    )

    gap = obs_atual - reconstruido

    # -------------------------------------------------------
    # CARDS PRINCIPAIS
    # -------------------------------------------------------

    st.subheader("🧮 Reconciliação do Obsoleto")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        card("Obsoleto Anterior", moeda_br(obs_ant), "#74c0fc")

    with c2:
        card("Movimentação Líquida", moeda_br(entrou_val - saiu_val - saiu_obs_val), "#51cf66")

    with c3:
        card("Variação de Valor", moeda_br(variacao_val), "#fcc419")

    with c4:
        card("Obsoleto Atual", moeda_br(obs_atual), "#ff6b6b")

    st.markdown("---")

    c5, c6 = st.columns(2)

    with c5:
        card("Reconstruído", moeda_br(reconstruido), "#74c0fc")

    with c6:
        cor_gap = "#51cf66" if abs(gap) < 1 else "#ff6b6b"
        card("Gap de Reconciliação", moeda_br(gap), "#fff", cor_valor=cor_gap)

    # -------------------------------------------------------
    # 🔎 QUEBRA DO GAP
    # -------------------------------------------------------

    st.markdown("### 🔎 Composição do Gap")

    # Base cheia (sem deduplicar)
    obs_full_ant = df_an[df_an["Status Estoque"] == "Obsoleto"]["Custo Total"].sum()
    obs_full_at = df_at[df_at["Status Estoque"] == "Obsoleto"]["Custo Total"].sum()

    gap_dedup = (obs_full_at - obs_full_ant) - (obs_atual - obs_ant)

    mudanca_status = saiu_obs["Vlr Ant"].sum()

    outros = gap - gap_dedup + mudanca_status

    c7, c8, c9 = st.columns(3)

    with c7:
        card("🧩 Deduplicação", moeda_br(gap_dedup), "#74c0fc")

    with c8:
        card("🔄 Mudança de Status", moeda_br(-mudanca_status), "#51cf66")

    with c9:
        card("📊 Outros Ajustes", moeda_br(outros), "#fcc419")