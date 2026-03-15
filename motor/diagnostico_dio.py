"""
Diagnóstico motor_dio — rastreia um produto específico
Uso: python diagnostico_dio.py
"""

import pandas as pd
import zipfile
import io
import os

PASTA_ZIPS = "dados_obsoleto"   # ajuste se necessário
PRODUTO    = "111082"
EMPRESA    = "Maquinas"         # parte do nome da empresa

DATA_FECHAMENTO  = pd.Timestamp("2026-02-28")
DATA_INICIO      = DATA_FECHAMENTO - pd.DateOffset(months=12)  # 2025-02-28

print(f"\n{'='*60}")
print(f"DIAGNÓSTICO — Produto: {PRODUTO}")
print(f"Janela: {DATA_INICIO.date()} → {DATA_FECHAMENTO.date()}")
print(f"{'='*60}\n")

zips = sorted([
    os.path.join(PASTA_ZIPS, f)
    for f in os.listdir(PASTA_ZIPS)
    if f.lower().endswith(".zip")
])

print(f"ZIPs encontrados: {[os.path.basename(z) for z in zips]}\n")

for zip_path in zips:
    print(f"\n{'─'*50}")
    print(f"ZIP: {os.path.basename(zip_path)}")
    print(f"{'─'*50}")

    with zipfile.ZipFile(zip_path, "r") as z:
        todos = z.namelist()

        # ── EMPRESAS ──────────────────────────────────
        arq_emp = next((n for n in todos if "05_Empresas" in n and n.endswith(".xlsx")), None)
        if arq_emp:
            with z.open(arq_emp) as f:
                df_emp = pd.read_excel(f, dtype=str, engine="openpyxl")
            df_emp["Mesclado"] = df_emp["Mesclado"].str.strip()
            df_emp["Empresa / Filial"] = df_emp["Empresa / Filial"].str.strip()
        else:
            df_emp = pd.DataFrame(columns=["Mesclado","Empresa / Filial"])
            print("  ⚠️  05_Empresas não encontrado")

        # ── 01_ENTRADAS_SAIDAS ─────────────────────────
        arqs_es = [n for n in todos if "01_Entradas_Saidas/" in n and n.lower().endswith(".xlsx")]
        print(f"\n  [01_Entradas_Saidas] {len(arqs_es)} arquivo(s)")

        for nome in arqs_es:
            nome_upper = nome.upper()
            if EMPRESA.upper() not in nome_upper:
                continue

            with z.open(nome) as arq:
                arquivo_bytes = io.BytesIO(arq.read())

            xl = pd.ExcelFile(arquivo_bytes, engine="openpyxl")
            print(f"    Arquivo: {nome}")
            print(f"    Abas: {xl.sheet_names}")

            for aba in ["SAIDA", "ENTRADA"]:
                if aba not in xl.sheet_names:
                    continue

                df = pd.read_excel(xl, sheet_name=aba, skiprows=1, dtype=str, engine="openpyxl")
                df.columns = df.columns.str.strip().str.upper()

                print(f"\n    === Aba {aba} ===")
                print(f"    Colunas: {list(df.columns)}")

                if "ESTOQUE" in df.columns:
                    df_s = df[df["ESTOQUE"] == "S"]
                else:
                    df_s = df.copy()

                # Filtra produto
                if "PRODUTO" not in df_s.columns:
                    print("    ⚠️  Coluna PRODUTO não encontrada")
                    continue

                df_prod = df_s[df_s["PRODUTO"].astype(str).str.strip() == PRODUTO]

                if df_prod.empty:
                    print(f"    Produto {PRODUTO} não encontrado nesta aba")
                    continue

                print(f"    ✅ Produto encontrado — {len(df_prod)} linha(s)")
                print(df_prod.to_string(index=False))

                # Identifica coluna de qtd
                col_qtd = next(
                    (c for c in df_prod.columns if "QUANT" in c or "QTD" in c or "QT " in c),
                    None
                )
                print(f"\n    Coluna de quantidade detectada: {col_qtd}")
                if col_qtd:
                    print(f"    Valores de qtd: {df_prod[col_qtd].tolist()}")
                    qtds = pd.to_numeric(df_prod[col_qtd], errors="coerce")
                    print(f"    Qtds numéricas: {qtds.tolist()}")
                    print(f"    Soma: {qtds.sum()}")

        # ── 04_MOVIMENTO ───────────────────────────────
        arqs_mov = [n for n in todos if "04_Movimento/" in n and n.lower().endswith(".xlsx")]
        print(f"\n  [04_Movimento] {len(arqs_mov)} arquivo(s)")

        for nome in arqs_mov:
            nome_upper = nome.upper()
            if EMPRESA.upper() not in nome_upper:
                continue

            with z.open(nome) as arq:
                arquivo_bytes = io.BytesIO(arq.read())

            df = pd.read_excel(arquivo_bytes, dtype=str, engine="openpyxl")
            df.columns = df.columns.str.strip().str.upper()

            print(f"\n    Arquivo: {nome}")
            print(f"    Colunas: {list(df.columns)}")

            if "PRODUTO" not in df.columns:
                print("    ⚠️  Coluna PRODUTO não encontrada")
                continue

            df_prod = df[df["PRODUTO"].astype(str).str.strip() == PRODUTO]

            if df_prod.empty:
                print(f"    Produto {PRODUTO} não encontrado em 04_Movimento")
                continue

            print(f"    ✅ Produto encontrado — {len(df_prod)} linha(s)")
            print(df_prod.to_string(index=False))

            col_qtd = next(
                (c for c in df_prod.columns if "QUANT" in c or "QTD" in c or "QT " in c),
                None
            )
            print(f"\n    Coluna de quantidade detectada: {col_qtd}")
            if col_qtd:
                qtds = pd.to_numeric(df_prod[col_qtd], errors="coerce")
                print(f"    Qtds numéricas: {qtds.tolist()}")
                print(f"    Soma: {qtds.sum()}")

print(f"\n{'='*60}")
print("FIM DO DIAGNÓSTICO")
print(f"{'='*60}\n")