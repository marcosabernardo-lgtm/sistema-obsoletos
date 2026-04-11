"""
SISTEMA-OBSOLETOS — Migração Supabase
Script: carga_historica.py

Importa dados do Protheus para o Supabase.
Aceita tanto um arquivo ZIP quanto uma pasta com os XLSXs extraídos:
  - 01_Entradas_Saidas/{empresa}.xlsx  → public.entradas_saidas
  - 02_Movimento/{empresa}.xlsx        → public.movimentos

Estratégia: upsert por row_hash (SHA256) — idempotente, seguro para recargas.
Carga em chunks de 1000 linhas para respeitar limites da API do Supabase.

Uso com ZIP:
    python carga_historica.py --origem "Z:\...\Dados_Movimento.zip"

Uso com pasta:
    python carga_historica.py --origem "Z:\...\Dados_Movimento"

Filtros opcionais:
    python carga_historica.py --origem "..." --tabela entradas_saidas
    python carga_historica.py --origem "..." --tabela movimentos
    python carga_historica.py --origem "..." --empresa Service
"""

import argparse
import hashlib
import io
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
from supabase import create_client, Client, ClientOptions

# ── Configuração ──────────────────────────────────────────────────────────────

# Lê credenciais do .streamlit/secrets.toml
import tomllib, pathlib
_secrets_path = pathlib.Path(__file__).parent / ".streamlit" / "secrets.toml"
with open(_secrets_path, "rb") as _f:
    _secrets = tomllib.load(_f)

SUPABASE_URL = _secrets["SUPABASE_URL"]
SUPABASE_KEY = _secrets["SUPABASE_KEY"]

CHUNK_SIZE = 1000  # linhas por upsert (limite seguro da API Supabase)

