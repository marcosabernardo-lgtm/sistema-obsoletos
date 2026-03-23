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

    # Adicionado "Tipo de Estoque" no agrupamento
    df = (
        df.groupby(
            ["Data Fechamento", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao", "Status Estoque"],
            as_index=False
        ).agg({"Saldo Atual": "sum", "Custo Total": "sum"})
    )

    df = (
        df.sort_values("Status Estoque")
        .drop_duplicates(subset=["Data Fechamento", "Empresa / Filial", "Produto"], keep="first")
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

    df_atual = df[(df["Data Fechamento"] == data_atual) & (df["obsoleto"] == True)].copy()
    df_ant   = df[(df["Data Fechamento"] == data_anterior) & (df["obsoleto"] == True)].copy()

    st.caption(f"Comparando **{data_atual.strftime('%d/%m/%Y')}** vs **{data_anterior.strftime('%d/%m/%Y')}**")

    chave = ["Empresa / Filial", "Produto"]

    # Selecionando colunas incluindo Tipo de Estoque
    df_ant_sel = df_ant[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque"]].copy()
    df_ant_sel = df_ant_sel.rename(columns={
        "Custo Total": "Vlr Ant", "Saldo Atual": "Qtd Ant",
        "Descricao": "Descricao_ant", "Conta": "Conta_ant", "Tipo de Estoque": "Tipo_ant"
    })

    df_atual_sel = df_atual[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque"]].copy()
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

    entrou  = base[(base["Vlr Ant"] == 0) & (base["Vlr Atual"] > 0)].copy()
    entrou["Status Mov"] = "🔴 Entrou"

    saiu = base[(base["Vlr Ant"] > 0) & (base["Vlr Atual"] == 0)].copy()
    saiu["Status Mov"] = "🟢 Saiu"

    reduziu = base[
        (base["Vlr Ant"] > 0) & (base["Vlr Atual"] > 0) &
        (base["Qtd Atual"] < base["Qtd Ant"])
    ].copy()
    reduziu["Status Mov"] = "🔽 Reduziu"

    variacao = base[
        (base["Vlr Ant"] > 0) & (base["Vlr Atual"] > 0) &
        (base["Qtd Atual"] == base["Qtd Ant"]) &
        (base["Vlr Atual"] != base["Vlr Ant"])
    ].copy()
    variacao["Status Mov"] = "📊 Variação"

    valor_entrou  = entrou["Vlr Atual"].sum()
    qtd_entrou    = len(entrou)
    valor_saiu    = saiu["Vlr Ant"].sum()
    qtd_saiu      = len(saiu)
    valor_reduziu = (reduziu["Vlr Ant"] - reduziu["Vlr Atual"]).sum()
    qtd_reduziu   = len(reduziu)
    obs_ant       = df_ant["Custo Total"].sum()
    obs_atual     = df_atual["Custo Total"].sum()
    variacao_real = obs_atual - obs_ant

    df_primeiro     = df[(df["Data Fechamento"] == pd.Timestamp(datas[0])) & (df["obsoleto"] == True)]
    obs_acum_inicio = df_primeiro["Custo Total"].sum()
    obs_acum_atual  = obs_atual
    variacao_acum   = obs_acum_atual - obs_acum_inicio

    st.subheader("📅 Mês Atual vs Mês Anterior")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("🔴 Entrou", moeda_br(valor_entrou), cor_valor="#ff6b6b", subtitulo=f"{qtd_entrou:,} itens")
    with c2: card("🟢 Saiu", moeda_br(valor_saiu), cor_valor="#51cf66", subtitulo=f"{qtd_saiu:,} itens")
    with c3: card("🔽 Reduziu", moeda_br(valor_reduziu), cor_valor="#74c0fc", subtitulo=f"{qtd_reduziu:,} itens")
    with c4:
        cor = "#ff6b6b" if variacao_real > 0 else "#51cf66"
        card("Δ Variação Real", moeda_br(variacao_real), cor_borda="#fff", cor_valor=cor)

    st.markdown("---")

    st.subheader("📈 Acumulado (desde o primeiro fechamento)")
    a1, a2, a3 = st.columns(3)
    with a1: card("Obsoleto no Início", moeda_br(obs_acum_inicio))
    with a2: card("Obsoleto Atual", moeda_br(obs_acum_atual))
    with a3:
        cor = "#ff6b6b" if variacao_acum > 0 else "#51cf66"
        card("Δ Variação Acumulada", moeda_br(variacao_acum), cor_borda="#fff", cor_valor=cor)

    st.markdown("---")

    # -------------------------------------------------------
    # TABELA COM FILTRO DE STATUS MOV
    # -------------------------------------------------------
    # Adicionado "Tipo de Estoque" na ordem das colunas
    colunas_tabela = ["Status Mov", "Empresa / Filial", "Tipo de Estoque", "Conta", "Produto", "Descricao",
                      "Qtd Ant", "Vlr Ant", "Qtd Atual", "Vlr Atual"]

    frames = []
    for df_tab in [entrou, saiu, reduziu, variacao]:
        if len(df_tab) > 0:
            cols = [c for c in colunas_tabela if c in df_tab.columns]
            frames.append(df_tab[cols].copy())

    if frames:
        mov = pd.concat(frames, ignore_index=True)
        mov = mov.sort_values("Vlr Atual", ascending=False)

        st.markdown("""
        <style>
        div[data-testid="stRadio"] > div { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 10px 16px; }
        div[data-testid="stTextInput"] input, div[data-testid="stTextInput"] > div, div[data-testid="stTextInput"] > div > div { background-color: #005562 !important; }
        div[data-testid="stTextInput"] input { border: 1px solid rgba(250,250,250,0.2) !important; border-radius: 6px !important; color: white !important; padding: 8px 12px !important; }
        </style>
        """, unsafe_allow_html=True)

        col_radio, col_export = st.columns([4, 1])
        with col_radio:
            status_radio = st.radio("Visualizar", options=["Todos", "🔴 Entrou", "🟢 Saiu", "🔽 Reduziu"], horizontal=True, key="filtro_status_mov")

        if status_radio == "Todos":
            mov_filtrado = mov
        else:
            mov_filtrado = mov[mov["Status Mov"] == status_radio]

        col_busca, col_ord, col_dir = st.columns([3, 2, 1])

        mov_display = mov_filtrado.copy()
        mov_display["Vlr Ant"]   = mov_display["Vlr Ant"].apply(moeda_br)
        mov_display["Vlr Atual"] = mov_display["Vlr Atual"].apply(moeda_br)

        with col_busca:
            busca = st.text_input("🔍 PESQUISAR", placeholder="Produto, empresa, tipo, conta...", key="busca_mov_obs")
        with col_ord:
            ord_col = st.selectbox("📊 Classificar por", list(mov_display.columns), key="ord_col_mov_obs")
        with col_dir:
            ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key="ord_dir_mov_obs")

        if busca:
            mask = mov_display.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
            mov_display = mov_display[mask]

        ascending = ord_dir == "⬆ Asc"
        try:
            mov_display = mov_display.sort_values(
                ord_col, ascending=ascending,
                key=lambda x: pd.to_numeric(
                    x.astype(str).str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."),
                    errors="coerce"
                ).fillna(x.astype(str))
            )
        except Exception:
            pass

        with col_export:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            buffer = io.BytesIO()
            mov_filtrado.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                label="📥 Exportar",
                data=buffer,
                file_name="movimentacao_obsoleto.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        st.caption(f"{len(mov_display)} itens")
        st.dataframe(mov_display, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação encontrada para o período.")