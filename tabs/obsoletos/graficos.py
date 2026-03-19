import streamlit as st
import pandas as pd


def render(df_filtrado, moeda_br):

    datas = sorted(df_filtrado["Data Fechamento"].unique())
    ultima_data = max(datas)
    base = df_filtrado[df_filtrado["Data Fechamento"] == ultima_data]

    # MoM — fechamento anterior
    idx = list(datas).index(ultima_data)
    if idx > 0:
        data_mom = datas[idx - 1]
        base_mom = df_filtrado[df_filtrado["Data Fechamento"] == data_mom]
        label_mom = pd.Timestamp(data_mom).strftime('%y-%b').lower()
    else:
        base_mom = pd.DataFrame()
        label_mom = "n/d"

    css = (
        "<style>.tb-obs{width:100%;border-collapse:collapse;font-size:13px;color:white}"
        ".tb-obs th{background:#0f5a60;padding:10px 12px;text-align:left;border-bottom:2px solid #EC6E21;font-weight:700}"
        ".tb-obs th:not(:first-child){text-align:right}"
        ".tb-obs td{padding:7px 12px;border-bottom:1px solid #1a6e75;background:#005562;color:white}"
        ".tb-obs td:not(:first-child){text-align:right}"
        ".tb-obs tr:last-child td{font-weight:700;border-top:2px solid #EC6E21}"
        ".tb-obs tr:hover td{background:#0a6570}</style>"
    )

    def icone_mom(v):
        if v > 1:    return f'<span style="color:#ff6b6b;font-weight:700">🔴 ⬆ {abs(v):.1f}%</span>'
        elif v < -1: return f'<span style="color:#51cf66;font-weight:700">🟢 ⬇ {abs(v):.1f}%</span>'
        return f'<span style="color:#f0a500;font-weight:700">🟡 ● {abs(v):.1f}%</span>'

    def montar_tabela(df_atual, df_comp, col_nome):
        total_atual = df_atual["Custo Total"].sum()

        if not df_comp.empty:
            df_mom_grp = df_comp.groupby(col_nome)["Custo Total"].sum().reset_index().rename(columns={"Custo Total": "Valor MoM"})
            df_merged = df_atual.merge(df_mom_grp, on=col_nome, how="left")
            df_merged["Valor MoM"] = df_merged["Valor MoM"].fillna(0)
        else:
            df_merged = df_atual.copy()
            df_merged["Valor MoM"] = 0

        df_merged["Variacao"] = df_merged["Custo Total"] - df_merged["Valor MoM"]
        df_merged["Perc MoM"] = df_merged.apply(
            lambda r: (r["Variacao"] / r["Valor MoM"] * 100) if r["Valor MoM"] != 0 else 0, axis=1
        )

        total_mom     = df_merged["Valor MoM"].sum()
        total_var     = df_merged["Variacao"].sum()
        total_perc    = ((total_atual - total_mom) / total_mom * 100) if total_mom != 0 else 0

        linhas = ""
        for _, row in df_merged.iterrows():
            perc_obs = row["Custo Total"] / total_atual * 100 if total_atual > 0 else 0
            var_html = f'<span style="color:#ff6b6b">+{moeda_br(abs(row["Variacao"]))}</span>' if row["Variacao"] > 0 else f'<span style="color:#51cf66">-{moeda_br(abs(row["Variacao"]))}</span>' if row["Variacao"] < 0 else moeda_br(0)
            linhas += (
                f"<tr>"
                f"<td>{row[col_nome]}</td>"
                f"<td>{moeda_br(row['Custo Total'])}</td>"
                f"<td>{perc_obs:.1f}%</td>"
                f"<td>{moeda_br(row['Valor MoM']) if row['Valor MoM'] != 0 else '—'}</td>"
                f"<td>{var_html}</td>"
                f"<td>{icone_mom(row['Perc MoM'])}</td>"
                f"</tr>"
            )

        # Total
        var_total_html = f'<span style="color:#ff6b6b">+{moeda_br(abs(total_var))}</span>' if total_var > 0 else f'<span style="color:#51cf66">-{moeda_br(abs(total_var))}</span>' if total_var < 0 else moeda_br(0)
        linhas += (
            f"<tr>"
            f"<td>Total</td>"
            f"<td>{moeda_br(total_atual)}</td>"
            f"<td>100%</td>"
            f"<td>{moeda_br(total_mom) if total_mom != 0 else '—'}</td>"
            f"<td>{var_total_html}</td>"
            f"<td>{icone_mom(total_perc)}</td>"
            f"</tr>"
        )

        st.markdown(
            css + f"<table class='tb-obs'><thead><tr>"
            f"<th>{col_nome}</th>"
            f"<th style='text-align:right'>Valor Obsoleto</th>"
            f"<th style='text-align:right'>% Obsoleto</th>"
            f"<th style='text-align:right'>MoM {label_mom}</th>"
            f"<th style='text-align:right'>Δ MoM</th>"
            f"<th style='text-align:right'>% MoM</th>"
            f"</tr></thead><tbody>{linhas}</tbody></table>",
            unsafe_allow_html=True
        )

    tab1, tab2, tab3 = st.tabs([
        "🏢 Por Empresa / Filial",
        "📋 Por Status do Movimento",
        "📦 Por Conta"
    ])

    with tab1:
        df_emp = base.groupby("Empresa / Filial").agg(**{"Custo Total": ("Custo Total", "sum")}).reset_index().sort_values("Custo Total", ascending=False)
        df_emp_mom = base_mom.groupby("Empresa / Filial").agg(**{"Custo Total": ("Custo Total", "sum")}).reset_index() if not base_mom.empty else pd.DataFrame()
        montar_tabela(df_emp, df_emp_mom, "Empresa / Filial")

    with tab2:
        df_status = base.groupby("Status do Movimento").agg(**{"Custo Total": ("Custo Total", "sum")}).reset_index().sort_values("Custo Total", ascending=False)
        df_status_mom = base_mom.groupby("Status do Movimento").agg(**{"Custo Total": ("Custo Total", "sum")}).reset_index() if not base_mom.empty else pd.DataFrame()
        montar_tabela(df_status, df_status_mom, "Status do Movimento")

    with tab3:
        df_conta = base.groupby("Conta").agg(**{"Custo Total": ("Custo Total", "sum")}).reset_index().sort_values("Custo Total", ascending=False)
        df_conta_mom = base_mom.groupby("Conta").agg(**{"Custo Total": ("Custo Total", "sum")}).reset_index() if not base_mom.empty else pd.DataFrame()
        montar_tabela(df_conta, df_conta_mom, "Conta")
