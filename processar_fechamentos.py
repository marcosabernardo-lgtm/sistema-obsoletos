import os
import pandas as pd

from motor.motor_obsoletos import executar_motor
from storage.base_obsoletos_lake import salvar_fechamento_obsoletos

PASTA_DADOS = "dados_obsoleto"

if not os.path.exists(PASTA_DADOS):
    raise Exception("Pasta dados_obsoleto não encontrada")

arquivos = [f for f in os.listdir(PASTA_DADOS) if f.endswith(".zip")]

if len(arquivos) == 0:
    raise Exception("Nenhum ZIP encontrado em dados_obsoleto")

for arquivo in sorted(arquivos):

    caminho = os.path.join(PASTA_DADOS, arquivo)

    print("Processando:", arquivo)

    df_final, _ = executar_motor(caminho)

    salvar_fechamento_obsoletos(df_final)

print("Processamento concluído.")