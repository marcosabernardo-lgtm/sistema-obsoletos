import streamlit as st
import pandas as pd
import io


def render(df_kpi, moeda_br):
    """
    Exibe itens com Status Estoque = 'Até 6 meses' que entrarão em obsoleto
    nos próximos 90 dias, com faixas de risco baseadas nos dias restantes.
    """

    # --------------------------------------------------
    # FILTRAR ITENS ATÉ 6 MESES
    # --------------------------------------------------

    df = df_kpi[df_kpi["Status Estoque"] == "Até 6 meses"].copy()

    if df.empty:
        st.info("Nenhum item próximo de entrar em obsoleto.")
        return

    # --------------------------------------------------
    # CALCULAR DIAS RESTANTES ATÉ COMPLETAR 6 MESES
    # --------------------------------------------------

    DataBase = pd.to_datetime(df["Data Fechamento"].iloc[0])

    df["Ult_Movimentacao"] = pd.to_datetime(df["Ult_Movimentacao"], errors="coerce")

    # Dias já sem movimento
    df["Dias Sem Mov"] = (DataBase - df["Ult_Movimentacao"]).dt.days.fillna(0).astype(int)

    # Dias restantes até completar 180 dias (6 meses)
    df["Dias Restantes"] = (180 - df["Dias Sem Mov"]).clip(lower=0)

    # Filtra apenas os que entrarão nos próximos 90 dias
    df = df[df["Dias Restantes"] <= 90].copy()

    if df.empty:
        st.info("Nenhum item entrará em obsoleto nos próximos 90 dias.")
        return

    # --------------------------------------------------
    # FAIXAS DE RISCO
    # --------------------------------------------------

    def classificar_risco(dias):
        if dias <= 30:
            return "🔴 Crítico"
        elif dias <= 60:
            return "🟠 Alerta"
        else:
            return "🟡 Atenção"

    df["Risco"] = df["Dias Restantes"].apply(classificar_risco)

    # --------------------------------------------------
    # KPIs
    # --------------------------------------------------

    qtd_critico  = len(df[df["Risco"] == "🔴 Crítico"])
    qtd_alerta   = len(df[df["Risco"] == "🟠 Alerta"])
    qtd_atencao  = len(df[df["Risco"] == "🟡 Atenção"])

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(f"""
    <div style="border:2px solid #ff6b6b;border-radius:12px;padding:16px;text-align:center;min-height:90px">
        <div style="font-size:13px;color:white">🔴 Crítico (&lt; 30 dias)</div>
        <div style="font-size:22px;font-weight:bold;color:#ff6b6b">{qtd_critico} itens</div>
    </div>
    """, unsafe_allow_html=True)

    c2.markdown(f"""
    <div style="border:2px solid #ffa94d;border-radius:12px;padding:16px;text-align:center;min-height:90px">
        <div style="font-size:13px;color:white">🟠 Alerta (30-60 dias)</div>
        <div style="font-size:22px;font-weight:bold;color:#ffa94d">{qtd_alerta} itens</div>
    </div>
    """, unsafe_allow_html=True)

    c3.markdown(f"""
    <div style="border:2px solid #ffe066;border-radius:12px;padding:16px;text-align:center;min-height:90px">
        <div style="font-size:13px;color:white">🟡 Atenção (60-90 dias)</div>
        <div style="font-size:22px;font-weight:bold;color:#ffe066">{qtd_atencao} itens</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # FILTRO DE RISCO
    # --------------------------------------------------

    st.markdown("""
    <style>
    div[data-testid="stRadio"] > div {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 10px 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    col_filtro, col_export = st.columns([4, 1])

    with col_filtro:
        risco_sel = st.radio(
            "Filtrar por risco",
            options=["Todos", "🔴 Crítico", "🟠 Alerta", "🟡 Atenção"],
            horizontal=True,
            key="filtro_risco_obsoleto",
            label_visibility="collapsed"
        )

    df_tab      = df.copy() if risco_sel == "Todos" else df[df["Risco"] == risco_sel].copy()
    df_tab      = df_tab.sort_values("Custo Total", ascending=False)
    valor_risco = df_tab["Custo Total"].sum()

    # Atualiza card Valor em Risco com valor do filtro atual
    c4.markdown(f"""
    <div style="border:2px solid #EC6E21;border-radius:12px;padding:16px;text-align:center;min-height:90px">
        <div style="font-size:13px;color:white">Valor em Risco</div>
        <div style="font-size:22px;font-weight:bold;color:white">{moeda_br(valor_risco)}</div>
    </div>
    """, unsafe_allow_html=True)

    with col_export:
        buffer = io.BytesIO()
        df_tab.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            label="📥 Exportar",
            data=buffer.getvalue(),
            file_name=f"proximos_obsoletos_{DataBase.strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # --------------------------------------------------
    # FORMATAR E EXIBIR TABELA
    # --------------------------------------------------

    colunas_exibir = [
        "Risco", "Dias Restantes", "Empresa / Filial", "Conta",
        "Produto", "Descricao", "Saldo Atual", "Custo Total",
    ]

    if "Ult_Movimentacao" in df_tab.columns:
        df_tab["Ult Movimento"] = pd.to_datetime(
            df_tab["Ult_Movimentacao"], errors="coerce"
        ).apply(lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "")
        colunas_exibir.append("Ult Movimento")

    df_display = df_tab[[c for c in colunas_exibir if c in df_tab.columns]].copy()
    df_display["Custo Total"] = df_display["Custo Total"].apply(moeda_br)

    st.caption(f"{len(df_display)} itens em risco de entrar em obsoleto")
    st.dataframe(df_display, use_container_width=True, hide_index=True)
