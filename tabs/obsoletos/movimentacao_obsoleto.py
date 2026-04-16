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

    # --- PROTEÇÃO ---
    if "Tipo de Estoque" not in df.columns:
        df["Tipo de Estoque"] = "Não Informado"
    if "Conta" not in df.columns:
        df["Conta"] = "Não Informado"

    # Coluna booleana para facilitar
    df["obsoleto"] = df["Status Estoque"] == "Obsoleto"
    datas = sorted(df["Data Fechamento"].unique())

    # --- Definição de datas ---
    if data_selecionada is not None:
        data_sel_ts = pd.Timestamp(data_selecionada)
        datas_anteriores = [d for d in datas if pd.Timestamp(d) < data_sel_ts]

        if data_sel_ts not in [pd.Timestamp(d) for d in datas]:
            st.warning("Data selecionada não encontrada no histórico.")
            return

        if len(datas_anteriores) == 0:
            st.info(f"{data_sel_ts.strftime('%d/%m/%Y')} é o primeiro fechamento.")
            return

        data_atual = data_sel_ts
        data_anterior = pd.Timestamp(max(datas_anteriores))
    else:
        if len(datas) < 2:
            st.warning("Histórico insuficiente.")
            return
        data_atual = pd.Timestamp(datas[-1])
        data_anterior = pd.Timestamp(datas[-2])

    # --- DEDUPLICAÇÃO CORRIGIDA (Respeita o valor financeiro) ---
    df_at_raw = df[df["Data Fechamento"] == data_atual].copy()
    df_an_raw = df[df["Data Fechamento"] == data_anterior].copy()

    # Ordenamos por valor para que, em caso de duplicatas, o status da linha principal prevaleça
    df_at_dedup = df_at_raw.sort_values("Custo Total", ascending=False).drop_duplicates(
        subset=["Empresa / Filial", "Produto"], keep="first"
    )
    df_an_dedup = df_an_raw.sort_values("Custo Total", ascending=False).drop_duplicates(
        subset=["Empresa / Filial", "Produto"], keep="first"
    )

    st.caption(f"Comparando **{data_atual.strftime('%d/%m/%Y')}** vs **{data_anterior.strftime('%d/%m/%Y')}**")

    chave = ["Empresa / Filial", "Produto"]

    # --- PREPARAÇÃO DOS DADOS ---
    df_ant_sel = df_an_dedup[chave + ["Custo Total", "Saldo Atual", "obsoleto"]].rename(columns={
        "Custo Total": "Vlr Ant",
        "Saldo Atual": "Qtd Ant",
        "obsoleto": "Obs Ant"
    })

    df_atual_sel = df_at_dedup[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque", "obsoleto"]].rename(columns={
        "Custo Total": "Vlr Atual",
        "Saldo Atual": "Qtd Atual",
        "obsoleto": "Obs Atual"
    })

    # Merge completo (Outer Join)
    base = df_atual_sel.merge(df_ant_sel, on=chave, how="outer")

    # Preencher vazios
    for c in ["Vlr Ant", "Qtd Ant", "Vlr Atual", "Qtd Atual"]:
        base[c] = base[c].fillna(0)
    
    base["Obs Ant"] = base["Obs Ant"].fillna(False)
    base["Obs Atual"] = base["Obs Atual"].fillna(False)

    # -------------------------------------------------------
    # CATEGORIZAÇÃO DAS MOVIMENTAÇÕES
    # -------------------------------------------------------

    # 1. Entrou: Não era obsoleto e agora é
    entrou = base[(base["Obs Ant"] == False) & (base["Obs Atual"] == True)].copy()
    entrou["Status Mov"] = "🔴 Entrou"

    # 2. Saiu Total: Era obsoleto e agora o saldo é zero
    saiu_total = base[(base["Obs Ant"] == True) & (base["Vlr Atual"] == 0)].copy()
    saiu_total["Status Mov"] = "🟢 Saiu Total"

    # 3. Mudou p/ Giro: Era obsoleto, ainda tem saldo, mas não é mais classificado como obsoleto
    mudou_giro = base[(base["Obs Ant"] == True) & (base["Obs Atual"] == False) & (base["Vlr Atual"] > 0)].copy()
    mudou_giro["Status Mov"] = "🔽 Mudou p/ Giro"

    # 4. Variação Interna: Era obsoleto, continua obsoleto, mas o valor mudou (venda parcial ou custo)
    variacao_interna = base[
        (base["Obs Ant"] == True) & 
        (base["Obs Atual"] == True) & 
        (base["Vlr Atual"] != base["Vlr Ant"])
    ].copy()
    variacao_interna["Status Mov"] = "📊 Var. Interna"

    # -------------------------------------------------------
    # CÁLCULOS DOS CARDS
    # -------------------------------------------------------
    v_entrou = entrou["Vlr Atual"].sum()
    v_saiu_total = saiu_total["Vlr Ant"].sum()
    v_mudou_giro = mudou_giro["Vlr Ant"].sum()
    v_var_interna = variacao_interna["Vlr Atual"].sum() - variacao_interna["Vlr Ant"].sum()
    
    # Diferença Real do Saldo (Final - Inicial)
    v_obs_ant = base[base["Obs Ant"] == True]["Vlr Ant"].sum()
    v_obs_atu = base[base["Obs Atual"] == True]["Vlr Atual"].sum()
    v_diff_total = v_obs_atu - v_obs_ant

    # -------------------------------------------------------
    # EXIBIÇÃO DOS CARDS (5 COLUNAS)
    # -------------------------------------------------------
    st.subheader("📅 Movimentação do Período")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        card("🔴 Entrou", moeda_br(v_entrou), "#ff6b6b", subtitulo=f"{len(entrou)} itens")
    with c2:
        card("🟢 Saiu Total", moeda_br(v_saiu_total), "#51cf66", subtitulo=f"{len(saiu_total)} itens")
    with c3:
        card("🔽 Mudou p/ Giro", moeda_br(v_mudou_giro), "#74c0fc", subtitulo=f"{len(mudou_giro)} itens")
    with c4:
        card("📊 Var. Interna", moeda_br(v_var_interna), "#fab005", cor_valor="#fab005", subtitulo="Ajustes/Parciais")
    with c5:
        card(
            "Δ Variação Real",
            moeda_br(v_diff_total),
            "#fff",
            cor_valor="#ff6b6b" if v_diff_total > 0 else "#51cf66",
            subtitulo="Saldo Final vs Inicial"
        )

    # -------------------------------------------------------
    # TABELA COM FILTROS
    # -------------------------------------------------------
    st.markdown("---")

    # Unir todos os grupos para a tabela
    frames = []
    for df_tab in [entrou, saiu_total, mudou_giro, variacao_interna]:
        if not df_tab.empty:
            frames.append(df_tab)

    if frames:
        mov_completa = pd.concat(frames, ignore_index=True)

        col_radio, col_export = st.columns([4, 1])

        with col_radio:
            status_radio = st.radio(
                "Filtrar Tabela:",
                options=["Todos", "🔴 Entrou", "🟢 Saiu Total", "🔽 Mudou p/ Giro", "📊 Var. Interna"],
                horizontal=True
            )

        # Filtro de rádio
        mov_filtrada = mov_completa if status_radio == "Todos" else mov_completa[mov_completa["Status Mov"] == status_radio]

        # Busca textual
        busca = st.text_input("🔍 PESQUISAR NA TABELA", placeholder="Produto, empresa, descrição...")
        if busca:
            mov_filtrada = mov_filtrada[
                mov_filtrada.apply(lambda row: row.astype(str).str.contains(busca, case=False).any(), axis=1)
            ]

        with col_export:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            buffer = io.BytesIO()
            mov_filtrada.to_excel(buffer, index=False)
            st.download_button("📥 Exportar", buffer.getvalue(), "movimentacao_detalhada.xlsx", use_container_width=True)

        # Formatação de exibição
        mov_display = mov_filtrada.copy()
        mov_display["Vlr Ant"] = mov_display["Vlr Ant"].apply(moeda_br)
        mov_display["Vlr Atual"] = mov_display["Vlr Atual"].apply(moeda_br)

        st.caption(f"{len(mov_display)} itens exibidos")
        st.dataframe(
            mov_display[[
                "Status Mov", "Empresa / Filial", "Tipo de Estoque", 
                "Produto", "Descricao", "Qtd Ant", "Vlr Ant", "Qtd Atual", "Vlr Atual"
            ]], 
            use_container_width=True, 
            hide_index=True
        )

    else:
        st.info("Nenhuma movimentação relevante encontrada para o período.")