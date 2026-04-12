import streamlit as st
import pandas as pd
import io
import re
import hashlib
import zipfile
from datetime import datetime

import httpx
import pdfplumber
from supabase import create_client, Client, ClientOptions

from utils.navbar import render_navbar

st.set_page_config(page_title="Configurador", layout="wide")
render_navbar("Configurador")

# -------------------------------------------------
# CSS
# -------------------------------------------------

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"]  { display: none !important; }

.kpi-card {
    background-color: #005562;
    border: 2px solid #EC6E21;
    padding: 16px;
    border-radius: 10px;
    text-align: center;
}
.kpi-title { font-size: 13px; color: #ccc; }
.kpi-value { font-size: 22px; font-weight: 700; color: white; }

.step-box {
    background: rgba(0,85,98,0.3);
    border: 1px solid rgba(236,110,33,0.3);
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.step-title {
    font-size: 16px;
    font-weight: 700;
    color: #EC6E21;
    margin-bottom: 8px;
}
.step-desc {
    font-size: 13px;
    color: rgba(255,255,255,0.6);
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

st.title("⚙️ Configurador")
st.markdown("Importação de fechamentos mensais para o Supabase.")
st.markdown("---")

# -------------------------------------------------
# CONEXÃO SUPABASE
# -------------------------------------------------

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase() -> Client:
    http_client = httpx.Client(verify=False, timeout=120.0)
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=ClientOptions(httpx_client=http_client))


def upsert_chunks(supabase, tabela, records, on_conflict="row_hash", chunk_size=1000):
    import time
    seen = {r[on_conflict]: r for r in records}
    records = list(seen.values())
    total = 0
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i+chunk_size]
        for tentativa in range(1, 4):
            try:
                supabase.table(tabela).upsert(chunk, on_conflict=on_conflict).execute()
                break
            except Exception:
                if tentativa == 3:
                    raise
                time.sleep(5)
        total += len(chunk)
    return total


def recriar_caches(supabase):
    """Recria resumo_movimentacoes_cache e motor_obsoletos_cache no Supabase."""

    sql_drop_resumo = "DROP TABLE IF EXISTS resumo_movimentacoes_cache;"
    sql_drop_motor  = "DROP TABLE IF EXISTS motor_obsoletos_cache;"

    sql_resumo = """
    CREATE TABLE resumo_movimentacoes_cache AS
    WITH fechamentos AS (
        SELECT DISTINCT data_fechamento
        FROM estoque_fechamentos
        WHERE data_fechamento >= '2025-12-31'
    ),
    mov AS (
        SELECT e.empresa_filial || '|' || m.produto AS id_unico,
               m.dt_emissao::date AS dt
        FROM movimentos m
        JOIN estoque_empresas e ON e.id = (m.empresa || ' ' || m.filial)
        WHERE m.dt_emissao IS NOT NULL
    ),
    es AS (
        SELECT e.empresa_filial || '|' || es.produto AS id_unico,
               es.tipo,
               es.digitacao::date AS dt
        FROM entradas_saidas es
        JOIN estoque_empresas e ON e.id = (es.empresa || ' ' || es.filial)
        WHERE es.estoque = 'S' AND es.digitacao IS NOT NULL
    ),
    combinado AS (
        SELECT f.data_fechamento, mov.id_unico,
               MAX(CASE WHEN mov.dt <= f.data_fechamento THEN mov.dt END) AS ult_mov,
               NULL::date AS ult_entrada, NULL::date AS ult_saida
        FROM fechamentos f CROSS JOIN mov
        GROUP BY f.data_fechamento, mov.id_unico
        UNION ALL
        SELECT f.data_fechamento, es.id_unico, NULL::date,
               MAX(CASE WHEN es.tipo='ENTRADA' AND es.dt<=f.data_fechamento THEN es.dt END),
               MAX(CASE WHEN es.tipo='SAIDA'   AND es.dt<=f.data_fechamento THEN es.dt END)
        FROM fechamentos f CROSS JOIN es
        GROUP BY f.data_fechamento, es.id_unico
    ),
    agrupado AS (
        SELECT data_fechamento, id_unico,
               MAX(ult_mov) AS ult_mov, MAX(ult_entrada) AS ult_entrada,
               MAX(ult_saida) AS ult_saida,
               GREATEST(MAX(ult_mov), MAX(ult_entrada), MAX(ult_saida)) AS ult_movimentacao
        FROM combinado GROUP BY data_fechamento, id_unico
    )
    SELECT data_fechamento, id_unico, ult_mov, ult_entrada, ult_saida, ult_movimentacao,
           CASE
               WHEN ult_movimentacao IS NULL       THEN NULL
               WHEN ult_movimentacao = ult_saida   THEN 'Ult_Saida'
               WHEN ult_movimentacao = ult_entrada THEN 'Ult_Entrada'
               WHEN ult_movimentacao = ult_mov     THEN 'Ult_Mov'
           END AS origem_mov
    FROM agrupado;
    CREATE INDEX ON resumo_movimentacoes_cache (data_fechamento, id_unico);
    """

    sql_motor = """
    CREATE TABLE motor_obsoletos_cache AS
    SELECT ef.data_fechamento,
           CASE
               WHEN ef.empresa ILIKE '%TOOLS%'      THEN 'Tools'
               WHEN ef.empresa ILIKE '%MAQUINAS%'   THEN 'Maquinas'
               WHEN ef.empresa ILIKE '%ALLSERVICE%' THEN 'Service'
               WHEN ef.empresa ILIKE '%ROBOTICA%'   THEN 'Robotica'
               ELSE ef.empresa
           END || ' / ' || INITCAP(ef.filial) AS empresa_filial,
           ef.tipo_de_estoque, ef.conta, ef.produto, ef.descricao,
           ef.unid, ef.saldo_atual, ef.vlr_unit, ef.custo_total,
           rc.ult_movimentacao, rc.origem_mov
    FROM estoque_fechamentos ef
    LEFT JOIN resumo_movimentacoes_cache rc
        ON rc.data_fechamento = ef.data_fechamento
        AND rc.id_unico = (
            CASE
                WHEN ef.empresa ILIKE '%TOOLS%'      THEN 'Tools'
                WHEN ef.empresa ILIKE '%MAQUINAS%'   THEN 'Maquinas'
                WHEN ef.empresa ILIKE '%ALLSERVICE%' THEN 'Service'
                WHEN ef.empresa ILIKE '%ROBOTICA%'   THEN 'Robotica'
                ELSE ef.empresa
            END || ' / ' || INITCAP(ef.filial) || '|' || ef.produto
        )
    WHERE ef.data_fechamento >= '2025-12-31';
    CREATE INDEX ON motor_obsoletos_cache (data_fechamento);
    """

    sb = supabase
    sb.rpc("exec_sql", {"query": sql_drop_resumo}).execute()
    sb.rpc("exec_sql", {"query": sql_drop_motor}).execute()
    sb.rpc("exec_sql", {"query": sql_resumo}).execute()
    sb.rpc("exec_sql", {"query": sql_motor}).execute()


# -------------------------------------------------
# EXTRAÇÃO PDF/TXT
# -------------------------------------------------

POSSIVEIS_TIPOS_ESTOQUE = [
    "EM ESTOQUE", "EM PROCESSO", "EM FABRICACAO",
    "EM TERCEIROS", "DE TERCEIROS"
]

PALAVRAS_FILIAL = [
    "MATRIZ", "FILIAL", "JARAGUA", "CAXIAS", "JUNDIAI",
    "JOINVILLE", "SAO PAULO", "CURITIBA"
]

def separar_empresa_filial(texto_firma):
    texto = texto_firma.replace('|', '').strip()
    partes = re.split(r'\s{2,}', texto)
    if len(partes) >= 2:
        return partes[0].strip(), partes[1].strip()
    for palavra in PALAVRAS_FILIAL:
        match = re.search(r'\b(' + palavra + r'\s*\w*)\s*$', texto, re.IGNORECASE)
        if match:
            filial = match.group(1).strip()
            empresa = texto[:match.start()].strip()
            return empresa, filial
    return texto, ""


def extrair_pdf(arquivo_bytes):
    all_data = []
    data_fechamento = None
    empresa = None
    filial = None
    tipo_estoque = None
    conta = None
    ignorar_resumo = False

    with pdfplumber.open(io.BytesIO(arquivo_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)
            if not text:
                continue
            for line in text.split('\n'):
                if "R E S U M O" in line:
                    ignorar_resumo = True
                    continue
                if "FIRMA:" in line:
                    ignorar_resumo = False
                if ignorar_resumo:
                    continue

                if "FIRMA:" in line:
                    conteudo = line.split(':', 1)[1]
                    empresa, filial = separar_empresa_filial(conteudo)

                elif "ESTOQUES EXISTENTES EM:" in line:
                    data_str = line.split("EM:", 1)[1].replace('|', '').strip()
                    data_fechamento = data_str

                elif '*' in line:
                    for tipo in POSSIVEIS_TIPOS_ESTOQUE:
                        if tipo in line:
                            tipo_estoque = tipo
                            break
                    match_conta = re.search(r'\*\*\*\s*([\w\s&/]+?)\s*\*\*\*', line)
                    if match_conta:
                        conta = match_conta.group(1).strip()

                elif line.strip().startswith('|') and "D I S C R I M I N A" not in line:
                    partes = [p.strip() for p in line.split('|')]
                    partes = [p for p in partes if p != '']
                    if len(partes) < 5:
                        continue
                    try:
                        descricao_completa = partes[1] if len(partes) > 1 else ""
                        match_cod = re.match(r'^([\d.]+)\s*-\s*(.*)', descricao_completa)
                        if not match_cod:
                            continue
                        codigo, descricao = match_cod.groups()
                        unid    = partes[2] if len(partes) > 2 else ""
                        qtd_str = partes[3] if len(partes) > 3 else "0"
                        vlr_str = partes[4] if len(partes) > 4 else "0"
                        quantidade  = float(qtd_str.replace('.', '').replace(',', '.'))
                        vlr_unit    = float(vlr_str.replace('.', '').replace(',', '.'))
                        valor_total = float(partes[5].replace('.', '').replace(',', '.')) if len(partes) > 5 and partes[5] else quantidade * vlr_unit
                        all_data.append({
                            "Data Fechamento": data_fechamento,
                            "Empresa":         empresa,
                            "Filial":          filial,
                            "Tipo de Estoque": tipo_estoque,
                            "Conta":           conta,
                            "Código":          codigo.strip(),
                            "Descrição":       descricao.strip(),
                            "Unid":            unid,
                            "Quantidade":      quantidade,
                            "Vlr Unit":        vlr_unit,
                            "Valor Total":     valor_total,
                        })
                    except (ValueError, IndexError):
                        continue

    return pd.DataFrame(all_data)


def df_para_supabase(df):
    """Converte DataFrame extraído para formato do Supabase."""
    records = []
    for _, row in df.iterrows():
        data_raw = str(row.get("Data Fechamento", "")).strip()
        try:
            data_iso = pd.to_datetime(data_raw, dayfirst=True).strftime("%Y-%m-%d")
        except Exception:
            data_iso = None

        produto = str(row.get("Código", "")).strip().replace(".0", "")
        empresa = str(row.get("Empresa", "")).strip()
        filial  = str(row.get("Filial",  "")).strip()

        row_hash = hashlib.sha256(
            f"{data_iso}|{empresa}|{filial}|{produto}".encode()
        ).hexdigest()

        records.append({
            "row_hash":        row_hash,
            "data_fechamento": data_iso,
            "empresa":         empresa,
            "filial":          filial,
            "tipo_de_estoque": str(row.get("Tipo de Estoque", "")).strip() or None,
            "conta":           str(row.get("Conta", "")).strip() or None,
            "produto":         produto,
            "descricao":       str(row.get("Descrição", "")).strip() or None,
            "unid":            str(row.get("Unid", "")).strip() or None,
            "saldo_atual":     row.get("Quantidade"),
            "vlr_unit":        row.get("Vlr Unit"),
            "custo_total":     row.get("Valor Total"),
        })
    return records


# -------------------------------------------------
# PROCESSAMENTO ZIP (entradas/saidas + movimentos)
# -------------------------------------------------

def parse_br_number(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def clean_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s if s else None


EMPRESA_MAP = {"01": "Tools", "03": "Maquinas", "05": "Robotica", "07": "Service"}

def parse_empresa(filename):
    name = filename.split("/")[-1]
    return EMPRESA_MAP.get(name[:2], name.replace(".xlsx", ""))


def processar_zip(supabase, zip_bytes, progress_callback=None):
    import time
    total_es = 0
    total_mov = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:

        # --- Entradas/Saídas ---
        arqs_es = [n for n in zf.namelist() if "01_Entradas_Saidas" in n and n.endswith(".xlsx")]
        for arquivo in arqs_es:
            empresa = parse_empresa(arquivo)
            if progress_callback:
                progress_callback(f"📥 Entradas/Saídas — {empresa}...")

            with zf.open(arquivo) as f:
                raw_bytes = io.BytesIO(f.read())

            xl = pd.ExcelFile(raw_bytes)
            abas = [a for a in xl.sheet_names if a.upper() in ("ENTRADA", "SAIDA")]

            for aba in abas:
                tipo = aba.upper()
                df_str = pd.read_excel(xl, sheet_name=aba, dtype=str)
                df_str.columns = [c.strip().upper() for c in df_str.columns]
                raw_bytes.seek(0)
                df_raw = pd.read_excel(io.BytesIO(raw_bytes.getvalue()))
                df_raw.columns = [c.strip().upper() for c in df_raw.columns]

                if "DIGITACAO" in df_raw.columns:
                    df_str["DIGITACAO"] = pd.to_datetime(
                        df_raw["DIGITACAO"], dayfirst=True, errors="coerce"
                    ).dt.strftime("%Y-%m-%d")

                df = df_str.dropna(how="all")
                if "ESTOQUE" in df.columns:
                    df = df[df["ESTOQUE"].str.strip().str.upper() == "S"]
                if "QUANTIDADE" in df.columns:
                    df["QUANTIDADE"] = df["QUANTIDADE"].apply(parse_br_number)
                    df = df[df["QUANTIDADE"].notna() & (df["QUANTIDADE"] != 0)]

                records = []
                for _, row in df.iterrows():
                    doc          = clean_text(row.get("DOCUMENTO"))
                    produto      = clean_text(row.get("PRODUTO"))
                    digitacao    = clean_text(row.get("DIGITACAO"))
                    centro_custo = clean_text(row.get("CENTRO CUSTO"))
                    row_hash     = hashlib.sha256(
                        f"{empresa}|{tipo}|{doc}|{produto}|{digitacao}|{centro_custo}".encode()
                    ).hexdigest()

                    records.append({
                        "row_hash": row_hash, "empresa": empresa, "tipo": tipo,
                        "filial": clean_text(row.get("FILIAL")),
                        "tipo_doc": clean_text(row.get("TIPO DOC")),
                        "documento": doc, "serie": clean_text(row.get("SERIE")),
                        "nota_devolucao": clean_text(row.get("NOTA DEVOLUCAO")),
                        "digitacao": digitacao,
                        "tipo_produto": clean_text(row.get("TIPO PRODUTO")),
                        "produto": produto, "descricao": clean_text(row.get("DESCRICAO")),
                        "tes": clean_text(row.get("TES")), "cfop": clean_text(row.get("CFOP")),
                        "centro_custo": centro_custo, "grupo": clean_text(row.get("GRUPO")),
                        "desc_grupo": clean_text(row.get("DESC GRUPO")),
                        "forn_cliente": clean_text(row.get("FORN/CLIENTE")),
                        "loja_forn_cliente": clean_text(row.get("LOJA FORN/CLIENTE")),
                        "razao_social": clean_text(row.get("RAZAO SOCIAL")),
                        "estado": clean_text(row.get("ESTADO")),
                        "quantidade": parse_br_number(row.get("QUANTIDADE")),
                        "preco_unitario": parse_br_number(row.get("PRECO UNITARIO")),
                        "total": parse_br_number(row.get("TOTAL")),
                        "custo_moeda1": parse_br_number(row.get("CUSTO MOEDA1")),
                        "valor_ipi": parse_br_number(row.get("VALOR IPI")),
                        "valor_icms": parse_br_number(row.get("VALOR ICMS")),
                        "valor_cofins": parse_br_number(row.get("VALOR COFINS")),
                        "valor_pis": parse_br_number(row.get("VALOR PIS")),
                        "duplicata": clean_text(row.get("DUPLICATA")),
                        "estoque": clean_text(row.get("ESTOQUE")),
                        "poder_terceiros": clean_text(row.get("PODER TERCEIROS")),
                    })

                total_es += upsert_chunks(supabase, "entradas_saidas", records)

        # --- Movimentos ---
        arqs_mov = [n for n in zf.namelist() if "02_Movimento" in n and n.endswith(".xlsx")]
        for arquivo in arqs_mov:
            empresa = parse_empresa(arquivo)
            if progress_callback:
                progress_callback(f"🔄 Movimentos — {empresa}...")

            with zf.open(arquivo) as f:
                raw_bytes = io.BytesIO(f.read())

            df_str = pd.read_excel(raw_bytes, dtype=str)
            df_str.columns = [c.strip().upper() for c in df_str.columns]
            raw_bytes.seek(0)
            df_raw = pd.read_excel(raw_bytes)
            df_raw.columns = [c.strip().upper() for c in df_raw.columns]

            if "DT EMISSAO" in df_raw.columns:
                df_str["DT EMISSAO"] = pd.to_datetime(
                    df_raw["DT EMISSAO"], dayfirst=True, errors="coerce"
                ).dt.strftime("%Y-%m-%d")

            df = df_str.dropna(how="all")
            records = []
            for _, row in df.iterrows():
                doc        = clean_text(row.get("DOCUMENTO"))
                produto    = clean_text(row.get("PRODUTO"))
                tp_mov     = clean_text(row.get("TP MOVIMENTO"))
                dt_emissao = clean_text(row.get("DT EMISSAO"))
                quantidade = parse_br_number(row.get("QUANTIDADE"))
                tipo_rede  = clean_text(row.get("TIPO RE/DE"))
                row_hash   = hashlib.sha256(
                    f"{empresa}|{doc}|{produto}|{tp_mov}|{dt_emissao}|{quantidade}|{tipo_rede}".encode()
                ).hexdigest()

                records.append({
                    "row_hash": row_hash, "empresa": empresa,
                    "filial": clean_text(row.get("FILIAL")),
                    "tp_movimento": tp_mov, "produto": produto,
                    "descricao": clean_text(row.get("DESCR. PROD")),
                    "quantidade": quantidade, "tipo_rede": tipo_rede,
                    "documento": doc, "dt_emissao": dt_emissao,
                })

            total_mov += upsert_chunks(supabase, "movimentos", records)

    return total_es, total_mov


# -------------------------------------------------
# INTERFACE
# -------------------------------------------------

supabase = get_supabase()

# ── BOTÃO 1: Fechamento ──────────────────────────────────────

st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-title">📄 Passo 1 — Importar Fechamento de Estoque</div>', unsafe_allow_html=True)
st.markdown('<div class="step-desc">Faça upload do PDF ou TXT gerado pelo Protheus. Os dados serão extraídos e inseridos em estoque_fechamentos.</div>', unsafe_allow_html=True)

arquivo_fechamento = st.file_uploader(
    "Selecione o arquivo de fechamento",
    type=["pdf", "txt"],
    key="upload_fechamento"
)

if arquivo_fechamento:
    st.info(f"Arquivo selecionado: **{arquivo_fechamento.name}**")

    if st.button("📥 Importar Fechamento", type="primary", key="btn_fechamento"):
        with st.spinner("Extraindo dados do arquivo..."):
            try:
                arquivo_bytes = arquivo_fechamento.read()

                if arquivo_fechamento.name.lower().endswith(".pdf"):
                    df_extraido = extrair_pdf(arquivo_bytes)
                else:
                    st.error("Suporte a TXT em desenvolvimento. Use o PDF por enquanto.")
                    st.stop()

                if df_extraido.empty:
                    st.error("Nenhum dado encontrado no arquivo.")
                    st.stop()

                st.success(f"✅ {len(df_extraido)} registros extraídos.")

                # Preview
                with st.expander("Ver prévia dos dados extraídos"):
                    st.dataframe(df_extraido.head(20), use_container_width=True)

            except Exception as e:
                st.error("Erro ao extrair o arquivo.")
                st.exception(e)
                st.stop()

        with st.spinner("Inserindo no Supabase..."):
            try:
                records = df_para_supabase(df_extraido)
                total = upsert_chunks(supabase, "estoque_fechamentos", records, on_conflict="row_hash")
                st.success(f"✅ {total} registros inseridos em estoque_fechamentos.")
                st.cache_data.clear()
            except Exception as e:
                st.error("Erro ao inserir no Supabase.")
                st.exception(e)
                st.stop()

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── BOTÃO 2: Movimentações ───────────────────────────────────

st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-title">📦 Passo 2 — Importar Movimentações</div>', unsafe_allow_html=True)
st.markdown('<div class="step-desc">Faça upload do Dados_Movimento.zip. Entradas/Saídas e Movimentos serão atualizados no Supabase.</div>', unsafe_allow_html=True)

arquivo_zip = st.file_uploader(
    "Selecione o Dados_Movimento.zip",
    type=["zip"],
    key="upload_zip"
)

if arquivo_zip:
    st.info(f"Arquivo selecionado: **{arquivo_zip.name}** ({arquivo_zip.size / 1024 / 1024:.1f} MB)")

    if st.button("📥 Importar Movimentações", type="primary", key="btn_zip"):
        status_box = st.empty()
        try:
            zip_bytes = arquivo_zip.read()
            log_msgs = []

            def atualizar_status(msg):
                log_msgs.append(msg)
                status_box.info("\n\n".join(log_msgs))

            atualizar_status("⏳ Iniciando processamento...")
            total_es, total_mov = processar_zip(supabase, zip_bytes, atualizar_status)
            atualizar_status(f"✅ Entradas/Saídas: {total_es} registros")
            atualizar_status(f"✅ Movimentos: {total_mov} registros")
            st.success("ZIP processado com sucesso!")
            st.cache_data.clear()

        except Exception as e:
            st.error("Erro ao processar o ZIP.")
            st.exception(e)
            st.stop()

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ── BOTÃO 3: Recriar Caches ──────────────────────────────────

st.markdown('<div class="step-box">', unsafe_allow_html=True)
st.markdown('<div class="step-title">🔄 Passo 3 — Atualizar Dashboards</div>', unsafe_allow_html=True)
st.markdown('<div class="step-desc">Após importar o fechamento e as movimentações, recrie os caches para atualizar os dashboards. Este processo pode levar alguns minutos.</div>', unsafe_allow_html=True)

st.warning("⚠️ Execute este passo somente após concluir os Passos 1 e 2.")

if st.button("🔄 Recriar Caches e Atualizar Dashboards", type="primary", key="btn_cache"):
    with st.spinner("Recriando caches no Supabase... Aguarde, isso pode levar alguns minutos."):
        try:
            recriar_caches(supabase)
            st.success("✅ Caches recriados! Os dashboards já refletem os novos dados.")
            st.cache_data.clear()
        except Exception as e:
            st.error("Erro ao recriar caches.")
            st.exception(e)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    '<p style="color:rgba(255,255,255,0.3);font-size:12px;text-align:center">'
    'Siga os passos em ordem: Fechamento → Movimentações → Atualizar Dashboards'
    '</p>',
    unsafe_allow_html=True
)
