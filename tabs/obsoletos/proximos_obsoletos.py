import streamlit as st
import pandas as pd
import io

def render(df_kpi, moeda_br):
    # Filtro inicial
    df = df_kpi[df_kpi["Status Estoque"] == "Até 6 meses"].copy()
    if df.empty:
        st.info("Nenhum item próximo de entrar em obsoleto.")
        return

    if "Tipo de Estoque" not in df.columns: df["Tipo de Estoque"] = "—"

    # --------------------------------------------------
    # CALCULAR DIAS RESTANTES (CORRIGIDO)
    # --------------------------------------------------
    DataBase = pd.to_datetime(df["Data Fechamento"].iloc[0])
    df["Ult_Movimentacao"] = pd.to_datetime(df["Ult_Movimentacao"], errors="coerce")

    # AJUSTE: Se não tem data, assumimos 180 dias (já é crítico) para não sumir do radar
    df["Dias Sem Mov"] = (DataBase - df["Ult_Movimentacao"]).dt.days.fillna(180).astype(int)

    # Dias restantes até completar 180 dias
    df["Dias Restantes"] = (180 - df["Dias Sem Mov"]).clip(lower=0)

    # Filtra apenas os que entrarão nos próximos 90 dias
    df = df[df["Dias Restantes"] <= 90].copy()

    if df.empty:
        st.info("Nenhum item entrará em obsoleto nos próximos 90 dias.")
        return

    # Classificação de Risco
    def classificar_risco(dias):
        if dias <= 30: return "🔴 Crítico"
        elif dias <= 60: return "🟠 Alerta"
        else: return "🟡 Atenção"

    df["Risco"] = df["Dias Restantes"].apply(classificar_risco)

    # --------------------------------------------------
    # KPIs E INTERFACE
    # --------------------------------------------------
    valor_total = df["Custo Total"].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    faixas = [
        ("🔴 Crítico (< 30d)", "🔴 Crítico", "#ff6b6b", c1),
        ("🟠 Alerta (30-60d)", "🟠 Alerta", "#ffa94d", c2),
        ("🟡 Atenção (60-90d)", "🟡 Atenção", "#ffe066", c3)
    ]

    for label, nivel, cor, col in faixas:
        vlr = df[df["Risco"] == nivel]["Custo Total"].sum()
        qtd = len(df[df["Risco"] == nivel])
        col.markdown(f"""
            <div style="border:2px solid {cor}; border-radius:12px; padding:16px; text-align:center;">
                <div style="font-size:12px;color:white">{label}</div>
                <div style="font-size:20px;font-weight:bold;color:{cor}">{moeda_br(vlr)}</div>
                <div style="font-size:11px;color:#aaa">{qtd} itens</div>
            </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
            <div style="border:2px solid #EC6E21; border-radius:12px; padding:16px; text-align:center;">
                <div style="font-size:12px;color:white">Valor em Risco</div>
                <div style="font-size:20px;font-weight:bold;color:white">{moeda_br(valor_total)}</div>
                <div style="font-size:11px;color:#aaa">total próximos 90d</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    # Filtros e Tabela (Mantenha sua lógica original de filtros abaixo)
    col_filtro, col_export = st.columns([4, 1])
    with col_filtro:
        risco_sel = st.radio("Filtro:", ["Todos", "🔴 Crítico", "🟠 Alerta", "🟡 Atenção"], horizontal=True)
    
    df_tab = df if risco_sel == "Todos" else df[df["Risco"] == risco_sel]
    
    with col_export:
        buffer = io.BytesIO()
        df_tab.to_excel(buffer, index=False)
        st.download_button("📥 Exportar", buffer.getvalue(), "proximos_obsoletos.xlsx")

    # Exibição Final
    df_display = df_tab.copy()
    df_display["Custo Total"] = df_display["Custo Total"].apply(moeda_br)
    
    st.dataframe(df_display[[
        "Risco", "Dias Restantes", "Empresa / Filial", "Produto", "Descricao", "Saldo Atual", "Custo Total"
    ]], use_container_width=True, hide_index=True)