import os
import pandas as pd

from motor.motor_estoque import executar_motor_estoque
from storage.base_estoque_lake import salvar_fechamento_estoque

PASTA_DADOS = "dados_estoque"

if not os.path.exists(PASTA_DADOS):
    raise Exception("Pasta dados_estoque não encontrada")

arquivos = [f for f in os.listdir(PASTA_DADOS) if f.endswith(".zip")]

if len(arquivos) == 0:
    raise Exception("Nenhum ZIP encontrado em dados_estoque")

for arquivo in sorted(arquivos):

    caminho = os.path.join(PASTA_DADOS, arquivo)

    print("Processando:", arquivo)

    df_final, _ = executar_motor_estoque(caminho)

    salvar_fechamento_estoque(df_final)

    print("Salvo:", arquivo)

print("Processamento concluído.")
