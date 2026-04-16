import streamlit as st
import pandas as pd
import io

def card(titulo, valor, cor_borda="#EC6E21", cor_valor=None, subtitulo=None):
    cor_val = cor_valor if cor_valor else "white"
    sub_html = f'<div style="font-size:12px;color:#aaa;margin-top:4px">{subtitulo}</div>' if subtitulo else ""
    st.markdown(
        f"""
        <div style="border:2px solid {cor_borda}; border-radius:12px; padding:16px; min-height:90px; display:flex; flex-direction:column; justify-content:center; text-align:center;">
            <div style="font-size:13px;color:white">{titulo}</div>
            <div style="font-size:22px;font-weight:bold;color:{cor_val}">{valor}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True
    )

def render(df_hist, moeda_br, data_selecionada=None):
    df = df_hist.copy()

    if "Tipo de Estoque" not in df.columns: df["Tipo de Estoque"] = "Não Informado"
    if "Conta" not in df.columns: df["Conta"] = "Não Informado"

    # Criar coluna booleana baseada no status
    df["obsoleto"] = df["Status Estoque"] == "Obsoleto"
    datas = sorted(df["Data Fechamento"].unique())

    # --- Definição de datas ---
    if data_selecionada is not None:
        data_sel_ts = pd.Timestamp(data_selecionada)
        datas_anteriores = [d for d in datas if pd.Timestamp(d) < data_sel_ts]
        if data_sel_ts not in [pd.Timestamp(d) for d in datas] or len(datas_anteriores) == 0:
            st.warning("Histórico insuficiente para comparação.")
            return
        data_atual = data_sel_ts
        data_anterior = pd.Timestamp(max(datas_anteriores))
    else:
        if len(datas) < 2: return
        data_atual, data_anterior = pd.Timestamp(datas[-1]), pd.Timestamp(datas[-2])

    # --- DEDUPLICAÇÃO CORRIGIDA ---
    # Ordenamos por Custo Total para garantir que o status 'Obsoleto' 
    # só seja mantido se for a linha principal do produto.
    df_at_raw = df[df["Data Fechamento"] == data_atual].copy()
    df_an_raw = df[df["Data Fechamento"] == data_anterior].copy()

    df_at_dedup = df_at_raw.sort_values("Custo Total", ascending=False).drop_duplicates(
        subset=["Empresa / Filial", "Produto"], keep="first"
    )
    df_an_dedup = df_an_raw.sort_values("Custo Total", ascending=False).drop_duplicates(
        subset=["Empresa / Filial", "Produto"], keep="first"
    )

    st.caption(f"Comparando **{data_atual.strftime('%d/%m/%Y')}** vs **{data_anterior.strftime('%d/%m/%Y')}**")

    chave = ["Empresa / Filial", "Produto"]

    # --- PREPARAÇÃO PARA MERGE ---
    df_ant_sel = df_an_dedup[chave + ["Custo Total", "Saldo Atual", "obsoleto"]].rename(columns={
        "Custo Total": "Vlr Ant", "Saldo Atual": "Qtd Ant", "obsoleto": "Obs Ant"
    })
    df_atual_sel = df_at_dedup[chave + ["Custo Total", "Saldo Atual", "Descricao", "Conta", "Tipo de Estoque", "obsoleto"]].rename(columns={
        "Custo Total": "Vlr Atual", "Saldo Atual": "Qtd Atual", "obsoleto": "Obs Atual"
    })

    base = df_atual_sel.merge(df_ant_sel, on=chave, how="outer")

    for c in ["Vlr Ant", "Qtd Ant", "Vlr Atual", "Qtd Atual"]: base[c] = base[c].fillna(0)
    base["Obs Ant"] = base["Obs Ant"].fillna(False)
    base["Obs Atual"] = base["Obs Atual"].fillna(False)

    # --- CATEGORIAS ---
    # 1. Entrou: Não era obsoleto (ou não existia) e agora é
    entrou = base[(base["Obs Ant"] == False) & (base["Obs Atual"] == True)].copy()
    entrou["Status Mov"] = "🔴 Entrou"

    # 2. Saiu: Era obsoleto e agora zerou ou não é mais obsoleto
    saiu = base[(base["Obs Ant"] == True) & ((base["Obs Atual"] == False) | (base["Vlr Atual"] == 0))].copy()
    saiu["Status Mov"] = "🟢 Saiu"
    
    # Subcategoria para o Card de "Saiu do Obsoleto" (Mudança de status com saldo)
    reduziu = saiu[saiu["Vlr Atual"] > 0].copy()
    reduziu["Vlr Reduzido"] = reduziu["Vlr Ant"]

    # 3. Variação (Itens que continuam obsoletos mas mudou o valor)
    variacao = base[(base["Obs Ant"] == True) & (base["Obs Atual"] == True) & (base["Vlr Atual"] != base["Vlr Ant"])].copy()
    variacao["Status Mov"] = "📊 Variação"

    # --- CARDS ---
    st.subheader("📅 Movimentação do Período")
    c1, c2, c3, c4 = st.columns(4)
    with c1: card("🔴 Entrou", moeda_br(entrou["Vlr Atual"].sum()), "#ff6b6b", subtitulo=f"{len(entrou)} itens")
    with c2: card("🟢 Saiu Total", moeda_br(saiu[saiu["Vlr Atual"]==0]["Vlr Ant"].sum()), "#51cf66", subtitulo=f"{len(saiu[saiu['Vlr Atual']==0])} itens")
    with c3: card("🔽 Mudou p/ Giro", moeda_br(reduziu["Vlr Atual"].sum()), "#74c0fc", subtitulo=f"{len(reduziu)} itens")
    with c4:
        v_ant = base[base["Obs Ant"] == True]["Vlr Ant"].sum()
        v_atu = base[base["Obs Atual"] == True]["Vlr Atual"].sum()
        dif = v_atu - v_ant
        card("Δ Variação Real", moeda_br(dif), "#fff", cor_valor="#ff6b6b" if dif > 0 else "#51cf66", subtitulo="Saldo Final vs Inicial")

    # --- TABELA ---
    st.markdown("---")
    frames = [df_tab for df_tab in [entrou, saiu, variacao] if not df_tab.empty]
    if frames:
        mov = pd.concat(frames, ignore_index=True).sort_values("Vlr Atual", ascending=False)
        status_radio = st.radio("Filtrar Tabela:", options=["Todos", "🔴 Entrou", "🟢 Saiu", "📊 Variação"], horizontal=True)
        mov_filtrado = mov if status_radio == "Todos" else mov[mov["Status Mov"] == status_radio]
        
        st.dataframe(mov_filtrado[[
            "Status Mov", "Empresa / Filial", "Produto", "Descricao", 
            "Qtd Ant", "Vlr Ant", "Qtd Atual", "Vlr Atual"
        ]].style.format({"Vlr Ant": moeda_br, "Vlr Atual": moeda_br}), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma movimentação detectada.")