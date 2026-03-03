import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # ==========================================
        # LOCALIZA 02_Estoque_Atual
        # ==========================================

        arquivo_estoque = next(
            (n for n in z.namelist()
             if "02_Estoque_Atual" in n and n.endswith(".xlsx")),
            None
        )

        if not arquivo_estoque:
            raise Exception("Arquivo 02_Estoque_Atual não encontrado no ZIP")

        # ==========================================
        # LEITURA DA ABA DETALHADO
        # ==========================================

        with z.open(arquivo_estoque) as f:
            df_estoque = pd.read_excel(
                f,
                sheet_name="Detalhado",
                dtype={"Código": str},
                engine="openpyxl"
            )

        # ==========================================
        # RENOMEIA COLUNAS PADRÃO
        # ==========================================

        df_estoque = df_estoque.rename(columns={
            "Valor Total": "Custo Total",
            "Código": "Produto",
            "Descrição": "Descricao",
            "Quantidade": "Saldo Atual"
        })

        # ==========================================
        # MONTA EMPRESA / FILIAL (SEM NORMALIZAR)
        # ==========================================

        df_estoque["Empresa"] = df_estoque["Empresa"].astype(str).str.strip()
        df_estoque["Filial"] = df_estoque["Filial"].astype(str).str.strip()

        df_estoque["Empresa / Filial"] = (
            df_estoque["Empresa"] + " / " + df_estoque["Filial"]
        )

        # ==========================================
        # PRODUTO PRESERVANDO ZERO À ESQUERDA
        # ==========================================

        df_estoque["Produto"] = (
            df_estoque["Produto"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )

        # ==========================================
        # ID ÚNICO
        # ==========================================

        df_estoque["ID_UNICO"] = (
            df_estoque["Empresa / Filial"] + "|" + df_estoque["Produto"]
        )

        # ==========================================
        # CONVERSÕES NUMÉRICAS
        # ==========================================

        df_estoque["Saldo Atual"] = pd.to_numeric(
            df_estoque["Saldo Atual"], errors="coerce"
        )

        df_estoque["Custo Total"] = pd.to_numeric(
            df_estoque["Custo Total"], errors="coerce"
        )

        # ==========================================
        # ORGANIZA COLUNAS
        # Empresa / Filial logo após Data Fechamento
        # ==========================================

        colunas = df_estoque.columns.tolist()

        nova_ordem = ["Data Fechamento", "Empresa / Filial"]
        demais = [c for c in colunas if c not in nova_ordem]

        df_final = df_estoque[nova_ordem + demais]

        # ==========================================
        # EXPORTAÇÃO
        # ==========================================

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