# Mapeamento: prefixo do arquivo → nome da empresa
EMPRESA_MAP = {
    "01": "Tools",
    "03": "Maquinas",
    "05": "Robotica",
    "07": "Service",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_hash(*values) -> str:
    """SHA256 de valores concatenados — chave natural para upsert."""
    raw = "|".join(str(v) if v is not None else "" for v in values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_empresa(filename: str) -> str:
    """Extrai nome da empresa a partir do nome do arquivo Excel."""
    name = filename.split("/")[-1]  # pega só o nome, sem pasta
    prefix = name[:2]
    return EMPRESA_MAP.get(prefix, name.replace(".xlsx", ""))


def parse_br_number(value) -> float | None:
    """Converte número em formato BR (1.234,56) para float."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    # Remove pontos de milhar e substitui vírgula decimal por ponto
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_br_date(value) -> str | None:
    """Converte data para ISO (YYYY-MM-DD). Aceita datetime, serial Excel e string BR."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    # Já é datetime/Timestamp
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if not s or s.lower() == "nan" or s.lower() == "none":
        return None
    # Tenta formatos de string
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Tenta via pandas (mais flexível)
    try:
        ts = pd.to_datetime(s, dayfirst=True)
        if pd.notna(ts):
            return ts.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def clean_text(value) -> str | None:
    """Limpa e normaliza campo texto."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s if s else None


def upsert_chunks(supabase: Client, tabela: str, records: list[dict], empresa: str) -> int:
    """Envia registros em chunks via upsert. Retorna total inserido/atualizado."""
    import time

    # Remove linhas 100% idênticas (mesmo hash) antes de enviar
    seen = {}
    for r in records:
        seen[r["row_hash"]] = r
    records = list(seen.values())

    total = 0
    for i in range(0, len(records), CHUNK_SIZE):
        chunk = records[i: i + CHUNK_SIZE]
        for tentativa in range(1, 4):
            try:
                supabase.table(tabela).upsert(chunk, on_conflict="row_hash").execute()
                break
            except Exception as e:
                if tentativa == 3:
                    raise
                print(f"\n   ⚠️  Timeout no chunk {i}–{i+CHUNK_SIZE}, tentativa {tentativa}/3. Aguardando 5s...")
                time.sleep(5)
        total += len(chunk)
        print(f"    [{empresa}] {total}/{len(records)} linhas enviadas...", end="\r")
    print()
    return total


# ── Processamento: entradas_saidas ───────────────────────────────────────────

def process_entradas_saidas(
    supabase: Client,
    zf: zipfile.ZipFile,
    empresa_filter: str | None = None,
) -> None:
    """Lê todos os XLSXs de 01_Entradas_Saidas e carrega no Supabase."""

    arquivos = [
        n for n in zf.namelist()
        if "01_Entradas_Saidas" in n and n.endswith(".xlsx")
    ]

    if not arquivos:
        print("⚠️  Nenhum arquivo encontrado em 01_Entradas_Saidas/")
        return

    for arquivo in arquivos:
        empresa = parse_empresa(arquivo)

        if empresa_filter and empresa.lower() != empresa_filter.lower():
            continue

        print(f"\n📂 Processando: {arquivo}")
        print(f"   Empresa: {empresa}")

        with zf.open(arquivo) as f:
            xl = pd.ExcelFile(io.BytesIO(f.read()))

        abas_disponiveis = [a for a in xl.sheet_names if a.upper() in ("ENTRADA", "SAIDA")]
        if not abas_disponiveis:
            print(f"   ⚠️  Nenhuma aba ENTRADA/SAIDA encontrada. Abas: {xl.sheet_names}")
            continue

        for aba in abas_disponiveis:
            tipo = aba.upper()  # 'ENTRADA' ou 'SAIDA'
            print(f"   📋 Aba: {tipo}")

            df = pd.read_excel(xl, sheet_name=aba, dtype=str)
            df.columns = [c.strip().upper() for c in df.columns]

            # Remove linhas completamente vazias
            df = df.dropna(how="all")

            print(f"   → {len(df)} linhas lidas (total bruto)")

            # Filtros: apenas linhas que movimentaram estoque
            if "ESTOQUE" in df.columns:
                df = df[df["ESTOQUE"].str.strip().str.upper() == "S"]
            if "QUANTIDADE" in df.columns:
                df["QUANTIDADE"] = df["QUANTIDADE"].apply(parse_br_number)
                df = df[df["QUANTIDADE"].notna() & (df["QUANTIDADE"] != 0)]

            print(f"   → {len(df)} linhas após filtro (ESTOQUE=S e QUANTIDADE<>0)")

            records = []
            for _, row in df.iterrows():
                doc      = clean_text(row.get("DOCUMENTO"))
                produto  = clean_text(row.get("PRODUTO"))
                digitacao = parse_br_date(row.get("DIGITACAO"))

                centro_custo = clean_text(row.get("CENTRO CUSTO"))
                row_hash = make_hash(empresa, tipo, doc, produto, digitacao, centro_custo)

                records.append({
                    "row_hash":          row_hash,
                    "empresa":           empresa,
                    "tipo":              tipo,
                    "filial":            clean_text(row.get("FILIAL")),
                    "tipo_doc":          clean_text(row.get("TIPO DOC")),
                    "documento":         doc,
                    "serie":             clean_text(row.get("SERIE")),
                    "nota_devolucao":    clean_text(row.get("NOTA DEVOLUCAO")),
                    "digitacao":         digitacao,
                    "tipo_produto":      clean_text(row.get("TIPO PRODUTO")),
                    "produto":           produto,
                    "descricao":         clean_text(row.get("DESCRICAO")),
                    "tes":               clean_text(row.get("TES")),
                    "cfop":              clean_text(row.get("CFOP")),
                    "centro_custo":      clean_text(row.get("CENTRO CUSTO")),
                    "grupo":             clean_text(row.get("GRUPO")),
                    "desc_grupo":        clean_text(row.get("DESC GRUPO")),
                    "forn_cliente":      clean_text(row.get("FORN/CLIENTE")),
                    "loja_forn_cliente": clean_text(row.get("LOJA FORN/CLIENTE")),
                    "razao_social":      clean_text(row.get("RAZAO SOCIAL")),
                    "estado":            clean_text(row.get("ESTADO")),
                    "quantidade":        parse_br_number(row.get("QUANTIDADE")),
                    "preco_unitario":    parse_br_number(row.get("PRECO UNITARIO")),
                    "total":             parse_br_number(row.get("TOTAL")),
                    "custo_moeda1":      parse_br_number(row.get("CUSTO MOEDA1")),
                    "valor_ipi":         parse_br_number(row.get("VALOR IPI")),
                    "valor_icms":        parse_br_number(row.get("VALOR ICMS")),
                    "valor_cofins":      parse_br_number(row.get("VALOR COFINS")),
                    "valor_pis":         parse_br_number(row.get("VALOR PIS")),
                    "duplicata":         clean_text(row.get("DUPLICATA")),
                    "estoque":           clean_text(row.get("ESTOQUE")),
                    "poder_terceiros":   clean_text(row.get("PODER TERCEIROS")),
                })

            total = upsert_chunks(supabase, "entradas_saidas", records, f"{empresa}/{tipo}")
            print(f"   ✅ {total} registros upsertados — {empresa}/{tipo}")


# ── Processamento: movimentos ─────────────────────────────────────────────────

def process_movimentos(
    supabase: Client,
    zf: zipfile.ZipFile,
    empresa_filter: str | None = None,
) -> None:
    """Lê todos os XLSXs de 02_Movimento e carrega no Supabase."""

    arquivos = [
        n for n in zf.namelist()
        if "02_Movimento" in n and n.endswith(".xlsx")
    ]

    if not arquivos:
        print("⚠️  Nenhum arquivo encontrado em 02_Movimento/")
        return

    for arquivo in arquivos:
        empresa = parse_empresa(arquivo)

        if empresa_filter and empresa.lower() != empresa_filter.lower():
            continue

        print(f"\n📂 Processando: {arquivo}")
        print(f"   Empresa: {empresa}")

        with zf.open(arquivo) as f:
            raw = io.BytesIO(f.read())

        # Lê tudo como string mas preserva a data original
        df = pd.read_excel(raw, dtype=str)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.dropna(how="all")

        # Converte data com dayfirst=True para formato BR
        if "DT EMISSAO" in df.columns:
            df["DT EMISSAO"] = pd.to_datetime(
                df["DT EMISSAO"], dayfirst=True, errors="coerce"
            )

        print(f"   → {len(df)} linhas lidas")

        records = []
        for _, row in df.iterrows():
            doc        = clean_text(row.get("DOCUMENTO"))
            produto    = clean_text(row.get("PRODUTO"))
            tp_mov     = clean_text(row.get("TP MOVIMENTO"))
            dt_emissao_raw = row.get("DT EMISSAO")
            if pd.isna(dt_emissao_raw) if not isinstance(dt_emissao_raw, str) else False:
                dt_emissao = None
            elif isinstance(dt_emissao_raw, (pd.Timestamp, datetime)):
                dt_emissao = dt_emissao_raw.strftime("%Y-%m-%d")
            else:
                dt_emissao = parse_br_date(dt_emissao_raw)
            quantidade = parse_br_number(row.get("QUANTIDADE"))
            tipo_rede  = clean_text(row.get("TIPO RE/DE"))

            row_hash = make_hash(empresa, doc, produto, tp_mov, dt_emissao, quantidade, tipo_rede)

            records.append({
                "row_hash":    row_hash,
                "empresa":     empresa,
                "filial":      clean_text(row.get("FILIAL")),
                "tp_movimento": tp_mov,
                "produto":     produto,
                "descricao":   clean_text(row.get("DESCR. PROD")),
                "quantidade":  quantidade,
                "tipo_rede":   tipo_rede,
                "documento":   doc,
                "dt_emissao":  dt_emissao,
            })

        total = upsert_chunks(supabase, "movimentos", records, empresa)
        print(f"   ✅ {total} registros upsertados — {empresa}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Carga histórica Protheus → Supabase (entradas_saidas + movimentos)"
    )
    parser.add_argument(
        "--zip", required=True,
        help="Caminho para o arquivo Dados_Movimento.zip"
    )
    parser.add_argument(
        "--tabela", choices=["entradas_saidas", "movimentos"],
        default=None,
        help="Processar apenas uma tabela (padrão: ambas)"
    )
    parser.add_argument(
        "--empresa",
        default=None,
        help="Filtrar por empresa: Tools | Maquinas | Robotica | Service"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  SISTEMA-OBSOLETOS — Carga Histórica Protheus → Supabase")
    print("=" * 60)
    print(f"  ZIP      : {args.zip}")
    print(f"  Tabela   : {args.tabela or 'ambas'}")
    print(f"  Empresa  : {args.empresa or 'todas'}")
    print(f"  Chunk    : {CHUNK_SIZE} linhas")
    print("=" * 60)

    # Conecta ao Supabase (verify=False para redes corporativas com SSL inspection)
    print("\n🔌 Conectando ao Supabase...")
    http_client = httpx.Client(verify=False, timeout=60.0)
    supabase: Client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(httpx_client=http_client)
    )
    print("   ✅ Conectado!")

    # Abre o ZIP (aceita com ou sem extensão .zip)
    print(f"\n📦 Abrindo: {args.zip}")
    try:
        zf = zipfile.ZipFile(args.zip, "r")
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {args.zip}")
        sys.exit(1)
    except zipfile.BadZipFile:
        print(f"❌ Não é um arquivo ZIP válido: {args.zip}")
        sys.exit(1)
    except IsADirectoryError:
        print(f"❌ Isso é uma pasta, não um arquivo ZIP: {args.zip}")
        sys.exit(1)

    inicio = datetime.now()

    with zf:
        if args.tabela in (None, "entradas_saidas"):
            print("\n" + "─" * 60)
            print("  📥 ENTRADAS E SAÍDAS")
            print("─" * 60)
            process_entradas_saidas(supabase, zf, args.empresa)

        if args.tabela in (None, "movimentos"):
            print("\n" + "─" * 60)
            print("  🔄 MOVIMENTOS")
            print("─" * 60)
            process_movimentos(supabase, zf, args.empresa)

    duracao = datetime.now() - inicio
    print("\n" + "=" * 60)
    print(f"  ✅ Carga concluída em {duracao}")
    print("=" * 60)


if __name__ == "__main__":
    main()