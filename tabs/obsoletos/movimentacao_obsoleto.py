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

    # Consolidar dados para evitar duplicatas de linhas idênticas
    df = (
        df.groupby(
            ["Data Fechamento", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao", "Status Estoque"],
            as_index=False
        ).agg({"Saldo Atual": "sum", "Custo Total": "sum"})
    )

    # Identificação booleana do obsoleto
    df["obsoleto"] = df["Status Estoque"] == "Obsoleto"
    datas = sorted(df["Data Fechamento"].unique())

    # Seleção de Datas
    if data_selecionada is not None:
        data_sel_ts = pd.Timestamp(data_selecionada)
        datas_anteriores = [d for d in datas if pd.Timestamp(d) < data_sel_ts]

        if data_sel_ts not in [pd.Timestamp(d) for d in datas]:
            st.warning("Data selecionada não encontrada no histórico.")
            return

        if len(datas_anteriores) == 0:
            st.info(f"ℹ️ {data_sel_ts.strftime('%d/%m/%Y')} é o primeiro fechamento — não há mês anterior para comparar.")
            return

        data_atual    = data_sel_ts
        data_anterior = pd.Timestamp(max(datas_anteriores))
    else:
        if len(datas) < 2:
            st.warning("Histórico insuficiente para análise.")
            return
        data_atual    = pd.Timestamp(datas[-1])
        data_anterior = pd.Timestamp(datas[-2])

    # -------------------------------------------------------
    # 🎯 CORREÇÃO: DEDUPLICAÇÃO POR PRIORIDADE DE STATUS
    # -------------------------------------------------------
    # Separamos os meses
    df_atual_raw = df[df["Data Fechamento"] == data_atual].copy()
    df_ant_raw   = df[df["Data Fechamento"] == data_anterior].copy()

    # Em cada mês, ordenamos para que 'obsoleto=True' fique no topo antes de tirar duplicatas.
    # Isso garante que se o item for Normal e Obsoleto, manteremos a linha do Obsoleto.
    df_atual_dedup = (
        df_atual_raw.sort_values("obsoleto", ascending=False)
        .drop_duplicates(subset=["Empresa / Filial", "Produto"], keep="first")
    )
    df_ant_dedup = (
        df_ant_raw.sort_values("obsoleto", ascending=False)
        .drop_duplicates(subset=["Empresa / Filial", "Produto"], keep="first")
    )

    # Agora sim filtramos apenas os que restaram como obsoletos para comparar
    df_atual_obs = df_atual_dedup[df_atual_dedup["obsoleto"] == True].copy()
    df_ant_obs   = df_ant_dedup[df_ant_dedup["obsoleto"] == True].copy()
    # -------------------------------------------------------

    st.caption(f"Comparando **{data_atual.strftime('%d/%m/%Y')}** vs **{data_anterior.strftime('%d/%m/%Y')}**")

    chave = ["Empresa / Filial", "Produto"]

    # Preparar para o Merge
    df_ant_sel = df_ant_obs[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque"]].copy()
    df_ant_sel = df_ant_sel.rename(columns={
        "Custo Total": "Vlr Ant", "Saldo Atual": "Qtd Ant",
        "Descricao": "Descricao_ant", "Conta": "Conta_ant", "Tipo de Estoque": "Tipo_ant"
    })

    df_atual_sel = df_atual_obs[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque"]].copy()
    df_atual_sel = df_atual_sel.rename(columns={
        "Custo Total": "Vlr Atual", "Saldo Atual": "Qtd Atual",
        "Descricao": "Descricao_atual", "Conta": "Conta_atual", "Tipo de Estoque": "Tipo_atual"
    })

    base = df_atual_sel.merge(df_ant_sel, on=chave, how="outer")
    base["Vlr Ant"]   = base["Vlr Ant"].fillna(0)
    base["Qtd Ant"]   = base["Qtd Ant"].fillna(0)
    base["Vlr Atual"] = base["Vlr Atual"].fillna(0)
    base["Qtd Atual"] = base["Qtd Atual"].fillna(0)
    base["Descricao"] = base["Descricao_atual"].fillna(base["Descricao_ant"])
    base["Conta"]     = base["Conta_atual"].fillna(base["Conta_ant"])
    base["Tipo de Estoque"] = base["Tipo_atual"].fillna(base["Tipo_ant"])

    # 🔍 DEBUG
    with st.expander("🔍 DEBUG — Itens presentes nos dois meses (Qtd Ant vs Qtd Atual)", expanded=False):
        debug_df = base[
            (base["Vlr Ant"] > 0) & (base["Vlr Atual"] > 0)
        ][["Empresa / Filial", "Produto", "Descricao", "Qtd Ant", "Qtd Atual", "Vlr Ant", "Vlr Atual"]].copy()

        debug_df["Δ Qtd"] = debug_df["Qtd Atual"] - debug_df["Qtd Ant"]
        debug_df["Δ Vlr"] = debug_df["Vlr Atual"] - debug_df["Vlr Ant"]

        st.caption(f"Total de itens em ambos os meses: **{len(debug_df)}**")
        c_r, c_i, c_a = st.columns(3)
        c_r.metric("🔽 Reduziram quantidade", len(debug_df[debug_df["Δ Qtd"] < 0]))
        c_i.metric("➡️ Quantidade igual", len(debug_df[debug_df["Δ Qtd"] == 0]))
        c_a.metric("🔼 Aumentaram quantidade", len(debug_df[debug_df["Δ Qtd"] > 0]))
        st.dataframe(debug_df.sort_values("Δ Qtd").head(50), use_container_width=True, hide_index=True)

    # --- CATEGORIZAÇÃO ---
    entrou  = base[(base["Vlr Ant"] == 0) & (base["Vlr Atual"] > 0)].copy()
    entrou["Status Mov"] = "🔴 Entrou"

    saiu = base[(base["Vlr Ant"] > 0) & (base["Vlr Atual"] == 0)].copy()
    saiu["Status Mov"] = "🟢 Saiu"

    reduziu = base[
        (base["Vlr Ant"] > 0) & (base["Vlr Atual"] > 0) &
        (base["Qtd Atual"] < base["Qtd Ant"])
    ].copy()
    reduziu["Status Mov"] = "🔽 Reduziu"
    reduziu["Qtd Reduzida"]   = reduziu["Qtd Ant"] - reduziu["Qtd Atual"]
    reduziu["Custo Unit Ant"] = reduziu["Vlr Ant"] / reduziu["Qtd Ant"].replace(0, pd.NA)
    reduziu["Vlr Reduzido"]   = reduziu["Custo Unit Ant"] * reduziu["Qtd Reduzida"]

    variacao = base[
        (base["Vlr Ant"] > 0) & (base["Vlr Atual"] > 0) &
        (base["Qtd Atual"] == base["Qtd Ant"]) &
        (base["Vlr Atual"] != base["Vlr Ant"])
    ].copy()
    variacao["Status Mov"] = "📊 Variação"

    # --- MÉTRICAS ---
    valor_entrou  = entrou["Vlr Atual"].sum()
    valor_saiu    = saiu["Vlr Ant"].sum()
    valor_reduziu = reduziu["Vlr Reduzido"].sum()
    
    obs_ant       = df_ant_obs["Custo Total"].sum()
    obs_atual     = df_atual_obs["Custo Total"].sum()
    variacao_real = obs_atual - obs_ant

    # Acumulado
    df_primeiro_dedup = (
        df[df["Data Fechamento"] == pd.Timestamp(datas[0])]
        .sort_values("obsoleto", ascending=False)
        .drop_duplicates(subset=["Empresa / Filial", "Produto"], keep="first")
    )
    obs_acum_inicio = df_primeiro_dedup[df_primeiro_dedup["obsoleto"] == True]["Custo Total"].sum()
    variacao_acum   = obs_atual - obs_acum_inicio

    st.subheader("📅 Mês Atual vs Mês Anterior")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("🔴 Entrou", moeda_br(valor_entrou), cor_valor="#ff6b6b", subtitulo=f"{len(entrou):,} itens")
    with c2: card("🟢 Saiu", moeda_br(valor_saiu), cor_valor="#51cf66", subtitulo=f"{len(saiu):,} itens")
    with c3: card("🔽 Reduziu", moeda_br(valor_reduziu), cor_valor="#74c0fc", subtitulo=f"{len(reduziu):,} itens")
    with c4:
        cor = "#ff6b6b" if variacao_real > 0 else "#51cf66"
        card("Δ Variação Real", moeda_br(variacao_real), cor_borda="#fff", cor_valor=cor)

    st.markdown("---")
    st.subheader("📈 Acumulado (desde o primeiro fechamento)")
    a1, a2, a3 = st.columns(3)
    with a1: card("Obsoleto no Início", moeda_br(obs_acum_inicio))
    with a2: card("Obsoleto Atual", moeda_br(obs_atual))
    with a3:
        cor = "#ff6b6b" if variacao_acum > 0 else "#51cf66"
        card("Δ Variação Acumulada", moeda_br(variacao_acum), cor_borda="#fff", cor_valor=cor)

    st.markdown("---")

    # --- TABELA DETALHADA ---
    colunas_tabela = ["Status Mov", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao",
                      "Qtd Ant", "Vlr Ant", "Qtd Atual", "Vlr Atual"]

    frames = [df_tab for df_tab in [entrou, saiu, reduziu, variacao] if not df_tab.empty]
    
    if frames:
        mov = pd.concat(frames, ignore_index=True).sort_values("Vlr Atual", ascending=False)
        
        st.markdown("""
        <style>
        div[data-testid="stRadio"] > div { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 10px 16px; }
        </style>
        """, unsafe_allow_html=True)

        col_radio, col_export = st.columns([4, 1])
        with col_radio:
            status_radio = st.radio("Visualizar", options=["Todos", "🔴 Entrou", "🟢 Saiu", "🔽 Reduziu"], horizontal=True)

        mov_filtrado = mov if status_radio == "Todos" else mov[mov["Status Mov"] == status_radio]

        col_busca, col_ord, col_dir = st.columns([3, 2, 1])
        with col_busca:
            busca = st.text_input("🔍 PESQUISAR", placeholder="Produto, empresa...")
        
        mov_display = mov_filtrado.copy()
        if busca:
            mask = mov_display.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
            mov_display = mov_display[mask]

        mov_display["Vlr Ant"]   = mov_display["Vlr Ant"].apply(moeda_br)
        mov_display["Vlr Atual"] = mov_display["Vlr Atual"].apply(moeda_br)

        with col_export:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            buffer = io.BytesIO()
            mov_filtrado.to_excel(buffer, index=False)
            st.download_button("📥 Exportar", buffer.getvalue(), "movimentacao.xlsx", use_container_width=True)

        st.caption(f"{len(mov_display)} itens exibidos")
        st.dataframe(mov_display, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação encontrada para o período.")