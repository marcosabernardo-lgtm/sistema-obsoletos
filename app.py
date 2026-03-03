import pandas as pd
import numpy as np
import zipfile
import io


# ============================================================
# FILIAIS QUE USAM MOV. INTERNA (CSV)
# ============================================================

EMPRESAS_MOV_INTERNA = {
    "Service / Filial",
    "Robotica / Matriz",
    "Robotica / Filial Jaragua"
}


# ============================================================
# NORMALIZAÇÃO — usada APENAS no CSV (04_Movimento)
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
        df_estoque["Empresa / Filial"] = df_estoque["Empresa"] + " / " + df_estoque["Filial"]
        df_estoque["Produto"] = df_estoque["Produto"].astype(str).str.strip().str.upper()
        df_estoque["ID_UNICO"] = df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]

        data_base = pd.to_datetime(
            df_estoque["Data Fechamento"], dayfirst=True, errors="coerce"
        ).max()

        df_estoque["Saldo Atual"] = pd.to_numeric(df_estoque["Saldo Atual"], errors="coerce")
        df_estoque["Custo Total"] = pd.to_numeric(df_estoque["Custo Total"], errors="coerce")

        # =====================================================
        # 2️⃣ MOVIMENTAÇÕES CSV — apenas empresas filtradas
        # =====================================================

        lista_mov = []

        arquivos_csv = [
            n for n in z.namelist()
            if "04_Movimento" in n and n.endswith(".csv")
        ]

        for arq in arquivos_csv:
            with z.open(arq) as f:
                df_temp = pd.read_csv(
                    f, sep=",", encoding="cp1252",
                    skiprows=2, dtype=str
                )

            df_temp.columns = df_temp.columns.str.strip()

            if "Quantidade" not in df_temp.columns or "DT Emissao" not in df_temp.columns:
                continue

            df_temp["Quantidade"] = pd.to_numeric(df_temp["Quantidade"], errors="coerce")
            df_temp["DT Emissao"] = pd.to_datetime(df_temp["DT Emissao"], dayfirst=True, errors="coerce")

            df_temp = df_temp[
                (df_temp["Quantidade"] != 0) & (df_temp["DT Emissao"].notna())
            ]

            if df_temp.empty:
                continue

            try:
                empresa_arquivo = arq.split("_")[1]
            except:
                continue

            empresa_normalizada = normalizar_empresa(empresa_arquivo)
            df_temp["Filial"] = df_temp["Filial"].astype(str).str.title()
            df_temp["Empresa / Filial"] = empresa_normalizada + " / " + df_temp["Filial"]

            # Filtro: apenas as 3 empresas de Mov. Interna
            df_temp = df_temp[df_temp["Empresa / Filial"].isin(EMPRESAS_MOV_INTERNA)]

            if df_temp.empty:
                continue

            df_temp["Produto"] = df_temp["Produto"].astype(str).str.strip().str.upper()
            df_temp["ID_UNICO"] = df_temp["Empresa / Filial"] + "|" + df_temp["Produto"]
            df_temp["Tipo Movimento"] = "Mov. Interna"

            lista_mov.append(df_temp[["ID_UNICO", "DT Emissao", "Tipo Movimento"]])

        # =====================================================
        # 3️⃣ ENTRADAS / SAÍDAS (Excel) — TODAS AS EMPRESAS
        # Empresa / Filial resolvida via 05_Empresas.xlsx
        # =====================================================

        arquivo_matriz = next(
            (n for n in z.namelist()
             if "05_Empresas" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_matriz:
            raise Exception("05_Empresas não encontrado")

        with z.open(arquivo_matriz) as f:
            df_matriz = pd.read_excel(f, dtype=str, engine="openpyxl")

        lista_exc = []

        arquivos_exc = [
            n for n in z.namelist()
            if "01_Entradas_Saidas" in n and n.endswith(".xlsx")
        ]

        for arq in arquivos_exc:

            # Extrai empresa do nome do arquivo: "01_Tools.xlsx" → "Tools"
            nome_arquivo = arq.split("/")[-1]
            try:
                empresa = nome_arquivo.split("_")[1].replace(".xlsx", "")
            except:
                continue

            for aba, tipo in [("ENTRADA", "Entrada"), ("SAIDA", "Saida")]:

                with z.open(arq) as f:
                    xl = pd.ExcelFile(f, engine="openpyxl")

                if aba not in xl.sheet_names:
                    continue

                with z.open(arq) as f:
                    df = pd.read_excel(
                        f, sheet_name=aba,
                        dtype=str, engine="openpyxl"
                    )

                df.columns = [str(c).upper().strip() for c in df.columns]

                colunas_necessarias = {"FILIAL", "PRODUTO", "DIGITACAO", "ESTOQUE", "QUANTIDADE"}
                if not colunas_necessarias.issubset(df.columns):
                    continue

                df = df[["FILIAL", "PRODUTO", "DIGITACAO", "ESTOQUE", "QUANTIDADE"]].copy()
                df["Tipo Movimento"] = tipo

                # Trata número brasileiro (1.234,56 → 1234.56)
                df["QUANTIDADE"] = (
                    df["QUANTIDADE"]
                    .astype(str)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                df["QUANTIDADE"] = pd.to_numeric(df["QUANTIDADE"], errors="coerce")
                df["DIGITACAO"] = pd.to_datetime(df["DIGITACAO"], errors="coerce")

                df = df[
                    (df["ESTOQUE"] == "S") &
                    (df["QUANTIDADE"] != 0) &
                    (df["DIGITACAO"].notna())
                ]

                if df.empty:
                    continue

                # Monta Mesclado: "Tools 00", "Service 01" etc.
                df["FILIAL"] = df["FILIAL"].astype(str).str.strip()
                df["Mesclado"] = empresa + " " + df["FILIAL"]

                # Resolve Empresa / Filial via matriz
                df = df.merge(
                    df_matriz[["Mesclado", "Empresa / Filial"]],
                    on="Mesclado", how="left"
                )
                df["Empresa / Filial"] = df["Empresa / Filial"].fillna("N/D")

                df["PRODUTO"] = df["PRODUTO"].astype(str).str.strip().str.upper()
                df["ID_UNICO"] = df["Empresa / Filial"] + "|" + df["PRODUTO"]

                df = df.rename(columns={
                    "PRODUTO":    "Produto",
                    "DIGITACAO":  "DT Emissao",
                    "QUANTIDADE": "Qtde"
                })

                lista_exc.append(
                    df[["ID_UNICO", "DT Emissao", "Tipo Movimento"]]
                )

        # =====================================================
        # 4️⃣ CONSOLIDA TODAS AS MOVIMENTAÇÕES
        # lista_mov = Mov. Interna (CSV, 3 empresas filtradas)
        # lista_exc = Entrada / Saída (Excel, todas empresas)
        # =====================================================

        todos = lista_mov + lista_exc

        if todos:
            df_mestra = pd.concat(todos, ignore_index=True)

            df_mestra["DtEnt"] = df_mestra["DT Emissao"].where(df_mestra["Tipo Movimento"] == "Entrada")
            df_mestra["DtSai"] = df_mestra["DT Emissao"].where(df_mestra["Tipo Movimento"] == "Saida")
            df_mestra["DtInt"] = df_mestra["DT Emissao"].where(df_mestra["Tipo Movimento"] == "Mov. Interna")

            df_cons = df_mestra.groupby("ID_UNICO", as_index=False).agg(
                Ult_Entrada=("DtEnt", "max"),
                Ult_Saida=("DtSai", "max"),
                Ult_Mov_Interna=("DtInt", "max"),
            )

            df_cons = df_cons.rename(columns={
                "Ult_Entrada":    "Ult. Entrada",
                "Ult_Saida":      "Ult. Saida",
                "Ult_Mov_Interna":"Ult. Mov. Interna",
            })

        else:
            df_cons = pd.DataFrame(
                columns=["ID_UNICO", "Ult. Entrada", "Ult. Saida", "Ult. Mov. Interna"]
            )

        # =====================================================
        # 5️⃣ MERGE FINAL + CÁLCULOS
        # =====================================================

        df_final = df_estoque.merge(
            df_cons[["ID_UNICO", "Ult. Entrada", "Ult. Saida", "Ult. Mov. Interna"]],
            on="ID_UNICO",
            how="left"
        )

        # Ult Mov = máximo das 3 colunas
        df_final["Ult Mov"] = df_final[
            ["Ult. Entrada", "Ult. Saida", "Ult. Mov. Interna"]
        ].max(axis=1)

        # Dias e meses sem movimento
        df_final["Dias Sem Mov"] = (
            (data_base - df_final["Ult Mov"]).dt.days
        ).fillna(9999)

        df_final["Meses Ult Mov"] = np.where(
            df_final["Ult Mov"].notna(),
            (data_base.year - df_final["Ult Mov"].dt.year) * 12
            + (data_base.month - df_final["Ult Mov"].dt.month),
            np.nan
        )

        # Status Estoque
        df_final["Status Estoque"] = np.where(
            df_final["Tipo de Estoque"] == "EM FABRICACAO",
            "Até 6 meses",
            np.where(df_final["Dias Sem Mov"] > 180, "Obsoleto", "Até 6 meses")
        )

        # Status do Movimento
        def status_mov(row):
            if row["Tipo de Estoque"] == "EM FABRICACAO":
                return "Até 6 meses"
            if pd.isna(row["Meses Ult Mov"]):
                return "Sem Movimento"
            if row["Meses Ult Mov"] <= 6:
                return "Até 6 meses"
            if row["Meses Ult Mov"] <= 12:
                return "Até 1 ano"
            if row["Meses Ult Mov"] <= 24:
                return "Até 2 anos"
            return "+ 2 anos"

        df_final["Status do Movimento"] = df_final.apply(status_mov, axis=1)

        # Texto legível
        def formatar_tempo(row):
            if row["Tipo de Estoque"] == "EM FABRICACAO":
                return "Em fabricação"
            if pd.isna(row["Ult Mov"]):
                return "Sem movimento"
            dias = (data_base - row["Ult Mov"]).days
            anos = dias // 365
            meses = (dias % 365) // 30
            dias_rest = (dias % 365) % 30
            return f"{anos} anos {meses} meses {dias_rest} dias"

        df_final["Ano Meses Dias"] = df_final.apply(formatar_tempo, axis=1)

        # Colunas finais
        df_export = df_final[[
            "Empresa / Filial", "Conta", "Tipo de Estoque", "Produto",
            "Descricao", "Saldo Atual", "Custo Total",
            "Ult. Entrada", "Ult. Saida", "Ult. Mov. Interna",
            "Ult Mov", "Meses Ult Mov", "Ano Meses Dias",
            "Status Estoque", "Status do Movimento"
        ]].copy()

        df_export = df_export.sort_values(
            by=["Status Estoque", "Meses Ult Mov"],
            ascending=[False, False]
        )

        buffer = io.BytesIO()
        df_export.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_export, buffer.getvalue()
