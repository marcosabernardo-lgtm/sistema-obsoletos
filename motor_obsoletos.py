import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        caminho_robotica = "04_Movimento/05_Robotica.csv"

        if caminho_robotica not in z.namelist():
            df_erro = pd.DataFrame({"Erro": ["Arquivo 05_Robotica.csv não encontrado"]})
            buffer = io.BytesIO()
            df_erro.to_excel(buffer, index=False)
            buffer.seek(0)
            return df_erro, buffer.getvalue()

        # 🔥 LEITURA CORRETA COM SEPARADOR ;
        with z.open(caminho_robotica) as f:
            df = pd.read_csv(
                f,
                sep=";",              # ← CORREÇÃO PRINCIPAL
                encoding="cp1252",
                skiprows=2,
                dtype=str
            )

        # Remove espaços invisíveis dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Garantia das colunas esperadas
        colunas_necessarias = [
            "Filial",
            "Produto",
            "Quantidade",
            "DT Emissao"
        ]

        for col in colunas_necessarias:
            if col not in df.columns:
                df_erro = pd.DataFrame({"Erro": [f"Coluna não encontrada: {col}"]})
                buffer = io.BytesIO()
                df_erro.to_excel(buffer, index=False)
                buffer.seek(0)
                return df_erro, buffer.getvalue()

        # Conversões
        df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce")

        df["DT Emissao"] = pd.to_datetime(
            df["DT Emissao"],
            dayfirst=True,
            errors="coerce"
        )

        # Filtrar apenas movimentações válidas
        df = df[
            (df["Quantidade"] != 0) &
            (df["DT Emissao"].notna())
        ]

        # Limpeza produto
        df["Produto"] = (
            df["Produto"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )

        # Mostrar apenas dados relevantes
        df_resultado = df[[
            "Filial",
            "Produto",
            "Quantidade",
            "DT Emissao"
        ]].copy()

        # Ordenar por data mais recente
        df_resultado = df_resultado.sort_values(
            by="DT Emissao",
            ascending=False
        )

        buffer = io.BytesIO()
        df_resultado.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_resultado, buffer.getvalue()
