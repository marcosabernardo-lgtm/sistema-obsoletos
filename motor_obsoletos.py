import pandas as pd
import zipfile
import io


# ============================================================
# FILIAIS QUE CALCULAM MOV (SOMENTE CSV)
# ============================================================

EMPRESAS_FILIAL_CONSIDERADAS = {
    "Service / Filial",
    "Robotica / Matriz",
    "Robotica / Filial Jaragua"
}


# ============================================================
# NORMALIZAÇÃO EMPRESA (SOMENTE PARA CSV)
# ============================================================

def normalizar_empresa(nome):
    nome = str(nome).upper()
    if "TOOLS" in nome:
        return "Tools"
    if "MAQUINAS" in nome:
        return "Maquinas"
    if "ALLSERVICE" in nome:
        return "Service"
    if "ROBOTICA" in nome:
        return "Robotica"
    return nome


# ============================================================
# MOTOR PRINCIPAL
# ============================================================

def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =====================================================
        # 1️⃣ ESTOQUE
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
                dtype={"Código": str},
                engine="openpyxl"
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

        df_estoque["Produto"] = (
            df_estoque["Produto"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        df_estoque["ID_UNICO"] = (
            df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
        )

        df_estoque["Saldo Atual"] = pd.to_numeric(
            df_estoque["Saldo Atual"], errors="coerce"
        )

        df_estoque["Custo Total"] = pd.to_numeric(
            df_estoque["Custo Total"], errors="coerce"
        )

        # =====================================================
        # 2️⃣ MOVIMENTAÇÕES CSV
        # =====================================================

        lista_mov = []

        arquivos_csv = [
            n for n in z.namelist()
            if "04_Movimento" in n and n.endswith(".csv")
        ]

        for arq in arquivos_csv:

            with z.open(arq) as f:
                df_temp = pd.read_csv(
                    f,
                    sep=",",
                    encoding="cp1252",
                    skiprows=2,
                    dtype=str
                )

            df_temp.columns = df_temp.columns.str.strip()

            if "Quantidade" not in df_temp.columns or "DT Emissao" not in df_temp.columns:
                continue

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

            if df_temp.empty:
                continue

            try:
                empresa_arquivo = arq.split("_")[1]
            except:
                continue

            empresa_normalizada = normalizar_empresa(empresa_arquivo)

            df_temp["Filial"] = df_temp["Filial"].astype(str).str.title()

            df_temp["Empresa / Filial"] = (
                empresa_normalizada + " / " + df_temp["Filial"]
            )

            df_temp = df_temp[
                df_temp["Empresa / Filial"]
                .isin(EMPRESAS_FILIAL_CONSIDERADAS)
            ]

            if df_temp.empty:
                continue

            df_temp["Produto"] = (
                df_temp["Produto"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

            df_temp["ID_UNICO"] = (
                df_temp["Empresa / Filial"] + "|" + df_temp["Produto"]
            )

            lista_mov.append(
                df_temp[["ID_UNICO", "DT Emissao"]]
            )

        # =====================================================
        # CONSOLIDA
        # =====================================================

        if lista_mov:
            df_mov = pd.concat(lista_mov, ignore_index=True)

            df_mov_cons = (
                df_mov.groupby("ID_UNICO", as_index=False)
                .agg(Ult_Mov=("DT Emissao", "max"))
            )
        else:
            df_mov_cons = pd.DataFrame(columns=["ID_UNICO", "Ult_Mov"])

        # =====================================================
        # MERGE FINAL
        # =====================================================

        df_final = df_estoque.merge(
            df_mov_cons,
            on="ID_UNICO",
            how="left"
        )

        df_final = df_final.drop(columns=["Empresa", "Filial"])

        # 🔎 FILTRO TEMPORÁRIO PARA TESTE (Robotica)
        df_final = df_final[
            df_final["Empresa / Filial"].str.contains("Robotica", na=False)
        ]

        # Organiza ordem
        colunas = df_final.columns.tolist()
        nova_ordem = ["Data Fechamento", "Empresa / Filial"]
        demais = [c for c in colunas if c not in nova_ordem]
        df_final = df_final[nova_ordem + demais]

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
