print("### MOTOR NOVO CARREGADO ###")
import pandas as pd
import zipfile
import io


def executar_motor(uploaded_file):

    with zipfile.ZipFile(uploaded_file) as z:

        # =========================
        # 1️⃣ LER TODOS CSV DA PASTA 04_Movimento
        # =========================

        arquivos_mov = [
            f for f in z.namelist()
            if "04_Movimento/" in f and f.lower().endswith(".csv")
        ]

        if not arquivos_mov:
            raise Exception("Nenhum CSV encontrado na pasta 04_Movimento.")

        lista_mov = []

        for nome_arquivo in arquivos_mov:

            with z.open(nome_arquivo) as arq:
                df_mov = pd.read_csv(
                    io.TextIOWrapper(arq, encoding="cp1252"),
                    sep=",",
                    skiprows=2,      # pula SD3 e linha vazia
                    dtype=str,       # preserva zeros
                    engine="python"
                )

            # Remove coluna vazia (vírgula final)
            df_mov = df_mov.dropna(axis=1, how="all")

            df_mov["ARQUIVO_ORIGEM"] = nome_arquivo.split("/")[-1]

            lista_mov.append(df_mov)

        df_mov_total = pd.concat(lista_mov, ignore_index=True)

        # =========================
        # 2️⃣ FILTRAR APENAS ROBOTICA
        # =========================

        df_mov_total = df_mov_total[
            df_mov_total["ARQUIVO_ORIGEM"].str.contains("Robotica", case=False)
        ]

        # =========================
        # 3️⃣ PADRONIZAR CAMPOS
        # =========================

        # Produto preservando zeros
        df_mov_total["Codigo"] = (
            df_mov_total["Produto"]
            .astype(str)
            .str.strip()
        )

        # Quantidade numérica
        df_mov_total["Qtd"] = pd.to_numeric(
            df_mov_total["Quantidade"],
            errors="coerce"
        )

        # Data
        df_mov_total["Dt_Mov"] = pd.to_datetime(
            df_mov_total["DT Emissao"],
            errors="coerce",
            dayfirst=True
        )

        # Empresa fixa Robotica
        df_mov_total["Empresa"] = "Robotica"

        df_mov_total["Filial"] = (
            df_mov_total["Filial"]
            .astype(str)
            .str.strip()
            .str.title()
        )

        df_mov_total["Empresa / Filial"] = (
            df_mov_total["Empresa"] + " / " + df_mov_total["Filial"]
        )

        # Descrição (se existir no CSV)
        if "Descricao" in df_mov_total.columns:
            df_mov_total["Descricao"] = df_mov_total["Descricao"]
        elif "Descrição" in df_mov_total.columns:
            df_mov_total["Descricao"] = df_mov_total["Descrição"]
        else:
            df_mov_total["Descricao"] = None

        # =========================
        # 4️⃣ COLUNAS FINAIS
        # =========================

        df_final = df_mov_total[
            [
                "Empresa / Filial",
                "Codigo",
                "Descricao",
                "Qtd",
                "Dt_Mov"
            ]
        ].copy()

        # Remove linhas sem data válida
        df_final = df_final[df_final["Dt_Mov"].notna()]

        # =========================
        # 5️⃣ EXPORTAR
        # =========================

        buffer = io.BytesIO()
        df_final.to_excel(buffer, index=False)
        buffer.seek(0)

        return df_final, buffer.getvalue()
