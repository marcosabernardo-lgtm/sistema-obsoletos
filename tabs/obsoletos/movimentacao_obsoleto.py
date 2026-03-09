import streamlit as st
import pandas as pd
import io

# -------------------------------------------------------
# 1. FUNÇÃO DE ESTILO (CARD)
# -------------------------------------------------------
def card(titulo, valor, cor_borda="#EC6E21", cor_valor=None):
    cor_val = cor_valor if cor_valor else "white"
    st.markdown(
        f"""
        <div style="
            border:2px solid {cor_borda};
            border-radius:12px;
            padding:16px;
            height:90px;
            display:flex;
            flex-direction:column;
            justify-content:center;
            text-align:center;
        ">
            <div style="font-size:13px;color:white">{titulo}</div>
            <div style="font-size:22px;font-weight:bold;color:{cor_val}">{valor}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# -------------------------------------------------------
# 2. GERADOR DE TEXTO ANÁLISE
# -------------------------------------------------------
def gerar_texto_analise(variacao_real, valor_entrou, valor_saiu, valor_baixas, var_custo, moeda_br):

    if variacao_real < 0:
        cor_titulo = "#28a745"
        titulo = "✅ O Estoque Obsoleto REDUZIU neste mês"
    else:
        cor_titulo = "#dc3545"
        titulo = "⚠️ O Estoque Obsoleto AUMENTOU neste mês"

    saldo_status = valor_entrou - valor_saiu

    if saldo_status > 0:
        texto_fluxo = f"**⚠️ Ponto de Atenção (Fluxo de Status):** Entraram **{moeda_br(valor_entrou)}** em novos obsoletos contra **{moeda_br(valor_saiu)}** recuperados. A torneira está aberta."
    else:
        texto_fluxo = f"**✅ Ponto Positivo (Fluxo de Status):** Recuperamos **{moeda_br(valor_saiu)}** de obsoletos, mais do que os **{moeda_br(valor_entrou)}** que entraram."

    texto_baixas = f"**📦 Baixas:** Saíram definitivamente do estoque **{moeda_br(valor_baixas)}** em itens obsoletos."

    if var_custo < 0:
        texto_custo = f"**📉 Variação de Custo:** Itens já obsoletos tiveram redução de custo médio de **{moeda_br(abs(var_custo))}**."
    elif var_custo > 0:
        texto_custo = f"**📈 Variação de Custo:** Itens já obsoletos tiveram aumento de custo médio de **{moeda_br(var_custo)}**."
    else:
        texto_custo = "Não houve variação de custo em itens já obsoletos."

    return titulo, cor_titulo, texto_fluxo, texto_baixas, texto_custo


# -------------------------------------------------------
# 3. FUNÇÃO PRINCIPAL
# -------------------------------------------------------
def render(df_hist, moeda_br, data_selecionada=None):

    if "analise_visivel" not in st.session_state:
        st.session_state["analise_visivel"] = False

    def toggle_analise():
        st.session_state["analise_visivel"] = not st.session_state["analise_visivel"]

    df = df_hist.copy()

    # -------------------------------------------------------
    # CONSOLIDAÇÃO
    # -------------------------------------------------------
    df = (
        df.groupby(
            ["Data Fechamento", "Empresa / Filial", "Produto", "Descricao", "Conta", "Status do Movimento"],
            as_index=False
        ).agg({"Saldo Atual": "sum", "Custo Total": "sum"})
    )

    df = (
        df.sort_values("Status do Movimento")
        .drop_duplicates(subset=["Data Fechamento", "Empresa / Filial", "Produto"], keep="first")
    )

    df["obsoleto"] = df["Status do Movimento"] != "Até 6 meses"

    datas = sorted(df["Data Fechamento"].unique())

    # -------------------------------------------------------
    # DEFINIR DATA ATUAL E ANTERIOR
    # -------------------------------------------------------
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

    df_atual = df[df["Data Fechamento"] == data_atual].copy()
    df_ant   = df[df["Data Fechamento"] == data_anterior].copy()

    st.caption(f"Comparando **{data_atual.strftime('%d/%m/%Y')}** vs **{data_anterior.strftime('%d/%m/%Y')}**")

    chave = ["Empresa / Filial", "Produto"]

    # -------------------------------------------------------
    # MERGE COMPLETO — atual x anterior trazendo TODAS as colunas
    # -------------------------------------------------------
    colunas_ant = chave + ["obsoleto", "Custo Total", "Descricao", "Conta", "Saldo Atual", "Status do Movimento"]
    colunas_ant = [c for c in colunas_ant if c in df_ant.columns]

    base = df_atual.merge(
        df_ant[colunas_ant],
        on=chave,
        how="outer",
        suffixes=("_atual", "_ant")
    )

    base["obsoleto_atual"]    = base["obsoleto_atual"].fillna(False)
    base["obsoleto_ant"]      = base["obsoleto_ant"].fillna(False)
    base["Custo Total_atual"] = base["Custo Total_atual"].fillna(0)
    base["Custo Total_ant"]   = base["Custo Total_ant"].fillna(0)

    # Para campos sem sufixo (quando só vem de um lado), garantir existência
    for col in ["Descricao", "Conta", "Saldo Atual", "Status do Movimento"]:
        col_at  = col + "_atual"
        col_ant = col + "_ant"
        if col_at not in base.columns:
            base[col_at] = None
        if col_ant not in base.columns:
            base[col_ant] = None

    # -------------------------------------------------------
    # CATEGORIAS
    # -------------------------------------------------------

    # ENTROU: não era obsoleto → virou obsoleto
    entrou = base[
        (base["obsoleto_atual"] == True) & (base["obsoleto_ant"] == False)
    ].copy()
    entrou["Status Mov"]        = "🔴 Entrou"
    entrou["Custo Total"]       = entrou["Custo Total_atual"]
    entrou["Descricao"]         = entrou["Descricao_atual"]
    entrou["Conta"]             = entrou["Conta_atual"]
    entrou["Saldo Atual"]       = entrou["Saldo Atual_atual"]
    entrou["Status do Movimento"] = entrou["Status do Movimento_atual"]

    # SAIU: era obsoleto → voltou para ativo (ainda existe)
    saiu = base[
        (base["obsoleto_atual"] == False) & (base["obsoleto_ant"] == True) &
        (base["Custo Total_atual"] > 0)
    ].copy()
    saiu["Status Mov"]          = "🟢 Saiu"
    saiu["Custo Total"]         = saiu["Custo Total_ant"]
    saiu["Descricao"]           = saiu["Descricao_atual"].fillna(saiu["Descricao_ant"])
    saiu["Conta"]               = saiu["Conta_atual"].fillna(saiu["Conta_ant"])
    saiu["Saldo Atual"]         = saiu["Saldo Atual_atual"].fillna(saiu["Saldo Atual_ant"])
    saiu["Status do Movimento"] = saiu["Status do Movimento_atual"].fillna(saiu["Status do Movimento_ant"])

    # BAIXAS: era obsoleto → sumiu do estoque
    baixas = base[
        (base["obsoleto_ant"] == True) &
        (base["Custo Total_atual"] == 0)
    ].copy()
    baixas["Status Mov"]          = "⚫ Baixa"
    baixas["Custo Total"]         = baixas["Custo Total_ant"]
    baixas["Descricao"]           = baixas["Descricao_ant"]
    baixas["Conta"]               = baixas["Conta_ant"]
    baixas["Saldo Atual"]         = baixas["Saldo Atual_ant"]
    baixas["Status do Movimento"] = baixas["Status do Movimento_ant"]

    # VARIAÇÃO DE CUSTO: era obsoleto, continua obsoleto, valor mudou
    var_custo_df = base[
        (base["obsoleto_atual"] == True) & (base["obsoleto_ant"] == True)
    ].copy()
    var_custo_df["delta"] = var_custo_df["Custo Total_atual"] - var_custo_df["Custo Total_ant"]

    # -------------------------------------------------------
    # VALORES
    # -------------------------------------------------------
    valor_entrou  = entrou["Custo Total"].sum()
    qtd_entrou    = entrou["Produto"].nunique()

    valor_saiu    = saiu["Custo Total"].sum()
    qtd_saiu      = saiu["Produto"].nunique()

    valor_baixas  = baixas["Custo Total"].sum()
    qtd_baixas    = baixas["Produto"].nunique()

    var_custo_val = var_custo_df["delta"].sum()

    obs_ant       = df_ant[df_ant["obsoleto"]]["Custo Total"].sum()
    obs_atual     = df_atual[df_atual["obsoleto"]]["Custo Total"].sum()
    variacao_real = obs_atual - obs_ant

    # -------------------------------------------------------
    # ACUMULADO
    # -------------------------------------------------------
    df_primeiro = df[df["Data Fechamento"] == pd.Timestamp(datas[0])].copy()
    obs_acum_inicio = df_primeiro[df_primeiro["obsoleto"]]["Custo Total"].sum()
    obs_acum_atual  = obs_atual
    variacao_acum   = obs_acum_atual - obs_acum_inicio

    # -------------------------------------------------------
    # CARDS — MÊS ATUAL
    # -------------------------------------------------------
    st.subheader("📅 Mês Atual vs Mês Anterior")

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1: card("🔴 Entrou (itens)", f"{qtd_entrou:,}")
    with c2: card("🔴 Valor que Entrou", moeda_br(valor_entrou), cor_valor="#ff6b6b")
    with c3: card("🟢 Valor que Saiu", moeda_br(valor_saiu), cor_valor="#51cf66")
    with c4: card("⚫ Baixas", moeda_br(valor_baixas), cor_valor="#aaa")
    with c5:
        cor = "#ff6b6b" if var_custo_val > 0 else "#51cf66"
        card("📊 Var. Custo Médio", moeda_br(var_custo_val), cor_valor=cor)
    with c6:
        cor = "#ff6b6b" if variacao_real > 0 else "#51cf66"
        card("Δ Variação Real", moeda_br(variacao_real), cor_borda="#fff", cor_valor=cor)

    st.markdown("---")

    # -------------------------------------------------------
    # CARDS — ACUMULADO
    # -------------------------------------------------------
    st.subheader("📈 Acumulado (desde o primeiro fechamento)")

    a1, a2, a3 = st.columns(3)

    with a1: card("Obsoleto no Início", moeda_br(obs_acum_inicio))
    with a2: card("Obsoleto Atual", moeda_br(obs_acum_atual))
    with a3:
        cor = "#ff6b6b" if variacao_acum > 0 else "#51cf66"
        card("Δ Variação Acumulada", moeda_br(variacao_acum), cor_borda="#fff", cor_valor=cor)

    st.markdown("---")

    # -------------------------------------------------------
    # BOTÃO ANALISAR
    # -------------------------------------------------------
    col_btn, col_vazia = st.columns([1, 4])

    if not st.session_state["analise_visivel"]:
        with col_btn:
            st.button(
                "🤖 Analisar Cenário",
                type="primary",
                on_click=toggle_analise,
                use_container_width=True
            )

    if st.session_state["analise_visivel"]:

        titulo, cor_titulo, texto_fluxo, texto_baixas, texto_custo = gerar_texto_analise(
            variacao_real, valor_entrou, valor_saiu, valor_baixas, var_custo_val, moeda_br
        )

        st.markdown(f"""
        <div style="
            background-color:#1E1E1E;
            padding:20px;
            border-radius:10px;
            border:1px solid #444;
            margin-bottom:15px;
        ">
        <h3 style="color:{cor_titulo}; margin-top:0;">{titulo}</h3>
        <p style="color:white;">{texto_fluxo}</p>
        <p style="color:white;">{texto_baixas}</p>
        <p style="color:white;">{texto_custo}</p>
        </div>
        """, unsafe_allow_html=True)

        col_fechar, _ = st.columns([1, 4])
        with col_fechar:
            st.button("❌ Fechar Análise", on_click=toggle_analise)

    st.markdown("---")

    # -------------------------------------------------------
    # TABELA
    # -------------------------------------------------------
    colunas_tabela = ["Status Mov", "Empresa / Filial", "Conta", "Produto",
                      "Descricao", "Saldo Atual", "Custo Total", "Status do Movimento"]

    frames = []
    for df_tab in [entrou, saiu, baixas]:
        if len(df_tab) > 0:
            cols_disp = [c for c in colunas_tabela if c in df_tab.columns]
            frames.append(df_tab[cols_disp].copy())

    if frames:
        mov = pd.concat(frames, ignore_index=True)
        mov = mov.rename(columns={
            "Saldo Atual": "Quantidade",
            "Status do Movimento": "Status do Estoque"
        })
        mov = mov.sort_values("Custo Total", ascending=False)

        buffer = io.BytesIO()
        mov.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="📥 Exportar movimentação para Excel",
            data=buffer,
            file_name="movimentacao_obsoleto.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        mov["Custo Total"] = mov["Custo Total"].apply(moeda_br)

        st.dataframe(mov, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação encontrada para o período.")