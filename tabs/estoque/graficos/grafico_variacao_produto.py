import streamlit as st
import pandas as pd


def render(df_hist, moeda_br, data_selecionada):

    if data_selecionada is None:
        st.warning("Selecione uma data de fechamento.")
        return

    df_atual = df_hist[df_hist["Data Fechamento"] == data_selecionada].copy()
    datas_sorted = sorted(df_hist["Data Fechamento"].unique())
    idx = list(datas_sorted).index(data_selecionada) if data_selecionada in datas_sorted else -1

    # MoM
    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)
        data_mom = None

    # YoY
    data_yoy_alvo = pd.Timestamp(data_selecionada) - pd.DateOffset(years=1)
    datas_yoy = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
    if datas_yoy:
        data_yoy = min(datas_yoy, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
        df_yoy = df_hist[df_hist["Data Fechamento"] == data_yoy].copy()
    else:
        df_yoy = pd.DataFrame(columns=df_hist.columns)
        data_yoy = None

    # CSS cards
    st.markdown("""
    <style>
    .card-mov { background-color:#005562; border:2px solid #EC6E21; border-radius:10px; padding:14px 16px; text-align:center; }
    .card-mov .titulo { font-size:12px; color:#ccc; margin-bottom:4px; }
    .card-mov .valor  { font-size:20px; font-weight:700; color:white; }
    .card-mov .sub    { font-size:12px; margin-top:4px; }
    .filtro-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 12px 20px 4px; margin-bottom: 16px; }
    </style>
    """, unsafe_allow_html=True)

    # Helper descrição
    desc_map = (
        df_hist[df_hist["Descricao"].notna() &
                (df_hist["Descricao"].astype(str).str.strip() != "") &
                (df_hist["Descricao"].astype(str) != "0")]
        .groupby("Produto")["Descricao"].first().to_dict()
    )

    def status_mov(row):
        if row["Valor_Comp"] > 0 and row["Valor_Atual"] == 0: return "Zerado"
        if row["Variacao"] < 0:  return "Reduziu"
        if row["Variacao"] > 0:  return "Aumentou"
        return "Manteve"

    def montar_df(df_comp):
        grp_atual = df_atual.groupby(["Empresa / Filial", "Conta", "Produto"]).agg(
            Valor_Atual=("Custo Total", "sum")
        ).reset_index()

        grp_comp = df_comp.groupby("Produto").agg(
            Valor_Comp=("Custo Total", "sum")
        ).reset_index()

        df = grp_atual.merge(grp_comp, on="Produto", how="outer").fillna(0)
        df["Descricao"]  = df["Produto"].map(desc_map).fillna("—").astype(str)
        df["Variacao"]   = df["Valor_Atual"] - df["Valor_Comp"]
        df["Perc"]       = df.apply(lambda r: (r["Variacao"] / r["Valor_Comp"] * 100) if r["Valor_Comp"] != 0 else 0, axis=1)
        df["Status Mov"] = df.apply(status_mov, axis=1)
        return df.sort_values("Variacao", key=abs, ascending=False).reset_index(drop=True)

    def render_cards(df, label_comp, label_atual):
        total_comp   = df["Valor_Comp"].sum()
        total_atual  = df["Valor_Atual"].sum()
        total_aument = df[df["Status Mov"] == "Aumentou"]["Variacao"].sum()
        total_reduz  = df[df["Status Mov"] == "Reduziu"]["Variacao"].abs().sum()
        total_zerado = df[df["Status Mov"] == "Zerado"]["Valor_Comp"].sum()
        qtd_aument   = len(df[df["Status Mov"] == "Aumentou"])
        qtd_reduz    = len(df[df["Status Mov"] == "Reduziu"])
        qtd_zerado   = len(df[df["Status Mov"] == "Zerado"])

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(f'<div class="card-mov"><div class="titulo">Estoque {label_comp}</div><div class="valor">{moeda_br(total_comp)}</div><div class="sub" style="color:#ccc">Período anterior</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="card-mov"><div class="titulo">⬆ Aumentos ({qtd_aument})</div><div class="valor" style="color:#ff6b6b">+{moeda_br(total_aument)}</div><div class="sub" style="color:#ff6b6b">Entradas</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="card-mov"><div class="titulo">⬇ Reduções ({qtd_reduz})</div><div class="valor" style="color:#51cf66">-{moeda_br(total_reduz)}</div><div class="sub" style="color:#51cf66">Saídas parciais</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="card-mov"><div class="titulo">🚫 Zerados ({qtd_zerado})</div><div class="valor" style="color:#51cf66">-{moeda_br(total_zerado)}</div><div class="sub" style="color:#51cf66">Saídas totais</div></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="card-mov"><div class="titulo">Estoque {label_atual}</div><div class="valor">{moeda_br(total_atual)}</div><div class="sub" style="color:#ccc">Período atual</div></div>', unsafe_allow_html=True)

    def render_tabela(df, label_comp, key_prefix):
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown('<div class="filtro-card">', unsafe_allow_html=True)
        status_sel = st.radio(
            "Filtrar por Status Mov",
            ["Todos", "Aumentou", "Reduziu", "Zerado", "Manteve"],
            horizontal=True,
            key=f"radio_{key_prefix}"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        df_filtrado = df.copy() if status_sel == "Todos" else df[df["Status Mov"] == status_sel].copy()

        # Monta tabela para exibição
        df_exib = df_filtrado[[
            "Status Mov", "Empresa / Filial", "Conta", "Produto", "Descricao",
            "Valor_Atual", "Valor_Comp", "Variacao", "Perc"
        ]].copy()

        df_exib["Valor Atual"]       = df_exib["Valor_Atual"].apply(moeda_br)
        df_exib[f"Valor {label_comp}"] = df_exib["Valor_Comp"].apply(moeda_br)
        df_exib[f"Δ {label_comp}"]   = df_exib["Variacao"].apply(lambda v: f"+{moeda_br(abs(v))}" if v > 0 else f"-{moeda_br(abs(v))}" if v < 0 else moeda_br(0))
        df_exib[f"% {label_comp}"]   = df_exib["Perc"].apply(lambda v: f"+{v:.1f}%" if v > 0 else f"{v:.1f}%")

        df_exib = df_exib.drop(columns=["Valor_Atual", "Valor_Comp", "Variacao", "Perc"])
        df_exib = df_exib.rename(columns={"Descricao": "Descrição"})

        st.caption(f"{len(df_filtrado)} produtos")
        st.dataframe(df_exib, use_container_width=True, hide_index=True)

    # ── ABAS ──────────────────────────────────────────────
    label_atual = data_selecionada.strftime("%d/%m/%Y")

    tab_mom, tab_yoy = st.tabs(["📈 Variação MoM", "📅 Variação YoY"])

    with tab_mom:
        if df_mom.empty:
            st.info("Sem dados do mês anterior.")
        else:
            label_mom = pd.Timestamp(data_mom).strftime("%d/%m/%Y")
            df_mom_var = montar_df(df_mom)
            render_cards(df_mom_var, label_mom, label_atual)
            render_tabela(df_mom_var, label_mom, "mom")

    with tab_yoy:
        if df_yoy.empty:
            st.info("Sem dados do ano anterior.")
        else:
            label_yoy = pd.Timestamp(data_yoy).strftime("%d/%m/%Y")
            df_yoy_var = montar_df(df_yoy)
            render_cards(df_yoy_var, label_yoy, label_atual)
            render_tabela(df_yoy_var, label_yoy, "yoy")
