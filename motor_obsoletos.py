import pandas as pd
import numpy as np
import zipfile
import io
from dateutil.relativedelta import relativedelta


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "TOOLS" in nome: return "Tools"
    if "MAQUINAS" in nome: return "Maquinas"
    if "ALLSERVICE" in nome: return "Service"
    if "ROBOTICA" in nome: return "Robotica"
    return nome


def criar_id_unico(df):
    df["Produto"] = (
        df["Produto"]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.zfill(6)
    )
    df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["Produto"]
    return df


# ============================================================
# MOTOR PRINCIPAL
# ============================================================

def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =====================================================
        # 1️⃣ ESTOQUE ATUAL
        # =====================================================

        arquivo_estoque = next(
            (n for n in z.namelist()
             if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_estoque:
            raise Exception("02_Estoque_Atual não encontrado")

        with z.open(arquivo_estoque) as f:
            df_estoque = pd.read_excel(
                f,
                sheet_name="Detalhado",
                dtype={"Código": str}
            )

        df_estoque = df_estoque.rename(columns={
            "Valor Total": "Custo Total",
            "Código": "Produto",
            "Descrição": "Descricao",
            "Quantidade": "Saldo Atual"
        })

        df_estoque["Empresa"] = df_estoque["Empresa"].apply(normalizar_empresa)
        df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.title()
        df_estoque["Empresa / Filial"] = (
            df_estoque["Empresa"] + " / " + df_estoque["Filial"]
        )

        df_estoque = criar_id_unico(df_estoque)

        df_estoque["Data_Base"] = pd.to_datetime(
            df_estoque["Data Fechamento"],
            dayfirst=True,
            errors="coerce"
        ).max()

        DataBase = df_estoque["Data_Base"].iloc[0]

        df_estoque["Saldo Atual"] = pd.to_numeric(
            df_estoque["Saldo Atual"], errors="coerce"
        )

        df_estoque["Custo Total"] = pd.to_numeric(
            df_estoque["Custo Total"], errors="coerce"
        )

        # =====================================================
        # 2️⃣ MOVIMENTAÇÕES CSV (04_Movimento)
        # =====================================================

        arquivos_csv = [
            n for n in z.namelist()
            if "04_Movimento" in n and n.endswith(".csv")
        ]

        lista_mov = []

        for arq in arquivos_csv:
            with z.open(arq) as f:
                df_temp = pd.read_csv(
                    f,
                    sep=",",
                    encoding="cp1252",
                    skiprows=2,
                    dtype=str
                )

            df_temp["Quantidade"] = pd.to_numeric(
                df_temp["Quantidade"], errors="coerce"
            )

            df_temp["DT Emissao"] = pd.to_datetime(
                df_temp["DT Emissao"],
                dayfirst=True,
                errors="coerce"
            )

            df_temp = df_temp[
                (df_temp["Quantidade"] != 0) &
                (df_temp["DT Emissao"].notna())
            ]

            empresa_arquivo = arq.split("_")[1]
            df_temp["Empresa"] = normalizar_empresa(empresa_arquivo)
            df_temp["Filial"] = df_temp["Filial"].astype(str).str.title()
            df_temp["Empresa / Filial"] = (
                df_temp["Empresa"] + " / " + df_temp["Filial"]
            )

            df_temp = criar_id_unico(df_temp)

            lista_mov.append(df_temp[
                ["ID_UNICO", "DT Emissao"]
            ])

        df_mov = (
            pd.concat(lista_mov)
            if lista_mov else
            pd.DataFrame(columns=["ID_UNICO", "DT Emissao"])
        )

        # =====================================================
        # 3️⃣ CONSOLIDA ÚLTIMO MOVIMENTO
        # =====================================================

        if not df_mov.empty:
            df_mov_cons = (
                df_mov.groupby("ID_UNICO", as_index=False)
                .agg(Ult_Mov=("DT Emissao", "max"))
            )
        else:
            df_mov_cons = pd.DataFrame(
                columns=["ID_UNICO", "Ult_Mov"]
            )

        # =====================================================
        # 4️⃣ MERGE FINAL
        # =====================================================

        df_final = df_estoque.merge(
            df_mov_cons,
            on="ID_UNICO",
            how="left"
        )

        # =====================================================
        # 5️⃣ CÁLCULOS DE OBSOLESCÊNCIA
        # =====================================================

        df_final["Dias Sem Mov"] = (
            DataBase - df_final["Ult_Mov"]
        ).dt.days

        df_final["Meses Ult Mov"] = np.where(
            df_final["Ult_Mov"].notna(),
            (DataBase.year - df_final["Ult_Mov"].dt.year) * 12 +
            (DataBase.month - df_final["Ult_Mov"].dt.month),
            np.nan
        )

        def status_mov(meses):
            if pd.isna(meses): return "Sem Movimento"
            if meses <= 6: return "Até 6 meses"
            if meses <= 12: return "Até 1 ano"
            if meses <= 24: return "Até 2 anos"
            return "+ 2 anos"

        df_final["Status do Movimento"] = (
            df_final["Meses Ult Mov"]
            .apply(status_mov)
        )

        df_final["Status Estoque"] = np.where(
            df_final["Meses Ult Mov"] > 6,
            "Obsoleto",
            "Até 6 meses"
        )

        def formatar(data):
            if pd.isna(data):
                return "Sem movimento"
            delta = relativedelta(DataBase, data)
            return f"{delta.years}a {delta.months}m {delta.days}d"

        df_final["Ano Meses Dias"] = (
            df_final["Ult_Mov"]
            .apply(formatar)
        )

        # =====================================================
        # 6️⃣ EXPORTAÇÃO
        # =====================================================

        df_export = df_final.sort_values(
            by=["Status Estoque", "Meses Ult Mov"],
            ascending=[False, False]
        )

        buffer = io.BytesIO()
        df_export.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
