import streamlit as st
import pandas as pd
import io

# -------------------------------------------------------
# 1. FUNÇÃO DE ESTILO (CARD)
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
# 2. FUNÇÃO PRINCIPAL
# -------------------------------------------------------
def render(df_hist, moeda_br, data_selecionada=None):

    df = df_hist.copy()

    # --- PROTEÇÃO PARA DADOS ANTIGOS ---
    if "Tipo de Estoque" not in df.columns:
        df["Tipo de Estoque"] = "Não Informado"
    if "Conta" not in df.columns:
        df["Conta"] = "Não Informado"

    # Agrupamento inicial
    df = (
        df.groupby(
            ["Data Fechamento", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao", "Status Estoque"],
            as_index=False
        ).agg({"Saldo Atual": "sum", "Custo Total": "sum"})
    )

    df["obsoleto"] = df["Status Estoque"] == "Obsoleto"
    datas = sorted(df["Data Fechamento"].unique())

    if data_selecionada is not None:
        data_sel_ts = pd.Timestamp(data_selecionada)
        datas_anteriores = [d for d in datas if pd.Timestamp(d) < data_sel_ts]
        if data_sel_ts not in [pd.Timestamp(d) for d in datas]:
            st.warning("Data selecionada não encontrada no histórico.")
            return
        if len(datas_anteriores) == 0:
            st.info(f"ℹ️ {data_sel_ts.strftime('%d/%m/%Y')} é o primeiro fechamento.")
            return
        data_atual    = data_sel_ts
        data_anterior = pd.Timestamp(max(datas_anteriores))
    else:
        if len(datas) < 2:
            st.warning("Histórico insuficiente.")
            return
        data_atual    = pd.Timestamp(datas[-1])
        data_anterior = pd.Timestamp(datas[-2])

    # --- DEDUPLICAÇÃO POR PRIORIDADE ---
    df_at_raw = df[df["Data Fechamento"] == data_atual].copy()
    df_an_raw = df[df["Data Fechamento"] == data_anterior].copy()

    df_at_dedup = df_at_raw.sort_values("obsoleto", ascending=False).drop_duplicates(subset=["Empresa / Filial", "Produto"], keep="first")
    df_an_dedup = df_an_raw.sort_values("obsoleto", ascending=False).drop_duplicates(subset=["Empresa / Filial", "Produto"], keep="first")

    df_atual_obs = df_at_dedup[df_at_dedup["obsoleto"] == True].copy()
    df_ant_obs   = df_an_dedup[df_an_dedup["obsoleto"] == True].copy()

    st.caption(f"Comparando **{data_atual.strftime('%d/%m/%Y')}** vs **{data_anterior.strftime('%d/%m/%Y')}**")

    chave = ["Empresa / Filial", "Produto"]

    # Preparar para Merge
    df_ant_sel = df_ant_obs[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque"]].rename(columns={
        "Custo Total": "Vlr Ant", "Saldo Atual": "Qtd Ant", "Descricao": "Desc_ant", "Conta": "Conta_ant", "Tipo de Estoque": "Tipo_ant"
    })
    df_atual_sel = df_atual_obs[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque"]].rename(columns={
        "Custo Total": "Vlr Atual", "Saldo Atual": "Qtd Atual", "Descricao": "Desc_at", "Conta": "Conta_at", "Tipo de Estoque": "Tipo_at"
    })

    base = df_atual_sel.merge(df_ant_sel, on=chave, how="outer")
    for c in ["Vlr Ant", "Qtd Ant", "Vlr Atual", "Qtd Atual"]: base[c] = base[c].fillna(0)
    base["Descricao"] = base["Desc_at"].fillna(base["Desc_ant"])
    base["Conta"]     = base["Conta_at"].fillna(base["Conta_ant"])
    base["Tipo de Estoque"] = base["Tipo_at"].fillna(base["Tipo_ant"])

    # Categorias
    entrou = base[(base["Vlr Ant"] == 0) & (base["Vlr Atual"] > 0)].copy()
    entrou["Status Mov"] = "🔴 Entrou"

    saiu = base[(base["Vlr Ant"] > 0) & (base["Vlr Atual"] == 0)].copy()
    saiu["Status Mov"] = "🟢 Saiu"

    reduziu = base[(base["Vlr Ant"] > 0) & (base["Vlr Atual"] > 0) & (base["Qtd Atual"] < base["Qtd Ant"])].copy()
    reduziu["Status Mov"] = "🔽 Reduziu"
    reduziu["Vlr Reduzido"] = (reduziu["Vlr Ant"] / reduziu["Qtd Ant"].replace(0, pd.NA)) * (reduziu["Qtd Ant"] - reduziu["Qtd Atual"])

    variacao = base[(base["Vlr Ant"] > 0) & (base["Vlr Atual"] > 0) & (base["Qtd Atual"] == base["Qtd Ant"]) & (base["Vlr Atual"] != base["Vlr Ant"])].copy()
    variacao["Status Mov"] = "📊 Variação"

    # Métricas
    obs_ant = df_ant_obs["Custo Total"].sum()
    obs_atual = df_atual_obs["Custo Total"].sum()

    st.subheader("📅 Mês Atual vs Mês Anterior")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("🔴 Entrou", moeda_br(entrou["Vlr Atual"].sum()), "#ff6b6b", subtitulo=f"{len(entrou)} itens")
    with c2: card("🟢 Saiu", moeda_br(saiu["Vlr Ant"].sum()), "#51cf66", subtitulo=f"{len(saiu)} itens")
    with c3: card("🔽 Reduziu", moeda_br(reduziu["Vlr Reduzido"].sum()), "#74c0fc", subtitulo=f"{len(reduziu)} itens")
    with c4: card("Δ Variação Real", moeda_br(obs_atual - obs_ant), "#fff", cor_valor="#ff6b6b" if (obs_atual-obs_ant)>0 else "#51cf66")

    # --- TABELA DETALHADA ---
    st.markdown("---")
    colunas_tabela = ["Status Mov", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao", "Qtd Ant", "Vlr Ant", "Qtd Atual", "Vlr Atual"]
    
    frames = []
    for df_tab in [entrou, saiu, reduziu, variacao]:
        if not df_tab.empty:
            frames.append(df_tab[colunas_tabela])

    if frames:
        mov = pd.concat(frames, ignore_index=True).sort_values("Vlr Atual", ascending=False)
        
        col_radio, col_export = st.columns([4, 1])
        with col_radio:
            status_radio = st.radio("Visualizar", options=["Todos", "🔴 Entrou", "🟢 Saiu", "🔽 Reduziu"], horizontal=True)

        mov_filtrado = mov if status_radio == "Todos" else mov[mov["Status Mov"] == status_radio]
        
        busca = st.text_input("🔍 PESQUISAR", placeholder="Produto, empresa...")
        if busca:
            mov_filtrado = mov_filtrado[mov_filtrado.apply(lambda row: row.astype(str).str.contains(busca, case=False).any(), axis=1)]

        with col_export:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            buffer = io.BytesIO()
            mov_filtrado.to_excel(buffer, index=False)
            st.download_button("📥 Exportar", buffer.getvalue(), "movimentacao.xlsx", use_container_width=True)

        mov_display = mov_filtrado.copy()
        mov_display["Vlr Ant"] = mov_display["Vlr Ant"].apply(moeda_br)
        mov_display["Vlr Atual"] = mov_display["Vlr Atual"].apply(moeda_br)

        st.caption(f"{len(mov_display)} itens exibidos")
        st.dataframe(mov_display, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação encontrada para o período.")