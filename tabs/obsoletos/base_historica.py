import streamlit as st
import pandas as pd
import io


def render(df_filtrado, moeda_br):

    st.markdown("""
    <style>
    div[data-testid="stRadio"] > div {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 10px 16px;
    }
    .mini-card {
        background-color: #005562;
        border: 1px solid rgba(236,110,33,0.5);
        border-radius: 8px;
        padding: 10px 16px;
        text-align: center;
    }
    .mini-card-title { font-size: 11px; color: rgba(255,255,255,0.5); letter-spacing: 1px; text-transform: uppercase; }
    .mini-card-value { font-size: 18px; font-weight: 700; color: white; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

    col_filtro1, col_export = st.columns([4, 1])

    with col_filtro1:
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

    # Total geral para cálculo do %
    total_custo_geral = base["Custo Total"].sum() if "Custo Total" in base.columns else 0

    base["Data Fechamento"] = pd.to_datetime(base["Data Fechamento"]).dt.date

    # --------------------------------------------------
    # ORDENAR POR CUSTO TOTAL (maior → menor)
    # --------------------------------------------------

    if "Custo Total" in base.columns:
        base = base.sort_values("Custo Total", ascending=False)

    with col_export:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        buffer = io.BytesIO()
        base.to_excel(buffer, index=False)
        buffer.seek(0)
        data_ref    = base["Data Fechamento"].max() if not base.empty else "sem_data"
        label_visao = "obsoletos" if visao == "Obsoleto" else "geral"
        st.download_button(
            label="📥 Exportar",
            data=buffer.getvalue(),
            file_name=f"base_historica_{label_visao}_{data_ref}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # --------------------------------------------------
    # MINI CARDS
    # --------------------------------------------------

    custo_filtrado = base["Custo Total"].sum() if "Custo Total" in base.columns else 0
    perc_total     = (custo_filtrado / total_custo_geral * 100) if total_custo_geral > 0 else 0

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    mc1, mc2, _ = st.columns([1, 1, 4])

    mc1.markdown(f"""
    <div class="mini-card">
        <div class="mini-card-title">Custo Total</div>
        <div class="mini-card-value">{moeda_br(custo_filtrado)}</div>
    </div>
    """, unsafe_allow_html=True)

    mc2.markdown(f"""
    <div class="mini-card">
        <div class="mini-card-title">% do Total Obsoleto</div>
        <div class="mini-card-value">{perc_total:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # --------------------------------------------------
    # FORMATA PARA EXIBIÇÃO
    # --------------------------------------------------

    base_display = base.copy()

    if "Vlr Unit" in base_display.columns:
        base_display["Vlr Unit"] = pd.to_numeric(base_display["Vlr Unit"], errors="coerce").apply(
            lambda x: moeda_br(x) if pd.notna(x) else ""
        )

    if "Custo Total" in base_display.columns:
        base_display["Custo Total"] = base_display["Custo Total"].apply(moeda_br)

    if "Ult_Movimentacao" in base_display.columns:
        base_display["Ult_Movimentacao"] = pd.to_datetime(
            base_display["Ult_Movimentacao"], errors="coerce"
        ).apply(lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "")
        base_display = base_display.rename(columns={"Ult_Movimentacao": "Ult Movimento"})

    st.caption(f"{len(base)} produtos")
    st.dataframe(base_display, use_container_width=True, hide_index=True)
