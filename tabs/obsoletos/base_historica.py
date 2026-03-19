import streamlit as st
import pandas as pd
import io


def render(df_filtrado, moeda_br):

    # CSS filtro card
    st.markdown("""
    <style>
    div[data-testid="stRadio"] > div {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 10px 16px;
    }
    .tb-hist{width:100%;border-collapse:collapse;font-size:13px;color:white}
    .tb-hist th{background:#0f5a60;padding:10px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap}
    .tb-hist td{padding:7px 12px;border-bottom:1px solid #1a6e75;background:#005562;color:white}
    .tb-hist tr:hover td{background:#0a6570}
    </style>
    """, unsafe_allow_html=True)

    col_filtro, col_export = st.columns([4, 1])

    with col_filtro:
        visao = st.radio(
            "Visualizar",
            ["Obsoleto", "Geral"],
            horizontal=True,
            key="base_historica_visao"
        )

    if visao == "Obsoleto":
        base = df_filtrado.copy()
    else:
        base = st.session_state.get("df_kpi_completo", df_filtrado).copy()

    base["Data Fechamento"] = pd.to_datetime(base["Data Fechamento"]).dt.date

    # Export ao lado do filtro
    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        buffer = io.BytesIO()
        base.to_excel(buffer, index=False)
        buffer.seek(0)
        data_ref   = base["Data Fechamento"].max() if not base.empty else "sem_data"
        label_visao = "obsoletos" if visao == "Obsoleto" else "geral"
        st.download_button(
            label="📥 Exportar",
            data=buffer.getvalue(),
            file_name=f"base_historica_{label_visao}_{data_ref}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    st.caption(f"{len(base)} produtos")

    # Colunas a exibir
    colunas = [
        "Data Fechamento", "Empresa / Filial", "Tipo de Estoque", "Conta",
        "Produto", "Descricao", "Unid", "Saldo Atual", "Vlr Unit", "Custo Total",
        "Ult_Movimentacao", "Origem Mov", "Dias Sem Mov", "Meses Ult Mov",
        "Status Estoque", "Status do Movimento", "Ano Meses Dias"
    ]
    colunas_pres = [c for c in colunas if c in base.columns]
    base_exib = base[colunas_pres].copy()

    # Formata valores
    if "Vlr Unit" in base_exib.columns:
        base_exib["Vlr Unit"] = pd.to_numeric(base_exib["Vlr Unit"], errors="coerce").apply(
            lambda x: moeda_br(x) if pd.notna(x) else ""
        )
    if "Custo Total" in base_exib.columns:
        base_exib["Custo Total"] = base_exib["Custo Total"].apply(moeda_br)

    # Monta cabeçalho
    cabecalho = "".join(f"<th>{c}</th>" for c in colunas_pres)

    # Monta linhas
    linhas = ""
    for _, row in base_exib.iterrows():
        cells = ""
        for c in colunas_pres:
            val = row[c]
            val = "" if pd.isna(val) else str(val)
            align = "text-align:right" if c in ["Saldo Atual", "Vlr Unit", "Custo Total", "Dias Sem Mov", "Meses Ult Mov"] else ""
            style = f" style='{align}'" if align else ""
            cells += f"<td{style}>{val}</td>"
        linhas += f"<tr>{cells}</tr>"

    css = (
        "<style>.tb-hist{width:100%;border-collapse:collapse;font-size:13px;color:white}"
        ".tb-hist th{background:#0f5a60;padding:10px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700;white-space:nowrap}"
        ".tb-hist td{padding:7px 12px;border-bottom:1px solid #1a6e75;background:#005562;color:white}"
        ".tb-hist tr:hover td{background:#0a6570}</style>"
    )

    st.markdown(
        css + f"<table class='tb-hist'><thead><tr>{cabecalho}</tr></thead><tbody>{linhas}</tbody></table>",
        unsafe_allow_html=True
    )
