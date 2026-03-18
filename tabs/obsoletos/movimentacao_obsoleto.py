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
# 2. GERADOR DE TEXTO ANÁLISE
# -------------------------------------------------------
def gerar_texto_analise(variacao_real, valor_entrou, valor_saiu, valor_reduziu, var_custo,
                        qtd_entrou, qtd_saiu, qtd_reduziu, moeda_br):

    saldo_status = valor_entrou - valor_saiu

    if variacao_real < 0:
        cor_titulo = "#28a745"
        titulo = "✅ O Estoque Obsoleto REDUZIU neste mês"
    else:
        cor_titulo = "#dc3545"
        titulo = "⚠️ O Estoque Obsoleto AUMENTOU neste mês"

    texto_resultado = (
        f"O estoque obsoleto variou **{moeda_br(abs(variacao_real))}** "
        f"({'redução' if variacao_real < 0 else 'aumento'}) neste período."
    )

    if saldo_status > 0:
        texto_fluxo = (
            f"⚠️ **Fluxo Operacional Negativo:** "
            f"**{qtd_entrou} itens** ({moeda_br(valor_entrou)}) viraram obsoletos, "
            f"contra apenas **{qtd_saiu} itens** ({moeda_br(valor_saiu)}) que saíram totalmente. "
            f"O saldo do fluxo é de +{moeda_br(saldo_status)} — a torneira está aberta."
        )
        cor_fluxo = "#ff6b6b"
    else:
        texto_fluxo = (
            f"✅ **Fluxo Operacional Positivo:** "
            f"Zeramos **{qtd_saiu} itens** ({moeda_br(valor_saiu)}) do obsoleto, "
            f"mais do que os **{qtd_entrou} itens** ({moeda_br(valor_entrou)}) que entraram. "
            f"O saldo do fluxo é de {moeda_br(saldo_status)}."
        )
        cor_fluxo = "#51cf66"

    if valor_reduziu > 0:
        if variacao_real < 0 and saldo_status > 0:
            texto_baixas = (
                f"⚠️ **Atenção — Resultado mascarado pelas reduções parciais:** "
                f"O obsoleto reduziu no mês, mas o fluxo de novos itens ainda é negativo. "
                f"A redução de **{moeda_br(valor_reduziu)}** veio da diminuição de quantidade "
                f"em **{qtd_reduziu} itens** que foram parcialmente vendidos ou consumidos."
            )
            cor_baixas = "#ffa94d"
        else:
            texto_baixas = (
                f"📦 **Reduções parciais:** **{qtd_reduziu} itens** tiveram redução de quantidade, "
                f"representando **{moeda_br(valor_reduziu)}** a menos no obsoleto."
            )
            cor_baixas = "#aaa"
    else:
        texto_baixas = "Não houve reduções parciais de itens obsoletos neste período."
        cor_baixas = "#aaa"

    if abs(var_custo) < 1:
        texto_custo = "A variação de custo médio dos itens já obsoletos foi irrelevante neste período."
        cor_custo = "#aaa"
    elif var_custo < 0:
        texto_custo = (
            f"📉 **Variação de Custo:** Itens já obsoletos tiveram redução de custo médio "
            f"de **{moeda_br(abs(var_custo))}**, contribuindo para a redução do obsoleto."
        )
        cor_custo = "#51cf66"
    else:
        texto_custo = (
            f"📈 **Variação de Custo:** Itens já obsoletos tiveram aumento de custo médio "
            f"de **{moeda_br(var_custo)}**, pressionando o obsoleto para cima."
        )
        cor_custo = "#ff6b6b"

    return titulo, cor_titulo, texto_resultado, texto_fluxo, cor_fluxo, texto_baixas, cor_baixas, texto_custo, cor_custo


