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

    if idx > 0:
        data_mom = datas_sorted[idx - 1]
        df_mom = df_hist[df_hist["Data Fechamento"] == data_mom].copy()
    else:
        df_mom = pd.DataFrame(columns=df_hist.columns)

    data_yoy_alvo = pd.Timestamp(data_selecionada) - pd.DateOffset(years=1)
    datas_yoy = [d for d in datas_sorted if abs((pd.Timestamp(d) - data_yoy_alvo).days) <= 31]
    if datas_yoy:
        data_yoy = min(datas_yoy, key=lambda d: abs((pd.Timestamp(d) - data_yoy_alvo).days))
        df_yoy = df_hist[df_hist["Data Fechamento"] == data_yoy].copy()
    else:
        df_yoy = pd.DataFrame(columns=df_hist.columns)

    top_n = st.slider("Quantidade de produtos", min_value=5, max_value=50, value=10, step=5)

    sub1, sub2, sub3 = st.tabs(["💰 Maior Valor em Estoque", "📈 Maior Variação MoM", "📅 Maior Variação YoY"])

    total_estoque = df_atual["Custo Total"].sum()

    desc_map = (
        df_hist[df_hist["Descricao"].notna() & (df_hist["Descricao"].astype(str).str.strip() != "") & (df_hist["Descricao"].astype(str) != "0")]
        .groupby("Produto")["Descricao"].first().to_dict()
    )

    def get_desc(produto):
        return str(desc_map.get(str(produto), "—"))

    def tabela_variacao(df_base, df_comp, label_comp, tipo="MoM"):
        if df_comp.empty:
            st.info(f"Sem dados de {label_comp} para calcular variação.")
            return

        grp_atual = df_base.groupby(["Empresa / Filial", "Conta", "Produto"]).agg(Valor_Atual=("Custo Total", "sum")).reset_index()
        grp_comp  = df_comp.groupby(["Produto"]).agg(Valor_Comp=("Custo Total", "sum")).reset_index()

        df_var = grp_atual.merge(grp_comp, on="Produto", how="outer").fillna(0)
        df_var["Descricao"] = df_var["Produto"].apply(get_desc)
        df_var["Variacao"]  = df_var["Valor_Atual"] - df_var["Valor_Comp"]
        df_var["% Var"]     = df_var.apply(lambda r: (r["Variacao"] / r["Valor_Comp"] * 100) if r["Valor_Comp"] != 0 else 0, axis=1)

        atual_label = pd.Timestamp(data_selecionada).strftime('%y-%b').lower()
        val_label   = f"Valor Estoque {atual_label}"
        delta_label = f"Δ {tipo} {label_comp}"
        perc_label  = f"% {tipo}"

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**⬆ Maiores Altas**")
            df_alta = df_var.sort_values("Variacao", ascending=False).head(top_n)[["Produto", "Descricao", "Valor_Atual", "Variacao", "% Var"]].copy()
            df_alta.columns = ["Produto", "Descrição", val_label, delta_label, perc_label]
            st.dataframe(df_alta, use_container_width=True, hide_index=True)

        with col2:
            st.markdown("**⬇ Maiores Quedas**")
            df_queda = df_var.sort_values("Variacao", ascending=True).head(top_n)[["Produto", "Descricao", "Valor_Atual", "Variacao", "% Var"]].copy()
            df_queda.columns = ["Produto", "Descrição", val_label, delta_label, perc_label]
            st.dataframe(df_queda, use_container_width=True, hide_index=True)

    # ABA 1
    with sub1:
        df_valor = (
            df_atual.groupby(["Empresa / Filial", "Conta", "Produto"])
            .agg(Qtd=("Saldo Atual", "sum"), Valor=("Custo Total", "sum"))
            .reset_index()
            .sort_values("Valor", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )
        df_valor["Descrição"] = df_valor["Produto"].apply(get_desc)
        df_valor["% Estoque"] = df_valor["Valor"].apply(lambda x: round(x / total_estoque * 100, 1) if total_estoque > 0 else 0)

        atual_label = pd.Timestamp(data_selecionada).strftime('%y-%b').lower()
        df_exib = df_valor[["Empresa / Filial", "Conta", "Produto", "Descrição", "Qtd", "Valor", "% Estoque"]].copy()
        df_exib = df_exib.rename(columns={"Valor": f"Valor Estoque {atual_label}"})

        st.dataframe(df_exib, use_container_width=True, hide_index=True)

        buffer = io.BytesIO()
        df_exib.to_excel(buffer, index=False)
        buffer.seek(0)
        st.download_button("📥 Exportar Excel", data=buffer, file_name="top_produtos_valor.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ABA 2
    with sub2:
        label_mom = pd.Timestamp(data_mom).strftime('%y-%b').lower() if not df_mom.empty else "mês anterior"
        tabela_variacao(df_atual, df_mom, label_mom, tipo="MoM")

    # ABA 3
    with sub3:
        label_yoy = pd.Timestamp(data_yoy).strftime('%y-%b').lower() if not df_yoy.empty else "ano anterior"
        tabela_variacao(df_atual, df_yoy, label_yoy, tipo="YoY")
