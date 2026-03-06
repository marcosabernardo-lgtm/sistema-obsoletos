import streamlit as st
import pandas as pd
from io import BytesIO


# ---------------------------------------------------------
# EXPORTAÇÃO PARA EXCEL
# ---------------------------------------------------------
def dataframe_para_excel(df: pd.DataFrame) -> bytes:
    """
    Converte DataFrame em arquivo Excel em memória.
    Retorna bytes para download.
    """

    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="dados")

        workbook = writer.book
        worksheet = writer.sheets["dados"]

        # Ajusta largura das colunas automaticamente
        for i, col in enumerate(df.columns):
            largura = max(
                df[col].astype(str).map(len).max(),
                len(col)
            ) + 2

            worksheet.set_column(i, i, largura)

    return output.getvalue()


# ---------------------------------------------------------
# BOTÃO PADRÃO DE DOWNLOAD
# ---------------------------------------------------------
def botao_download_excel(df: pd.DataFrame, nome_arquivo: str):
    """
    Cria botão padrão para download de Excel.
    """

    excel = dataframe_para_excel(df)

    st.download_button(
        label="📥 Exportar para Excel",
        data=excel,
        file_name=nome_arquivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------------------------------------------------------
# LEITURA CACHEADA DO PARQUET
# ---------------------------------------------------------
@st.cache_data
def carregar_parquet(caminho: str) -> pd.DataFrame:
    """
    Carrega parquet com cache do Streamlit.
    """

    df = pd.read_parquet(caminho)

    return df


# ---------------------------------------------------------
# FORMATAR VALOR MONETÁRIO
# ---------------------------------------------------------
def formatar_moeda(valor: float) -> str:
    """
    Formata valor em padrão brasileiro.
    """

    if pd.isna(valor):
        return "R$ 0,00"

    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")