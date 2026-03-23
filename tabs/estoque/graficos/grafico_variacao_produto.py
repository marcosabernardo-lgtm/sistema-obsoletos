import streamlit as st
import pandas as pd
import io


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

    # CSS
    st.markdown("""
    <style>
    .card-mov { background-color:#005562; border:2px solid #EC6E21; border-radius:10px; padding:14px 16px; text-align:center; }
    .card-mov .titulo { font-size:12px; color:#ccc; margin-bottom:4px; }
    .card-mov .valor  { font-size:20px; font-weight:700; color:white; }
    .card-mov .sub    { font-size:12px; margin-top:4px; }
    </style>
    """, unsafe_allow_html=True)

    def status_mov(row):
        if row["Valor_Comp"] > 0 and row["Valor_Atual"] == 0: return "Zerado"
        if row["Variacao"] < 0:  return "Reduziu"
        if row["Variacao"] > 0:  return "Aumentou"
        return "Manteve"

    def montar_df(df_comp):
        # Mapeamento de descrição considerando as novas chaves
        desc_map = (
            df_hist[df_hist["Descricao"].notna() &
                    (df_hist["Descricao"].astype(str).str.strip() != "") &
                    (df_hist["Descricao"].astype(str) != "0")]
            .groupby(["Empresa / Filial", "Conta", "Tipo de Estoque", "Produto"])["Descricao"].first()
            .to_dict()
        )

        # Agrupamento incluindo Conta e Tipo de Estoque
        grp_atual = df_atual.groupby(["Empresa / Filial", "Conta", "Tipo de Estoque", "Produto"]).agg(
            Valor_Atual=("Custo Total", "sum"),
            Qtd_Atual=("Saldo Atual", "sum")
        ).reset_index()
        
        grp_comp = df_comp.groupby(["Empresa / Filial", "Conta", "Tipo de Estoque", "Produto"]).agg(
            Valor_Comp=("Custo Total", "sum"),
            Qtd_Comp=("Saldo Atual", "sum")
        ).reset_index()
        
        df = grp_atual.merge(grp_comp, on=["Empresa / Filial", "Conta", "Tipo de Estoque", "Produto"], how="outer")
        df[["Valor_Atual","Qtd_Atual","Valor_Comp","Qtd_Comp"]] = df[["Valor_Atual","Qtd_Atual","Valor_Comp","Qtd_Comp"]].fillna(0)
        
        df["Descricao"] = df.apply(
            lambda r: desc_map.get((r["Empresa / Filial"], r["Conta"], r["Tipo de Estoque"], r["Produto"]), "—"), axis=1
        ).astype(str)
        
        df["Variacao"]   = df["Valor_Atual"] - df["Valor_Comp"]
        df["Perc"] = df.apply(
            lambda r: (r["Variacao"] / r["Valor_Comp"] * 100) if r["Valor_Comp"] != 0
            else (100.0 if r["Valor_Atual"] > 0 else 0.0), axis=1
        )
        df["Status Mov"] = df.apply(status_mov, axis=1)
        return df.sort_values("Valor_Atual", ascending=False).reset_index(drop=True)

    def render_cards(df, label_comp, label_atual):
        total_comp   = df["Valor_Comp"].sum()
        total_atual  = df["Valor_Atual"].sum()
        total_aument = df[df["Status Mov"] == "Aumentou"]["Variacao"].sum()
        total_reduz  = df[df["Status Mov"] == "Reduziu"]["Variacao"].abs().sum()
        total_zerado = df[df["Status Mov"] == "Zerado"]["Valor_Comp"].sum()
        qtd_aument   = len(df[df["Status Mov"] == "Aumentou"])
        qtd_reduz    = len(df[df["Status Mov"] == "Reduziu"])
        qtd_zerado   = len(df[df["Status Mov"] == "Zerado"])
        variacao_liq = total_atual - total_comp
        perc_var     = (variacao_liq / total_comp * 100) if total_comp != 0 else 0
        sinal_var    = "+" if variacao_liq >= 0 else ""
        cor_var      = "#ff6b6b" if variacao_liq >= 0 else "#51cf66"

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.markdown(f'<div class="card-mov"><div class="titulo">Estoque {label_atual}</div><div class="valor">{moeda_br(total_atual)}</div><div class="sub" style="color:#ccc">Período atual</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="card-mov"><div class="titulo">⬆ Aumentos ({qtd_aument})</div><div class="valor" style="color:#ff6b6b">+{moeda_br(total_aument)}</div><div class="sub" style="color:#ff6b6b">Entradas</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="card-mov"><div class="titulo">⬇ Reduções ({qtd_reduz})</div><div class="valor" style="color:#51cf66">-{moeda_br(total_reduz)}</div><div class="sub" style="color:#51cf66">Saídas parciais</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="card-mov"><div class="titulo">🚫 Zerados ({qtd_zerado})</div><div class="valor" style="color:#51cf66">-{moeda_br(total_zerado)}</div><div class="sub" style="color:#51cf66">Saídas totais</div></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="card-mov"><div class="titulo">Variação {label_comp}</div><div class="valor" style="color:{cor_var}">{sinal_var}{moeda_br(variacao_liq)}</div><div class="sub" style="color:{cor_var}">{sinal_var}{perc_var:.1f}%</div></div>', unsafe_allow_html=True)
        c6.markdown(f'<div class="card-mov"><div class="titulo">Estoque {label_comp}</div><div class="valor">{moeda_br(total_comp)}</div><div class="sub" style="color:#ccc">Período anterior</div></div>', unsafe_allow_html=True)

    def render_tabela(df, label_comp, key_prefix):
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
        <style>
        div[data-testid="stRadio"] > div { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 10px 16px; }
        div[data-testid="stTextInput"] input, div[data-testid="stTextInput"] > div, div[data-testid="stTextInput"] > div > div { background-color: #005562 !important; }
        div[data-testid="stTextInput"] input { border: 1px solid rgba(250,250,250,0.2) !important; border-radius: 6px !important; color: white !important; padding: 8px 12px !important; }
        div[data-testid="stTextInput"] label { color: rgba(250,250,250,0.6) !important; font-size: 0.75rem !important; font-weight: 400 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
        </style>
        """, unsafe_allow_html=True)
        col_filtro, col_export = st.columns([4, 1])

        with col_filtro:
            status_sel = st.radio("Filtrar por Status Movimento", ["Todos", "Aumentou", "Reduziu", "Zerado", "Manteve"], horizontal=True, key=f"radio_{key_prefix}")

        df_filtrado = df.copy() if status_sel == "Todos" else df[df["Status Mov"] == status_sel].copy()

        tipo = "MoM" if key_prefix == "mom" else "YoY"
        atual_label = pd.Timestamp(data_selecionada).strftime('%y-%b').lower()
        val_label   = f"Valor Estoque {atual_label}"
        qtd_label   = f"Qtd Estoque {atual_label}"
        comp_label  = f"{tipo} {label_comp}"
        qtd_comp_label = f"Qtd {tipo} {label_comp}"
        delta_label = f"Δ {tipo} {label_comp}"
        perc_label  = f"% {tipo}"

        # Seleção das colunas com Conta e Tipo de Estoque após Empresa / Filial
        cols_ordem = [
            "Status Mov", "Empresa / Filial", "Conta", "Tipo de Estoque", 
            "Produto", "Descricao", "Qtd_Atual", "Qtd_Comp", 
            "Valor_Atual", "Valor_Comp", "Variacao", "Perc"
        ]
        
        df_exib = df_filtrado[cols_ordem].copy()
        df_exib = df_exib.rename(columns={
            "Status Mov":  "Status Movimento",
            "Descricao":   "Descrição",
            "Qtd_Atual":   qtd_label,
            "Qtd_Comp":    qtd_comp_label,
            "Valor_Atual": val_label,
            "Valor_Comp":  comp_label,
            "Variacao":    delta_label,
            "Perc":        perc_label,
        })

        for col in [qtd_label, qtd_comp_label]:
            if col in df_exib.columns:
                df_exib[col] = df_exib[col].apply(lambda v: int(round(v)) if isinstance(v, (int,float)) else v)
        for col in [val_label, comp_label, delta_label]:
            if col in df_exib.columns:
                df_exib[col] = df_exib[col].apply(moeda_br)
        if perc_label in df_exib.columns:
            df_exib[perc_label] = df_exib[perc_label].apply(lambda v: f"{v:.1f}%" if isinstance(v, (int,float)) else v)

        col_busca, col_ord, col_dir = st.columns([3, 2, 1])
        with col_busca:
            busca = st.text_input("🔍 PESQUISAR", placeholder="Código, descrição, conta, empresa...", key=f"busca_{key_prefix}")
        with col_ord:
            colunas_ord = list(df_exib.columns)
            ord_col = st.selectbox("📊 Classificar por", colunas_ord, index=0, key=f"ord_col_{key_prefix}")
        with col_dir:
            ord_dir = st.selectbox("↕ Direção", ["⬇ Desc", "⬆ Asc"], key=f"ord_dir_{key_prefix}")

        if busca:
            mask = df_exib.apply(lambda col: col.astype(str).str.contains(busca, case=False, na=False)).any(axis=1)
            df_exib = df_exib[mask]

        ascending = ord_dir == "⬆ Asc"
        try:
            df_exib = df_exib.sort_values(ord_col, ascending=ascending, key=lambda x: pd.to_numeric(x.str.replace(r"[R$\s\.,%+]", "", regex=True).str.replace(",", "."), errors="coerce").fillna(x.astype(str)))
        except Exception:
            pass

        buffer_exp = io.BytesIO()
        df_exib.to_excel(buffer_exp, index=False)
        buffer_exp.seek(0)
        with col_export:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            st.download_button(
                label="📥 Exportar",
                data=buffer_exp,
                file_name=f"variacao_{tipo.lower()}_{atual_label}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"export_top_{key_prefix}",
                use_container_width=True
            )

        st.caption(f"{len(df_exib)} produtos")
        st.dataframe(df_exib, use_container_width=True, hide_index=True)


    # ── ABAS ──────────────────────────────────────────────
    label_atual = data_selecionada.strftime("%d/%m/%Y")

    tab_mom, tab_yoy = st.tabs(["📈 Variação MoM", "📅 Variação YoY"])

    with tab_mom:
        if df_mom is None or (hasattr(df_mom, 'empty') and df_mom.empty):
            st.info("Sem dados do mês anterior.")
        else:
            label_mom = pd.Timestamp(data_mom).strftime("%y-%b").lower()
            df_mom_var = montar_df(df_mom)
            render_cards(df_mom_var, label_mom, label_atual)
            render_tabela(df_mom_var, label_mom, "mom")

    with tab_yoy:
        if df_yoy is None or (hasattr(df_yoy, 'empty') and df_yoy.empty):
            st.info("Sem dados do ano anterior.")
        else:
            label_yoy = pd.Timestamp(data_yoy).strftime("%y-%b").lower()
            df_yoy_var = montar_df(df_yoy)
            render_cards(df_yoy_var, label_yoy, label_atual)
            render_tabela(df_yoy_var, label_yoy, "yoy")