# -------------------------------------------------------
# 3. FUNÇÃO PRINCIPAL
# -------------------------------------------------------
def render(df_hist, moeda_br, data_selecionada=None):

    if "analise_visivel" not in st.session_state:
        st.session_state["analise_visivel"] = False

    def toggle_analise():
        st.session_state["analise_visivel"] = not st.session_state["analise_visivel"]

    df = df_hist.copy()

    df = (
        df.groupby(
            ["Data Fechamento", "Empresa / Filial", "Produto", "Descricao", "Conta", "Status Estoque"],
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

    df_ant_sel = df_ant[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta"]].copy()
    df_ant_sel = df_ant_sel.rename(columns={
        "Custo Total": "Vlr Ant", "Saldo Atual": "Qtd Ant",
        "Descricao": "Descricao_ant", "Conta": "Conta_ant",
    })

    df_atual_sel = df_atual[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta"]].copy()
    df_atual_sel = df_atual_sel.rename(columns={
        "Custo Total": "Vlr Atual", "Saldo Atual": "Qtd Atual",
        "Descricao": "Descricao_atual", "Conta": "Conta_atual",
    })

    base = df_atual_sel.merge(df_ant_sel, on=chave, how="outer")
    base["Vlr Ant"]   = base["Vlr Ant"].fillna(0)
    base["Qtd Ant"]   = base["Qtd Ant"].fillna(0)
    base["Vlr Atual"] = base["Vlr Atual"].fillna(0)
    base["Qtd Atual"] = base["Qtd Atual"].fillna(0)
    base["Descricao"] = base["Descricao_atual"].fillna(base["Descricao_ant"])
    base["Conta"]     = base["Conta_atual"].fillna(base["Conta_ant"])

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
    valor_risco   = risco["Vlr Atual"].sum() if not risco.empty else 0
    qtd_risco     = len(risco)
    var_custo_val = variacao["Vlr Atual"].sum() - variacao["Vlr Ant"].sum()
    obs_ant       = df_ant["Custo Total"].sum()
    obs_atual     = df_atual["Custo Total"].sum()
    variacao_real = obs_atual - obs_ant

    df_primeiro     = df[(df["Data Fechamento"] == pd.Timestamp(datas[0])) & (df["obsoleto"] == True)]
    obs_acum_inicio = df_primeiro["Custo Total"].sum()
    obs_acum_atual  = obs_atual
    variacao_acum   = obs_acum_atual - obs_acum_inicio

    st.subheader("📅 Mês Atual vs Mês Anterior")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: card("🔴 Entrou", moeda_br(valor_entrou), cor_valor="#ff6b6b", subtitulo=f"{qtd_entrou:,} itens")
    with c2: card("🟢 Saiu", moeda_br(valor_saiu), cor_valor="#51cf66", subtitulo=f"{qtd_saiu:,} itens")
    with c3: card("🔽 Reduziu", moeda_br(valor_reduziu), cor_valor="#74c0fc", subtitulo=f"{qtd_reduziu:,} itens")
    with c4: card("🟡 Risco Iminente", moeda_br(valor_risco), cor_borda="#f1c40f", cor_valor="#f1c40f", subtitulo=f"{qtd_risco:,} itens (4-6 meses)")
    with c5:
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

    col_btn, col_vazia = st.columns([1, 4])
    if not st.session_state["analise_visivel"]:
        with col_btn:
            st.button("🤖 Analisar Cenário", type="primary", on_click=toggle_analise, use_container_width=True)

    if st.session_state["analise_visivel"]:
        titulo, cor_titulo, texto_resultado, texto_fluxo, cor_fluxo, texto_baixas, cor_baixas, texto_custo, cor_custo = gerar_texto_analise(
            variacao_real, valor_entrou, valor_saiu, valor_reduziu, var_custo_val,
            qtd_entrou, qtd_saiu, qtd_reduziu, moeda_br
        )
        st.markdown(f"""
        <div style="background-color:#1E1E1E;padding:20px;border-radius:10px;border:1px solid #444;margin-bottom:15px;">
        <h3 style="color:{cor_titulo}; margin-top:0;">{titulo}</h3>
        <p style="color:#ccc;">{texto_resultado}</p>
        <hr style="border-color:#333">
        <p style="color:{cor_fluxo};">{texto_fluxo}</p>
        <p style="color:{cor_baixas};">{texto_baixas}</p>
        <p style="color:{cor_custo};">{texto_custo}</p>
        </div>
        """, unsafe_allow_html=True)
        col_fechar, _ = st.columns([1, 4])
        with col_fechar:
            st.button("❌ Fechar Análise", on_click=toggle_analise)

    st.markdown("---")

    # -------------------------------------------------------
    # TABELA COM FILTRO DE STATUS MOV
    # -------------------------------------------------------
    colunas_tabela = ["Status Mov", "Empresa / Filial", "Conta", "Produto", "Descricao",
                      "Qtd Ant", "Vlr Ant", "Qtd Atual", "Vlr Atual"]

    frames = []
    for df_tab in [entrou, saiu, reduziu, variacao, risco]:
        if len(df_tab) > 0:
            cols = [c for c in colunas_tabela if c in df_tab.columns]
            frames.append(df_tab[cols].copy())

    if frames:
        mov = pd.concat(frames, ignore_index=True)
        mov = mov.sort_values("Vlr Atual", ascending=False)

        # Filtro de Status Mov — radio button
        status_radio = st.radio(
            "Visualizar",
            options=["Todos", "🔴 Entrou", "🟢 Saiu", "🔽 Reduziu", "🟡 Risco Iminente"],
            horizontal=True,
            key="filtro_status_mov"
        )

        if status_radio == "Todos":
            mov_filtrado = mov
        else:
            mov_filtrado = mov[mov["Status Mov"] == status_radio]

        buffer = io.BytesIO()
        mov_filtrado.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="📥 Exportar movimentação para Excel",
            data=buffer,
            file_name="movimentacao_obsoleto.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        mov_display = mov_filtrado.copy()
        mov_display["Vlr Ant"]   = mov_display["Vlr Ant"].apply(moeda_br)
        mov_display["Vlr Atual"] = mov_display["Vlr Atual"].apply(moeda_br)

        st.caption(f"{len(mov_filtrado)} itens")
        st.dataframe(mov_display, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação encontrada para o período.")
